/* gim_proto.c — see gim_proto.h */
#include <string.h>
#include "gim_proto.h"

static void put_f32(uint8_t *p, float v) { memcpy(p, &v, 4); } /* ESP32 + x86 are LE */
static void put_u24(uint8_t *p, uint32_t v) { p[0] = v & 0xFF; p[1] = (v >> 8) & 0xFF; p[2] = (v >> 16) & 0xFF; }

uint8_t gim_enc_simple(uint8_t b[8], uint8_t cmd) { memset(b, 0, 8); b[0] = cmd; return 8; }

uint8_t gim_enc_position(uint8_t b[8], float rad, uint32_t ms) {
    memset(b, 0, 8); b[0] = GIM_CMD_POSITION; put_f32(b + 1, rad); put_u24(b + 5, ms); return 8;
}
uint8_t gim_enc_speed(uint8_t b[8], float rad_s, uint32_t ms) {
    memset(b, 0, 8); b[0] = GIM_CMD_SPEED; put_f32(b + 1, rad_s); put_u24(b + 5, ms); return 8;
}
uint8_t gim_enc_current(uint8_t b[8], float amps, uint16_t ms) {
    memset(b, 0, 8); b[0] = GIM_CMD_CURRENT; put_f32(b + 1, amps);
    b[5] = ms & 0xFF; b[6] = (ms >> 8) & 0xFF; return 8;
}
uint8_t gim_enc_cfg_write(uint8_t b[8], uint8_t param, uint32_t v) {
    memset(b, 0, 8); b[0] = GIM_CMD_CFG_WRITE; b[2] = param;
    b[4] = v & 0xFF; b[5] = (v >> 8) & 0xFF; b[6] = (v >> 16) & 0xFF; b[7] = (v >> 24) & 0xFF;
    return 8;
}

float gim_dec_pos(uint16_t u) { return (float)((double)u * 25.0 / 65535.0 - 12.5); }
float gim_dec_speed(uint16_t u) { return (float)((double)u * 130.0 / 4095.0 - 65.0); }
float gim_dec_torque(uint16_t u, float ktg) { return (float)(ktg * ((double)u * 450.0 / 4095.0 - 225.0)); }

int gim_dec_reply(const uint8_t *b, uint8_t dlc, float ktg,
                  uint8_t *cmd, float *pos, float *vel, float *tq, uint8_t *temp) {
    if (dlc < 8) return -1;
    uint16_t up = (uint16_t)(b[3] | (b[4] << 8));
    uint16_t us = (uint16_t)((b[5] << 4) | (b[6] >> 4));
    uint16_t ut = (uint16_t)(((b[6] & 0x0F) << 8) | b[7]);
    if (cmd) *cmd = b[0];
    if (temp) *temp = b[2];
    if (pos) *pos = gim_dec_pos(up);
    if (vel) *vel = gim_dec_speed(us);
    if (tq) *tq = gim_dec_torque(ut, ktg);
    return 0;
}
