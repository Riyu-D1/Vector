#include "motor_en.h"

void motor_en_init(motor_en_t *m) {
    m->motor_en = 0;
    m->fault_latched = 0;
    m->drop_reason = MEDR_NONE;
    m->phase = MEP_IDLE;
    m->boot_start_ms = 0;
    m->esc_boot_window_ms = MEDR_ESC_BOOT_WINDOW_MS;
}

uint8_t motor_en_step(motor_en_t *m, const motor_en_in_t *in) {
    uint8_t dropped = 0;

    if (m->motor_en) {
        uint8_t reason = MEDR_NONE;
        if (!in->estop_released)      reason = MEDR_ESTOP;
        else if (!in->host_alive)     reason = MEDR_HOST_TIMEOUT;
        else if (in->can_bus_off)     reason = MEDR_CAN_BUS_OFF;
        else if (in->esc_fault)       reason = MEDR_ESC_FAULT;
        else if (m->phase == MEP_ARMED && !in->esc_all_alive)
                                      reason = MEDR_ESC_LOST;
        else if (m->phase == MEP_BOOTING &&
                 (uint32_t)(in->now_ms - m->boot_start_ms) >
                     m->esc_boot_window_ms)
                                      reason = MEDR_ESC_BOOT_TIMEOUT;
        if (reason != MEDR_NONE) {
            m->motor_en = 0;
            m->fault_latched = 1;
            m->drop_reason = reason;
            m->phase = MEP_IDLE;
            dropped = 1;
        } else if (m->phase == MEP_BOOTING && in->esc_all_alive) {
            m->phase = MEP_ARMED;
        }
    }

    /* phase 1 (pre-arm): explicit host command while the host link,
     * estop loop and CAN bus are sane. ESC heartbeats are deliberately
     * NOT required here — the drives sit on the switched +12V_MOT rail
     * and are dead until K1 closes. Phase 2 (boot window) supervises
     * their power-up. */
    if (!m->motor_en && in->arm_cmd &&
        in->host_seen && in->host_alive && in->estop_released &&
        !in->can_bus_off) {
        m->motor_en = 1;
        m->fault_latched = 0;
        m->drop_reason = MEDR_NONE;
        m->phase = MEP_BOOTING;
        m->boot_start_ms = in->now_ms;
    }

    return dropped;
}
