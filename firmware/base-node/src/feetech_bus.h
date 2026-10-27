/* feetech_bus.h — Feetech STS half-duplex TTL bus driver.
 * Bus A on UART1 (IO17 TX / IO11 RX via 1k coupling R1) for J4/J5/J6.
 * TX and RX share the single bus wire: our own transmit echoes into RX
 * and is discarded after every send. */
#pragma once

#include <stdint.h>
#include "../../shared/feetech_proto.h"

typedef struct {
    uint16_t pos;      /* counts 0..4095          */
    int16_t  speed;
    int16_t  load;
    uint8_t  volt;     /* 0.1 V units             */
    uint8_t  temp;     /* deg C                   */
    uint8_t  err;      /* last response error byte */
    uint8_t  online;
    uint32_t last_rx_ms;
} ft_servo_state_t;

void ft_bus_init(void);

/* single transactions — each discards its TX echo then waits for the
 * response inside `timeout_ms`. */
bool ft_ping(uint8_t id);
bool ft_write_reg(uint8_t id, uint8_t addr, const uint8_t *data, uint8_t n);
bool ft_write_u8(uint8_t id, uint8_t addr, uint8_t v);
bool ft_write_u16(uint8_t id, uint8_t addr, uint16_t v);
bool ft_read(uint8_t id, uint8_t addr, uint8_t nbytes,
             uint8_t *out_params, uint8_t *err);

/* high level */
bool ft_goal(uint8_t id, uint16_t pos_counts, uint16_t speed_counts);
bool ft_torque_enable(uint8_t id, bool on);
bool ft_read_telemetry(uint8_t id, ft_servo_state_t *st);
