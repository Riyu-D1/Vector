#include "motor_en.h"

void motor_en_init(motor_en_t *m) {
    m->motor_en = 0;
    m->fault_latched = 0;
    m->drop_reason = MEDR_NONE;
}

uint8_t motor_en_step(motor_en_t *m, const motor_en_in_t *in) {
    uint8_t dropped = 0;

    if (m->motor_en) {
        uint8_t reason = MEDR_NONE;
        if (!in->estop_released)      reason = MEDR_ESTOP;
        else if (!in->host_alive)     reason = MEDR_HOST_TIMEOUT;
        else if (in->can_bus_off)     reason = MEDR_CAN_BUS_OFF;
        else if (in->esc_fault)       reason = MEDR_ESC_FAULT;
        else if (!in->esc_all_alive)  reason = MEDR_ESC_LOST;
        if (reason != MEDR_NONE) {
            m->motor_en = 0;
            m->fault_latched = 1;
            m->drop_reason = reason;
            dropped = 1;
        }
    }

    if (!m->motor_en && in->arm_cmd &&
        in->host_seen && in->host_alive && in->estop_released &&
        in->esc_all_alive && !in->esc_fault && !in->can_bus_off) {
        m->motor_en = 1;
        m->fault_latched = 0;
        m->drop_reason = MEDR_NONE;
    }

    return dropped;
}
