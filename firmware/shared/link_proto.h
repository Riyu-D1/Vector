/*
 * link_proto.h — framed serial link between Orange Pi (brain) and the
 * ESP32-S3 base node. Runs over the DevKitC USB-UART (or native USB-CDC).
 *
 * Frame:  0xAA 0x55 | seq u8 | type u8 | len u8 | payload[len] | crc16 LE
 * CRC16-CCITT (poly 0x1021, init 0xFFFF, no reflect) over
 * seq..payload inclusive. Max payload 200 bytes.
 *
 * Every valid incoming command frame counts as a host heartbeat; the
 * base-node watchdog torque-disables the arm if no frame arrives within
 * LINK_TIMEOUT_MS (default 500 ms).
 *
 * All floats are fp32 little-endian. Joint order is always J1..J6.
 * Positions in radians at the output shaft (J6 = gripper, 0 = open,
 * ~1.57 = closed — calibrate on bench).
 */
#ifndef SOMA_LINK_PROTO_H
#define SOMA_LINK_PROTO_H

#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

#define LINK_SYNC0     0xAA
#define LINK_SYNC1     0x55
#define LINK_MAX_PAYLOAD 200
#define LINK_MAX_FRAME   (2 + 3 + LINK_MAX_PAYLOAD + 2)
#define LINK_TIMEOUT_MS  500u

typedef enum {
    /* host -> base node */
    LK_SET_JOINT_POS   = 0x01,  /* 6*fp32 rad: stream at 20-50 Hz      */
    LK_SET_JOINT_VEL   = 0x02,  /* 6*fp32 rad/s (jog mode)             */
    LK_SET_TORQUE      = 0x03,  /* 3*fp32 Nm feedforward J1..J3        */
    LK_SET_CURRENT_LIM = 0x05,  /* u8 joint(1..3) + fp32 amps          */
    LK_SET_MODE        = 0x06,  /* u8 joint(0=all CAN) + u8 nmt_cmd    */
    LK_ESTOP           = 0x07,  /* immediate torque-off, latched       */
    LK_CLEAR_ESTOP     = 0x08,  /* re-enable after estop               */
    LK_GET_STATE       = 0x10,  /* request one STATE frame             */
    LK_HEARTBEAT       = 0x12,  /* u32 counter — presence only         */
    LK_PING            = 0x13,  /* -> PONG                             */
    LK_READ_PARAM      = 0x16,  /* u8 bus(0=CAN,1=FT) + u8 node + u16 addr */
    LK_SET_SERVO_REG   = 0x18,  /* u8 id + u8 addr + u8 len + data     */

    /* base node -> host */
    LK_STATE           = 0x11,  /* 6*fp32 pos + 6*fp32 vel + 6*fp32
                                   iq/load + u8 flags + u8 can_ok_mask  */
    LK_PONG            = 0x14,  /* u32 fw_version + u8 status flags    */
    LK_PARAM           = 0x17,  /* echo of READ_PARAM + 4B value       */
    LK_EVENT           = 0x1E,  /* u8 code + u8 arg (estop, fault...)  */
    LK_NACK            = 0x7F   /* u8 offending type + u8 err code     */
} link_type_t;

/* LK_STATE.flags bits */
#define LKF_ESTOP       0x01
#define LKF_WATCHDOG    0x02
#define LKF_ARMED       0x04
#define LKF_CAN_ONLINE  0x08

/* LK_EVENT codes */
#define LKE_ESTOP_ASSERTED  0x01
#define LKE_ESTOP_CLEARED   0x02
#define LKE_WD_TRIPPED      0x03
#define LKE_CAN_FAULT       0x04
#define LKE_BOOT            0x05

uint16_t link_crc16(const uint8_t *data, uint16_t n);

/* build a frame; returns total length in bytes. */
uint16_t link_build(uint8_t *out, uint8_t seq, uint8_t type,
                    const uint8_t *payload, uint8_t len);

/* streaming parser state: feed bytes, get callbacks on complete frames */
typedef struct {
    uint8_t  buf[LINK_MAX_FRAME];
    uint16_t idx;
    uint8_t  synced;      /* 0 = hunting sync, 1 = collecting frame */
    uint16_t want;        /* expected total frame length when known */
} link_parser_t;

void link_parser_init(link_parser_t *p);

/* feed one byte; on complete valid frame returns 1 and fills
 * type/seq/payload/len. returns 0 otherwise (incl. bad crc, discarded). */
int link_parser_feed(link_parser_t *p, uint8_t byte,
                     uint8_t *type, uint8_t *seq,
                     uint8_t *payload, uint8_t *len);

/* ---- payload helpers ------------------------------------------------- */
static inline void lp_put_f32(uint8_t *b, float v) { memcpy(b, &v, 4); }
static inline float lp_get_f32(const uint8_t *b) { float v; memcpy(&v, b, 4); return v; }

#ifdef __cplusplus
}
#endif

#endif /* SOMA_LINK_PROTO_H */
