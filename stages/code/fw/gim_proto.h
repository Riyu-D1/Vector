/* gim_proto.h — Steadywin GIM CAN protocol codec (pure C, no I/O).
 * Source: cad/vendor/GIM-protocol.pdf. Frame: std ID = motor CAN id, DLC 8,
 * unused bytes 0. Test vectors in software/robot-os/tests/test_gim_proto.py. */
#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

#define GIM_CMD_CFG_WRITE 0x83
#define GIM_CMD_START     0x91
#define GIM_CMD_STOP      0x92
#define GIM_CMD_CURRENT   0x93
#define GIM_CMD_SPEED     0x94
#define GIM_CMD_POSITION  0x95
#define GIM_CMD_ESTOP     0x97
#define GIM_CMD_CLEAR_ERR 0xB3
#define GIM_CFG_CAN_ID    0x12

/* all encoders fill b[0..7] and return 8 */
uint8_t gim_enc_simple(uint8_t b[8], uint8_t cmd);                 /* 0x91 0x92 0x97 0xB3 */
uint8_t gim_enc_position(uint8_t b[8], float rad, uint32_t ms);    /* 0x95, ms u24 */
uint8_t gim_enc_speed(uint8_t b[8], float rad_s, uint32_t ms);     /* 0x94, ms u24 */
uint8_t gim_enc_current(uint8_t b[8], float amps, uint16_t ms);    /* 0x93, ms u16 */
uint8_t gim_enc_cfg_write(uint8_t b[8], uint8_t param, uint32_t v);/* 0x83 */

/* reply decode: b0 cmd echo, b1 error flags [U], b2 temp degC,
 * b3..4 pos u16 LE, b5..7 speed u12 | torque-current u12 (big-endian nibbles) */
float gim_dec_pos(uint16_t u);              /* rad: u*25/65535 - 12.5 */
float gim_dec_speed(uint16_t u12);          /* rad/s: u*130/4095 - 65 */
float gim_dec_torque(uint16_t u12, float ktg); /* N.m: ktg*(u*450/4095 - 225) */
int gim_dec_reply(const uint8_t *b, uint8_t dlc, float ktg,
                  uint8_t *cmd, float *pos, float *vel, float *tq, uint8_t *temp);

#ifdef __cplusplus
}
#endif
