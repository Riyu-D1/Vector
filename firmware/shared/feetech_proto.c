#include "feetech_proto.h"

uint8_t ft_checksum(uint8_t id, uint8_t len, uint8_t inst,
                    const uint8_t *params) {
    uint16_t s = id + len + inst;
    uint8_t i;
    for (i = 0; i + 2 < len; i++) s += params[i];
    return (uint8_t)(~s & 0xFF);
}

uint8_t ft_build(uint8_t *out, uint8_t id, uint8_t inst,
                 const uint8_t *params, uint8_t nparams) {
    uint8_t len = nparams + 2;
    out[0] = FT_HEADER0;
    out[1] = FT_HEADER1;
    out[2] = id;
    out[3] = len;
    out[4] = inst;
    if (nparams) memcpy(out + 5, params, nparams);
    out[5 + nparams] = ft_checksum(id, len, inst, params);
    return nparams + 6;
}

uint8_t ft_build_ping(uint8_t *out, uint8_t id) {
    return ft_build(out, id, FT_INST_PING, NULL, 0);
}

uint8_t ft_build_read(uint8_t *out, uint8_t id, uint8_t addr, uint8_t nbytes) {
    uint8_t p[2] = { addr, nbytes };
    return ft_build(out, id, FT_INST_READ, p, 2);
}

uint8_t ft_build_write(uint8_t *out, uint8_t id, uint8_t addr,
                       const uint8_t *data, uint8_t ndata) {
    uint8_t p[FT_MAX_PARAMS];
    if (ndata + 1 > FT_MAX_PARAMS) return 0;
    p[0] = addr;
    memcpy(p + 1, data, ndata);
    return ft_build(out, id, FT_INST_WRITE, p, ndata + 1);
}

uint8_t ft_build_write_u8(uint8_t *out, uint8_t id, uint8_t addr, uint8_t v) {
    return ft_build_write(out, id, addr, &v, 1);
}

uint8_t ft_build_write_u16(uint8_t *out, uint8_t id, uint8_t addr, uint16_t v) {
    uint8_t d[2] = { (uint8_t)(v & 0xFF), (uint8_t)(v >> 8) };
    return ft_build_write(out, id, addr, d, 2);
}

uint8_t ft_build_goal(uint8_t *out, uint8_t id, uint16_t pos,
                      uint16_t speed) {
    /* addr 42: pos L/H then speed L/H contiguous? No — 44/45 are run-time
     * (SCS) and 46/47 speed. Can't span. Write pos@42, speed@46 as one
     * 6-byte write starting at 42, with 44/45 zeroed = fastest run-time.
     * On STS parts 44/45 are ignored. */
    uint8_t d[6] = {
        (uint8_t)(pos & 0xFF), (uint8_t)(pos >> 8),
        0, 0,
        (uint8_t)(speed & 0xFF), (uint8_t)(speed >> 8)
    };
    return ft_build_write(out, id, FT_REG_GOAL_POS, d, 6);
}

int ft_parse_response(const uint8_t *pkt, uint8_t pkt_len,
                      uint8_t *id, uint8_t *err,
                      const uint8_t **params, uint8_t *params_n) {
    uint8_t len, cksum;
    if (pkt_len < 6) return -1;
    if (pkt[0] != FT_HEADER0 || pkt[1] != FT_HEADER1) return -2;
    len = pkt[3];
    if (len + 4 != pkt_len) return -3;
    cksum = ft_checksum(pkt[2], pkt[3], pkt[4], pkt + 5);
    if (cksum != pkt[pkt_len - 1]) return -4;
    if (id) *id = pkt[2];
    if (err) *err = pkt[4];
    if (params) *params = pkt + 5;
    if (params_n) *params_n = len - 2;
    return 0;
}
