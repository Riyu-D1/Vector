/*
 * pins.h — ESP32-S3 GPIO map for the soma-carrier PCB **v1.3**
 * (~/Vector-wt/pcb13/pcb13/STATUS-pcb13.md is authoritative).
 * Carrier board is FINAL — do not remap.
 *
 * v1.3 changes vs the v1.1-era map: bus B (IO15/12), I2C2 (IO41/42) and
 * the wrist UART (IO39/40) were REMOVED from the board. Net WTX on
 * U1A.15 became MOTOR_EN — it now drives relay K1 (via Q3/R11/R12 and
 * the J19 NC e-stop loop) which switches +12V_MOT on J18/J20.
 *
 *   U1A pad18 IO2  -> SP1 -> J15.3   CAN_TX to TJA1051T/3 transceiver D
 *   U1A pad19 IO1  -> SP2 -> J15.4   CAN_RX from transceiver R
 *   U1A pad13 IO38 -> ESTOP -> J9.1  estop sense (NC loop to GND, J9.2)
 *   U1A pad15 IO40 -> MOTOR_EN -> R11 -> Q3 base  relay K1 low side
 *                    (through the J19 NC e-stop loop; HIGH = motors get
 *                    +12V_MOT, LOW by default)
 *   U1B pad13 IO17 -> BUSA_DATA -> J4/J5  Feetech bus A TX
 *                    (J1 STS3250 id1, J4/J5/J6 STS3215 id4/5/6, grip id7)
 *   U1B pad6  IO11 -> RXA via R1          Feetech bus A RX (1k coupled)
 *   U1B pad14 IO16 -> LEDGPIO via R4      status LED (D3 STAT)
 *   U1B pad16 IO7  -> BUZ via R5/Q1       buzzer
 *   U1B pad7  IO10 -> VSNS ADC1           12 V rail voltage divider
 *   U1B pad11 IO8 -> SDA1, pad12 IO18 -> SCL1  I2C-1 (J11 OLED, J12 IMU)
 *
 * Host link: Serial = UART0 console on the DevKit's USB-UART port
 * (IO43/IO44, not routed through the carrier).
 */
#pragma once

#include <driver/gpio.h>

/* CAN transceiver on spare header J15 (TJA1051T/3 on carrier v1.3) */
#define PIN_CAN_TX    GPIO_NUM_2    /* J15.3 = SP1 */
#define PIN_CAN_RX    GPIO_NUM_1    /* J15.4 = SP2 */

/* safety */
#define PIN_ESTOP     GPIO_NUM_38   /* J9.1; NC loop to GND.
                                     * HIGH (loop open) = ESTOP */
#define PIN_MOTOR_EN  GPIO_NUM_40   /* R11 -> Q3 -> relay K1 coil low
                                     * side through the J19 NC loop.
                                     * HIGH = motors powered (+12V_MOT).
                                     * MUST stay LOW until the safety
                                     * state machine closes it. */

/* Feetech servo bus A: J1 STS3250 (id 1), J4/J5/J6 STS3215 (id 4/5/6),
 * gripper STS3215 (id 7) */
#define PIN_BUSA_TX   GPIO_NUM_17
#define PIN_BUSA_RX   GPIO_NUM_11

/* misc carrier peripherals */
#define PIN_LED_STAT  GPIO_NUM_16
#define PIN_BUZZER    GPIO_NUM_7
#define PIN_VSENSE    GPIO_NUM_10   /* ADC1_CH9 */

/* I2C-1 only (I2C-2 was removed from the board in v1.3) */
#define PIN_SDA1      GPIO_NUM_8
#define PIN_SCL1      GPIO_NUM_18
