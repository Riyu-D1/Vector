# SOMA — System Architecture

## The three-level nervous system

```
┌─────────────────────────────────────────────────────────────┐
│ MIND — your computer / cloud                                │
│  LLM agent (files, web, planning). Talks to the arm over    │
│  LAN/WebSocket; optionally via an MCP server so any MCP     │
│  client (Claude Desktop, Cursor, custom loops) can drive it │
└───────────────────────┬─────────────────────────────────────┘
                        │  WiFi/LAN — tool calls + telemetry
┌───────────────────────▼─────────────────────────────────────┐
│ BRAIN — Orange Pi 5 (onboard, 6 TOPS NPU)                   │
│  Robot OS: joint-space & Cartesian IK, trajectory gen,      │
│  admittance/yield loops, NPU vision (YOLO-class), face      │
│  renderer, voice I/O, tool API server, dataset logging      │
│  (LeRobot-format: joints + torques + tactile + video)       │
└───────────────────────┬─────────────────────────────────────┘
                        │  USB serial, JSON frames @ ~50–100 Hz
┌───────────────────────▼─────────────────────────────────────┐
│ BRAINSTEM — ESP32-S3 (base node)                            │
│  Hard real-time: servo bus master (UART half-duplex),       │
│  SEA encoder reads (I2C #1), IMU (I2C #2), joint-torque     │
│  estimator (k·Δθ), safety watchdog (estop, torque caps,     │
│  heartbeat — dies safe if Pi stalls)                        │
└───────┬───────────────────────────────────┬───────────────┘
        │ servo bus (3-pin TTL, daisy-chained)│ 4-wire harness (5V, GND, UART TX/RX)
        ▼                                   ▼
  6× serial servos                  ESP32 wrist/face node
  (J1–J5 + gripper)                 — 2× GC9A01 eyes (SPI)
                                    — 2× BMP390 fingertip pads (I2C)
                                    — AS5600 tendon idler (I2C)
                                    — USB camera passes up to Pi
```

**Why this split:** Linux SBCs are bad at real-time motor timing; MCUs are bad
at vision and planning. Every serious robot splits "thinking" (Pi) from
"reflexes" (ESP32). The Pi can even crash mid-motion and the ESP32's watchdog
freezes the arm safely.

## Compliance stack (how "flexible" actually works)

1. **Mechanical**: torsion springs at J2/J3 outputs; TPU shell; compliant
   fingertips. The arm physically can't transmit full shock loads.
2. **Measured**: τ_joint = k·Δθ on J2/J3 (AS5600 output encoders); tendon
   tension = grip force at the gripper; pressure at fingertips.
3. **Control**: admittance loop — measured deflection above a threshold →
   command the servo to relieve it. The arm yields within a servo-response
   timescale (springy, protective, not buttery like a QDD — honest trade).
4. **Limits**: `torque_limit` register per joint = per-task force cap
   ("handshake" vs "push the box"); torque-off = coast for hand-guiding.

## Grip force measurement

```
servo → tendon (Dyneema) ──→ over sprung idler pulley ──→ finger links
                                  │ lever arm on torsion spring
                                  └─ AS5600 reads lever angle
                                    → tension = k_lever · θ
                                    → grip force ≈ f(tension, finger geometry)
```

One sensor, real Newtons, no structural load cell inline with the tendon —
the idler is a passive add-on in the tendon path. Calibrate by hanging known
weights from a finger pad.

## Electrical netlist (for the wiring diagram)

**Power**
- 12 V/6–8 A brick → SM-class servo rail (J2, J3)
- Buck 12→7.4 V/3 A → STS3215 rail (J1, J4, J5, gripper) — keep ≤8 V
- Buck 12→5 V/4 A → Orange Pi 5 + ESP32s + sensors + displays
- Common ground; servo rails fused separately (6 A / 3 A)

**Buses** (two physical servo buses — SM servos are RS485, STS are TTL)
- RS485: ESP32-S3 UART2 → MAX3485 transceiver → SM60CL (J2), SM40BL (J3)
- TTL half-duplex: ESP32-S3 UART1 (+DIR pin or bus hub) → STS3215 ×4 daisy-chain
- I2C-1 (base node): AS5600 ×2 (SEA outputs) + IMU — fixed AS5600 addr is fine,
  only these two + IMU on this bus... AS5600s share addr 0x36 → put them on
  **separate buses**: SEA-J2 on I2C-1, SEA-J3 on I2C-2 (ESP32-S3 has two I2C
  controllers)
- I2C (wrist node): BMP390 ×2 (addr 0x76/0x77 — no conflict) + AS5600 idler
- SPI (wrist node): GC9A01 ×2 (separate CS)
- UART (arm harness): base node ⇄ wrist node
- USB: wrist camera → Pi; Pi ⇄ base node (USB serial)

## Software blocks

| Block | Runs on | Job |
|---|---|---|
| `servo-daemon` | ESP32-S3 | Bus master, position cmds, telemetry poll @ 50 Hz |
| `torque-est` | ESP32-S3 | k·Δθ → τ, publish; yield-admit trigger |
| `watchdog` | ESP32-S3 | Estop, torque caps, link-loss freeze |
| `ik-node` | Pi | FK/IK (analytic 5DOF + Jacobian fallback) |
| `perception` | Pi | Camera ingest, NPU detection, AprilTag/aruco pose |
| `face` | Pi→wrist | Expression renderer → eye keyframes over UART |
| `api` | Pi | WebSocket/JSON tool server + MCP server |
| `logger` | Pi | LeRobot-format dataset writer (joints, τ, tactile, frames) |

## Upgrade paths (design keeps them open)

- **J6 wrist yaw**: wrist mount accepts a 6th servo — bolt-on + bus ID only.
- **CyberGear at J2**: shoulder cartridge is a self-contained subassembly; a
  QDD swap later only redesigns one cartridge (24 V rail + CAN transceiver on
  the same ESP32-S3 — TWAI peripheral already on-chip).
- **Onboard→hybrid**: everything works with the Pi removed and a laptop doing
  brain duty over USB — the ESP32 protocol doesn't change.
