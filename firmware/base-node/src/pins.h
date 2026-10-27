/*
 * pins.h — ESP32-S3 GPIO map, transcribed from pcb/gen_pcb.py (authoritative)
 * for the soma-carrier PCB. Carrier board is FINAL — do not remap.
 *
 * DevKitC-1 module pad -> net -> carrier connector (see pcb/gen_pcb.py
 * u1a_map/u1b_map, lines ~257-281):
 *
 *   U1A pad18 IO2  -> SP1 -> J15.3   CAN_TX to SN65HVD230 module CTX/D
 *   U1A pad19 IO1  -> SP2 -> J15.4   CAN_RX from SN65HVD230 module CRX/R
 *   U1A pad13 IO38 -> ESTOP -> J9.1  estop loop to GND (J9.2); NC switch
 *   U1B pad13 IO17 -> BUSA_DATA -> J4/J5  Feetech bus A TX (J4,J5,J6 servos)
 *   U1B pad6  IO11 -> RXA via R1          Feetech bus A RX (1k coupled)
 *   U1B pad15 IO15 -> BUSB_DATA -> J6     spare bus B TX (unused in v3)
 *   U1B pad5  IO12 -> RXB via R2          spare bus B RX
 *   U1B pad14 IO16 -> LEDGPIO via R4      status LED (D3 STAT)
 *   U1B pad16 IO7  -> BUZ via R5/Q1       buzzer
 *   U1B pad7  IO10 -> VSNS ADC1           12 V rail voltage divider
 *   U1B pad11 IO8 -> SDA1, pad12 IO18 -> SCL1  I2C-1 (J7/J11/J12)
 *   U1A pad16 IO41 -> SDA2, pad17 IO42 -> SCL2  I2C-2 (J8)
 *   U1A pad14 IO39 -> WRX, pad15 IO40 -> WTX   wrist node UART (J10)
 *
 * Host link: Serial = UART0 console on the DevKit's USB-UART port
 * (IO43/IO44, not routed through the carrier).
 */
#pragma once

#include <driver/gpio.h>

/* CAN transceiver on spare header J15 (ARM_HYBRID_V3.md bus plan) */
#define PIN_CAN_TX    GPIO_NUM_2    /* J15.3 = SP1 */
#define PIN_CAN_RX    GPIO_NUM_1    /* J15.4 = SP2 */

/* safety */
#define PIN_ESTOP     GPIO_NUM_38   /* J9.1; NC loop to GND.
                                     * HIGH (loop open) = ESTOP */

/* Feetech servo bus A (J4 wrist pitch id4, J5 wrist roll id5, J6 grip id6) */
#define PIN_BUSA_TX   GPIO_NUM_17
#define PIN_BUSA_RX   GPIO_NUM_11
/* spare bus B — wired in firmware, unused in v3 (was Hiwonder in v2) */
#define PIN_BUSB_TX   GPIO_NUM_15
#define PIN_BUSB_RX   GPIO_NUM_12

/* misc carrier peripherals */
#define PIN_LED_STAT  GPIO_NUM_16
#define PIN_BUZZER    GPIO_NUM_7
#define PIN_VSENSE    GPIO_NUM_10   /* ADC1_CH9 */

/* I2C buses (free for future SEA/aux sensors; AS5600 for J1-J3 lives on
 * the actuator ESC boards, not on this bus) */
#define PIN_SDA1      GPIO_NUM_8
#define PIN_SCL1      GPIO_NUM_18
#define PIN_SDA2      GPIO_NUM_41
#define PIN_SCL2      GPIO_NUM_42

/* wrist node UART (J10) — spare, not used by Stream C v1 */
#define PIN_WRIST_TX  GPIO_NUM_40
#define PIN_WRIST_RX  GPIO_NUM_39
