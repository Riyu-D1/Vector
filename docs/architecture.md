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
│ BRAIN — Orange Pi 5B 4 GB (onboard, 6 TOPS NPU)             │
│  Robot OS: joint-space & Cartesian IK, trajectory gen,      │
│  admittance/yield loops, NPU vision (YOLO-class), face      │
│  renderer, voice I/O, tool API server, dataset logging      │
│  (LeRobot-format: joints + torques + tactile + video)       │
│  OPTIONAL — headless mode: your computer does brain duty    │
│  over USB-C; ESP32 protocol is identical either way         │
└───────────────────────┬─────────────────────────────────────┘
                        │  USB serial, JSON frames @ ~50–100 Hz
┌───────────────────────▼─────────────────────────────────────┐
│ BRAINSTEM — ESP32-S3-DevKitC-1 (base node)                  │
│  Hard real-time: TWO TTL servo buses (UART1 Feetech,        │
│  UART2 Hiwonder), SEA encoder reads (I2C-1/I2C-2),          │
│  joint-torque estimator (k·Δθ), safety watchdog (estop,     │
│  torque caps, heartbeat — dies safe if brain stalls)        │
└───────┬───────────────────────────────────┬───────────────┘
        │ 12 V TTL servo bus (daisy-chained)   │ 4-wire harness (5V, GND, UART TX/RX)
        ▼                                    ▼
  UART1: 5× STS3215-12V          ESP32-S3-LCD-1.28 wrist/face node
  (J1, J3, J4, J5, gripper)      — GC9A01 eye #1 (onboard) + eye #2 (SPI)
  UART2: 1× HTD-45H (J2)         — QMI8658 IMU (onboard)
                                 — 2× BMP390 fingertip pads (I2C)
                                 — AS5600 tendon idler (I2C)
  ESP32-CAM at the wrist streams MJPEG → agent over WiFi
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
- 12 V/8 A brick → single servo rail feeding **all six servos**
  (HTD-45H: 9–12.6 V ✓, STS3215-12V: 6–12.6 V ✓ — no 7.4 V rail needed)
- Buck 12→5 V/≥5 A → Orange Pi 5B + ESP32s + sensors + displays
- Common ground; servo rail fused at 6 A, logic at 3 A

**Buses** — all TTL, two UARTs (Hiwonder and Feetech speak different protocols,
so each gets its own wire; both ride the same 12 V power rail)
- UART1 (TTL half-duplex, Feetech protocol): STS3215-12V ×5 daisy-chain
  (J1, J3, J4, J5, gripper)
- UART2 (TTL half-duplex, Hiwonder protocol): HTD-45H (J2) — single servo on
  its own wire, no RS485 transceiver needed
- I2C-1 (base node): AS5600 SEA-J2; I2C-2 (base node): AS5600 SEA-J3
  (AS5600s share fixed addr 0x36 → separate buses; ESP32-S3 has two I2C
  controllers)
- I2C (wrist node): BMP390 ×2 (addr 0x76/0x77 — no conflict) + AS5600 idler
  + QMI8658 IMU (onboard the ESP32-S3-LCD board)
- SPI (wrist node): GC9A01 eye #1 (onboard) + bare GC9A01 eye #2 (separate CS)
- UART (arm harness): base node ⇄ wrist node
- WiFi: ESP32-CAM video → agent; Pi ⇄ base node (USB serial)

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
