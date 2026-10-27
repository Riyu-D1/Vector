/*
 * main.cpp — SOMA v3 base node firmware (ESP32-S3-DevKitC-1).
 *
 *   host (Orange Pi) <--- USB serial, framed link ---> ESP32-S3
 *       |-- CAN 1 Mbps (TWAI) ---> J1..J3 B-G431B-ESC1 cycloidal joints
 *       |-- UART1 1 Mbps half-duplex ---> J4..J6 Feetech STS3215
 *       '-- ESTOP pin (J9, NC loop) + host-link watchdog
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
static uint16_t ft_telem_idx = 0;
static uint8_t  estop_debounce = 0;

/* pending SDO responses to relay to the host */
static bool     sdo_resp_ready = false;
static uint8_t  sdo_resp_val[4];
static uint8_t  sdo_resp_node = 0;
uint8_t         g_pending_sdo_node = 0;
uint16_t        g_pending_sdo_addr = 0;

void arm_clamp_q(float q[6]) {
    for (int i = 0; i < 6; i++) {
        if (q[i] < Q_MIN[i]) q[i] = Q_MIN[i];
        if (q[i] > Q_MAX[i]) q[i] = Q_MAX[i];
    }
    /* table/case guard (cad/arm checks.py c7, generated header):
     * q3 >= ARM_GUARD_A + ARM_GUARD_B*q2 — raise only the elbow, never
     * move the shoulder (that could swing the link into the base). */
    float q3_lo = ARM_GUARD_A + ARM_GUARD_B * q[1];
    if (q[2] < q3_lo) q[2] = q3_lo;
}

void arm_estop(const char *why) {
    if (g_arm.estop) return;
    g_arm.estop = true;
    g_arm.armed = false;
    can_estop_broadcast();
    for (int i = 0; i < FT_N_SERVOS; i++)
        ft_torque_enable(ft_ids[i], false);
    digitalWrite(PIN_LED_STAT, HIGH);
    host_link_send_event(LKE_ESTOP_ASSERTED, 0);
    Serial.printf("ESTOP: %s\n", why);
}

void arm_clear_estop(void) {
    if (!g_arm.estop) return;
    /* refuse to clear while the physical estop loop is still open */
    if (digitalRead(PIN_ESTOP) == HIGH) return;
    g_arm.estop = false;
    g_arm.watchdog_tripped = false;
    digitalWrite(PIN_LED_STAT, LOW);
    host_link_send_event(LKE_ESTOP_CLEARED, 0);
}

void arm_set_armed(bool on) {
    if (on && g_arm.estop) return;
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
        if (++estop_debounce >= 3) arm_estop("pin");
    } else {
        estop_debounce = 0;
    }
}

static void joint_update(void) {
    if (g_arm.estop || !g_arm.armed) return;
    /* integrate jog velocities into the commanded setpoint */
    const float dt = 1.0f / JOINT_LOOP_HZ;
    for (int i = 0; i < 6; i++) {
        if (g_arm.dq_cmd[i] != 0.0f) {
            g_arm.q_cmd[i] += g_arm.dq_cmd[i] * dt;
            if (g_arm.q_cmd[i] < Q_MIN[i]) { g_arm.q_cmd[i] = Q_MIN[i]; g_arm.dq_cmd[i] = 0; }
            if (g_arm.q_cmd[i] > Q_MAX[i]) { g_arm.q_cmd[i] = Q_MAX[i]; g_arm.dq_cmd[i] = 0; }
        }
    }
    /* joint clamps above may leave (q2,q3) past the table guard —
     * arm_clamp_q lifts q3 onto the boundary (and zeros its jog). */
    float q3_lo = ARM_GUARD_A + ARM_GUARD_B * g_arm.q_cmd[1];
    if (g_arm.q_cmd[2] < q3_lo) {
        g_arm.q_cmd[2] = q3_lo;
        if (g_arm.dq_cmd[2] < 0.0f) g_arm.dq_cmd[2] = 0.0f;
    }
    for (int i = 0; i < CAN_N_JOINTS; i++) {
        can_send_pdo2(can_ids[i], g_arm.q_cmd[i], g_arm.dq_cmd[i]);
        if (g_arm.tau_ff[i] != 0.0f)
            can_send_pdo3(can_ids[i], g_arm.tau_ff[i]);
    }
    for (int i = 0; i < FT_N_SERVOS; i++) {
        int16_t c = (int16_t)(FT_CENTER
                    + g_arm.q_cmd[3 + i] * FT_COUNTS_PER_RAD);
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

static void update_online_mask(void) {
    uint32_t now = millis();
    uint8_t mask = 0;
    for (int i = 0; i < CAN_N_JOINTS; i++) {
        if (g_arm.can[i].online && (now - g_arm.can[i].last_rx_ms) < 250)
            mask |= (1 << i);
        else
            g_arm.can[i].online = 0;
    }
    g_arm.can_ok_mask = mask;
}

static void watchdog_poll(void) {
    if (g_arm.estop) return;
    if ((millis() - host_link_last_rx_ms()) > HOST_TIMEOUT_MS) {
        g_arm.watchdog_tripped = true;
        arm_estop("host-timeout");
        host_link_send_event(LKE_WD_TRIPPED, 0);
    }
}

void setup() {
    Serial.begin(115200);
    memset(&g_arm, 0, sizeof(g_arm));
    /* safe default pose: arm folded back on itself (straight up is
     * q2=+90deg — but we boot disabled anyway; zeros keep it sane) */
    for (int i = 0; i < 6; i++) g_arm.q_cmd[i] = 0.0f;

    pinMode(PIN_ESTOP, INPUT_PULLUP);
    pinMode(PIN_LED_STAT, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    digitalWrite(PIN_LED_STAT, LOW);
    digitalWrite(PIN_BUZZER, LOW);

    can_bus_init();
    ft_bus_init();
    host_link_init();

    /* push driver-side current caps and joint soft limits out of
     * reset (generated arm_params_gen.h — same source the host uses;
     * drivers clamp RPDO2 targets to them in user coords) */
    for (int i = 0; i < CAN_N_JOINTS; i++) {
        can_sdo_write_f32(can_ids[i], SDO_CURRENT_LIMIT_A,
                          PHASE_CURRENT_LIMIT_A[i]);
        can_sdo_write_f32(can_ids[i], SDO_POS_LIMIT_LO,
                          ARM_JOINT_MIN_RAD[i]);
        can_sdo_write_f32(can_ids[i], SDO_POS_LIMIT_HI,
                          ARM_JOINT_MAX_RAD[i]);
    }

    host_link_send_event(LKE_BOOT, 0);
    Serial.printf("SOMA base node fw %06lX — CAN@1M J15(IO2/IO1), "
                  "FT@1M IO17/IO11, ESTOP IO38\n", (unsigned long)FW_VERSION);
}

void loop() {
    host_link_poll();
    estop_pin_poll();
    watchdog_poll();
    can_bus_poll(g_arm.can, NULL, sdo_resp_val,
                 &sdo_resp_ready, &sdo_resp_node);
    if (sdo_resp_ready) {
        host_link_send_param(0, g_pending_sdo_node ? g_pending_sdo_node
                             : sdo_resp_node, g_pending_sdo_addr,
                             sdo_resp_val);
        sdo_resp_ready = false;
    }
    can_bus_housekeeping();

    uint32_t now = millis();
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
