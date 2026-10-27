#include <Arduino.h>
#include <driver/twai.h>
#include "pins.h"
#include "config.h"
#include "can_bus.h"

static bool tx_frame(uint16_t id, const uint8_t *payload, uint8_t dlc) {
    twai_message_t m;
    memset(&m, 0, sizeof(m));
    m.identifier = id;
    m.data_length_code = dlc;
    if (dlc) memcpy(m.data, payload, dlc);
    return twai_transmit(&m, pdMS_TO_TICKS(5)) == ESP_OK;
}

void can_bus_init(void) {
    twai_general_config_t g =
        TWAI_GENERAL_CONFIG_DEFAULT(PIN_CAN_TX, PIN_CAN_RX, TWAI_MODE_NORMAL);
    twai_timing_config_t t = TWAI_TIMING_CONFIG_1MBITS();
    twai_filter_config_t f = TWAI_FILTER_CONFIG_ACCEPT_ALL();
    /* alerts for RX + bus-off recovery */
    g.alerts_enabled = TWAI_ALERT_RX_DATA | TWAI_ALERT_BUS_OFF |
                       TWAI_ALERT_BUS_RECOVERED | TWAI_ALERT_TX_FAILED;
    if (twai_driver_install(&g, &t, &f) == ESP_OK) {
        twai_start();
    }
}

bool can_send_nmt(uint8_t nmt_cmd, uint8_t target_node) {
    uint8_t b[8]; uint8_t n = enc_nmt(b, nmt_cmd, target_node);
    return tx_frame(0x000, b, n);
}

bool can_send_pdo2(uint8_t node, float pos, float vel) {
    uint8_t b[8]; uint8_t n = enc_rpdo2_cmd(b, pos, vel);
    return tx_frame(can_id_make(CAN_FC_RPDO2, node), b, n);
}

bool can_send_pdo3(uint8_t node, float torque_nm) {
    uint8_t b[8]; uint8_t n = enc_rpdo3_torque(b, torque_nm);
    return tx_frame(can_id_make(CAN_FC_RPDO3, node), b, n);
}

bool can_send_ping(uint8_t node, uint32_t token) {
    uint8_t b[8]; uint8_t n = enc_rpdo1_ping(b, token);
    return tx_frame(can_id_make(CAN_FC_RPDO1, node), b, n);
}

bool can_sdo_write_f32(uint8_t node, uint16_t addr, float v) {
    uint8_t b[8]; uint8_t n = enc_rsdo_write_f32(b, addr, v);
    return tx_frame(can_id_make(CAN_FC_RSDO, node), b, n);
}

bool can_sdo_write_u32(uint8_t node, uint16_t addr, uint32_t v) {
    uint8_t b[8]; uint8_t n = enc_rsdo_write_u32(b, addr, v);
    return tx_frame(can_id_make(CAN_FC_RSDO, node), b, n);
}

bool can_sdo_read(uint8_t node, uint16_t addr) {
    uint8_t b[8]; uint8_t n = enc_rsdo_read(b, addr);
    return tx_frame(can_id_make(CAN_FC_RSDO, node), b, n);
}

static int node_index(uint8_t node) {
    static const uint8_t ids[CAN_N_JOINTS] = CAN_JOINT_NODES;
    for (int i = 0; i < CAN_N_JOINTS; i++)
        if (ids[i] == node) return i;
    return -1;
}

void can_bus_poll(can_joint_state_t state[CAN_N_JOINTS],
                  void *unused, uint8_t sdo_resp_val[4],
                  bool *sdo_resp_ready, uint8_t *sdo_resp_node) {
    (void)unused;
    twai_message_t m;
    while (twai_receive(&m, 0) == ESP_OK) {
        uint8_t fc = can_id_fc(m.identifier);
        uint8_t node = can_id_node(m.identifier);
        int idx = node_index(node);
        if (idx < 0) continue;
        can_joint_state_t *s = &state[idx];
        s->last_rx_ms = millis();
        s->online = 1;
        switch (fc) {
        case CAN_FC_TPDO2:
            dec_pdo2(m.data, m.data_length_code, &s->pos, &s->vel);
            break;
        case CAN_FC_TPDO3:
            dec_pdo3(m.data, m.data_length_code, &s->iq);
            break;
        case CAN_FC_TSDO:
            if (sdo_resp_ready && dec_tsdo_resp(m.data,
                    m.data_length_code, sdo_resp_val) == 0) {
                *sdo_resp_ready = true;
                *sdo_resp_node = node;
            }
            break;
        case CAN_FC_EMCY:
            /* fault report — surfaced to host via STATE flags/event */
            s->status |= 0x8;
            break;
        default:
            break;
        }
    }
}

void can_estop_broadcast(void) {
    can_send_nmt(NMT_ESTOP, CAN_NODE_ALL);
}

void can_enable_all(void) {
    static const uint8_t ids[CAN_N_JOINTS] = CAN_JOINT_NODES;
    /* NMT targets are per-node; broadcast uses node 0 */
    can_send_nmt(NMT_ENABLE, CAN_NODE_ALL);
    (void)ids;
}

void can_disable_all(void) {
    can_send_nmt(NMT_DISABLE, CAN_NODE_ALL);
}

void can_bus_housekeeping(void) {
    uint32_t alerts = 0;
    if (twai_read_alerts(&alerts, 0) != ESP_OK) return;
    if (alerts & TWAI_ALERT_BUS_OFF) {
        twai_initiate_recovery();
    }
    if (alerts & TWAI_ALERT_BUS_RECOVERED) {
        twai_start();
    }
}
