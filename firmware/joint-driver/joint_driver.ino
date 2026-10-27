/*
 * joint_driver.ino — SOMA v3 joint drive firmware for the ST
 * B-G431B-ESC1 (STM32G431CB), one per cycloidal actuator (J1, J2, J3).
 *
 * SimpleFOC-based re-implementation of the Berkeley Humanoid Lite
 * Recoil-Motor-Controller-BESC protocol (MIT licence — protocol shape
 * and CANopen-style ID layout kept compatible in spirit):
 *   11-bit CAN ID = (function_code << 7) | node_id
 *   RPDO2 0x300+id : fp32 pos + fp32 vel command (output shaft, rad)
 *   TPDO2 0x280+id : fp32 pos + fp32 vel feedback
 *   RPDO3 0x400+id : fp32 feedforward output torque (Nm) / iq cmd in
 *                    torque mode
 *   TPDO3 0x380+id : fp32 measured q-axis current (A)
 *   RSDO  0x600+id : param read/write (see sdo_addr_t in can_proto.h)
 *   TSDO  0x580+id : param read response (4 bytes)
 *   NMT   0x000    : byte0 cmd, byte1 node (0 = broadcast)
 *                    0=DISABLE 1=ENABLE 2=CALIBRATE 0x7F=ESTOP(latched)
 *   EMCY  0x080+id : fault report
 *
 * Hardware (ST UM2516 + NuttX board doc — verified):
 *   6PWM : A_PHASE_UH/UL/VH/VL/WH/WL (PA8,PC13,PA9,PA12,PA10,PB15)
 *   shunt: 0.003 ohm, PGA gain 16 -> sense gain -9.14 (inverting)
 *   CAN  : PA11 RX, PB9 TX, onboard transceiver, PC14 = CAN_TERM(H=on)
 *   AS5600 on I2C1 PB6(SCL)/PB7(SDA) via the J8 sensor connector
 *          — UNVERIFIED: confirm J8 pin order against UM2516 fig/;
 *            alternative pair PB7(SDA)/PB8(SCL) also lands on J8.
 */
#include <SimpleFOC.h>
#include <Wire.h>
#include <EEPROM.h>
extern "C" {
#include "../../shared/can_proto.h"
}
#include "bus_can.h"

/* ------------------------------------------------------------ config */
#define DEVICE_CAN_ID   1           /* set per joint: 1=J1, 2=J2, 3=J3   */
#define CAN_TERM_LAST   true        /* 120R: true only on the last node */
#define POLE_PAIRS      7           /* 5010 = 12N14P -> 7 pp UNVERIFIED  */
#define GEAR_RATIO      15.0f       /* printed cycloidal 15:1           */
#define CURRENT_LIMIT_A 5.0f        /* phase q-axis cap; J1 ships 3.0   */
#define VOLTAGE_LIMIT   8.0f        /* of the 12 V rail                 */
#define VEL_LIMIT_MOTOR 60.0f       /* rad/s motor-side cap             */
#define KT_MOTOR        0.0265f     /* Nm/A estimate for 5010 360KV     */
                                    /* (Kt ~= 60/(2*pi*KV)) UNVERIFIED  */
#define POS_P_GAIN      20.0f       /* angle P gain (SimpleFOC units)   */
#define VEL_FF_GAIN     1.0f

#define FB_HZ           50          /* TPDO2/TPDO3 telemetry rate       */
#define CMD_TIMEOUT_MS  300         /* hold last pos if bus goes quiet  */

/* ------------------------------------------------------------ params */
typedef struct {
    uint32_t magic;          /* 'SOMA' = 0x534F4D41                     */
    uint32_t can_id;
    float    zero_offset;    /* electrical zero (rad) from initFOC      */
    int32_t  direction;      /* +1 CW, -1 CCW                           */
    float    current_limit;
    float    gear_ratio;
    uint32_t calibrated;     /* nonzero once calibrate ran              */
    float    kp, kd;
    float    pos_lo, pos_hi;
} params_t;
static params_t P;

typedef enum { MODE_DISABLED = 0, MODE_POSITION, MODE_VELOCITY,
               MODE_TORQUE } run_mode_t;

static run_mode_t mode = MODE_DISABLED;
static bool   estop = false;
static bool   armed = false;
static float  cmd_pos = 0.0f, cmd_vel_ff = 0.0f;
static float  cmd_iq  = 0.0f;          /* torque-mode q-current setpoint */
static uint32_t last_cmd_ms = 0, last_fb_ms = 0, last_rx_any_ms = 0;

/* ------------------------------------------------------------ motor  */
BLDCMotor motor = BLDCMotor(POLE_PAIRS);
BLDCDriver6PWM driver = BLDCDriver6PWM(A_PHASE_UH, A_PHASE_UL,
                                     A_PHASE_VH, A_PHASE_VL,
                                     A_PHASE_WH, A_PHASE_WL);
LowsideCurrentSense currentSense =
    LowsideCurrentSense(0.003f, -64.0f / 7.0f,   /* shunt, -9.14 gain   */
                        A_OP1_OUT, A_OP2_OUT, A_OP3_OUT);
MagneticSensorI2C sensor = MagneticSensorI2C(AS5600_I2C);

static float motor_iq_a = 0.0f;

/* ------------------------------------------------------------ flash  */
#define EEPROM_ADDR 0
void params_load(void) {
    EEPROM.get(EEPROM_ADDR, P);
    if (P.magic != 0x534F4D41) {
        memset(&P, 0, sizeof(P));
        P.magic         = 0x534F4D41;
        P.can_id        = DEVICE_CAN_ID;
        P.current_limit = CURRENT_LIMIT_A;
        P.gear_ratio    = GEAR_RATIO;
        P.kp            = POS_P_GAIN;
        P.kd            = 0.2f;
        P.pos_lo        = -3.14f;
        P.pos_hi        =  3.14f;
    }
}
void params_save(void) { EEPROM.put(EEPROM_ADDR, P); }

/* ------------------------------------------------------------ helpers */
static float output_pos(void)  { return motor.shaft_angle / P.gear_ratio; }
static float output_vel(void)  { return motor.shaft_velocity / P.gear_ratio; }

static void send_pdo2(void) {
    uint8_t b[8];
    uint8_t n = enc_tpdo2_state(b, output_pos(), output_vel());
    bus_can_send(can_id_make(CAN_FC_TPDO2, P.can_id), b, n);
}
static void send_pdo3(void) {
    uint8_t b[8];
    uint8_t n = enc_tpdo3_iq(b, motor_iq_a);
    bus_can_send(can_id_make(CAN_FC_TPDO3, P.can_id), b, n);
}
static void send_emcy(uint16_t code, uint8_t reg) {
    uint8_t b[8];
    uint8_t n = enc_emcy(b, code, reg);
    bus_can_send(can_id_make(CAN_FC_EMCY, P.can_id), b, n);
}
static void send_tsdo(const uint8_t val4[4]) {
    uint8_t b[8];
    uint8_t n = enc_tsdo_resp(b, val4);
    bus_can_send(can_id_make(CAN_FC_TSDO, P.can_id), b, n);
}

static void set_mode(run_mode_t m) {
    mode = m;
    switch (m) {
    case MODE_DISABLED:
        motor.disable();
        break;
    case MODE_POSITION:
        motor.controller = MotionControlType::angle;
        motor.target = motor.shaft_angle;   /* hold where we are */
        motor.enable();
        break;
    case MODE_VELOCITY:
        motor.controller = MotionControlType::velocity;
        motor.enable();
        break;
    case MODE_TORQUE:
        motor.controller = MotionControlType::torque;
        motor.enable();
        break;
    }
}

static void do_estop(void) {
    estop = true;
    armed = false;
    set_mode(MODE_DISABLED);
}

static void do_enable(void) {
    if (P.calibrated == 0) {
        send_emcy(0x01, 0x10);        /* not calibrated yet */
    }
    estop = false;
    armed = true;
    set_mode(MODE_POSITION);
}

/* ------------------------------------------------------------ calib  */
static void do_calibrate(void) {
    /* rotor must be FREE TO SPIN — encoder direction + electrical zero */
    motor.initFOC();
    P.zero_offset = motor.zero_electric_angle;
    P.direction   = (int32_t)sensor.direction;
    P.calibrated  = 1;
    params_save();
    send_emcy(0x00, 0x00);            /* cal done "all clear" event */
}

/* ------------------------------------------------------------ SDO     */
static void sdo_write(uint16_t addr, const uint8_t val4[4]) {
    switch (addr) {
    case SDO_CURRENT_LIMIT_A:
        P.current_limit = get_f32(val4);
        motor.current_limit = P.current_limit;
        break;
    case SDO_POLE_PAIRS:
        /* pole pairs is a constructor arg — needs reflash; store for
         * record and report in SDO reads */
        break;
    case SDO_GEAR_RATIO:     P.gear_ratio = get_f32(val4); break;
    case SDO_CAN_NODE_ID:    P.can_id = get_u32(val4) & 0x7F; break;
    case SDO_KP:             P.kp = get_f32(val4); motor.P_angle.P = P.kp; break;
    case SDO_KD:             P.kd = get_f32(val4); break;
    case SDO_POS_LIMIT_LO:   P.pos_lo = get_f32(val4); break;
    case SDO_POS_LIMIT_HI:   P.pos_hi = get_f32(val4); break;
    case SDO_CALIBRATE:      if (get_u32(val4)) do_calibrate(); break;
    case SDO_ZERO_HERE:
        if (get_u32(val4)) { motor.target = 0; sensor.offset = 0;
                             cmd_pos = 0;
                             /* rotate frame so current = 0 rad */
                             sensor.full_rotations = 0;
                             sensor.direction = sensor.direction; }
        break;
    case SDO_SAVE_FLASH:
        if (get_u32(val4) == 0x53515645) params_save();
        break;
    default: break;
    }
}

static void sdo_read(uint16_t addr) {
    uint8_t b[4] = {0, 0, 0, 0};
    switch (addr) {
    case SDO_CURRENT_LIMIT_A: put_f32(b, P.current_limit); break;
    case SDO_POLE_PAIRS:      put_u32(b, POLE_PAIRS); break;
    case SDO_GEAR_RATIO:      put_f32(b, P.gear_ratio); break;
    case SDO_ENCODER_OFFSET:  put_f32(b, P.zero_offset); break;
    case SDO_CAN_NODE_ID:     put_u32(b, P.can_id); break;
    case SDO_KP:              put_f32(b, P.kp); break;
    case SDO_KD:              put_f32(b, P.kd); break;
    case SDO_POS_LIMIT_LO:    put_f32(b, P.pos_lo); break;
    case SDO_POS_LIMIT_HI:    put_f32(b, P.pos_hi); break;
    case SDO_TEMPERATURE_C:   put_f32(b, 0.0f); /* TODO: PA5? sensor */
        break;
    case SDO_BUS_VOLTAGE_V: {
        float vbus = analogRead(A_VBUS) * (3.3f / 4096.0f) * 10.4f;
        put_f32(b, vbus);
        break;
    }
    case SDO_FW_VERSION:      put_u32(b, 0x000100); break;
    case SDO_STATUS: {
        uint32_t s = 0;
        if (armed) s |= 0x1;
        if (estop) s |= 0x2;
        if (P.calibrated) s |= 0x4;
        put_u32(b, s);
        break;
    }
    case SDO_VELOCITY_RADS:   put_f32(b, output_vel()); break;
    case SDO_IQ_MEAS_A:       put_f32(b, motor_iq_a); break;
    default: break;
    }
    send_tsdo(b);
}

/* ------------------------------------------------------------ CAN rx  */
static void handle_frame(uint16_t id, const uint8_t *d, uint8_t dlc) {
    uint8_t fc = can_id_fc(id);
    uint8_t node = can_id_node(id);
    last_rx_any_ms = millis();

    if (fc == CAN_FC_NMT) {
        uint8_t cmd, target;
        if (dec_nmt(d, dlc, &cmd, &target) != 0) return;
        if (target != 0 && target != P.can_id) return;  /* not for us */
        switch (cmd) {
        case NMT_DISABLE:   set_mode(MODE_DISABLED); armed = false; break;
        case NMT_ENABLE:    do_enable(); break;
        case NMT_CALIBRATE: do_calibrate(); break;
        case NMT_ESTOP:     do_estop(); break;
        }
        return;
    }
    if (node != P.can_id) return;                     /* addressed msgs */

    switch (fc) {
    case CAN_FC_RPDO1: {                              /* ping -> echo   */
        bus_can_send(can_id_make(CAN_FC_TPDO1, P.can_id), d, dlc);
        break;
    }
    case CAN_FC_RPDO2: {
        float pos, vel;
        if (dec_pdo2(d, dlc, &pos, &vel) != 0) break;
        last_cmd_ms = millis();
        cmd_pos = pos;
        cmd_vel_ff = vel;
        if (armed && !estop) {
            if (mode != MODE_POSITION) set_mode(MODE_POSITION);
            float p = pos;
            if (p < P.pos_lo) p = P.pos_lo;
            if (p > P.pos_hi) p = P.pos_hi;
            motor.target = p * P.gear_ratio;
            motor.feed_forward_velocity = vel * P.gear_ratio * VEL_FF_GAIN;
        }
        break;
    }
    case CAN_FC_RPDO3: {
        float tau;
        if (dec_pdo3(d, dlc, &tau) != 0) break;
        /* output torque Nm -> motor q-current setpoint (torque mode);
         * in position mode it is ignored (documented) */
        cmd_iq = tau / (P.gear_ratio * KT_MOTOR);
        if (armed && !estop && mode == MODE_TORQUE) {
            if (cmd_iq > P.current_limit) cmd_iq = P.current_limit;
            if (cmd_iq < -P.current_limit) cmd_iq = -P.current_limit;
            motor.target = cmd_iq;
        }
        break;
    }
    case CAN_FC_RSDO: {
        uint8_t scmd; uint16_t addr; uint8_t val4[4];
        if (dec_rsdo_req(d, dlc, &scmd, &addr, val4) != 0) break;
        if (scmd == SDO_CMD_DOWNLOAD) sdo_write(addr, val4);
        else if (scmd == SDO_CMD_UPLOAD) sdo_read(addr);
        break;
    }
    default: break;
    }
}

/* ------------------------------------------------------------ arduino */
void setup() {
    params_load();
    if (P.can_id == 0 || P.can_id > 0x7F) P.can_id = DEVICE_CAN_ID;

    bus_can_init(CAN_TERM_LAST);

    /* AS5600 on I2C1 PB6(SCL)/PB7(SDA) at the J8 sensor connector */
    Wire.setSCL(PB6);
    Wire.setSDA(PB7);
    Wire.begin();
    sensor.init(&Wire);
    motor.linkSensor(&sensor);

    driver.voltage_power_supply = 12;
    driver.init();
    motor.linkDriver(&driver);

    currentSense.linkDriver(&driver);
    currentSense.init();
    currentSense.skip_align = true;
    motor.linkCurrentSense(&currentSense);

    motor.voltage_sensor_align = 2;
    motor.voltage_limit = VOLTAGE_LIMIT;
    motor.current_limit = P.current_limit;
    motor.velocity_limit = VEL_LIMIT_MOTOR;
    motor.controller = MotionControlType::angle;
    motor.P_angle.P = P.kp;
    motor.PID_velocity.P = 0.2f;
    motor.PID_velocity.I = 20.0f;
    motor.foc_modulation = FOCModulationType::SpaceVectorPWM;

    motor.init();
    if (P.calibrated) {
        /* skip the rotation alignment: reuse stored electrical zero */
        motor.initFOC(P.zero_offset, (Direction)P.direction);
    }
    /* else: stays un-FOC'd until NMT_CALIBRATE runs on the bench */

    last_cmd_ms = last_fb_ms = last_rx_any_ms = millis();
}

void loop() {
    /* FOC at full rate */
    motor.loopFOC();
    if (armed && !estop && mode != MODE_DISABLED) motor.move();

    /* measure iq for telemetry (cheap, non-blocking path) */
    if (armed) {
        DQCurrent c = currentSense.getFOCCurrents(motor.electrical_angle);
        motor_iq_a = c.q;
    }

    /* CAN RX — drain FIFO */
    uint16_t id; uint8_t d[8]; uint8_t dlc;
    while (bus_can_recv(&id, d, &dlc)) handle_frame(id, d, dlc);

    uint32_t now = millis();

    /* command watchdog: quiet bus -> hold position (never torque-off
     * under load silently — the arm would drop) */
    if (armed && !estop && (now - last_cmd_ms) > CMD_TIMEOUT_MS &&
        mode == MODE_POSITION) {
        motor.target = motor.shaft_angle;   /* freeze where we are */
    }

    /* telemetry */
    if (armed && (now - last_fb_ms) >= (1000 / FB_HZ)) {
        last_fb_ms = now;
        send_pdo2();
        send_pdo3();
    }
}
