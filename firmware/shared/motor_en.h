/*
 * motor_en.h — MOTOR_EN (relay K1 -> +12V_MOT) safety state machine.
 *
 * Pure C, no platform deps: compiled into firmware/base-node AND into a
 * host-side pytest harness (ctypes) — the test exercises the exact code
 * that runs on the ESP32.
 *
 * Spec (docs/can-protocol.md, carrier v1.3) — TWO-PHASE ARM:
 *   - motor_en LOW at boot.
 *   - Phase 1 (pre-arm): rises on an explicit host ARM command while
 *       host handshake seen AND host link alive AND the estop loop is
 *       released AND no CAN bus-off. ESC heartbeats are NOT required —
 *       the ESCs sit on the switched +12V_MOT rail and are dead until
 *       the relay closes (requiring them first was the W1 deadlock).
 *       Closing K1 starts the esc_boot_window_ms timer.
 *   - Phase 2 (boot window): every configured ESC must send its first
 *       heartbeat inside esc_boot_window_ms (default 1500 ms, param in
 *       the state struct). Window expiry drops motor_en immediately
 *       with reason MEDR_ESC_BOOT_TIMEOUT; a fresh explicit ARM is
 *       required to retry. All ESCs alive -> MEP_ARMED.
 *   - Once armed: any estop, host watchdog timeout, CAN bus-off, ESC
 *     fault or a heartbeat lost for the alive window (400 ms) drops
 *     motor_en LOW immediately; the caller must then send an NMT stop
 *     (returned via `dropped`). Estop/host-timeout/bus-off/ESC-fault
 *     also drop during the boot window.
 *   - re-arm always needs an explicit host command again.
 */
#ifndef SOMA_MOTOR_EN_H
#define SOMA_MOTOR_EN_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* drop reasons (also reported to the host as the event arg) */
typedef enum {
    MEDR_NONE             = 0,
    MEDR_ESTOP            = 1,   /* J9/J19 estop sense: NC loop opened       */
    MEDR_HOST_TIMEOUT     = 2,   /* no host frame inside the watchdog window */
    MEDR_CAN_BUS_OFF      = 3,   /* TWAI bus-off alert                       */
    MEDR_ESC_FAULT        = 4,   /* EMCY frame or STATUS fault bit           */
    MEDR_ESC_LOST         = 5,   /* a configured ESC went quiet while armed  */
    MEDR_ESC_BOOT_TIMEOUT = 6    /* not all ESCs heartbeated inside the
                                    * boot window after the relay closed    */
} medr_t;

/* phases of the two-phase arm */
typedef enum {
    MEP_IDLE    = 0,   /* motor_en low                                       */
    MEP_BOOTING = 1,   /* relay closed; waiting for first ESC heartbeats     */
    MEP_ARMED   = 2    /* every configured ESC alive; steady supervision     */
} mep_t;

/* default for the esc_boot_window_ms param */
#define MEDR_ESC_BOOT_WINDOW_MS 1500u

typedef struct {
    uint8_t host_seen;      /* >=1 valid host frame ever received       */
    uint8_t host_alive;     /* host frame inside the watchdog window    */
    uint8_t estop_released; /* estop sense input released (loop closed) */
    uint8_t esc_all_alive;  /* every configured CAN node heard recently */
    uint8_t esc_fault;      /* EMCY / drive fault seen                  */
    uint8_t can_bus_off;    /* bus-off latched by the CAN driver        */
    uint8_t arm_cmd;        /* explicit host ARM_MOTOR this tick (edge) */
    uint32_t now_ms;        /* caller's millis() — drives boot window   */
} motor_en_in_t;

typedef struct {
    uint8_t  motor_en;      /* OUTPUT: drive the relay pin with this    */
    uint8_t  fault_latched; /* a drop happened; cleared by a good arm   */
    uint8_t  drop_reason;   /* medr_t of the last drop                  */
    uint8_t  phase;         /* mep_t                                    */
    uint32_t boot_start_ms; /* now_ms when the relay closed             */
    uint32_t esc_boot_window_ms; /* param: max wait for first ESC
                                    * heartbeats once K1 is closed      */
} motor_en_t;

void motor_en_init(motor_en_t *m);

/* Advance the machine one tick. Returns 1 on the tick the output fell
 * (caller should broadcast NMT stop + servo torque-off), else 0. */
uint8_t motor_en_step(motor_en_t *m, const motor_en_in_t *in);

#ifdef __cplusplus
}
#endif

#endif /* SOMA_MOTOR_EN_H */
