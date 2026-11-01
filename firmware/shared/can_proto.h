/*
 * can_proto.h — SOMA v3 joint CAN protocol (J2-J3 brushless actuators)
 *
 * CANopen-flavoured layout, compatible in spirit with the Berkeley Humanoid
 * Lite Recoil-Motor-Controller-BESC firmware (MIT licence,
 * github.com/T-K-233/Recoil-Motor-Controller-BESC):
 *   11-bit CAN ID = (function_code << 7) | node_id
 *   function code: upper 4 bits, node id: lower 7 bits (1..127, 0 = invalid
 *   except NMT broadcast where the target is carried in byte 1).
 *
 * All multi-byte fields are little-endian. PDO payloads are fp32.
 * Units (output shaft, post-gearbox): position rad, velocity rad/s,
 * torque N·m, current A (phase/q-axis), temperature °C, voltage V.
 *
 * Bus: CAN 2.0B classical, 1 Mbit/s.
 */
#ifndef SOMA_CAN_PROTO_H
#define SOMA_CAN_PROTO_H

#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SOMA_CAN_BITRATE   1000000u

/* function codes (upper 4 bits of the 11-bit ID) */
typedef enum {
    CAN_FC_NMT   = 0x0,   /* 0x000        : node management / e-stop (master) */
    CAN_FC_EMCY  = 0x1,   /* 0x080+node   : emergency / fault report (drive)  */
    CAN_FC_TPDO1 = 0x3,   /* 0x180+node   : presence echo reply (drive)       */
    CAN_FC_RPDO1 = 0x4,   /* 0x200+node   : ping/echo request (master)        */
    CAN_FC_TPDO2 = 0x5,   /* 0x280+node   : state feedback pos/vel (drive)    */
    CAN_FC_RPDO2 = 0x6,   /* 0x300+node   : pos/vel command (master)          */
    CAN_FC_TPDO3 = 0x7,   /* 0x380+node   : measured q-current A (drive)      */
    CAN_FC_RPDO3 = 0x8,   /* 0x400+node   : torque/iq feedforward (master)    */
    CAN_FC_TSDO  = 0xB,   /* 0x580+node   : param read response (drive)       */
    CAN_FC_RSDO  = 0xC    /* 0x600+node   : param read/write request (master) */
} can_fc_t;

/* joint CAN node IDs — J2/J3 only; J1 is an STS3250 servo on bus A */
#define CAN_NODE_J2   2u
#define CAN_NODE_J3   3u
#define CAN_NODE_ALL  0u    /* NMT broadcast target only */

/* NMT commands (byte 0); byte 1 = target node (0 = broadcast) */
typedef enum {
    NMT_DISABLE   = 0x00,   /* torque off, coast                            */
    NMT_ENABLE    = 0x01,   /* enable FOC position/velocity control         */
    NMT_CALIBRATE = 0x02,   /* run encoder-offset calibration               */
    NMT_HOME      = 0x03,   /* drive into the hard stop, set zero, mark
                               * homed (AS5600 is single-turn: required
                               * every boot before torque is allowed)    */
    NMT_ESTOP     = 0x7F    /* latch e-stop: immediate torque-off until
                               * an explicit NMT_ENABLE clears it          */
} nmt_cmd_t;

/* SDO request command byte (byte 0), Berkeley-style */
#define SDO_CMD_DOWNLOAD  0x20u   /* write: bytes 4-7 = value */
#define SDO_CMD_UPLOAD    0x40u   /* read:  response carries 4 bytes 0-3 */

/* SDO parameter addresses (little-endian u16). Type: F = fp32, U = u32. */
typedef enum {
    SDO_CURRENT_LIMIT_A = 0x0001, /* F rw  q-axis phase current cap, A   */
    SDO_POLE_PAIRS      = 0x0002, /* U rw  motor pole pairs (4008 = 7?)  */
    SDO_GEAR_RATIO      = 0x0003, /* F rw  reducer ratio, 40.0           */
    SDO_ENCODER_OFFSET  = 0x0004, /* U rw  AS5600 electrical zero offset */
    SDO_CAN_NODE_ID     = 0x0005, /* U rw  node id (persist to flash)    */
    SDO_KP              = 0x0006, /* F rw  position-loop gain            */
    SDO_KD              = 0x0007, /* F rw  damping gain                  */
    SDO_POS_LIMIT_LO    = 0x0008, /* F rw  output position min, rad      */
    SDO_POS_LIMIT_HI    = 0x0009, /* F rw  output position max, rad      */
    SDO_TEMPERATURE_C   = 0x000A, /* F ro  MCU/mosfet temperature        */
    SDO_BUS_VOLTAGE_V   = 0x000B, /* F ro  supply rail                   */
    SDO_CALIBRATE       = 0x000C, /* U wo  write 1 = run calibration     */
    SDO_ZERO_HERE       = 0x000D, /* U wo  write 1 = set present pos = 0 */
    SDO_FW_VERSION      = 0x000E, /* U ro                                */
    SDO_STATUS          = 0x000F, /* U ro  bit0 enabled b1 estop b2 cal
                                          b3 fault b4 homed               */
    SDO_SAVE_FLASH      = 0x0010, /* U wo  write 0x53515645 = persist    */
    SDO_VELOCITY_RADS   = 0x0011, /* F ro  measured output velocity      */
    SDO_IQ_MEAS_A       = 0x0012, /* F ro  measured q-axis current, A    */
    SDO_HOME_STOP_RAD   = 0x0013, /* F rw  output rad at the hard stop   */
    SDO_HOME_CURRENT_A  = 0x0014, /* F rw  iq used while homing          */
    SDO_HOME_SPEED_RADS = 0x0015  /* F rw  homing crawl, output rad/s    */
} sdo_addr_t;

/* ---- helpers ---------------------------------------------------------- */

static inline uint16_t can_id_make(uint8_t fc, uint8_t node) {
    return (uint16_t)(((fc & 0xF) << 7) | (node & 0x7F));
}
static inline uint8_t can_id_fc(uint16_t id)   { return (id >> 7) & 0xF; }
static inline uint8_t can_id_node(uint16_t id) { return id & 0x7F; }

static inline void put_f32(uint8_t *b, float v) { memcpy(b, &v, 4); }
static inline float get_f32(const uint8_t *b)   { float v; memcpy(&v, b, 4); return v; }
static inline void put_u32(uint8_t *b, uint32_t v) { memcpy(b, &v, 4); }
static inline uint32_t get_u32(const uint8_t *b)   { uint32_t v; memcpy(&v, b, 4); return v; }
static inline void put_u16(uint8_t *b, uint16_t v) { memcpy(b, &v, 2); }
static inline uint16_t get_u16(const uint8_t *b)   { uint16_t v; memcpy(&v, b, 2); return v; }

/* ---- encoders (all return DLC, payload written into out[8]) ----------- */

uint8_t enc_nmt(uint8_t *out, uint8_t cmd, uint8_t target_node);
uint8_t enc_rpdo1_ping(uint8_t *out, uint32_t token);
uint8_t enc_rpdo2_cmd(uint8_t *out, float pos_rad, float vel_rads);
uint8_t enc_rpdo3_torque(uint8_t *out, float torque_nm);
uint8_t enc_rsdo_write(uint8_t *out, uint16_t addr, const uint8_t val4[4]);
uint8_t enc_rsdo_write_f32(uint8_t *out, uint16_t addr, float v);
uint8_t enc_rsdo_write_u32(uint8_t *out, uint16_t addr, uint32_t v);
uint8_t enc_rsdo_read(uint8_t *out, uint16_t addr);
uint8_t enc_tpdo2_state(uint8_t *out, float pos_rad, float vel_rads);
uint8_t enc_tpdo3_iq(uint8_t *out, float iq_a);
uint8_t enc_tsdo_resp(uint8_t *out, const uint8_t val4[4]);
uint8_t enc_emcy(uint8_t *out, uint16_t err_code, uint8_t err_reg);

/* ---- decoders (return 0 on success, -1 on bad length/field) ----------- */

int dec_nmt(const uint8_t *d, uint8_t dlc, uint8_t *cmd, uint8_t *target);
int dec_pdo2(const uint8_t *d, uint8_t dlc, float *pos, float *vel);
int dec_pdo3(const uint8_t *d, uint8_t dlc, float *val);
int dec_rsdo_req(const uint8_t *d, uint8_t dlc, uint8_t *cmd,
                 uint16_t *addr, uint8_t val4[4]);
int dec_tsdo_resp(const uint8_t *d, uint8_t dlc, uint8_t val4[4]);
int dec_emcy(const uint8_t *d, uint8_t dlc, uint16_t *code, uint8_t *reg);

#ifdef __cplusplus
}
#endif

#endif /* SOMA_CAN_PROTO_H */
