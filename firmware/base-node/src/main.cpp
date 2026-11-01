/*
 * main.cpp — SOMA v3 base node firmware (ESP32-S3-DevKitC-1), carrier v1.3.
 *
 *   host (Orange Pi) <--- USB serial, framed link ---> ESP32-S3
 *       |-- CAN 1 Mbps (TWAI) ---> J2/J3 B-G431B-ESC1 cycloidal joints
 *       |-- UART1 1 Mbps half-duplex ---> J1 STS3250 + J4/J5/J6/GRIP STS3215
 *       |-- IO40 MOTOR_EN ---> relay K1 -> +12V_MOT (switched motor rail)
 *       '-- ESTOP sense IO38 (J9 NC loop) + host-link watchdog
 *
 * MOTOR_EN (firmware/shared/motor_en.c, unit-tested on host):
 *   two-phase arm. Phase 1: an explicit host ARM_MOTOR while the host
 *   link is alive, the estop loop released and no bus-off closes K1 —
 *   the ESCs are dead until the rail is live, so heartbeats can't be
 *   a precondition. Phase 2: every configured ESC must heartbeat
 *   inside esc_boot_window_ms (else drop, MEDR_ESC_BOOT_TIMEOUT).
 *   Once armed: any estop / watchdog / CAN bus-off / ESC fault /
 *   lost heartbeat drops it instantly + NMT stop. Re-arm needs the
 *   explicit host command again.
 */
#include <Arduino.h>
#include "pins.h"
#include "config.h"
#include "arm_state.h"
#include "can_bus.h"
#include "feetech_bus.h"
#include "host_link.h"

arm_state_t g_arm;

static const uint8_t can_ids[CAN_N_JOINTS] = CAN_JOINT_NODES;
static const uint8_t ft_ids[FT_N_SERVOS]  = FT_SERVO_IDS;

static uint32_t last_joint_ms = 0;
static uint32_t last_state_ms = 0;
static uint32_t last_ping_ms  = 0;
static uint16_t ft_telem_idx  = 0;
static uint8_t  estop_debounce = 0;
static bool     estop_pin_active = false;
static uint8_t  motor_pin_level  = 0;

/* pending SDO responses to relay to the host */
static bool     sdo_resp_ready = false;
static uint8_t  sdo_resp_val[4];
static uint8_t  sdo_resp_node = 0;
uint8_t         g_pending_sdo_node = 0;
uint16_t        g_pending_sdo_addr = 0;

void arm_clamp_q(float q[ARM_N_CHAN]) {
    for (int i = 0; i < ARM_N_CHAN; i++) {
        if (q[i] < Q_MIN[i]) q[i] = Q_MIN[i];
        if (q[i] > Q_MAX[i]) q[i] = Q_MAX[i];
    }
}

static const char *medr_str(uint8_t r) {
    switch (r) {
    case MEDR_ESTOP:            return "estop";
    case MEDR_HOST_TIMEOUT:     return "host-timeout";
    case MEDR_CAN_BUS_OFF:      return "can-bus-off";
    case MEDR_ESC_FAULT:        return "esc-fault";
    case MEDR_ESC_LOST:         return "esc-lost";
    case MEDR_ESC_BOOT_TIMEOUT: return "esc-boot-timeout";
    default:                    return "estop";
    }
}

void arm_estop(uint8_t medr_reason) {
    /* cut the motor rail immediately (the state machine would do the
     * same on its next tick — mirror its fields so the two stay in
     * lock-step) */
    if (g_arm.motor.motor_en) {
        g_arm.motor.motor_en = 0;
        g_arm.motor.fault_latched = 1;
        g_arm.motor.drop_reason = medr_reason;
        g_arm.motor.phase = MEP_IDLE;
    }
    digitalWrite(PIN_MOTOR_EN, LOW);
    motor_pin_level = 0;
    host_link_send_event(LKE_MOTOR_EN_OFF, medr_reason);

    if (medr_reason == MEDR_HOST_TIMEOUT) {
        g_arm.watchdog_tripped = true;
        host_link_send_event(LKE_WD_TRIPPED, 0);
    } else if (medr_reason == MEDR_CAN_BUS_OFF ||
               medr_reason == MEDR_ESC_FAULT ||
               medr_reason == MEDR_ESC_LOST ||
               medr_reason == MEDR_ESC_BOOT_TIMEOUT) {
        host_link_send_event(LKE_CAN_FAULT, medr_reason);
    }

    if (g_arm.estop) return;
    g_arm.estop = true;
    g_arm.armed = false;
    can_estop_broadcast();              /* NMT stop to every drive */
    for (int i = 0; i < FT_N_SERVOS; i++)
        ft_torque_enable(ft_ids[i], false);
    digitalWrite(PIN_LED_STAT, HIGH);
    host_link_send_event(LKE_ESTOP_ASSERTED, 0);
    Serial.printf("ESTOP: %s\n", medr_str(medr_reason));
}

void arm_clear_estop(void) {
    if (!g_arm.estop) return;
    /* refuse to clear while the physical estop loop is still open */
    if (estop_pin_active) return;
    g_arm.estop = false;
    g_arm.watchdog_tripped = false;
    digitalWrite(PIN_LED_STAT, LOW);
    host_link_send_event(LKE_ESTOP_CLEARED, 0);
}

void arm_set_armed(bool on) {
    if (on && (g_arm.estop || !g_arm.motor.motor_en)) return;
    g_arm.armed = on;
    if (on) {
        can_enable_all();
        for (int i = 0; i < FT_N_SERVOS; i++)
            ft_torque_enable(ft_ids[i], true);
    } else {
        can_disable_all();
        for (int i = 0; i < FT_N_SERVOS; i++)
            ft_torque_enable(ft_ids[i], false);
    }
}

static void estop_pin_poll(void) {
    /* NC loop to GND: HIGH = loop open = estop. 3-sample debounce. */
    if (digitalRead(PIN_ESTOP) == HIGH) {
        if (++estop_debounce >= 3) estop_pin_active = true;
    } else {
        estop_debounce = 0;
        estop_pin_active = false;
    }
}

static void joint_update(void) {
    if (g_arm.estop || !g_arm.armed) return;
    /* integrate jog velocities into the commanded setpoint */
    const float dt = 1.0f / JOINT_LOOP_HZ;
    for (int i = 0; i < ARM_N_CHAN; i++) {
        if (g_arm.dq_cmd[i] != 0.0f) {
            g_arm.q_cmd[i] += g_arm.dq_cmd[i] * dt;
            if (g_arm.q_cmd[i] < Q_MIN[i]) { g_arm.q_cmd[i] = Q_MIN[i]; g_arm.dq_cmd[i] = 0; }
            if (g_arm.q_cmd[i] > Q_MAX[i]) { g_arm.q_cmd[i] = Q_MAX[i]; g_arm.dq_cmd[i] = 0; }
        }
    }
    for (int i = 0; i < CAN_N_JOINTS; i++) {
        uint8_t ch = CAN_JOINT_CHAN[i];
        can_send_pdo2(can_ids[i], g_arm.q_cmd[ch], g_arm.dq_cmd[ch]);
        if (g_arm.tau_ff[i] != 0.0f)
            can_send_pdo3(can_ids[i], g_arm.tau_ff[i]);
    }
    for (int i = 0; i < FT_N_SERVOS; i++) {
        uint8_t ch = FT_SERVO_CHAN[i];
        int16_t c = (int16_t)(FT_CENTER
                    + g_arm.q_cmd[ch] * FT_COUNTS_PER_RAD);
        if (c < 0) c = 0;
        if (c > 4095) c = 4095;
        ft_goal(ft_ids[i], (uint16_t)c, FT_CMD_SPEED);
    }
}

static void telemetry_update(void) {
    /* round-robin one servo read per slice to bound bus time */
    ft_read_telemetry(ft_ids[ft_telem_idx], &g_arm.ft[ft_telem_idx]);
    ft_telem_idx = (ft_telem_idx + 1) % FT_N_SERVOS;
}

static void can_ping_update(uint32_t now) {
    /* RPDO1 ping -> TPDO1 echo is the ESC heartbeat the MOTOR_EN state
     * machine requires */
    if (now - last_ping_ms < CAN_PING_PERIOD_MS) return;
    last_ping_ms = now;
    static uint8_t idx = 0;
    can_send_ping(can_ids[idx], 0xA5A50000u | idx);
    idx = (idx + 1) % CAN_N_JOINTS;
}

static uint8_t esc_all_alive(uint32_t now) {
    for (int i = 0; i < CAN_N_JOINTS; i++) {
        if (!g_arm.can[i].online ||
            (now - g_arm.can[i].last_rx_ms) > CAN_ALIVE_MS) return 0;
    }
    return 1;
}

static uint8_t esc_fault_seen(void) {
    for (int i = 0; i < CAN_N_JOINTS; i++)
        if (g_arm.can[i].status & 0x8) return 1;
    return 0;
}

/* one tick of the MOTOR_EN safety state machine */
static void safety_tick(void) {
    uint32_t now = millis();
    motor_en_in_t in;
    memset(&in, 0, sizeof(in));
    in.host_seen       = host_link_seen();
    in.host_alive      = (now - host_link_last_rx_ms()) < HOST_TIMEOUT_MS;
    in.estop_released  = !estop_pin_active && !g_arm.estop;
    in.esc_all_alive   = esc_all_alive(now) && !g_arm.can_bus_off;
    in.esc_fault       = esc_fault_seen();
    in.can_bus_off     = g_arm.can_bus_off;
    in.arm_cmd         = g_arm.motor_arm_req;
    in.now_ms          = now;
    g_arm.motor_arm_req = 0;

    if (motor_en_step(&g_arm.motor, &in)) {
        /* output just fell: NMT stop + full estop latch */
        arm_estop(g_arm.motor.drop_reason);
        return;
    }
    if (g_arm.motor.motor_en != motor_pin_level) {
        motor_pin_level = g_arm.motor.motor_en;
        digitalWrite(PIN_MOTOR_EN, motor_pin_level ? HIGH : LOW);
        host_link_send_event(motor_pin_level ? LKE_MOTOR_EN_ON
                                             : LKE_MOTOR_EN_OFF,
                             g_arm.motor.drop_reason);
    }
}

static void update_online_mask(void) {
    uint32_t now = millis();
    uint8_t mask = 0;
    for (int i = 0; i < CAN_N_JOINTS; i++) {
        if (g_arm.can[i].online && (now - g_arm.can[i].last_rx_ms) < CAN_ALIVE_MS)
            mask |= (1 << i);
        else
            g_arm.can[i].online = 0;
    }
    g_arm.can_ok_mask = mask;
}

void setup() {
    Serial.begin(115200);
    memset(&g_arm, 0, sizeof(g_arm));
    motor_en_init(&g_arm.motor);
    g_arm.motor.esc_boot_window_ms = ESC_BOOT_WINDOW_MS;
    /* safe default pose: zeros keep it sane; we boot disabled anyway */
    for (int i = 0; i < ARM_N_CHAN; i++) g_arm.q_cmd[i] = 0.0f;

    /* MOTOR_EN first: the motor rail must come up LOW and stay there */
    pinMode(PIN_MOTOR_EN, OUTPUT);
    digitalWrite(PIN_MOTOR_EN, LOW);
    pinMode(PIN_ESTOP, INPUT_PULLUP);
    pinMode(PIN_LED_STAT, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_LED_STAT, LOW);
    digitalWrite(PIN_BUZZER, LOW);

    can_bus_init();
    ft_bus_init();
    host_link_init();

    /* push driver-side current caps out of reset */
    for (int i = 0; i < CAN_N_JOINTS; i++)
        can_sdo_write_f32(can_ids[i], SDO_CURRENT_LIMIT_A,
                          PHASE_CURRENT_LIMIT_A[i]);

    host_link_send_event(LKE_BOOT, 0);
    Serial.printf("SOMA base node fw %06lX — CAN@1M J15(IO2/IO1), "
                  "FT@1M IO17/IO11, ESTOP IO38, MOTOR_EN IO40\n",
                  (unsigned long)FW_VERSION);
}

void loop() {
    host_link_poll();
    estop_pin_poll();
    can_bus_poll(g_arm.can, NULL, sdo_resp_val,
                 &sdo_resp_ready, &sdo_resp_node);
    if (sdo_resp_ready) {
        host_link_send_param(0, g_pending_sdo_node ? g_pending_sdo_node
                             : sdo_resp_node, g_pending_sdo_addr,
                             sdo_resp_val);
        sdo_resp_ready = false;
    }
    can_bus_housekeeping(&g_arm.can_bus_off);
    safety_tick();

    uint32_t now = millis();
    can_ping_update(now);
    if (now - last_joint_ms >= (1000 / JOINT_LOOP_HZ)) {
        last_joint_ms = now;
        joint_update();
        update_online_mask();
    }
    /* servo telemetry slice: every 5th joint tick => 20 Hz total */
    static uint8_t telem_div = 0;
    if (++telem_div >= FT_TELEM_DIV) {
        telem_div = 0;
        telemetry_update();
    }
    if (now - last_state_ms >= (1000 / STATE_TX_HZ)) {
        last_state_ms = now;
        host_link_send_state();
    }
}
