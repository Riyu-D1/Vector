#include "can_proto.h"

uint8_t enc_nmt(uint8_t *out, uint8_t cmd, uint8_t target_node) {
    out[0] = cmd; out[1] = target_node;
    return 2;
}

uint8_t enc_rpdo1_ping(uint8_t *out, uint32_t token) {
    put_u32(out, token);
    return 4;
}

uint8_t enc_rpdo2_cmd(uint8_t *out, float pos_rad, float vel_rads) {
    put_f32(out, pos_rad);
    put_f32(out + 4, vel_rads);
    return 8;
}

uint8_t enc_rpdo3_torque(uint8_t *out, float torque_nm) {
    put_f32(out, torque_nm);
    return 4;
}

uint8_t enc_rsdo_write(uint8_t *out, uint16_t addr, const uint8_t val4[4]) {
    out[0] = SDO_CMD_DOWNLOAD;
    put_u16(out + 1, addr);
    memcpy(out + 4, val4, 4);
    return 8;
}

uint8_t enc_rsdo_write_f32(uint8_t *out, uint16_t addr, float v) {
    out[0] = SDO_CMD_DOWNLOAD;
    put_u16(out + 1, addr);
    put_f32(out + 4, v);
    return 8;
}

uint8_t enc_rsdo_write_u32(uint8_t *out, uint16_t addr, uint32_t v) {
    out[0] = SDO_CMD_DOWNLOAD;
    put_u16(out + 1, addr);
    put_u32(out + 4, v);
    return 8;
}

uint8_t enc_rsdo_read(uint8_t *out, uint16_t addr) {
    out[0] = SDO_CMD_UPLOAD;
    put_u16(out + 1, addr);
    memset(out + 3, 0, 5);
    return 8;
}

uint8_t enc_tpdo2_state(uint8_t *out, float pos_rad, float vel_rads) {
    put_f32(out, pos_rad);
    put_f32(out + 4, vel_rads);
    return 8;
}

uint8_t enc_tpdo3_iq(uint8_t *out, float iq_a) {
    put_f32(out, iq_a);
    return 4;
}

uint8_t enc_tsdo_resp(uint8_t *out, const uint8_t val4[4]) {
    memcpy(out, val4, 4);
    return 4;
}

uint8_t enc_emcy(uint8_t *out, uint16_t err_code, uint8_t err_reg) {
    put_u16(out, err_code);
    out[2] = err_reg;
    return 3;
}

int dec_nmt(const uint8_t *d, uint8_t dlc, uint8_t *cmd, uint8_t *target) {
    if (dlc < 2) return -1;
    *cmd = d[0]; *target = d[1];
    return 0;
}

int dec_pdo2(const uint8_t *d, uint8_t dlc, float *pos, float *vel) {
    if (dlc < 8) return -1;
    *pos = get_f32(d); *vel = get_f32(d + 4);
    return 0;
}

int dec_pdo3(const uint8_t *d, uint8_t dlc, float *val) {
    if (dlc < 4) return -1;
    *val = get_f32(d);
    return 0;
}

int dec_rsdo_req(const uint8_t *d, uint8_t dlc, uint8_t *cmd,
                 uint16_t *addr, uint8_t val4[4]) {
    if (dlc < 3) return -1;
    *cmd = d[0];
    *addr = get_u16(d + 1);
    if (*cmd == SDO_CMD_DOWNLOAD) {
        if (dlc < 8) return -1;
        memcpy(val4, d + 4, 4);
    } else {
        memset(val4, 0, 4);
    }
    return 0;
}

int dec_tsdo_resp(const uint8_t *d, uint8_t dlc, uint8_t val4[4]) {
    if (dlc < 4) return -1;
    memcpy(val4, d, 4);
    return 0;
}

int dec_emcy(const uint8_t *d, uint8_t dlc, uint16_t *code, uint8_t *reg) {
    if (dlc < 3) return -1;
    *code = get_u16(d); *reg = d[2];
    return 0;
}
