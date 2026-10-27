#include <Arduino.h>
#include "pins.h"
#include "config.h"
#include "arm_state.h"
#include "can_bus.h"
#include "feetech_bus.h"
#include "host_link.h"

static link_parser_t parser;
static uint8_t seq_tx = 0;
static uint32_t last_rx_ms = 0;

static void send(uint8_t type, const uint8_t *payload, uint8_t len) {
    uint8_t frame[LINK_MAX_FRAME];
    uint16_t n = link_build(frame, ++seq_tx, type, payload, len);
    Serial.write(frame, n);
}

void host_link_init(void) {
    link_parser_init(&parser);
    last_rx_ms = millis();
}

uint32_t host_link_last_rx_ms(void) { return last_rx_ms; }

void host_link_send_state(void) {
    uint8_t p[74];
    /* measured positions: CAN joints from TPDO2, servos counts->rad */
    for (int i = 0; i < 3; i++) {
        lp_put_f32(p + 4 * i, g_arm.can[i].pos);
        lp_put_f32(p + 12 + 4 * i, ft_counts_to_rad(g_arm.ft[i].pos));
        lp_put_f32(p + 24 + 4 * i, g_arm.can[i].vel);
        lp_put_f32(p + 24 + 12 + 4 * i,
                   (float)g_arm.ft[i].speed * (6.283185307f / 4096.0f));
        lp_put_f32(p + 48 + 4 * i, g_arm.can[i].iq);
        lp_put_f32(p + 48 + 12 + 4 * i, (float)g_arm.ft[i].load);
    }
    uint8_t flags = 0;
    if (g_arm.estop) flags |= LKF_ESTOP;
    if (g_arm.watchdog_tripped) flags |= LKF_WATCHDOG;
    if (g_arm.armed) flags |= LKF_ARMED;
    if (g_arm.can_ok_mask) flags |= LKF_CAN_ONLINE;
    p[72] = flags;
    p[73] = g_arm.can_ok_mask;
    send(LK_STATE, p, 74);
}

void host_link_send_event(uint8_t code, uint8_t arg) {
    uint8_t p[2] = { code, arg };
    send(LK_EVENT, p, 2);
}

void host_link_send_param(uint8_t bus, uint8_t node, uint16_t addr,
                          const uint8_t val4[4]) {
    uint8_t p[8];
    p[0] = bus; p[1] = node;
    p[2] = (uint8_t)(addr & 0xFF); p[3] = (uint8_t)(addr >> 8);
    if (val4) memcpy(p + 4, val4, 4);
    send(LK_PARAM, p, 8);
}

static void nack(uint8_t type, uint8_t err) {
    uint8_t p[2] = { type, err };
    send(LK_NACK, p, 2);
}

static void dispatch(uint8_t seq, uint8_t type,
                     const uint8_t *p, uint8_t len) {
    (void)seq;
    switch (type) {
    case LK_SET_JOINT_POS:
        if (len == 24) {
            float q[6];
            for (int i = 0; i < 6; i++) q[i] = lp_get_f32(p + 4 * i);
            arm_clamp_q(q);
            memcpy(g_arm.q_cmd, q, sizeof(q));
        } else nack(type, 1);
        break;
    case LK_SET_JOINT_VEL:
        if (len == 24)
            for (int i = 0; i < 6; i++)
                g_arm.dq_cmd[i] = lp_get_f32(p + 4 * i);
        else nack(type, 1);
        break;
    case LK_SET_TORQUE:
        if (len == 12)
            for (int i = 0; i < 3; i++)
                g_arm.tau_ff[i] = lp_get_f32(p + 4 * i);
        else nack(type, 1);
        break;
    case LK_SET_CURRENT_LIM:
        if (len == 5 && p[0] >= 1 && p[0] <= 3) {
            static const uint8_t ids[CAN_N_JOINTS] = CAN_JOINT_NODES;
            can_sdo_write_f32(ids[p[0] - 1], SDO_CURRENT_LIMIT_A,
                              lp_get_f32(p + 1));
        } else nack(type, 1);
        break;
    case LK_SET_MODE:
        if (len == 2) {
            if (p[1] == NMT_ENABLE) arm_set_armed(true);
            else if (p[1] == NMT_DISABLE) arm_set_armed(false);
            else if (p[1] == NMT_CALIBRATE && p[0] >= 1 && p[0] <= 3) {
                static const uint8_t ids[CAN_N_JOINTS] = CAN_JOINT_NODES;
                can_send_nmt(NMT_CALIBRATE, ids[p[0] - 1]);
            }
        } else nack(type, 1);
        break;
    case LK_ESTOP:
        arm_estop("host");
        break;
    case LK_CLEAR_ESTOP:
        arm_clear_estop();
        break;
    case LK_GET_STATE:
        host_link_send_state();
        break;
    case LK_HEARTBEAT:
        g_arm.heartbeat_count++;
        break;
    case LK_PING: {
        uint8_t pr[5];
        pr[0] = (uint8_t)(FW_VERSION & 0xFF);
        pr[1] = (uint8_t)(FW_VERSION >> 8);
        pr[2] = (uint8_t)(FW_VERSION >> 16);
        pr[3] = (uint8_t)(FW_VERSION >> 24);
        pr[4] = (g_arm.armed ? 0x04 : 0) | (g_arm.estop ? 0x01 : 0);
        send(LK_PONG, pr, 5);
        break;
    }
    case LK_READ_PARAM:
        if (len == 4) {
            uint8_t bus = p[0], node = p[1];
            uint16_t addr = p[2] | ((uint16_t)p[3] << 8);
            if (bus == 0) {             /* CAN SDO read */
                g_pending_sdo_node = node;
                g_pending_sdo_addr = addr;
                can_sdo_read(node, addr);
                /* response relayed from loop() via PARAM frame */
            } else {                    /* feetech read */
                uint8_t vals[16] = {0}, err = 0;
                if (ft_read(node, (uint8_t)(addr & 0xFF), 4, vals, &err))
                    host_link_send_param(bus, node, addr, vals);
                else
                    host_link_send_param(bus, node, addr, NULL);
            }
        } else nack(type, 1);
        break;
    case LK_SET_SERVO_REG:
        if (len >= 3 && len == (uint8_t)(3 + p[2])) {
            if (!ft_write_reg(p[0], p[1], p + 3, p[2])) nack(type, 2);
        } else nack(type, 1);
        break;
    default:
        nack(type, 2);
        break;
    }
}

void host_link_poll(void) {
    while (Serial.available()) {
        uint8_t b = (uint8_t)Serial.read();
        uint8_t type, seq, plen;
        static uint8_t payload[LINK_MAX_PAYLOAD];
        if (link_parser_feed(&parser, b, &type, &seq, payload, &plen)) {
            last_rx_ms = millis();
            dispatch(seq, type, payload, plen);
        }
    }
}
