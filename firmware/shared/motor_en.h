/*
 * motor_en.h — MOTOR_EN (relay K1 -> +12V_MOT) safety state machine.
 *
 * Pure C, no platform deps: compiled into firmware/base-node AND into a
 * host-side pytest harness (ctypes) — the test exercises the exact code
 * that runs on the ESP32.
 *
 * Spec (docs/can-protocol.md, carrier v1.3):
 *   - motor_en LOW at boot.
 *   - rises only on an explicit host ARM command while ALL of:
 *       host handshake seen AND host link alive AND estop loop released
 *       AND every configured ESC heartbeat on CAN (no fault, no bus-off).
 *   - any estop, host watchdog timeout, CAN bus-off, ESC fault or a
 *     heartbeat lost while powered drops motor_en LOW immediately;
 *     the caller must then send an NMT stop (returned via `dropped`).
 *   - re-arm needs an explicit host command again.
 */
#ifndef SOMA_MOTOR_EN_H
#define SOMA_MOTOR_EN_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* drop reasons (also reported to the host as the event arg) */
typedef enum {
    MEDR_NONE         = 0,
    MEDR_ESTOP        = 1,   /* J9/J19 estop sense: NC loop opened       */
    MEDR_HOST_TIMEOUT = 2,   /* no host frame inside the watchdog window */
    MEDR_CAN_BUS_OFF  = 3,   /* TWAI bus-off alert                       */
    MEDR_ESC_FAULT    = 4,   /* EMCY frame or STATUS fault bit           */
    MEDR_ESC_LOST     = 5    /* a configured ESC went quiet while armed  */
} medr_t;

typedef struct {
    uint8_t host_seen;      /* >=1 valid host frame ever received       */
    uint8_t host_alive;     /* host frame inside the watchdog window    */
    uint8_t estop_released; /* estop sense input released (loop closed) */
    uint8_t esc_all_alive;  /* every configured CAN node heard recently */
    uint8_t esc_fault;      /* EMCY / drive fault seen                  */
    uint8_t can_bus_off;    /* bus-off latched by the CAN driver        */
    uint8_t arm_cmd;        /* explicit host ARM_MOTOR this tick (edge) */
} motor_en_in_t;

typedef struct {
    uint8_t  motor_en;      /* OUTPUT: drive the relay pin with this    */
    uint8_t  fault_latched; /* a drop happened; cleared by a good arm   */
    uint8_t  drop_reason;   /* medr_t of the last drop                  */
} motor_en_t;

void motor_en_init(motor_en_t *m);

/* Advance the machine one tick. Returns 1 on the tick the output fell
 * (caller should broadcast NMT stop + servo torque-off), else 0. */
uint8_t motor_en_step(motor_en_t *m, const motor_en_in_t *in);

#ifdef __cplusplus
}
#endif

#endif /* SOMA_MOTOR_EN_H */
