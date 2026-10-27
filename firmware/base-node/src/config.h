/* config.h — SOMA v3 base-node constants.
 * Joint limits + table guard come from firmware/shared/arm_params_gen.h
 * (GENERATED from cad/arm/arm_params.py — the single source of truth,
 * same file the robot-os kinematics consumes). */
#pragma once

#include "../../shared/arm_params_gen.h"

/* CAN bus: classical CAN 2.0B, 1 Mbit/s (spec), SN65HVD230 on J15 */
#define CAN_JOINT_NODES   { 1, 2, 3 }     /* J1, J2, J3 */
#define CAN_N_JOINTS      3

/* Feetech bus A: J4=4, J5=5, J6=6 — factory baud, spec flags 1 Mbps
 * UNVERIFIED on this wiring; drop to 500000 if the bus is flaky. */
#define FT_BAUD           1000000L
#define FT_SERVO_IDS      { 4, 5, 6 }
#define FT_N_SERVOS       3
#define FT_CMD_SPEED      600             /* counts/s goal speed (~88 deg/s) */
#define FT_READ_TIMEOUT_MS 8

/* joint limits (rad, output shaft, host frame) — verified CAD ranges:
 * J1 +-170, J2 -35..+70, J3 +-90, J4 +-95, J5 +-160, J6 +-90 deg
 * (CAD frame J2 is -70..+35, down-positive; generator flips the sign).
 * Table/case guard: q3 >= ARM_GUARD_A + ARM_GUARD_B * q2  (see
 * arm_clamp_q in main.cpp). */
#define Q_MIN ARM_JOINT_MIN_RAD
#define Q_MAX ARM_JOINT_MAX_RAD

/* driver phase-current caps (A): spec ~5 A max, lower for J1 */
static const float PHASE_CURRENT_LIMIT_A[3] = { 3.0f, 5.0f, 5.0f };
#define GEAR_RATIO        15.0f

/* rates */
#define JOINT_LOOP_HZ     100             /* RPDO2 + servo goal update    */
#define STATE_TX_HZ       25              /* LK_STATE telemetry           */
#define FT_TELEM_DIV      5               /* servo telemetry = loop/5 = 20 Hz */
#define HOST_TIMEOUT_MS   500             /* watchdog: no frame -> freeze  */

/* conversions */
#define FT_COUNTS_PER_RAD (4096.0f / 6.283185307f)
#define FT_CENTER         2048

#define FW_VERSION        0x000100u       /* 0.1.0 */
