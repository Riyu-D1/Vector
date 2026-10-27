/* arm_state.h — shared state between main loop, host link and buses. */
#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "can_bus.h"
#include "feetech_bus.h"

typedef struct {
    /* commanded joint setpoints (rad, output shaft; J6 = jaw) */
    float    q_cmd[6];
    float    dq_cmd[6];         /* jog velocities (SET_JOINT_VEL)      */
    float    tau_ff[3];         /* torque feedforward J1..J3 (Nm)      */

    /* mode flags */
    bool     estop;             /* latched: pin or host or watchdog    */
    bool     armed;             /* torque enabled on all joints        */
    bool     watchdog_tripped;
    uint32_t heartbeat_count;

    /* feedback */
    can_joint_state_t can[3];   /* J1..J3, index = joint-1             */
    ft_servo_state_t  ft[3];    /* J4..J6, index = joint-4             */
    uint8_t  can_ok_mask;       /* bits J1..J3 online                  */
} arm_state_t;

extern arm_state_t g_arm;

/* set by host_link on LK_READ_PARAM(CAN) so the SDO response can be
 * relayed with the matching address (TSDO resp carries data only) */
extern uint8_t  g_pending_sdo_node;
extern uint16_t g_pending_sdo_addr;

/* clamp a 6-joint vector into the config limits */
void arm_clamp_q(float q[6]);

/* trigger/reset estop (also used by pin ISR and watchdog) */
void arm_estop(const char *why);
void arm_clear_estop(void);
void arm_set_armed(bool on);
