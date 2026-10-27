/*
 * feetech_proto.h — Feetech STS/SCS serial bus servo packet codec.
 * For J4/J5/J6 STS3215-12V servos on the carrier's TTL half-duplex bus.
 *
 * Packet: 0xFF 0xFF | id | len | inst | params... | checksum
 *   len   = params + 2  (instruction + checksum bytes)
 *   cksum = ~(id + len + inst + params...) & 0xFF
 * Response swaps inst -> error byte.
 *
 * Register table (Feetech SMS_STS / STS3215 memory map):
 *   EPROM: 5 ID, 9-10 MIN_ANGLE, 11-12 MAX_ANGLE
 *   SRAM:  33 MODE, 40 TORQUE_ENABLE, 41 ACC, 42-43 GOAL_POS,
 *          46-47 GOAL_SPEED, 48-49 TORQUE_LIMIT, 55 LOCK,
 *          56-57 PRESENT_POS, 58-59 PRESENT_SPEED, 60-61 PRESENT_LOAD,
 *          62 PRESENT_VOLTAGE (0.1 V), 63 PRESENT_TEMP (°C), 66 MOVING,
 *          69-70 PRESENT_CURRENT (6.5 mA/LSB — UNVERIFIED for STS3215-C047)
 * Counts: 0..4095 = 0..360 deg, 2048 = centre.
 */
#ifndef SOMA_FEETECH_PROTO_H
#define SOMA_FEETECH_PROTO_H

#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

#define FT_HEADER0     0xFF
#define FT_HEADER1     0xFF
#define FT_MAX_PARAMS  16
#define FT_MAX_PACKET  (4 + FT_MAX_PARAMS + 1)

/* instructions */
enum {
    FT_INST_PING       = 0x01,
    FT_INST_READ       = 0x02,
    FT_INST_WRITE      = 0x03,
    FT_INST_REG_WRITE  = 0x04,
    FT_INST_ACTION     = 0x05,
    FT_INST_RESET      = 0x06,
    FT_INST_SYNC_READ  = 0x82,
    FT_INST_SYNC_WRITE = 0x83
};

/* registers used by SOMA (STS3215 memory map) */
enum {
    FT_REG_ID            = 5,
    FT_REG_MODE          = 33,
    FT_REG_TORQUE_EN     = 40,
    FT_REG_ACC           = 41,
    FT_REG_GOAL_POS      = 42,   /* u16 counts */
    FT_REG_GOAL_SPEED    = 46,   /* u16 counts/s */
    FT_REG_TORQUE_LIMIT  = 48,   /* u16, 0..1000 ~ 0..100% */
    FT_REG_LOCK          = 55,
    FT_REG_PRESENT_POS   = 56,   /* u16 */
    FT_REG_PRESENT_SPEED = 58,   /* u16 (b15 = sign) */
    FT_REG_PRESENT_LOAD  = 60,   /* u16 (b10 = direction) */
    FT_REG_PRESENT_VOLT  = 62,   /* u8, 0.1 V */
    FT_REG_PRESENT_TEMP  = 63,   /* u8, deg C */
    FT_REG_MOVING        = 66,
    FT_REG_PRESENT_CUR   = 69    /* u16, ~6.5 mA/LSB (UNVERIFIED) */
};

/* servo IDs on bus A (J4..J6) */
#define FT_ID_J4  4
#define FT_ID_J5  5
#define FT_ID_J6  6
#define FT_ID_BROADCAST  0xFE

/* default bus baud: Feetech factory default; spec marks 1 Mbps UNVERIFIED
 * on this wiring — confirm on bench, adjust feetech_bus.h if wrong. */
#define FT_BAUD_DEFAULT  1000000u

uint8_t ft_checksum(uint8_t id, uint8_t len, uint8_t inst,
                    const uint8_t *params);

/* build a command packet into out; returns total length. */
uint8_t ft_build(uint8_t *out, uint8_t id, uint8_t inst,
                 const uint8_t *params, uint8_t nparams);

uint8_t ft_build_ping(uint8_t *out, uint8_t id);
uint8_t ft_build_read(uint8_t *out, uint8_t id, uint8_t addr, uint8_t nbytes);
uint8_t ft_build_write(uint8_t *out, uint8_t id, uint8_t addr,
                       const uint8_t *data, uint8_t ndata);
uint8_t ft_build_write_u8(uint8_t *out, uint8_t id, uint8_t addr, uint8_t v);
uint8_t ft_build_write_u16(uint8_t *out, uint8_t id, uint8_t addr, uint16_t v);
/* position goal + speed in one write (addr 42 covers 42-43, 44-45 time
 * unused by STS — write pos@42 then speed@46 separately is 2 packets;
 * this packs pos into 42/43 only). */
uint8_t ft_build_goal(uint8_t *out, uint8_t id, uint16_t pos,
                      uint16_t speed);

/* parse a response packet. returns 0 ok, <0 error:
 * -1 too short, -2 bad header, -3 bad length, -4 checksum mismatch.
 * on success *id,*err set, params/params_n filled (may be NULL/0). */
int ft_parse_response(const uint8_t *pkt, uint8_t pkt_len,
                      uint8_t *id, uint8_t *err,
                      const uint8_t **params, uint8_t *params_n);

/* unit conversions: 4096 counts / 2pi rad */
static inline uint16_t ft_rad_to_counts(float rad) {
    int32_t c = 2048 + (int32_t)(rad * (4096.0f / 6.283185307179586f));
    if (c < 0) c = 0; if (c > 4095) c = 4095;
    return (uint16_t)c;
}
static inline float ft_counts_to_rad(uint16_t c) {
    return ((float)c - 2048.0f) * (6.283185307179586f / 4096.0f);
}

#ifdef __cplusplus
}
#endif

#endif /* SOMA_FEETECH_PROTO_H */
