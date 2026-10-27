/* bus_can.h — minimal FDCAN1 classic-CAN driver for the B-G431B-ESC1.
 *
 * Board facts (ST UM2516 §5.5 + NuttX b-g431b-esc1 board doc, verified):
 *   - CAN transceiver already on-board, J1 is the CAN connector
 *   - FDCAN1_RX = PA11, FDCAN1_TX = PB9 (AF9)
 *   - CAN_TERM = PC14: drive HIGH to insert the on-board 120 ohm
 *     termination, LOW to remove it
 *   - bit timing below targets 1 Mbit/s from PCLK1 = 170 MHz:
 *     170 MHz / (10 * (1 + 13 + 3)) = 1.000 MHz, sample point 82.4 %
 */
#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* can_term: true -> 120R termination ON (set on the LAST node of the bus) */
void bus_can_init(bool can_term);
bool bus_can_send(uint16_t id, const uint8_t *data, uint8_t dlc);
/* returns true and fills id/dlc/data when a frame was waiting */
bool bus_can_recv(uint16_t *id, uint8_t *data, uint8_t *dlc);
/* call periodically — re-inits the peripheral after bus-off */
void bus_can_recover(void);

#ifdef __cplusplus
}
#endif
