/* arm_state.h — shared state between main loop, host link and buses. */
#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "config.h"
#include "can_bus.h"
#include "feetech_bus.h"
#include "../../shared/motor_en.h"

typedef struct {
    /* commanded joint setpoints (rad, output shaft; ch6 = GRIP jaw) */
    float    q_cmd[ARM_N_CHAN];
    float    dq_cmd[ARM_N_CHAN]; /* jog velocities (SET_JOINT_VEL)      */
    float    tau_ff[CAN_N_JOINTS]; /* torque feedforward J2..J3 (Nm)    */

    /* mode flags */
    bool     estop;             /* latched: pin or host or watchdog    */
    bool     armed;             /* torque enabled on all joints        */
    bool     watchdog_tripped;
    uint32_t heartbeat_count;

    /* MOTOR_EN safety state machine (firmware/shared/motor_en.c) */
    motor_en_t motor;
    uint8_t  motor_arm_req;     /* host LK_ARM_MOTOR latched for a tick */
    bool     can_bus_off;       /* latched from TWAI alert              */

    /* feedback */
    can_joint_state_t can[CAN_N_JOINTS]; /* J2,J3 -> nodes 2,3           */
    ft_servo_state_t  ft[FT_N_SERVOS];   /* ids 1,4,5,6,7 -> J1,J4..GRIP */
    uint8_t  can_ok_mask;       /* bits J2,J3 online                    */
} arm_state_t;

extern arm_state_t g_arm;

/* set by host_link on LK_READ_PARAM(CAN) so the SDO response can be
 * relayed with the matching address (TSDO resp carries data only) */
extern uint8_t  g_pending_sdo_node;
extern uint16_t g_pending_sdo_addr;

/* clamp a 7-channel vector into the config limits */
void arm_clamp_q(float q[ARM_N_CHAN]);

/* trigger/reset estop (medr_t reason); always cuts the MOTOR_EN relay
 * and emits an NMT stop as well */
void arm_estop(uint8_t medr_reason);
void arm_clear_estop(void);
void arm_set_armed(bool on);
