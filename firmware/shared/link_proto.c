#include "link_proto.h"

uint16_t link_crc16(const uint8_t *data, uint16_t n) {
    uint16_t crc = 0xFFFF;
    uint16_t i;
    int b;
    for (i = 0; i < n; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (b = 0; b < 8; b++)
            crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : (crc << 1);
    }
    return crc;
}

uint16_t link_build(uint8_t *out, uint8_t seq, uint8_t type,
                    const uint8_t *payload, uint8_t len) {
    uint16_t crc;
    out[0] = LINK_SYNC0;
    out[1] = LINK_SYNC1;
    out[2] = seq;
    out[3] = type;
    out[4] = len;
    if (len) memcpy(out + 5, payload, len);
    crc = link_crc16(out + 2, (uint16_t)(3 + len));
    out[5 + len]     = (uint8_t)(crc & 0xFF);
    out[5 + len + 1] = (uint8_t)(crc >> 8);
    return (uint16_t)(len + 7);
}

void link_parser_init(link_parser_t *p) {
    p->idx = 0; p->synced = 0; p->want = 0;
}

int link_parser_feed(link_parser_t *p, uint8_t byte,
                     uint8_t *type, uint8_t *seq,
                     uint8_t *payload, uint8_t *len) {
    if (!p->synced) {
        /* hunt the 2-byte sync */
        if (p->idx == 0) {
            if (byte == LINK_SYNC0) p->buf[p->idx++] = byte;
        } else { /* idx == 1, have SYNC0 */
            if (byte == LINK_SYNC1) {
                p->buf[p->idx++] = byte;
                p->synced = 1;
                p->want = 0;
            } else {
                p->idx = (byte == LINK_SYNC0) ? 1 : 0;
            }
        }
        return 0;
    }

    /* collecting the frame body */
    if (p->idx < LINK_MAX_FRAME)
        p->buf[p->idx] = byte;
    p->idx++;

    if (p->idx == 5) {
        if (p->buf[4] > LINK_MAX_PAYLOAD) {  /* impossible len: resync */
            p->idx = 0; p->synced = 0;
            return 0;
        }
        p->want = (uint16_t)(5 + p->buf[4] + 2);
    }
    if (p->want && p->idx >= p->want) {
        uint16_t n = p->want;
        uint16_t got_crc = p->buf[n - 2] | ((uint16_t)p->buf[n - 1] << 8);
        uint16_t calc = link_crc16(p->buf + 2, (uint16_t)(n - 4));
        p->idx = 0; p->synced = 0; p->want = 0;
        if (got_crc != calc) return 0;
        *seq  = p->buf[2];
        *type = p->buf[3];
        *len  = p->buf[4];
        if (*len) memcpy(payload, p->buf + 5, *len);
        return 1;
    }
    if (p->idx >= LINK_MAX_FRAME) {  /* overflow guard */
        p->idx = 0; p->synced = 0; p->want = 0;
    }
    return 0;
}
