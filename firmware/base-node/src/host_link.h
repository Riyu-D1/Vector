/* host_link.h — framed serial link to the Orange Pi.
 * Parses LINK frames off the USB console Serial and dispatches them;
 * emits STATE/PONG/PARAM/EVENT/NACK responses. */
#pragma once

#include <stdint.h>
#include "../../shared/link_proto.h"

void host_link_init(void);

/* feed available Serial bytes; call every loop iteration */
void host_link_poll(void);

/* emit one STATE telemetry frame (pos/vel/tau per joint + flags) */
void host_link_send_state(void);
void host_link_send_event(uint8_t code, uint8_t arg);
void host_link_send_param(uint8_t bus, uint8_t node, uint16_t addr,
                          const uint8_t val4[4]);

/* timestamp of the last valid frame received (for the watchdog) */
uint32_t host_link_last_rx_ms(void);
/* true once >=1 valid host frame has been received (the "handshake"
 * the MOTOR_EN machine requires) */
bool host_link_seen(void);
