/* can_bus.h — TWAI (CAN 2.0B @ 1 Mbps) driver + SOMA joint protocol glue.
 * Talks to the three B-G431B-ESC1 joint drivers (nodes 1,2,3). */
#pragma once

#include <stdint.h>
#include "../../shared/can_proto.h"

typedef struct {
    float    pos;        /* last TPDO2 feedback, rad (output shaft)   */
    float    vel;        /* rad/s                                    */
    float    iq;         /* last TPDO3, A                            */
    uint32_t status;     /* last SDO_STATUS value                    */
    uint32_t last_rx_ms; /* millis() of last frame from this node    */
    uint8_t  online;     /* seen a frame in the last 250 ms          */
} can_joint_state_t;

void can_bus_init(void);

/* send helpers (encode + transmit); all return true if queued */
bool can_send_nmt(uint8_t nmt_cmd, uint8_t target_node);
bool can_send_pdo2(uint8_t node, float pos, float vel);
bool can_send_pdo3(uint8_t node, float torque_nm);
bool can_send_ping(uint8_t node, uint32_t token);
bool can_sdo_write_f32(uint8_t node, uint16_t addr, float v);
bool can_sdo_write_u32(uint8_t node, uint16_t addr, uint32_t v);
bool can_sdo_read(uint8_t node, uint16_t addr);

/* poll the RX queue; call every loop iteration. Fills `state` and, for
 * TSDO responses, copies the 4-byte value to sdo_resp_val and sets
 * sdo_resp_ready (addr/node tracked by the requester — TSDO resp
 * carries data only). Pass NULL for sdo_resp_* to ignore them. */
void can_bus_poll(can_joint_state_t state[CAN_N_JOINTS],
                  void *unused, uint8_t sdo_resp_val[4],
                  bool *sdo_resp_ready, uint8_t *sdo_resp_node);

/* emit e-stop broadcast (NMT ESTOP to node 0) */
void can_estop_broadcast(void);
/* clear estop: NMT ENABLE broadcast */
void can_enable_all(void);
void can_disable_all(void);

/* bus health: attempts recovery if driver reports bus-off */
void can_bus_housekeeping(void);
