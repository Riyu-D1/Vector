/* config.h — SOMA v3 base-node constants. Mirror of
 * software/robot-os/soma_arm/config.py — keep in sync. */
#pragma once

/* CAN bus: classical CAN 2.0B, 1 Mbit/s (spec), TJA1051T/3 on J15.
 * Only J2/J3 are CAN joints now (J1 = STS3250 servo on bus A). */
#define CAN_JOINT_NODES   { 2, 3 }        /* J2, J3 */
#define CAN_N_JOINTS      2

/* Feetech bus A: J1 STS3250 id 1, J4/J5/J6 STS3215 id 4/5/6, gripper
 * STS3215 id 7 — factory baud, spec flags 1 Mbps UNVERIFIED on this
 * wiring; drop to 500000 if the bus is flaky. */
#define FT_BAUD           1000000L
#define FT_SERVO_IDS      { 1, 4, 5, 6, 7 }
#define FT_N_SERVOS       5
#define FT_CMD_SPEED      600             /* counts/s goal speed (~88 deg/s) */
#define FT_READ_TIMEOUT_MS 8

/* 7 command channels: J1..J6 + GRIP (index 6, gripper jaw) */
#define ARM_N_CHAN        7
#define CH_J1 0
#define CH_J2 1
#define CH_J3 2
#define CH_J4 3
#define CH_J5 4
#define CH_J6 5
#define CH_GRIP 6

/* channel index per CAN slot / servo slot */
static const uint8_t CAN_JOINT_CHAN[CAN_N_JOINTS] = { CH_J2, CH_J3 };
static const uint8_t FT_SERVO_CHAN[FT_N_SERVOS]   = {
    CH_J1, CH_J4, CH_J5, CH_J6, CH_GRIP };

/* joint limits (rad) — from sim/STATUS-sim.md joint ranges
 * (J1 ±180, J2 -120..+70, J3 -180..+30, J4 ±70, J5 ±70, J6 ±180 deg);
 * jaw 0..1.4 rad UNVERIFIED (calibrate on bench). */
static const float Q_MIN[ARM_N_CHAN] = {
    -3.1416f, -2.0944f, -3.1416f, -1.2217f, -1.2217f, -3.1416f, 0.0f };
static const float Q_MAX[ARM_N_CHAN] = {
     3.1416f,  1.2217f,  0.5236f,  1.2217f,  1.2217f,  3.1416f, 1.4f };

/* driver phase-current caps (A) for J2/J3 — spec 5 A, conservative
 * until the bench test [U] */
static const float PHASE_CURRENT_LIMIT_A[CAN_N_JOINTS] = { 5.0f, 5.0f };
#define GEAR_RATIO        40.0f

/* rates */
#define JOINT_LOOP_HZ     100             /* RPDO2 + servo goal update    */
#define STATE_TX_HZ       25              /* LK_STATE telemetry           */
#define FT_TELEM_DIV      5               /* servo telemetry = loop/5 = 20 Hz */
#define HOST_TIMEOUT_MS   500             /* watchdog: no frame -> drop   */
#define CAN_PING_PERIOD_MS 200            /* RPDO1 heartbeat probe        */
#define CAN_ALIVE_MS      400             /* ESC heartbeat freshness      */

/* conversions */
#define FT_COUNTS_PER_RAD (4096.0f / 6.283185307f)
#define FT_CENTER         2048

#define FW_VERSION        0x000200u       /* 0.2.0 — carrier v1.3 arm */
