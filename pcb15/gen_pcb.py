#!/usr/bin/env python3
"""SOMA base-carrier board generator.

Emit a KiCad .kicad_pcb directly — no schematic needed for a passive
carrier board; pads get nets assigned here so DRC is meaningful.

Board: 100 x 85 mm, 2-layer, 100% through-hole, zero ICs.
Contents: ESP32-S3-DevKitC-1 socket rows, 12 V in (XT60 or screw
terminal) -> power-enable jumper -> fuse -> servo bus ports (KK-254),
optional Mini-360 buck footprint + 5 V screw terminal, Schottky on
ESP32 5 V feed, I2C ports (OLED + IMU), UART port to wrist node,
estop pins, power + status LEDs. v1.1 adds: SSD1306 OLED socket,
GY-521/MPU6050 IMU socket, KY-040 jog-encoder socket, 5V active buzzer
(+2N2222 driver), VS1838B IR receiver, DS18B20 temp sensor, 12V rail
voltage divider -> ADC, WS2812 port, spare-GPIO header, input TVS.
v1.3: hardware e-stop relay (NC loop in series with the coil low side,
2N2222 driven by MOTOR_EN) feeding a new +12V_MOT rail to two motor
outputs; IRF4905 reverse-polarity P-FET between the power jumper and
the fuse. v1.1 leftovers removed: J6/R2 (bus B), J7/J8 (SEA encoders),
J10 (wrist UART).
GND zone on B.Cu.

Run:  python3 pcb/gen_pcb.py
Out:  pcb/soma-carrier-v15.kicad_pcb  +  pcb/soma-carrier-v15.kicad_pro
"""

import math
import re
import time
import uuid
from pathlib import Path

KICAD_LIB = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
OUT = Path(__file__).resolve().parent
BOARD_W, BOARD_H = 135.0, 115.0

NETS = [
    "GND", "+12V_IN", "+12V_SW", "+12V", "+12V_RP", "+12V_MOT",
    "+5V", "+5V_MCU", "+3V3",
    "BUSA_DATA", "RXA",
    "SDA1", "SCL1",
    "MOTOR_EN", "ESTOP", "LEDGPIO", "LED1_A", "LED2_A",
    "BUZ", "BZB", "BZC", "VSNS",
    "ENC_A", "ENC_B", "ENC_SW", "IRIN", "TEMP", "NEO", "NEO_A", "NEO5V",
    "SP3",
    "CAN_TX", "CAN_RX", "CANH", "CANL", "CAN_TERM",
    "RP_GATE", "RLY_LOW", "RLY_SW", "Q3_B",
]
NET_ID = {n: i + 1 for i, n in enumerate(NETS)}


def rot(p, deg):
    a = math.radians(deg)
    return (p[0] * math.cos(a) - p[1] * math.sin(a),
            p[0] * math.sin(a) + p[1] * math.cos(a))


def load_footprint(libdir, name):
    return (KICAD_LIB / libdir / name).read_text()


def pad_info(fp_text):
    """Return {pad_num: (x, y, half_size, layers)} in local footprint coords."""
    out = {}
    pat = re.compile(
        r'\(pad "([^"]+)" (\S+) (\S+)\s*\(\s*at\s+([-\d.]+)\s+([-\d.]+)'
        r'[^)]*\)\s*\(\s*size\s+([\d.]+)\s+([\d.]+)\)')
    for m in pat.finditer(fp_text):
        num, typ, shape, x, y, sx, sy = m.groups()
        layers = ("F.Cu", "B.Cu") if typ == "thru_hole" else ("F.Cu",)
        hx, hy = float(sx) / 2, float(sy) / 2
        # rect/oval pads reach the corner; circles reach the radius
        prr = math.hypot(hx, hy) if shape != "circle" else max(hx, hy)
        out[num] = (float(x), float(y), hx, hy, prr, layers)
    return out


def inject(fp_text, pad_nets):
    """Add net/pintype/uuid to every pad (net 0 "" when unassigned)."""
    result, lines = [], fp_text.split("\n")
    depth, buf, padnum = 0, [], None
    for line in lines:
        if buf:
            buf.append(line)
            depth += line.count("(") - line.count(")")
            if depth <= 0:
                block = "\n".join(buf).rstrip()
                n = pad_nets.get(padnum)
                nid, nname = (NET_ID[n], n) if n else (0, "")
                block = block[:-1] + f' (net {nid} "{nname}")'
                block += ' (pinfunction "") (pintype "passive")'
                block += f' (uuid "{uuid.uuid4()}"))'
                result.append(block)
                buf, padnum = [], None
        else:
            m = re.search(r'\(pad "([^"]+)"', line)
            if m:
                buf, padnum = [line], m.group(1)
                depth = line.count("(") - line.count(")")
                if depth <= 0:
                    block = buf[0].rstrip()
                    n = pad_nets.get(padnum)
                    nid, nname = (NET_ID[n], n) if n else (0, "")
                    block = block[:-1] + f' (net {nid} "{nname}")'
                    block += ' (pinfunction "") (pintype "passive")'
                    block += f' (uuid "{uuid.uuid4()}"))'
                    result.append(block)
                    buf, padnum = [], None
            else:
                result.append(line)
    return "\n".join(result)


class Placed:
    def __init__(self, ref, value, libdir, fname, x, y, rot_deg=0.0, pad_nets=None):
        self.ref, self.x, self.y, self.r = ref, x, y, rot_deg
        src = load_footprint(libdir, fname)
        lib_name = fname[:-len(".kicad_mod")]
        lib = libdir[:-len(".pretty")]
        src = re.sub(r'\(footprint "[^"]*"',
                     f'(footprint "{lib}:{lib_name}"', src, count=1)
        # drop library-file-only attrs
        src = re.sub(r'\n\t\(version [^)]*\)', '', src)
        src = re.sub(r'\n\t\(generator [^)]*\)', '', src)
        # placement + identity after (layer "F.Cu")
        src = src.replace(
            '(layer "F.Cu")',
            f'(layer "F.Cu")\n\t\t(uuid "{uuid.uuid4()}")'
            f'\n\t\t(at {x:.3f} {y:.3f} {rot_deg:g})', 1)
        src = re.sub(r'\(property "Reference" "[^"]*"',
                     f'(property "Reference" "{ref}"', src, count=1)
        src = re.sub(r'\(property "Value" "[^"]*"',
                     f'(property "Value" "{value}"', src, count=1)
        if ref in REF_FIX:
            # move the silk reference to a clear spot next to the body
            dx, dy = REF_FIX[ref]                      # wanted, in world
            lx, ly = rot((dx, dy), rot_deg)            # world -> local
            src = re.sub(
                r'(\(property "Reference" "[^"]*"\s*\n'
                r'\s*\(at\s+)[-\d.]+\s+[-\d.]+',
                lambda m: f'{m.group(1)}{lx:.2f} {ly:.2f}', src, count=1)
        if ref in VAL_FIX:
            dx, dy = VAL_FIX[ref]
            lx, ly = rot((dx, dy), rot_deg)
            src = re.sub(
                r'(\(property "Value" "[^"]*"\s*\n'
                r'\s*\(at\s+)[-\d.]+\s+[-\d.]+',
                lambda m: f'{m.group(1)}{lx:.2f} {ly:.2f}', src, count=1)
        if pad_nets:
            src = inject(src, pad_nets)
        self.src = src
        # KiCad file convention: +y down, positive angle CCW on screen ==
        # rot() with the NEGATED angle. Internal pads must match the file
        # exactly or the router targets empty space (checked by
        # check_pads.py — run after every rotation change).
        self.pad_nets = pad_nets or {}
        self.pads, self.padinfo = {}, {}
        for n, (px, py, hx, hy, prr, layers) in pad_info(
                load_footprint(libdir, fname)).items():
            rx, ry = rot((px, py), -rot_deg)
            self.pads[n] = (x + rx, y + ry)
            self.padinfo[n] = (x + rx, y + ry, hx, hy, prr, layers)

    def pad(self, num):
        return self.pads[num]


C = {}


# Silk reference overrides — desired offset in *world* coords from the
# footprint origin (converted back to footprint-local at emit).
REF_FIX = {
    "U1A": (26.67, 2.5), "U1B": (26.67, -2.5),
    "J4": (-3.5, 0), "J5": (-3.5, 0),
    "J9": (0, 2.6), "J11": (0, 2.6),
    "J13": (0, 2.6), "J15": (0, 2.6),
    "D2": (2.6, 3.4), "D3": (-2.5, 0),
    "R7": (-3.8, 0), "R8": (-3.8, 0),
    "H1": (0, 3.75), "H2": (0, 3.75),
    "H3": (0, -3.75), "H4": (0, -3.75),
}

# Value-text overrides (same world-coord convention) — only where the
# default value lands on copper/silk it shouldn't.
VAL_FIX = {
    "D2": (-2.4, 3.4),
}


def place(ref, value, libdir, fname, x, y, rot_deg=0, pad_nets=None):
    C[ref] = Placed(ref, value, libdir, fname, x, y, rot_deg, pad_nets or {})


# ---------------------------------------------------------------------------
# Component placement  (x, y in mm; board 100x85)
# ---------------------------------------------------------------------------

# Power in — left edge. Vertical XT60 plug OR screw terminal, in parallel.
place("J16", "XT60", "Connector_AMASS.pretty",
      "AMASS_XT60-M_1x02_P7.20mm_Vertical.kicad_mod",
      7.0, 17.0, pad_nets={"1": "GND", "2": "+12V_IN"})
place("J1", "12V_IN", "TerminalBlock_Phoenix.pretty",
      "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.kicad_mod",
      8.0, 48.0, rot_deg=90, pad_nets={"1": "+12V_IN", "2": "GND"})
# JP1: jumper shunt = power switch (or wire a panel rocker here)
place("JP1", "PWR-ON", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x02_P2.54mm_Vertical.kicad_mod", 10.0, 58.0,
      pad_nets={"1": "+12V_IN", "2": "+12V_SW"})
place("J2", "5V_IN", "TerminalBlock_Phoenix.pretty",
      "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.kicad_mod",
      8.0, 36.0, rot_deg=90, pad_nets={"1": "+5V", "2": "GND"})
# D4: 15V bidirectional TVS across the input (P6KE15CA / 1.5KE15CA)
place("D4", "TVS15", "Diode_THT.pretty",
      "D_DO-201_P12.70mm_Horizontal.kicad_mod",
      22.0, 58.0, rot_deg=0, pad_nets={"1": "+12V_IN", "2": "GND"})
# South-west pocket: the mini blade fuse is ~11 mm tall and the DevKitC
# module overhangs ~4.7-8 mm past each header end at ~8.5 mm socket
# clearance — it must sit fully below the module's south edge (y>=53).
place("F1", "10A", "Fuse.pretty", "Fuse_Blade_Mini_directSolder.kicad_mod",
      17.0, 64.0, rot_deg=90, pad_nets={"1": "+12V_RP", "2": "+12V"})
# v1.3: IRF4905 reverse-polarity P-FET between JP1 and the fuse.
# Wrong-way input reverse-biases the body diode and leaves the gate at
# source potential -> FET stays off. Pins vertical (rot 90): gate
# south to R10, drain to JP1, source north to F1.
place("Q2", "IRF4905", "Package_TO_SOT_THT.pretty",
      "TO-220-3_Vertical.kicad_mod", 12.0, 74.0, rot_deg=90,
      pad_nets={"1": "RP_GATE", "2": "+12V_SW", "3": "+12V_RP"})
place("R10", "10k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      10.0, 82.0, pad_nets={"1": "RP_GATE", "2": "GND"})
place("C1", "1000uF", "Capacitor_THT.pretty", "CP_Radial_D10.0mm_P5.00mm.kicad_mod",
      40.0, 19.0, pad_nets={"1": "+12V", "2": "GND"})

# 12V rail voltage monitor: 30k + 6.8k divider -> ADC pin (VSNS)
place("R7", "30k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      27.0, 36.0, pad_nets={"1": "+12V", "2": "VSNS"})
place("R8", "6.8k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      27.0, 40.0, pad_nets={"1": "GND", "2": "VSNS"})

# Optional Mini-360 buck module — 4 edge pads, top-left
place("J3", "MINI360", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x04_P2.54mm_Vertical.kicad_mod", 26.0, 14.0,
      pad_nets={"1": "+12V", "2": "GND", "3": "+5V", "4": "GND"})

# Servo bus ports along top edge (pin1=GND pin2=+12V pin3=DATA)
place("J4", "BUS_A1", "Connector_Molex.pretty",
      "Molex_KK-254_AE-6410-03A_1x03_P2.54mm_Vertical.kicad_mod",
      30.0, 9.0, pad_nets={"1": "GND", "2": "+12V", "3": "BUSA_DATA"})
place("J5", "BUS_A2", "Connector_Molex.pretty",
      "Molex_KK-254_AE-6410-03A_1x03_P2.54mm_Vertical.kicad_mod",
      45.0, 9.0, pad_nets={"1": "GND", "2": "+12V", "3": "BUSA_DATA"})
# (J6 bus-B port removed in v1.3 — frees the top edge strip)

# DevKitC-1 socket: two 1x22 rows, 22.86 mm apart, USB ports -> left edge.
# v1.5 fix (CHECK-pcb14 F1): the v1.4 map below assumed socket pad N meets
# module J-position (23-N).  Espressif's DevKitC-1 v1.1 user guide numbers
# BOTH headers from the USB end, and this board's pad 1 sits at the USB
# (west) end, so socket pad N actually meets module J-position N.  The old
# map put +3V3 on J1-22 (GND) and +5V on J1-2 (3V3) — the corrected map is
# applied to copper only; firmware GPIO assignments are unchanged.
# U1A (bottom row, y=51.16) = module J3 column;
# U1B (top row, y=28.30)  = module J1 column.
# GPIO per pad (real DevKitC-1 v1.1 pinout, Espressif user guide v1.1):
#   U1B: 1=3V3 2=3V3 3=RST 4=IO4 5=IO5 6=IO6 7=IO7 8=IO15 9=IO16
#        10=IO17 11=IO18 12=IO8 13=IO3 14=IO46 15=IO9 16=IO10 17=IO11
#        18=IO12 19=IO13 20=IO14 21=5V 22=G
#   U1A: 1=G 2=IO43(TX) 3=IO44(RX) 4=IO1 5=IO2 6=IO42 7=IO41 8=IO40
#        9=IO39 10=IO38 11=IO37 12=IO36 13=IO35 14=IO0 15=IO45 16=IO48
#        17=IO47 18=IO21 19=IO20(USB) 20=IO19(USB) 21=G 22=G
# Strapping (IO0/3/45/46), USB (IO19/20), console (IO43/44) and N16R8
# flash/PSRAM pins (IO26-37) stay unconnected. VSNS sits on IO10 (ADC1).
u1a_map = {1: "GND", 21: "GND", 22: "GND",
           4: "CAN_RX", 5: "CAN_TX",                     # IO1/IO2 -> U2 (CAN)
           8: "MOTOR_EN",                               # IO40 -> R11/Q3
           10: "ESTOP",                                 # IO38 -> J9
           16: "ENC_SW", 17: "ENC_B", 18: "ENC_A"}      # IO48/47/21 -> J13
place("U1A", "DevKitC-J3", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x22_P2.54mm_Vertical.kicad_mod",
      22.14, 51.16, rot_deg=90,
      pad_nets={str(k): v for k, v in u1a_map.items()})
u1b_map = {1: "+3V3", 2: "+3V3", 21: "+5V_MCU", 22: "GND",
           4: "NEO",                                    # IO4  -> U3
           5: "IRIN",                                   # IO5  -> IR1
           6: "TEMP",                                   # IO6  -> DST
           7: "BUZ",                                    # IO7  -> R5
           9: "LEDGPIO",                                # IO16 -> R4
           10: "BUSA_DATA",                             # IO17 -> J4/J5
           11: "SCL1", 12: "SDA1",                      # IO18/8 -> J11/J12
           16: "VSNS",                                  # IO10 ADC1 -> R7/R8
           17: "RXA"}                                   # IO11 -> R1
place("U1B", "DevKitC-J1", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x22_P2.54mm_Vertical.kicad_mod",
      22.14, 28.30, rot_deg=90,
      pad_nets={str(k): v for k, v in u1b_map.items()})

# Bus coupling resistor: RX <- DATA through 1k (R2/bus B removed v1.3)
place("R1", "1k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      44.0, 44.0, pad_nets={"1": "BUSA_DATA", "2": "RXA"})

# Schottky on the ESP32 5V feed
place("D1", "1N5820", "Diode_THT.pretty",
      "D_DO-201_P12.70mm_Horizontal.kicad_mod",
      38.0, 58.0, rot_deg=0, pad_nets={"1": "+5V_MCU", "2": "+5V"})

# 5V bulk + decoupling
place("C3", "220uF", "Capacitor_THT.pretty", "CP_Radial_D8.0mm_P3.50mm.kicad_mod",
      78.0, 22.0, pad_nets={"1": "+5V", "2": "GND"})
place("C2", "100nF", "Capacitor_THT.pretty", "C_Disc_D5.0mm_W2.5mm_P2.50mm.kicad_mod",
      56.0, 14.0, pad_nets={"1": "+12V", "2": "GND"})
place("C4", "100nF", "Capacitor_THT.pretty", "C_Disc_D5.0mm_W2.5mm_P2.50mm.kicad_mod",
      82.0, 30.0, pad_nets={"1": "+5V", "2": "GND"})

# I/O ports along bottom edge — horizontal pin rows, y-staggered so the
# pad walls never line up into one long barrier (no sealed pockets).
# Pin headers extend -y from origin, so rot=+90 puts pin1 leftmost.
# (J7/J8 SEA-encoder sockets and J10 wrist UART removed in v1.3 —
# the mid-board strip they sat on is now the relay pocket.)
place("J9", "ESTOP", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x02_P2.54mm_Vertical.kicad_mod", 30.0, 95.0, rot_deg=90,
      pad_nets={"1": "ESTOP", "2": "GND"})

# On-board peripherals — mid-right cluster + bottom-right corner
place("BZ1", "BUZZ5V", "Buzzer_Beeper.pretty",
      "Buzzer_12x9.5RM7.6.kicad_mod", 66.0, 95.0,
      pad_nets={"1": "+5V", "2": "BZC"})
# TO-92 parts go on 2.54mm-pitch pads — spread the leads, hand-solderable
# (the true 1.27mm TO-92 inline pitch can't pass a track to pin 2).
place("Q1", "2N2222A", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x03_P2.54mm_Vertical.kicad_mod", 128.0, 62.0,
      pad_nets={"1": "GND", "2": "BZB", "3": "BZC"})
place("R5", "1k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      112.0, 95.0, rot_deg=90, pad_nets={"1": "BUZ", "2": "BZB"})
place("IR1", "VS1838B", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x03_P2.54mm_Vertical.kicad_mod", 128.0, 36.0,
      pad_nets={"1": "IRIN", "2": "GND", "3": "+3V3"})
# DS18B20 on three spread test pads: a 1x03's mid-pad keepout merges
# with its neighbours and seals the pad entirely — spread pads keep
# every face open. Leads bend to fit; same trick as Q1's TO-92.
_DS = "TestPoint_THTPad_D1.5mm_Drill0.7mm.kicad_mod"
place("DSG", "DS18B20-G", "TestPoint.pretty", _DS, 124.0, 76.0,
      pad_nets={"1": "GND"})
place("DST", "DS18B20-DQ", "TestPoint.pretty", _DS, 127.0, 78.5,
      pad_nets={"1": "TEMP"})
place("DSV", "DS18B20-V", "TestPoint.pretty", _DS, 130.0, 76.0,
      pad_nets={"1": "+3V3"})
place("R6", "4.7k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      112.0, 82.0, pad_nets={"1": "+3V3", "2": "TEMP"})

# Plug-in module sockets — right edge column + bottom strip
place("J11", "OLED", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x04_P2.54mm_Vertical.kicad_mod", 44.0, 95.0, rot_deg=90,
      pad_nets={"1": "GND", "2": "+3V3", "3": "SCL1", "4": "SDA1"})
place("J12", "IMU", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x08_P2.54mm_Vertical.kicad_mod", 93.0, 24.0,
      pad_nets={"1": "+5V", "2": "GND", "3": "SCL1", "4": "SDA1",
                "7": "GND"})
place("J14", "NEOPIX", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x03_P2.54mm_Vertical.kicad_mod", 128.0, 48.0,
      pad_nets={"1": "GND", "2": "NEO5V", "3": "+5V"})
place("J13", "JOG", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x05_P2.54mm_Vertical.kicad_mod", 14.0, 95.0, rot_deg=90,
      pad_nets={"1": "GND", "2": "+3V3", "3": "ENC_SW", "4": "ENC_B",
                "5": "ENC_A"})
# 1x05: under-row dive-lane capacity is ~2 tracks/side; two spare GPIO
# is the most that fits cleanly next to the JOG header's five dives.
place("J15", "SPARE", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x05_P2.54mm_Vertical.kicad_mod", 64.0, 64.0, rot_deg=90,
      pad_nets={"1": "+5V", "2": "GND", "5": "+3V3"})

# --- v1.5 adds (CHECK-pcb14) ---
# F2: 74AHCT125 level-shifts NEO 3V3 -> 5V. Socketed DIP-14 (THT board).
# /OE pins are active-low -> tied to GND so all four buffers stay on;
# only 1A/1Y used (pins 2/3). Unused inputs (5/9/12) also tie to GND —
# floating CMOS inputs oscillate and burn current. Powered from +5V
# (pin14) with C8 100nF decoupling beside it.
# F2 (cont): K1's courtyard reaches x118.55, so the socket rotates 90
# and sits north of the relay; pins 1-7 become the y46 row, 8-14 the
# y38.38 row (pad N x = 109 + (N-1)*2.54 on the 1-7 side).
place("U3", "74AHCT125", "Package_DIP.pretty",
      "DIP-14_W7.62mm_Socket.kicad_mod", 109.0, 46.0, rot_deg=90,
      pad_nets={"1": "GND", "2": "NEO", "3": "NEO_A", "4": "GND",
                "5": "GND", "7": "GND", "9": "GND", "10": "GND",
                "12": "GND", "13": "GND", "14": "+5V"})
# 330R series on the strip data line, south of U3, fed toward J14
place("R13", "330", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      108.0, 50.5, pad_nets={"1": "NEO5V", "2": "NEO_A"})
# NeoPixel strip bulk cap (470-1000uF D10) north of the module area;
# +5V pad lands on the y43.5 feed lane, GND on the pour.
place("C7", "470-1000uF", "Capacitor_THT.pretty",
      "CP_Radial_D10.0mm_P5.00mm.kicad_mod", 102.0, 30.0,
      pad_nets={"1": "+5V", "2": "GND"})
place("C8", "100nF", "Capacitor_THT.pretty",
      "C_Disc_D5.0mm_W2.5mm_P2.50mm.kicad_mod", 112.0, 34.5,
      pad_nets={"1": "+5V", "2": "GND"})
# F4: optional 3V6 zener clamp on RXA (populate only if bench shows the
# bus high level > 3.6 V); cathode lands on the RXA lane.
place("D6", "3V6-opt", "Diode_THT.pretty",
      "D_DO-35_SOD27_P7.62mm_Horizontal.kicad_mod", 54.0, 44.0, rot_deg=90,
      pad_nets={"1": "RXA", "2": "GND"})
# flyback diode for the inductive buzzer: cathode to +5V, anode to BZC
place("D7", "1N4148", "Diode_THT.pretty",
      "D_DO-35_SOD27_P7.62mm_Horizontal.kicad_mod", 66.0, 104.0,
      pad_nets={"1": "+5V", "2": "BZC"})

# v1.2: CAN bus to the 3 printed brushless actuators. TJA1051T/3 transceiver
# (F.Cu SOIC-8), 100nF on VCC and VIO, KK-254 bus port, 120R termination on
# a jumper (CANH -> R9 -> JP2 -> CANL), and a fused 12V output terminal for
# the motor controller boards.
place("U2", "TJA1051T/3", "Package_SO.pretty",
      "SOIC-8_3.9x4.9mm_P1.27mm.kicad_mod", 87.0, 82.0,
      pad_nets={"1": "CAN_TX", "2": "GND", "3": "+5V_MCU", "4": "CAN_RX",
                "5": "+3V3", "6": "CANL", "7": "CANH", "8": "GND"})
place("C5", "100nF", "Capacitor_THT.pretty",
      "C_Disc_D5.0mm_W2.5mm_P2.50mm.kicad_mod",
      84.0, 77.0, pad_nets={"1": "+5V_MCU", "2": "GND"})
place("C6", "100nF", "Capacitor_THT.pretty",
      "C_Disc_D5.0mm_W2.5mm_P2.50mm.kicad_mod",
      89.0, 89.0, pad_nets={"1": "+3V3", "2": "GND"})
place("R9", "120", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      75.0, 88.0, pad_nets={"1": "CAN_TERM", "2": "CANH"})
place("JP2", "CAN-TERM", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x02_P2.54mm_Vertical.kicad_mod", 78.0, 95.0,
      pad_nets={"1": "CAN_TERM", "2": "CANL"})
place("J17", "CAN", "Connector_Molex.pretty",
      "Molex_KK-254_AE-6410-03A_1x03_P2.54mm_Vertical.kicad_mod",
      90.0, 105.0, pad_nets={"1": "GND", "2": "CANH", "3": "CANL"})
place("J18", "12V_MOT", "TerminalBlock_Phoenix.pretty",
      "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.kicad_mod",
      100.0, 105.0, pad_nets={"1": "+12V_MOT", "2": "GND"})
# second switched motor output, same Phoenix 2-pin
place("J20", "12V_MOT", "TerminalBlock_Phoenix.pretty",
      "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.kicad_mod",
      115.0, 105.0, pad_nets={"1": "+12V_MOT", "2": "GND"})

# v1.3: hardware e-stop relay. SRD-12VDC-SL-A: pads 1/2 = coil, 3 = COM,
# 5 = NO (pad 4 absent = NC). Coil: K1.1 +12V, K1.2 RLY_LOW -> J19 -> Q3.
# Contact: COM +12V -> NO +12V_MOT. rot=0 puts NO (K1.5) at the north
# side; the +12V_MOT trunk exits east then drops to the bottom row.
place("K1", "SRD-12V", "Relay_THT.pretty",
      "Relay_SPST_SANYOU_SRD_Series_Form_A.kicad_mod", 100.0, 62.0,
      pad_nets={"1": "+12V", "2": "RLY_LOW", "3": "+12V",
                "5": "+12V_MOT"})
# flyback across the coil: pad1 = cathode (+12V), pad2 = anode (RLY_LOW)
place("D5", "1N4007", "Diode_THT.pretty",
      "D_DO-41_SOD81_P10.16mm_Horizontal.kicad_mod", 86.0, 70.0,
      pad_nets={"1": "+12V", "2": "RLY_LOW"})
place("J19", "ESTOP-NC", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x02_P2.54mm_Vertical.kicad_mod", 92.0, 74.0,
      pad_nets={"1": "RLY_LOW", "2": "RLY_SW"})
place("Q3", "2N2222A", "Connector_PinHeader_2.54mm.pretty",
      "PinHeader_1x03_P2.54mm_Vertical.kicad_mod", 96.0, 82.0,
      pad_nets={"1": "GND", "2": "Q3_B", "3": "RLY_SW"})
place("R11", "1k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      88.0, 96.0, pad_nets={"1": "MOTOR_EN", "2": "Q3_B"})
place("R12", "10k", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      98.0, 96.0, pad_nets={"1": "Q3_B", "2": "GND"})

# LEDs
place("D2", "PWR", "LED_THT.pretty", "LED_D3.0mm.kicad_mod",
      70.0, 68.0, pad_nets={"1": "GND", "2": "LED1_A"})
place("R3", "330", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      54.0, 56.0, pad_nets={"1": "+5V", "2": "LED1_A"})
place("D3", "STAT", "LED_THT.pretty", "LED_D3.0mm.kicad_mod",
      76.0, 56.0, pad_nets={"1": "GND", "2": "LED2_A"})
place("R4", "330", "Resistor_THT.pretty",
      "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal.kicad_mod",
      60.0, 42.0, pad_nets={"1": "LEDGPIO", "2": "LED2_A"})

# Test pads + mounting holes
place("TP1", "GND", "TestPoint.pretty", "TestPoint_THTPad_D1.5mm_Drill0.7mm.kicad_mod",
      74.0, 44.0, pad_nets={"1": "GND"})
place("TP2", "+12V", "TestPoint.pretty", "TestPoint_THTPad_D1.5mm_Drill0.7mm.kicad_mod",
      30.0, 17.0, pad_nets={"1": "+12V"})
for i, (hx, hy) in enumerate([(4, 4), (131, 4), (4, 111), (131, 111)]):
    place(f"H{i+1}", "M3", "MountingHole.pretty",
          "MountingHole_3.2mm_M3_DIN965.kicad_mod", hx, hy)


# ---------------------------------------------------------------------------
# Routing table — net: (width, [waypoints]) — segments on F.Cu.
# (x,y) may be absolute or a (ref, pad) reference resolved below.
# ---------------------------------------------------------------------------

def P(ref, pad):
    return ("PAD", ref, pad)


SEG = []  # (net, width, layer, [pts])
VIA = []  # (x, y, net)


def path(net, width, pts, layer="F.Cu"):
    pts = [C[p[1]].pad(p[2])
           if isinstance(p, tuple) and len(p) == 3 and p[0] == "PAD"
           else p for p in pts]
    SEG.append((net, width, layer, pts))


def via(x, y, net):
    VIA.append((x, y, net))


# ---------------------------------------------------------------------------
# Tiny A* grid router — through-hole pads conduct both layers, so each net
# is routed entirely on one layer and never needs vias.
# ---------------------------------------------------------------------------
import heapq

GRID = 0.127           # 5 mil routing grid
EDGE_KEEP = 1.0        # keep copper this far inside the outline
CLR = 0.2              # copper-to-copper clearance target, mm
PAD_R = 0.85           # THT pad half-size (1.7mm square pads)
obstacles = {"F.Cu": {}, "B.Cu": {}}  # cell -> net that owns the track there
PADS = []              # all pads + mounting holes: (x, y)


def cell(p):
    return (round(p[0] / GRID), round(p[1] / GRID))


def disc_cells(x, y, r):
    out = set()
    for gx in range(int((x - r) / GRID) - 1, int((x + r) / GRID) + 2):
        for gy in range(int((y - r) / GRID) - 1, int((y + r) / GRID) + 2):
            cx, cy = gx * GRID, gy * GRID
            if (cx - x) ** 2 + (cy - y) ** 2 <= r * r:
                out.add((gx, gy))
    return out


def rect_cells(x, y, hx, hy):
    """Grid cells whose centres fall inside the axis-aligned box
    (x±hx, y±hy). Exact keepout shape for rect/oval pads — the old
    disc model covered pad corners but sealed diagonal corridors
    around them (prr=hypot is 0.35mm fatter than the pad edge)."""
    out = set()
    for gx in range(int((x - hx) / GRID) - 1, int((x + hx) / GRID) + 2):
        for gy in range(int((y - hy) / GRID) - 1, int((y + hy) / GRID) + 2):
            cx, cy = gx * GRID, gy * GRID
            if x - hx <= cx <= x + hx and y - hy <= cy <= y + hy:
                out.add((gx, gy))
    return out


def stadium_cells(x, y, hx, hy, m):
    """True clearance keepout for a rect pad: the Minkowski sum of the
    pad box (x±hx,y±hy) with a disc of radius m — straight edges plus
    quarter-disc corners at (±hx,±hy). A plain expanded box (hx+m)x(hy+m)
    would also work but over-covers the corner overhang; corner discs at
    the *expanded* corner (the earlier bug) poke m into inter-pin gaps
    and seal pad approaches entirely."""
    out = set()
    X, Y = hx + m, hy + m
    for gx in range(int((x - X) / GRID) - 1, int((x + X) / GRID) + 2):
        for gy in range(int((y - Y) / GRID) - 1, int((y + Y) / GRID) + 2):
            cx, cy = gx * GRID, gy * GRID
            dx, dy = abs(cx - x), abs(cy - y)
            if (dx <= hx and dy <= Y) or (dy <= hy and dx <= X) \
                    or (dx - hx) ** 2 + (dy - hy) ** 2 <= m * m:
                out.add((gx, gy))
    return out


def block_disc(layer, x, y, r, net):
    # first-writer-wins: a later net's halo must not reassign cells that
    # already belong to an earlier track (losing the owner un-protects it)
    for c in disc_cells(x, y, r):
        obstacles[layer].setdefault(c, net)


OWNCU = {}   # net -> {"F.Cu": set, "B.Cu": set}: cells with real copper
NETW2 = {}   # net -> largest copper half-width marked (via clearance lookup)


def mark_copper(net, layer, x, y, r):
    OWNCU.setdefault(net, {"F.Cu": set(), "B.Cu": set()})[layer].update(
        disc_cells(x, y, r))
    NETW2[net] = max(r, NETW2.get(net, 0.0))


def collect_pads():
    """Gather every pad + mounting hole:
    (x, y, hx, hy, prr, kind, layers, net).
    kind 'circle' -> disc keepout of radius prr; 'box' -> rect keepout of
    half extents hx+m / hy+m (rect and oval pads; exact, unlike the old
    circumscribed-disc which over-blocked pad diagonals)."""
    for ref, c in C.items():
        for num, (px, py, hx, hy, prr, layers) in c.padinfo.items():
            kind = "circle" if prr <= max(hx, hy) + 1e-9 else "box"
            PADS.append((px, py, hx, hy, prr, kind, layers,
                         c.pad_nets.get(num)))
    for ref in ("H1", "H2", "H3", "H4"):
        # M3 hole: 3.2 drill + margin; obstacle on both layers
        PADS.append((C[ref].x, C[ref].y, 1.9, 1.9, 1.9, "circle",
                     ("F.Cu", "B.Cu"), None))


def mark_track(net, width, layer, pts, reserve=None):
    # keep future track centers clear of this track's edge; reserve =
    # half-width of the widest track that may still route after this one
    # (computed from ROUTES order — fat rails run first, so signals only
    # need to defend against other thin signals).
    # +0.15: the disc-union model under-covers the drawn segment polygon
    # at bends/joins — KiCad measures true polygon distance and flags
    # sub-0.2mm grazes without this headroom.
    r = width / 2 + CLR + (0.85 if reserve is None else reserve) + 0.1
    for a, b in zip(pts, pts[1:]):
        steps = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / GRID) + 1)
        for t in range(steps + 1):
            x, y = a[0] + (b[0] - a[0]) * t / steps, a[1] + (b[1] - a[1]) * t / steps
            block_disc(layer, x, y, r, net)
            mark_copper(net, layer, x, y, width / 2 + 0.02)


LNAME = ("F.Cu", "B.Cu")
VIA_COST = 8.0        # mm-equivalent cost; discourages gratuitous vias
VIA_R = 0.65          # via keep-out radius vs pads/marks
VIA_DIA = 0.7         # emitted via annulus diameter (0.3 drill)
VIA_DRILL = 0.3
VIA_PAD = VIA_DIA / 2  # via copper radius


def astar(net, starts, goals, w=0.5, slack=18, extra=(), halo=True):
    """3D A* over (grid cell, layer); returns [(x, y, layer_idx), ...].
    starts/goals: terminal dicts {x, y, r, layers} — r is the pad's own
    half-size so the search can end anywhere on its copper.
    extra: extra start states (cell, layer_idx) — used to seed a leg from
    the net's existing drawn copper, not just terminal pads.
    halo=False: ignore foreign nets' reservation halos — they only exist
    to keep corridors open for nets still to come. Post-order repairs
    (heal) may legally use them; cuobs still enforces true clearance
    against the real copper underneath."""
    # per-layer pad obstacles with ownership: cell -> {pad idx}
    padown = [dict(), dict()]
    for idx, (px, py, hx, hy, prr, kind, layers, pnet) in enumerate(PADS):
        for li, ln in enumerate(LNAME):
            if ln in layers:
                # +0.03 headroom: worst-case true clearance is still
                # CLR+0.03. The old +0.12 made keepout>half-pitch (1.295 vs
                # 1.27) and sealed every inter-pad gap on the 2.54mm rows —
                # guide §3e requires one 0.25 track to fit between pins.
                m = CLR + w / 2 + 0.03
                cells = (disc_cells(px, py, prr + m) if kind == "circle"
                         else stadium_cells(px, py, hx, hy, m))
                for c in cells:
                    padown[li].setdefault(c, set()).add(idx)
    obs_l = (obstacles["F.Cu"], obstacles["B.Cu"])

    # identify which pads are this route's terminals
    tidx = set()
    for t in starts + goals:
        for idx, (px, py, hx, hy, prr, kind, layers, pnet) \
                in enumerate(PADS):
            if (px - t["x"]) ** 2 + (py - t["y"]) ** 2 < 0.16:
                tidx.add(idx)

    def terminal_cells(t):
        out = []
        tr = max(t["r"], t.get("goal_r", 0.0), GRID)
        for c in disc_cells(t["x"], t["y"], tr):
            for li, ln in enumerate(LNAME):
                if ln in t["layers"]:
                    out.append((c, li))
        return out

    # cells on a terminal's own copper: always enterable — a track may land
    # on its pad even where a neighbour's keepout overlaps that copper.
    # (On 2.54mm pitch, a wide route's keepout for pad N swallows N±1's pads.)
    termcu = set()
    for t in starts + goals:
        if t["r"] > 0:   # real pads only; waypoints don't bypass keepouts
            for c in disc_cells(t["x"], t["y"], t["r"]):
                for li in range(len(LNAME)):
                    termcu.add((c, li))

    def blocked(c, li):
        if (c, li) in termcu:
            return False
        owners = padown[li].get(c)
        return owners is not None and bool(owners - tidx)

    owncu = OWNCU.get(net, {"F.Cu": set(), "B.Cu": set()})

    def free(c, li):
        """Cell enterable by this net? Marks of our own net only count if
        they cover real drawn copper — the halo around our track is not
        copper, and landing on it is how dangling stubs happen."""
        if (c, li) in termcu:
            return True
        if blocked(c, li):
            return False
        if c in cuobs[li]:
            return False
        o = obs_l[li].get(c)
        if o is None:
            return True
        if o == net:
            return c in owncu[LNAME[li]]
        # foreign-owned cell: real copper blocks; a bare reservation
        # halo blocks only while routing (halo=True)
        return not halo and c not in OWNCU.get(o, {}).get(LNAME[li], ())

    # precomputed no-via region: pad keepouts on both layers (one set —
    # vias span both). Built once per route, not per search state.
    # VIA_R = via pad (0.35) + CLR (0.2) + 0.1 margin off the pad edge.
    viabad = set()
    for px, py, hx, hy, prr, kind, _, _pnet in PADS:
        viabad |= (disc_cells(px, py, prr + VIA_R) if kind == "circle"
                   else stadium_cells(px, py, hx, hy, VIA_R))

    # via keep-out vs tracks: measure distance to *foreign copper cells*
    # (OWNCU), not to the fat reserve halo in `obstacles` — that halo is
    # w/2+CLR+reserve wide, which demanded a ~2-4mm clear circle and made
    # vias nearly unplaceable. A 0.7mm via only needs CLR to real copper.
    # fcu[layer]: cell -> owning net (the one with the widest copper).
    fcu = (dict(), dict())
    for other, layers in OWNCU.items():
        if other == net:
            continue
        for li, ln in enumerate(LNAME):
            f = fcu[li]
            for c0 in layers[ln]:
                p = f.get(c0)
                if p is None or NETW2.get(other, 0.3) > NETW2.get(p, 0.3):
                    f[c0] = other

    # a foreign copper cell at distance d is a violation iff
    # d < NETW2[owner] + VIA_PAD + CLR. Widest copper half-width is ~0.77
    # (1.5mm rail), so the dangerous radius is <= ~1.33mm — scan a full
    # r=13-cell disc (~1.65mm) sorted nearest-first for early exits.
    _VIA_SCAN = sorted(
        (math.hypot(dx, dy) * GRID, dx, dy)
        for dx in range(-13, 14) for dy in range(-13, 14)
        if dx * dx + dy * dy <= 169)

    # hard floor: foreign copper + vias expanded by THIS net's real
    # half-width. Track marks only reserve for nets still to come in
    # `order` — a fat rail re-routed late by rip-up can otherwise squeeze
    # through a signal's thin halo and lay overlapping copper (the
    # +5V/SDA1 short-class DRC failures).
    _cneed = w / 2 + CLR + 0.03
    cuobs = (dict(), dict())
    _offs = {}
    for other, layers in OWNCU.items():
        if other == net:
            continue
        r2 = NETW2.get(other, 0.3) + _cneed
        offs = _offs.get(r2)
        if offs is None:
            offs = _offs[r2] = disc_cells(0.0, 0.0, r2)
        for li, ln in enumerate(LNAME):
            d = cuobs[li]
            for c0 in layers.get(ln, ()):
                for dx, dy in offs:
                    d[(c0[0] + dx, c0[1] + dy)] = other
    _r_via = VIA_PAD + _cneed
    _voffs = disc_cells(0.0, 0.0, _r_via)
    for vx, vy, vnet in VIA:
        if vnet == net:
            continue
        vc = (int(round(vx / GRID)), int(round(vy / GRID)))
        for dx, dy in _voffs:
            cc = (vc[0] + dx, vc[1] + dy)
            cuobs[0][cc] = vnet
            cuobs[1][cc] = vnet

    def via_ok(cc):
        if cc in viabad:
            return False
        cx, cy = cc
        lim = VIA_PAD + CLR
        for f in fcu:
            get = f.get
            for d, dx, dy in _VIA_SCAN:
                o = get((cx + dx, cy + dy))
                if o is not None and d < NETW2.get(o, 0.3) + lim:
                    return False
        return True

    start_cells = [s for t in starts for s in terminal_cells(t)]
    goal = {g for t in goals for g in terminal_cells(t)}
    # O(1) heuristic: Manhattan distance to the goal centroid. The goal set
    # is one pad/waypoint disc per leg, so centroid distance tracks the true
    # distance closely — and it replaces a min() over the whole set per push.
    _gc = [g[0] for g in goal]
    gx0 = sum(c[0] for c in _gc) / len(_gc)
    gy0 = sum(c[1] for c in _gc) / len(_gc)
    W, H = int(BOARD_W / GRID) - 1, int(BOARD_H / GRID) - 1
    # search window: terminal bbox + slack (keeps local routes cheap)
    bx0 = int((min(t["x"] for t in starts + goals) - slack) / GRID)
    bx1 = int((max(t["x"] for t in starts + goals) + slack) / GRID)
    by0 = int((min(t["y"] for t in starts + goals) - slack) / GRID)
    by1 = int((max(t["y"] for t in starts + goals) + slack) / GRID)
    inside = lambda c: (max(10, bx0) <= c[0] <= min(W - 10, bx1)
                        and max(10, by0) <= c[1] <= min(H - 10, by1))
    start_cells += [s for s in extra if inside(s[0])]
    start_cells = [s for s in start_cells if inside(s[0])]
    openq = [(0, s) for s in start_cells]
    heapq.heapify(openq)
    came, cost = {}, {s: 0 for s in start_cells}
    dirs = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1),
            (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    found = None
    # Node cap: a legit leg explores well under ~400k states; beyond that the
    # goal is sealed and grinding the whole board for 40min helps nobody —
    # fail fast and let the caller retry/report. Whole-board slack retries
    # are the worst offenders — a sealed goal burns a full capped search.
    _CAP = 250000 if slack < 50 else 500000
    _DEADLINE = time.time() + 60    # hard 60 s per leg (ROUTING_GUIDE §7.6)
    while openq:
        if len(cost) > _CAP or time.time() > _DEADLINE:
            found = None
            break
        f, cur = heapq.heappop(openq)
        if cur in goal:
            found = cur
            break
        c2, li = cur
        for dx, dy, d in dirs:
            n2 = (c2[0] + dx, c2[1] + dy)
            if not inside(n2) or not free(n2, li):
                continue
            if dx and dy:                      # no corner-cutting
                if not free((c2[0] + dx, c2[1]), li) \
                        or not free((c2[0], c2[1] + dy), li):
                    continue
            nxt = (n2, li)
            nc = cost[cur] + d
            if nxt not in cost or nc < cost[nxt]:
                cost[nxt] = nc
                h = abs(n2[0] - gx0) + abs(n2[1] - gy0)
                heapq.heappush(openq, (nc + h * 1.4, nxt))
                came[nxt] = cur
        nxt = (c2, 1 - li)                      # layer hop = via
        if not blocked(c2, 1 - li) and via_ok(c2):
            nc = cost[cur] + VIA_COST
            if nxt not in cost or nc < cost[nxt]:
                cost[nxt] = nc
                h = abs(c2[0] - gx0) + abs(c2[1] - gy0)
                heapq.heappush(openq, (nc + h * 1.4, nxt))
                came[nxt] = cur
    if found is None:
        gx = [c[0] for c, _ in cost]; gy = [c[1] for c, _ in cost]
        print(f"  [{net}] explored {len(cost)} states, "
              f"x {min(gx)*GRID:.1f}..{max(gx)*GRID:.1f} "
              f"y {min(gy)*GRID:.1f}..{max(gy)*GRID:.1f} | "
              f"starts {[(t['x'], t['y']) for t in starts]} "
              f"goals {[(t['x'], t['y']) for t in goals]}")
        # Debug: report WHO blocks the goal cells and the cells just
        # outside them — pad keepouts vs another net's track marks.
        own = {}
        for g in goal:
            for li in range(len(LNAME)):
                p = padown[li].get(g[0])
                o = obs_l[li].get(g[0])
                if p:
                    own[f"pad{sorted(p)}@{LNAME[li]}"] = \
                        own.get(f"pad{sorted(p)}@{LNAME[li]}", 0) + 1
                if o is not None:
                    own[f"mark:{o}@{LNAME[li]}"] = \
                        own.get(f"mark:{o}@{LNAME[li]}", 0) + 1
        print(f"  [{net}] goal-cell owners: {own}")
        err = RuntimeError(f"no route for {net}")
        err.blockers = {o[5:o.index("@")] for o in own
                        if o.startswith("mark:")}
        raise err
    path = [found]
    while path[-1] in came:
        path.append(came[path[-1]])
    path.reverse()
    pts = [(gx * GRID, gy * GRID, li) for (gx, gy), li in path]
    # simplify collinear runs within a single layer — index-based so the
    # repair pass below can re-insert skipped cell points
    keep = {0, len(pts) - 1}
    ai = 0
    for i in range(1, len(pts) - 1):
        a, b, cpt = pts[ai], pts[i], pts[i + 1]
        if a[2] != b[2] or b[2] != cpt[2]:
            keep.add(i)
            ai = i
            continue
        cross = ((b[0] - a[0]) * (cpt[1] - b[1])
                 - (b[1] - a[1]) * (cpt[0] - b[0]))
        if abs(cross) > 0.05:
            keep.add(i)
            ai = i
    # chord-vs-pad repair: cell centres stay outside foreign pad
    # keepouts, but a straightened chord between kept points can cut back
    # inside — KiCad measures the emitted segment, not the cells. Where a
    # chord violates the keepout distance, re-insert the skipped point
    # nearest the pad and re-check. Same margin the search used.
    need = CLR + w / 2 + 0.03
    for _pass in range(40):
        idxs = sorted(keep)
        bad = None
        for ia, ib in zip(idxs, idxs[1:]):
            a, b = pts[ia], pts[ib]
            if a[2] != b[2] or ib - ia < 2:
                continue  # via hop or adjacent cells — chord == cell edge
            pln = LNAME[a[2]]
            seglen = math.hypot(b[0] - a[0], b[1] - a[1])
            if seglen < 1e-6:
                continue
            n = max(2, int(seglen / 0.1) + 1)
            for pidx, (px, py, hx, hy, prr, kind, plays, pnet) \
                    in enumerate(PADS):
                if pidx in tidx or pnet == net or pln not in plays:
                    continue
                m = (prr if kind == "circle" else max(hx, hy)) + need
                if (max(a[0], b[0]) < px - m or min(a[0], b[0]) > px + m
                        or max(a[1], b[1]) < py - m
                        or min(a[1], b[1]) > py + m):
                    continue
                viol = False
                for s in range(1, n):
                    cxp = a[0] + (b[0] - a[0]) * s / n
                    cyp = a[1] + (b[1] - a[1]) * s / n
                    if kind == "circle":
                        if (cxp - px) ** 2 + (cyp - py) ** 2 \
                                < (prr + need) ** 2:
                            viol = True
                            break
                    else:
                        ddx, ddy = abs(cxp - px), abs(cyp - py)
                        if (ddx <= hx and ddy <= hy + need) \
                                or (ddy <= hy and ddx <= hx + need) \
                                or (ddx - hx) ** 2 + (ddy - hy) ** 2 \
                                < need * need:
                            viol = True
                            break
                if viol:
                    bad = min(range(ia + 1, ib),
                              key=lambda k: (pts[k][0] - px) ** 2
                              + (pts[k][1] - py) ** 2)
                    break
            # chord-vs-copper: same repair against cuobs — a chord may
            # cut inside foreign copper the cell path legally dodged.
            if bad is None:
                cob = cuobs[a[2]]
                for s in range(1, n):
                    cxp = a[0] + (b[0] - a[0]) * s / n
                    cyp = a[1] + (b[1] - a[1]) * s / n
                    ccx, ccy = round(cxp / GRID), round(cyp / GRID)
                    hit = False
                    for ddx in (-1, 0, 1):
                        for ddy in (-1, 0, 1):
                            if (ccx + ddx, ccy + ddy) in cob:
                                hit = True
                                break
                        if hit:
                            break
                    if hit:
                        bad = min(range(ia + 1, ib),
                                  key=lambda k: (pts[k][0] - cxp) ** 2
                                  + (pts[k][1] - cyp) ** 2)
                        break
            if bad is not None:
                break
        if bad is None:
            break
        keep.add(bad)
    return [pts[i] for i in sorted(keep)]


def term(s):
    """Route endpoint -> terminal dict for astar."""
    if isinstance(s[0], str):
        x, y, hx, hy, prr, layers = C[s[0]].padinfo[s[1]]
        # goal disc = pad's inscribed circle: every cell in it is on copper
        return {"x": x, "y": y, "r": min(hx, hy), "layers": layers}
    # coordinate waypoint: fuzzy goal disc — "near the corridor" counts,
    # and it must NOT bypass pad keepouts (r stays 0 for keepout bypass)
    return {"x": s[0], "y": s[1], "r": 0.0, "goal_r": 1.2,
            "layers": ("F.Cu", "B.Cu")}


def route(net, stops, layer="F.Cu", w=0.5):
    """stops: (ref, pad) tuples or (x, y) waypoints, connected serially.
    The router picks layers itself; `layer` is ignored (kept for the table).

    Each leg is seeded from the net's real copper (OWNCU cells) plus all
    real pad terminals — NOT from fuzzy waypoint discs. Seeding from a
    waypoint disc lets a leg start on cells the previous leg never drew,
    which produced floating stubs that DRC reports as unconnected."""
    res = RESERVE.get(net, 0.85)
    done = [term(stops[0])]
    for s in stops[1:]:
        t = term(s)
        print(f"    {net}: -> ({t['x']:.1f},{t['y']:.1f})")
        extra = [(c, li) for li, ln in enumerate(LNAME)
                 for c in OWNCU.get(net, {}).get(ln, ())]
        try:
            pts3 = astar(net, done, [t], w, extra=extra)
        except RuntimeError:
            pts3 = astar(net, done, [t], w, slack=99, extra=extra)
        # split into contiguous per-layer runs; emit a via at each hop
        run = [pts3[0][:2]]
        li = pts3[0][2]
        for p in pts3[1:]:
            if p[2] != li:
                if len(run) > 1:
                    SEG.append((net, w, LNAME[li], run))
                    mark_track(net, w, LNAME[li], run, res)
                vx, vy = p[0], p[1]
                VIA.append((vx, vy, net))
                for l in LNAME:
                    block_disc(l, vx, vy, VIA_PAD + CLR + res + 0.1, net)
                    mark_copper(net, l, vx, vy, VIA_PAD + 0.02)
                run, li = [p[:2]], p[2]
            else:
                run.append(p[:2])
        if len(run) > 1:
            SEG.append((net, w, LNAME[li], run))
            mark_track(net, w, LNAME[li], run, res)
        # next leg: real pad terminals + exact endpoint (on drawn copper)
        ep = pts3[-1]
        done = [d for d in done if d["r"] >= GRID]
        if t["r"] > 0:
            done.append(t)
        done.append({"x": ep[0], "y": ep[1], "r": 0.3,
                     "layers": (LNAME[ep[2]],)})


# ---------------------------------------------------------------------------
# Route every net through the grid router.
# F.Cu: power rails + servo-bus nets.  B.Cu: the small signal wires
# (through-hole pads conduct both sides, so no vias are needed).
# ---------------------------------------------------------------------------
collect_pads()

ROUTES = [
    # net, stops, layer(hint only), width — guide order: 12V trunk first,
    # then 5V/3V3, then fixed-function (bus/I2C/UART), then GPIOs.
    # Stops are pad refs; the A* fills the path between them.
    # 6 A path (fuse): 2.5 mm trunk — ~5-6 A at 20-30 degC rise on 1 oz
    # (IPC-2221). Dives to each KK-254 pin stay 2.5 mm too: they fit
    # between pads (need 1.45 mm, have 1.69 mm).
    ("+12V_IN", [("J16", "2"), ("J1", "1"), ("JP1", "1"), ("D4", "1")],
     "F.Cu", 2.5),
    ("+12V_SW", [("JP1", "2"), (15.0, 71.46), ("Q2", "2")], "F.Cu", 2.5),
    ("+12V_RP", [("Q2", "3"), ("F1", "1")], "F.Cu", 2.5),
    # F1.2->R7.1 enters the inter-row pocket through the west door
    # (x<19.4 between the two socket rows). The (19,34)/(18.5,22)/(19,14)
    # waypoints then force the fat rail back OUT the door and up the west
    # side — without them A* hugs U1B's north row edge at y~25 and its
    # ~2.4 mm halo seals +5V_MCU's dive channel at (24.7,25.4).
    ("+12V", [("F1", "2"), (18.0, 44.0), (20.0, 44.0), ("R7", "1"),
              (19.0, 34.0), (17.9, 27.5), (18.5, 22.0), (19.0, 14.0),
              ("J3", "1"),
              ("TP2", "1"), (28.0, 4.0),
              (32.5, 5.0), ("J4", "2"), (47.5, 5.0), ("J5", "2"),
              (80.5, 5.0), ("C2", "1"), ("C1", "1"),
              # v1.3: relay feed — east lane down to K1.3 (COM), back
              # west into K1.1 (coil) through the y62 lane between the
              # NO and coil-low pads, then the D5.1 flyback tap.
              (95.0, 8.0), (100.0, 40.0), (112.0, 52.0), (117.0, 60.0),
              (114.0, 65.0), ("K1", "3"), (106.0, 62.0), ("K1", "1"),
              (93.0, 63.0), (87.0, 66.0), ("D5", "1")],
     "F.Cu", 2.5),
    # K1.5 (NO) -> the two motor outputs. Exit east, drop the x~105 slot
    # (west of R6/R5, east of Q3/J19), then along the south edge lane.
    ("+12V_MOT", [("K1", "5"), (106.0, 58.0), (105.0, 70.0),
                  (105.0, 99.0), (100.0, 102.0), ("J18", "1"),
                  (99.0, 109.0), (110.0, 109.0), ("J20", "1")],
     "F.Cu", 2.5),
    # +5V feeds the buck output + NeoPixel: 1.5 mm ~ 3.2 A @10 degC.
    # C4/J12 sit east of the U1B pad wall — at w=1.5 the gap east of
    # U1B.22 is too tight once signals re-route, so come over the top:
    # the y~20 lane between the bus headers and the socket row is open.
    ("+5V", [("J2", "1"), ("J3", "3"), (82.0, 21.0), ("C4", "1"),
             ("J12", "1"),
             ("C3", "1"), (125.5, 44.0), (126.0, 52.2), ("J14", "3"),
             ("U3", "14"), ("C7", "1"), ("C8", "1")],
     "F.Cu", 1.5),
    # v1.3 south tail. J10 — the +5V stepping-stone the old east dive
    # anchored to — is gone, and the relay pocket now fills that strip.
    # These taps are all low-current (buzzer, spare header, the D1/R3 LED
    # island): drop to 0.6 mm so the feed threads the signal lanes the fat
    # rail can't. Descend the proven west-mid lane to the D1/R3 island,
    # around the +5V_MCU wall's west end to J15.1, then the open x64
    # channel to BZ1 — all west of JP2, so CAN_TERM never lists it as a
    # blocker and the rail is never the one ripped.
    ("+5V", [("J3", "3"), (30.0, 46.0), (36.0, 53.0),
             ("D1", "2"), ("R3", "1"), (48.0, 62.0), (56.0, 64.0),
             ("J15", "1"), (64.5, 80.0), (65.5, 90.0), ("BZ1", "1")],
     "F.Cu", 0.6),
    # +5V_MCU: east lane to U1B.2's north dive. The descent must stay
    # EAST of C4 (x87.5 lane between C4's keepout ~86 and J12's ~91.2)
    # — the old x81.3 column sits inside C4.1's keepout and only ever
    # worked via goal-annulus leniency; once re-routed signal marks pile
    # on, it seals. The west-side fix on +12V keeps the dive channel at
    # (24.7,25.4) free of the fat rail's halo on first pass.
    ("+5V_MCU", [("D1", "1"), (80.0, 60.0), (81.3, 45.0), (87.5, 34.0),
                 (87.5, 26.0), (79.0, 25.0), (45.0, 25.5), (24.7, 25.4),
                 ("U1B", "21"),
                 # v1.2: U2 VCC + its 100nF — short drop off the east lane.
                 (82.0, 66.0), ("C5", "1"), ("U2", "3")], "F.Cu", 1.0),
    # +3V3: the U1A pad wall seals the inter-row pocket for w>=0.35 — exit
    # east at x~79, run the east lane south, then west along the bottom
    # to reach J11.2 on the front edge.
    ("+3V3", [("U1B", "1"), ("U1B", "2"), (79.0, 44.0), (79.0, 104.0),
              (46.5, 97.6), ("J11", "2"), ("IR1", "3"),
              ("DSV", "1"), (115.0, 84.8), ("R6", "1"), (74.2, 67.5),
              ("J15", "5"), ("J13", "2"),
              # v1.2: U2 VIO + its 100nF — tees off the x~79 east lane,
              # landing on pad 5 from due south so pad 6's face stays open.
              ("C6", "1"), (89.5, 86.0), ("U2", "5")], "F.Cu", 0.6),
    # fixed-function: servo-bus UART, coupling R1/R2, I2C, wrist UART
    ("BUSA_DATA", [("U1B", "10"), ("R1", "1"), ("J4", "3"),
                   ("J5", "3")], "F.Cu", 0.25),
    # U1B.6's exits seal at random once the U1B-row moat fills; the proven
    # escape (r3 board) is a B.Cu dive diagonal under the row through
    # ~(44,37.5). Pin it so the leg can't be walled at the pad.
    ("RXA", [("U1B", "17"), (44.0, 37.5), ("R1", "2")], "F.Cu", 0.25),
    # Same west-door crossing as SCL1, one lane further west — the two
    # share the x~21.5-22 corridor between F1/+12V copper and U1A.1.
    ("SDA1", [(21.5, 60.0), (21.5, 48.0), (21.5, 26.5),
              (34.0, 26.0), ("U1B", "12"), ("J11", "4"),
              ("J12", "4")], "F.Cu", 0.25),
    # The west-door crossing between F1's keepout (~x19.3) and U1A.1
    # (~x23) stays anchored — the lane is the only clean crossing.
    ("SCL1", [(22.0, 68.0), (22.0, 48.0), (22.0, 26.5),
              (49.5, 26.7), ("U1B", "11"), ("J11", "3"),
              ("J12", "3")], "F.Cu", 0.25),
    # v1.3: MOTOR_EN (was WTX on U1A.15/IO40) -> R11 -> Q3 base.
    ("MOTOR_EN", [("U1A", "8"), (60.0, 60.0), (72.0, 84.0),
                  (80.0, 92.0), ("R11", "1")], "F.Cu", 0.25),
    ("RP_GATE", [("Q2", "1"), ("R10", "1")], "F.Cu", 0.25),
    ("RLY_LOW", [("K1", "2"), ("D5", "2"), ("J19", "1")], "F.Cu", 0.25),
    ("RLY_SW", [("J19", "2"), (92.0, 80.0), (96.0, 90.0), ("Q3", "3")],
     "F.Cu", 0.25),
    ("Q3_B", [("R11", "2"), ("R12", "1"), (100.0, 84.5), ("Q3", "2")],
     "F.Cu", 0.25),
    ("VSNS", [("U1B", "16"), ("R7", "2"), ("R8", "2")], "F.Cu", 0.25),
    # reassigned GPIOs — encoder/ESTOP approach their y95 front-row
    # pads end-on from the south lane (y~97.3): running along the row
    # grazes neighbouring pad edges (DRC clearance 0.15-0.19)
    ("ENC_A", [("U1A", "18"), (30.0, 97.4), (21.6, 97.2),
               ("J13", "5")], "B.Cu", 0.25),
    ("ENC_B", [("U1A", "17"), (30.0, 97.4), (19.1, 97.2),
               ("J13", "4")], "B.Cu", 0.25),
    ("ENC_SW", [("U1A", "16"), (30.0, 97.4), (25.5, 97.2),
                ("J13", "3")], "B.Cu", 0.25),
    ("ESTOP", [("U1A", "10"), (22.0, 56.0), (30.0, 97.4),
               ("J9", "1")], "B.Cu", 0.25),
    # v1.2 CAN group: logic pair to U2, then the CANH/CANL bus pair
    # (0.3mm apart where parallel) and the R9/JP2 termination chain.
    ("CAN_TX", [("U1A", "5"), (80.0, 72.0), ("U2", "1")], "F.Cu", 0.25),
    ("CAN_RX", [("U1A", "4"), (80.5, 75.0), ("U2", "4")], "F.Cu", 0.25),
    ("CANH", [("U2", "7"), (94.0, 79.5), (94.5, 91.5), (84.0, 92.5),
              ("R9", "2"), (85.0, 101.0), ("J17", "2")], "F.Cu", 0.25),
    ("CANL", [("U2", "6"), (92.5, 91.5), ("J17", "3"),
              ("JP2", "2")], "F.Cu", 0.25),
    ("CAN_TERM", [("R9", "1"), ("JP2", "1")], "F.Cu", 0.25),
    # v1.5 F2: NEO (IO4/U1B.4) -> 74AHCT125 -> R13 330R -> J14.2
    ("NEO", [("U1B", "4"), (100.0, 60.0), ("U3", "2")], "B.Cu", 0.25),
    ("NEO_A", [("U3", "3"), ("R13", "2")], "B.Cu", 0.25),
    ("NEO5V", [("R13", "1"), (110.0, 55.0), ("J14", "2")],
     "B.Cu", 0.25),
    ("IRIN", [("U1B", "5"), ("IR1", "1")], "B.Cu", 0.25),
    ("TEMP", [("U1B", "6"), (124.0, 60.0), (124.0, 70.0),
              ("DST", "1"), ("R6", "2")], "B.Cu", 0.25),
    # BUZ's R5.1 dive also comes up the south lane — the old along-row
    # path grazed J10's pad edges (0.17-0.18mm actual)
    ("BUZ", [("U1B", "7"), (100.0, 97.4), (112.0, 97.2),
             ("R5", "1")], "B.Cu", 0.25),
    ("BZB", [("R5", "2"), ("Q1", "2")], "B.Cu", 0.25),
    # v1.2 round 5: pin the whole south corridor. The direct diagonal
    # Q1.3->BZ1.2 clips J10.4's keepout (the +5V goal moat) and any
    # single mid waypoint still lets A* wander north through the DSG/R6
    # cluster or into JP2.2. Run the east edge down, then west at
    # y~99-100 — below the J10 pad row (~96.4 keepout edge), above the
    # J17/J18 pads (~103.9), and south of BUZ's B.Cu lane at y~97.3.
    ("BZC", [("Q1", "3"), (124.0, 86.0), (100.0, 100.0), (82.0, 100.0),
             (75.0, 99.0), ("BZ1", "2")], "B.Cu", 0.25),
    ("LEDGPIO", [("U1B", "9"), ("R4", "1")], "B.Cu", 0.25),
    ("LED1_A", [("R3", "2"), ("D2", "2")], "B.Cu", 0.25),
    ("LED2_A", [("R4", "2"), ("D3", "2")], "B.Cu", 0.25),
]

def route_span(stops):
    pts_of = lambda s: C[s[0]].pad(s[1]) if isinstance(s[0], str) else s
    pts = [pts_of(s) for s in stops]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return max(xs) - min(xs) + max(ys) - min(ys)


# GND backbone first (its walls are bridgeable by vias); then shortest-span
# nets first: short hops can't dodge walls, long rails can
failed = []
# Fat power nets first: they can't squeeze gaps, so they run while the
# board is empty. GND is the backbone tree; then the 12V/5V rails.
# Route groups (ROUTING_GUIDE 3g): 12V trunk, then 5V/3V3 rails, then
# fixed-function (bus UART + I2C + wrist UART), then the free GPIOs.
PWR = {"+12V_IN": 0, "+12V_SW": 0, "+12V_RP": 0, "+12V": 0,
       "+12V_MOT": 0,
       "+5V": 1, "+5V_MCU": 1, "+3V3": 1,
       "BUSA_DATA": 2, "RXA": 2,
       "SDA1": 2, "SCL1": 2,
       "MOTOR_EN": 2, "VSNS": 2,
       "CAN_TX": 3, "CAN_RX": 3, "CANH": 3, "CAN_TERM": 3,
       # CANL in group 2: U2.6's only exit is a ~1mm east channel whose
       # fate depends on what wanders through it first. CANH routed
       # before CANL twice sealed it with a B.Cu dive; CANL must land
       # while the channel is still empty.
       "CANL": 2}
# Signals sort by pinned-waypoint count (descending): the heavily
# constrained corridors (I2C/+3V3/CAN/ENC) lay their lanes first so
# short free-form nets wander around them, not vice-versa.
def _pins(stops):
    return sum(1 for w in stops if not isinstance(w[0], str))


import os
PLACE_ONLY = bool(os.environ.get("PLACE_ONLY"))

order = sorted(ROUTES, key=lambda r: (PWR.get(r[0], 10), -_pins(r[1]),
                                      route_span(r[1])))
ONLY = os.environ.get("ONLY")
if ONLY:
    _sel = set(ONLY.split(","))
    order = [r for r in order if r[0] in _sel]
# per-net mark reserve: half-width of the widest track still to come
RESERVE = {}
_ws = [r[3] for r in order]
for i, (net, _, _, _w) in enumerate(order):
    later = _ws[i + 1:]
    RESERVE[net] = (max(later) / 2) if later else 0.2


def _snap(net):
    return (len(SEG), len(VIA),
            {l: dict(o) for l, o in obstacles.items()},
            {l: set(s) for l, s in OWNCU.get(net, {}).items()},
            NETW2.get(net))


def _undo(net, st):
    n, nv, so, oc, nw = st
    del SEG[n:]
    del VIA[nv:]
    obstacles.clear()
    obstacles.update(so)
    if oc:
        OWNCU[net] = oc
    else:
        OWNCU.pop(net, None)
    if nw is None:
        NETW2.pop(net, None)
    else:
        NETW2[net] = nw


def _rip(net):
    """Rip up every mark/copper cell, segment and via owned by net."""
    for ln in LNAME:
        obs = obstacles[ln]
        for c in [c for c, o in obs.items() if o == net]:
            del obs[c]
    NETW2.pop(net, None)
    OWNCU.pop(net, None)
    SEG[:] = [s for s in SEG if s[0] != net]
    VIA[:] = [v for v in VIA if v[2] != net]


failed = []          # indices into `order`
if not PLACE_ONLY:
    for i, (net, stops, layer, w) in enumerate(order):
        st = _snap(net)
        try:
            route(net, stops, layer, w)
        except RuntimeError:
            _undo(net, st)  # leave no stray copper to wall later nets
            failed.append(i)
            print(f"  deferred {net}")

if not PLACE_ONLY:
    # Rip-up-and-reroute: a deferred net's owner report names the exact
    # nets walling its goals. Rip those up, land the victim, then
    # re-route the ripped nets — the classic autorouter escape.
    for _pass in range(12):
        if not failed:
            break
        progressed = False
        for i in list(failed):
            net, stops, layer, w = order[i]
            st = _snap(net)
            try:
                route(net, stops, layer, w)
                failed.remove(i)
                progressed = True
                print(f"  routed {net} on retry")
                continue
            except RuntimeError as ex:
                _undo(net, st)
                blockers = [b for b in getattr(ex, "blockers", ())
                            if b != net]
                ripped = []
                for b in blockers:
                    if OWNCU.get(b) or any(s[0] == b for s in SEG):
                        _rip(b)
                        ripped += [j for j, e in enumerate(order)
                                   if e[0] == b and j not in failed]
                failed += [j for j in ripped if j not in failed]
                if not ripped:
                    continue
                st = _snap(net)
                try:
                    route(net, stops, layer, w)
                    failed.remove(i)
                    progressed = True
                    print(f"  routed {net} after rip-up {blockers}")
                except RuntimeError:
                    _undo(net, st)
        if not progressed:
            break
if failed:
    # Don't die here: emit the board anyway so heal_unconnected() can
    # attempt pad-level closure of the orphaned terminals, and so DRC —
    # not a waypoint miss — is the final arbiter of connectivity.
    print(f"  WARNING unrouted nets {[order[i][0] for i in failed]} — "
          f"emitting; heal pass will attempt pad-level closure")


def prune_stubs():
    """Drop dead-end copper. Fuzzy waypoint legs leave spurs where a leg
    overshoots the junction point — KiCad flags them as track_dangling.
    Atoms are first split at interior via touches (a via landing mid-run
    is an independent junction), then every atom must attach at BOTH ends
    to a same-net pad, via, endpoint junction, or another segment's body.
    Iterate to chase stub chains."""
    VIA_R = 0.35  # emitted vias are 0.7 mm dia
    atoms = []
    for n, w, layer, pts in SEG:
        atoms += [[n, w, layer, a, b] for a, b in zip(pts, pts[1:])]
    via_pt = {}
    for x, y, n in VIA:
        via_pt.setdefault(n, []).append((x, y))

    # split atoms where a same-net via touches the body
    out = []
    for n, w, l, a, b in atoms:
        vx, vy = b[0] - a[0], b[1] - a[1]
        L2 = vx * vx + vy * vy
        ts = []
        if L2:
            for vxp, vyp in via_pt.get(n, ()):
                t = ((vxp - a[0]) * vx + (vyp - a[1]) * vy) / L2
                if 0.02 < t < 0.98:
                    dx = a[0] + vx * t - vxp
                    dy = a[1] + vy * t - vyp
                    if dx * dx + dy * dy <= (VIA_R + w / 2 + 0.02) ** 2:
                        ts.append(t)
        pts_ = [a] + [(a[0] + vx * t, a[1] + vy * t)
                      for t in sorted(ts)] + [b]
        out += [[n, w, l, u, v] for u, v in zip(pts_, pts_[1:])]
    atoms = out

    def on_pad(n, p):
        for (px, py, hx, hy, prr, kind, plays, pnet) in PADS:
            if pnet != n:
                continue
            if kind == "circle":
                if (p[0] - px) ** 2 + (p[1] - py) ** 2 <= (prr + 0.05) ** 2:
                    return True
            elif abs(p[0] - px) <= hx + 0.05 \
                    and abs(p[1] - py) <= hy + 0.05:
                return True
        return False

    while True:
        ep = {}
        for i, (n, w, l, a, b) in enumerate(atoms):
            ep.setdefault((n, l, round(a[0], 2), round(a[1], 2)),
                          []).append(i)
            ep.setdefault((n, l, round(b[0], 2), round(b[1], 2)),
                          []).append(i)
        # spatial index for interior-touches (T junctions where a leg
        # seeds off the middle of another net's drawn copper)
        cov = {}
        for i, (n, w, l, a, b) in enumerate(atoms):
            for gx in range(int(min(a[0], b[0]) / 0.6) - 1,
                            int(max(a[0], b[0]) / 0.6) + 2):
                for gy in range(int(min(a[1], b[1]) / 0.6) - 1,
                                int(max(a[1], b[1]) / 0.6) + 2):
                    cov.setdefault((n, l, gx, gy), []).append(i)

        def attached(i, p):
            n, w, l = atoms[i][0], atoms[i][1], atoms[i][2]
            if len(ep.get((n, l, round(p[0], 2), round(p[1], 2)), ())) > 1:
                return True
            if on_pad(n, p):
                return True
            r = VIA_R + w / 2 + 0.05
            if any((p[0] - vx) ** 2 + (p[1] - vy) ** 2 <= r * r
                   for vx, vy in via_pt.get(n, ())):
                return True
            for j in cov.get((n, l, int(p[0] / 0.6), int(p[1] / 0.6)), ()):
                if j == i:
                    continue
                _, w2, _, a2, b2 = atoms[j]
                vx2, vy2 = b2[0] - a2[0], b2[1] - a2[1]
                L2 = vx2 * vx2 + vy2 * vy2
                t = 0.0 if L2 == 0 else max(0.0, min(1.0,
                    ((p[0] - a2[0]) * vx2 + (p[1] - a2[1]) * vy2) / L2))
                dx = p[0] - (a2[0] + vx2 * t)
                dy = p[1] - (a2[1] + vy2 * t)
                if dx * dx + dy * dy <= (max(w, w2) / 2 + 0.05) ** 2:
                    return True
            return False

        drop = {i for i, (n, w, l, a, b) in enumerate(atoms)
                if not attached(i, a) or not attached(i, b)}
        if not drop:
            break
        atoms = [a_ for i, a_ in enumerate(atoms) if i not in drop]
        print(f"  pruned {len(drop)} dangling segment(s)")

    SEG[:] = [(n, w, l, [a, b]) for n, w, l, a, b in atoms]


def merge_close_vias():
    """Two same-net vias < ~0.9mm apart share drill space (hole_to_hole).
    A* layer hops can land 2-3 cells apart in tight doors. Snap the later
    via onto the earlier one's centre and retarget nearby segment ends."""
    for i in range(len(VIA)):
        x1, y1, n = VIA[i]
        for j in range(i + 1, len(VIA)):
            x2, y2, n2 = VIA[j]
            if n2 != n or (x1 - x2) ** 2 + (y1 - y2) ** 2 >= 0.81:
                continue
            VIA[j] = (x1, y1, n)
            for si, (sn, w, l, pts) in enumerate(SEG):
                if sn != n:
                    continue
                SEG[si] = (sn, w, l, [
                    (x1, y1) if (px - x2) ** 2 + (py - y2) ** 2 <= 0.36
                    else (px, py) for px, py in pts])
    # drop now-identical via tuples
    seen = set()
    VIA[:] = [v for v in VIA if not (v in seen or seen.add(v))]


merge_close_vias()
prune_stubs()


def heal_unconnected():
    """DRC-style connectivity repair, run after stub pruning.

    KiCad joins copper only on real geometric overlap — the grid router's
    fuzzy endpoint tolerances occasionally leave a pad or a fragment a
    hair short, which DRC reports as unconnected / dangling.  Mirror that
    rule here: union every emitted atom, via and pad that physically
    overlaps; dead copper (no pad anywhere in the component) is dropped;
    atoms with a truly free end are spurs and dropped; then each pad that
    ended up isolated from its net's main component gets one fresh
    bounded A* leg onto that component."""

    def pt_seg_d(p, a, b):
        vx, vy = b[0] - a[0], b[1] - a[1]
        L2 = vx * vx + vy * vy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0,
                ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
        return math.hypot(p[0] - (a[0] + vx * t), p[1] - (a[1] + vy * t))

    def seg_seg_d(a, b, c, d):
        def ccw(p, q, r):
            return (r[1] - p[1]) * (q[0] - p[0]) \
                 - (q[1] - p[1]) * (r[0] - p[0])
        d1, d2, d3, d4 = ccw(c, d, a), ccw(c, d, b), ccw(a, b, c), \
            ccw(a, b, d)
        if (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0):
            return 0.0
        return min(pt_seg_d(a, c, d), pt_seg_d(b, c, d),
                   pt_seg_d(c, a, b), pt_seg_d(d, a, b))

    def on_pad(a, b, w, pad):
        px, py, hx, hy, prr, kind = pad
        n = max(4, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.3))
        for i in range(n + 1):
            t = i / n
            qx, qy = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            if kind == "circle":
                if (qx - px) ** 2 + (qy - py) ** 2 <= (prr + w / 2) ** 2:
                    return True
            elif abs(qx - px) <= hx + w / 2 and abs(qy - py) <= hy + w / 2:
                return True
        return False

    # pad universe straight from the component table (ref, num kept for
    # heal start terminals)
    pads = []
    for ref, c in C.items():
        for num, (px, py, hx, hy, prr, plays) in c.padinfo.items():
            pn = c.pad_nets.get(num)
            if pn is None:
                continue
            kind = "circle" if prr <= max(hx, hy) + 1e-9 else "box"
            pads.append({"ref": ref, "num": num, "net": pn,
                         "shape": (px, py, hx, hy, prr, kind),
                         "layers": plays, "x": px, "y": py})

    def atomize():
        out = []
        for n, w, layer, pts in SEG:
            for a, b in zip(pts, pts[1:]):
                if a != b:
                    out.append([n, w, layer, a, b])
        return out

    atoms = atomize()

    def analyze(atoms):
        """Union atoms+vias+pads on strict overlap. Returns (uf, comp_of,
        comp_pads, comp_atoms) for the CURRENT atom list."""
        NA, NV, NP = len(atoms), len(VIA), len(pads)
        N = NA + NV + NP
        par = list(range(N))

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]
                x = par[x]
            return x

        def union(a_, b_):
            ra, rb = find(a_), find(b_)
            if ra != rb:
                par[ra] = rb

        # spatial buckets: (net, layer, 1mm cell) -> atom indices
        buck = {}
        for i, (n, w, l, a, b) in enumerate(atoms):
            for gx in range(int(min(a[0], b[0]) // 1.0),
                            int(max(a[0], b[0]) // 1.0) + 1):
                for gy in range(int(min(a[1], b[1]) // 1.0),
                                int(max(a[1], b[1]) // 1.0) + 1):
                    buck.setdefault((n, l, gx, gy), []).append(i)

        def near_atoms(n, l, x, y, r=1.6):
            out = set()
            for gx in range(int((x - r) // 1.0), int((x + r) // 1.0) + 1):
                for gy in range(int((y - r) // 1.0),
                                int((y + r) // 1.0) + 1):
                    out.update(buck.get((n, l, gx, gy), ()))
            return out

        # atom-atom, same net+layer: endpoint-share or body overlap
        for i, (n, w, l, a, b) in enumerate(atoms):
            for j in near_atoms(n, l, a[0], a[1]) | \
                      near_atoms(n, l, b[0], b[1]):
                if j <= i:
                    continue
                _, w2, _, a2, b2 = atoms[j]
                lim = (w + w2) / 2 - 0.005
                if seg_seg_d(a, b, a2, b2) <= lim:
                    union(i, j)
        # via edges: via <-> atom overlap on either layer; via <-> pad
        for vi, (vx, vy, vn) in enumerate(VIA):
            node = NA + vi
            for l in ("F.Cu", "B.Cu"):
                for i in near_atoms(vn, l, vx, vy):
                    _, w, _, a, b = atoms[i]
                    if pt_seg_d((vx, vy), a, b) <= VIA_PAD + w / 2 - 0.005:
                        union(node, i)
            for pi, p in enumerate(pads):
                if p["net"] != vn:
                    continue
                x, y, hx, hy, prr, kind = p["shape"]
                r = prr if kind == "circle" else math.hypot(hx, hy)
                if (vx - x) ** 2 + (vy - y) ** 2 <= (r + VIA_PAD) ** 2:
                    union(node, NA + NV + pi)
        # pad <-> atom (pad layers only)
        for pi, p in enumerate(pads):
            node = NA + NV + pi
            for l in p["layers"]:
                for i in near_atoms(p["net"], l, p["x"], p["y"]):
                    n, w, al, a, b = atoms[i]
                    if al == l and on_pad(a, b, w, p["shape"]):
                        union(node, i)
        comp_of = {}
        for i in range(N):
            comp_of.setdefault(find(i), []).append(i)
        return comp_of, NA, NV

    def drop_dead_and_spurs(atoms):
        """Iteratively remove atoms in padless components, then atoms with
        a strictly free endpoint (KiCad's dangling test)."""
        changed = True
        while changed:
            changed = False
            comp_of, NA, NV = analyze(atoms)
            comp_pads = {k: [x for x in v if x >= NA + NV]
                         for k, v in comp_of.items()}
            dead = {k for k, v in comp_pads.items()
                    if not v and any(x < NA for x in comp_of[k])}
            if dead:
                keep = {x for k in dead for x in comp_of[k] if x < NA}
                atoms = [a for i, a in enumerate(atoms) if i not in keep]
                changed = True
                continue
            # free-end spurs: an atom endpoint touching nothing strictly
            ep = {}
            for i, (n, w, l, a, b) in enumerate(atoms):
                ep.setdefault((n, l, round(a[0], 2), round(a[1], 2)),
                              []).append(i)
                ep.setdefault((n, l, round(b[0], 2), round(b[1], 2)),
                              []).append(i)

            def free_end(i, p):
                n, w, l = atoms[i][0], atoms[i][1], atoms[i][2]
                if len(ep.get((n, l, round(p[0], 2), round(p[1], 2)),
                              ())) > 1:
                    return False
                for px, py, hx, hy, prr, kind, plays, pn in PADS:
                    if pn != n or l not in plays:
                        continue
                    if kind == "circle":
                        if (p[0] - px) ** 2 + (p[1] - py) ** 2 \
                                <= (prr + w / 2) ** 2:
                            return False
                    elif abs(p[0] - px) <= hx + w / 2 \
                            and abs(p[1] - py) <= hy + w / 2:
                        return False
                for vx, vy, vn in VIA:
                    if vn == n and (p[0] - vx) ** 2 + (p[1] - vy) ** 2 \
                            <= (VIA_PAD + w / 2 - 0.005) ** 2:
                        return False
                for j, (n2, w2, l2, a2, b2) in enumerate(atoms):
                    if j == i or n2 != n or l2 != l:
                        continue
                    # endpoint must sit ON the other's copper — inside its
                    # half-width — not merely within both half-widths
                    if pt_seg_d(p, a2, b2) <= w2 / 2 - 0.005:
                        return False
                return True

            drop = {i for i, (n, w, l, a, b) in enumerate(atoms)
                    if free_end(i, a) or free_end(i, b)}
            if drop:
                atoms = [a for i, a in enumerate(atoms) if i not in drop]
                print(f"  strict-pruned {len(drop)} spur atom(s)")
                changed = True
        return atoms

    def emit_leg(net, w, pts3):
        if len(pts3) < 2:
            return 0
        run = [pts3[0][:2]]
        li = pts3[0][2]
        for p in pts3[1:]:
            if p[2] != li:
                if len(run) > 1:
                    SEG.append((net, w, LNAME[li], run))
                    mark_track(net, w, LNAME[li], run)
                # dedup: a second same-net via within 0.4mm is a
                # hole_to_hole violation, not a connection
                if not any((p[0] - vx) ** 2 + (p[1] - vy) ** 2 <= 0.16
                           for vx, vy, vn in VIA if vn == net):
                    VIA.append((p[0], p[1], net))
                for l in LNAME:
                    block_disc(l, p[0], p[1],
                               VIA_PAD + CLR + 0.95, net)
                    mark_copper(net, l, p[0], p[1], VIA_PAD + 0.02)
                run, li = [p[:2]], p[2]
            else:
                run.append(p[:2])
        if len(run) > 1:
            SEG.append((net, w, LNAME[li], run))
            mark_track(net, w, LNAME[li], run)
        return len(pts3)

    atoms = drop_dead_and_spurs(atoms)
    SEG[:] = [(n, w, l, [a, b]) for n, w, l, a, b in atoms]

    tried = set()
    for _round in range(8):
        # orphan pads: no same-net atom strictly touches them — exactly
        # what KiCad reports as unconnected. Heal each once.
        atoms_now = atomize()
        for pi, pd in enumerate(pads):
            if pd["net"] == "GND" or pi in tried:
                continue
            if any(n == pd["net"] and l in pd["layers"]
                   and on_pad(a, b, w, pd["shape"])
                   for n, w, l, a, b in atoms_now):
                continue
            tried.add(pi)
            # goal: nearest same-net atom midpoint, per layer present
            def dist_a(i):
                _, _, _, a, b = atoms_now[i]
                return math.hypot((a[0] + b[0]) / 2 - pd["x"],
                                  (a[1] + b[1]) / 2 - pd["y"])
            goals, wleg = [], 0.25
            for l in ("F.Cu", "B.Cu"):
                cand = [i for i in range(len(atoms_now))
                        if atoms_now[i][0] == pd["net"]
                        and atoms_now[i][2] == l]
                if not cand:
                    continue
                i = min(cand, key=dist_a)
                n2, wleg, l2, a2, b2 = atoms_now[i]
                goals.append({"x": (a2[0] + b2[0]) / 2,
                              "y": (a2[1] + b2[1]) / 2,
                              "r": 0.12, "layers": (l,)})
            if not goals:
                # fully-unrouted net (router gave up): aim a leg at the
                # nearest same-net *pad* — the first emitted leg seeds
                # this net's copper so later orphans can join it.
                sib = [q for q in pads
                       if q["net"] == pd["net"] and q is not pd]
                if not sib:
                    continue
                q = min(sib, key=lambda q: math.hypot(q["x"] - pd["x"],
                                                      q["y"] - pd["y"]))
                goals = [{"x": q["x"], "y": q["y"],
                          "r": min(q["shape"][2], q["shape"][3]),
                          "layers": q["layers"]}]
                wleg = next(w for n, _s, _l, w in ROUTES
                            if n == pd["net"])
            starts = [{"x": pd["x"], "y": pd["y"],
                       "r": min(pd["shape"][2], pd["shape"][3]),
                       "layers": pd["layers"]}]
            try:
                pts3 = astar(pd["net"], starts, goals, wleg, slack=99,
                             halo=False)
            except RuntimeError:
                if wleg > 0.25:
                    # declared width can't fit — try an emergency link
                    try:
                        pts3 = astar(pd["net"], starts, goals, 0.25,
                                     slack=99, halo=False)
                        wleg = 0.25
                    except RuntimeError:
                        print(f"  heal: {pd['net']} {pd['ref']}."
                              f"{pd['num']} FAILED")
                        continue
                else:
                    print(f"  heal: {pd['net']} {pd['ref']}.{pd['num']} "
                          f"FAILED")
                    continue
            emit_leg(pd["net"], wleg, pts3)
            print(f"  heal: {pd['net']} {pd['ref']}.{pd['num']} "
                  f"orphan -> net ({len(pts3)} cells)")
            atoms_now = atomize()

        comp_of, NA, NV = analyze(atomize())
        # per-net: which components hold pads
        net_comps = {}
        for k, v in comp_of.items():
            pn = None
            for x in v:
                if x >= NA + NV:
                    pn = pads[x - NA - NV]["net"]
                    break
            net_comps.setdefault(pn, []).append(k)
        healed = False
        for net, ks in net_comps.items():
            if net in (None, "GND") or len(ks) < 2:
                continue
            # main comp: most pads, then most atoms
            def score(k):
                v = comp_of[k]
                return (sum(x >= NA + NV for x in v),
                        sum(x < NA for x in v))
            main = max(ks, key=score)
            atoms_now = atomize()
            main_atoms = [x for x in comp_of[main] if x < NA]
            for k in ks:
                if k == main:
                    continue
                comp_pads = [x - NA - NV for x in comp_of[k] if x >= NA + NV]
                if not comp_pads:
                    continue
                p0 = min(comp_pads, key=lambda pi: pads[pi]["num"])
                if p0 in tried:
                    continue
                tried.add(p0)
                pd = pads[p0]
                # goal(s): nearest main-comp atom midpoint per layer
                def dist_to(i):
                    _, _, _, a, b = atoms_now[i]
                    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                    return math.hypot(mx - pd["x"], my - pd["y"])
                goals = []
                for l in ("F.Cu", "B.Cu"):
                    cand = [i for i in main_atoms
                            if atoms_now[i][2] == l]
                    if not cand:
                        continue
                    i = min(cand, key=dist_to)
                    n2, w2, l2, a2, b2 = atoms_now[i]
                    goals.append({"x": (a2[0] + b2[0]) / 2,
                                  "y": (a2[1] + b2[1]) / 2,
                                  "r": 0.12, "layers": (l,)})
                wleg = atoms_now[min(main_atoms, key=dist_to)][1]
                starts = [{"x": pd["x"], "y": pd["y"],
                           "r": min(pd["shape"][2], pd["shape"][3]),
                           "layers": pd["layers"]}]
                # also seed from the orphan comp's own copper endpoints
                for x in comp_of[k]:
                    if x < NA:
                        n3, w3, l3, a3, b3 = atoms_now[x]
                        for e in (a3, b3):
                            starts.append({"x": e[0], "y": e[1], "r": 0.2,
                                           "layers": (l3,)})
                try:
                    pts3 = astar(net, starts, goals, wleg, slack=99,
                                 halo=False)
                except RuntimeError:
                    print(f"  heal: {net} {pd['ref']}.{pd['num']} "
                          f"leg FAILED")
                    continue
                emit_leg(net, wleg, pts3)
                print(f"  heal: {net} {pd['ref']}.{pd['num']} -> "
                      f"main comp ({len(pts3)} cells)")
                healed = True
        if not healed:
            break
        atoms = drop_dead_and_spurs(atomize())
        SEG[:] = [(n, w, l, [a, b]) for n, w, l, a, b in atoms]

    # final report: pads still split off their net's main component
    comp_of, NA, NV = analyze(atomize())
    pad_roots = {}
    for pi, p in enumerate(pads):
        if p["net"] == "GND":
            continue
        pad_roots.setdefault(p["net"], {}).setdefault(
            next(k for k, v in comp_of.items() if NA + NV + pi in v),
            []).append(f"{p['ref']}.{p['num']}")
    for net, roots in pad_roots.items():
        if len(roots) > 1:
            print(f"  heal: WARNING {net} still split: {roots}")


# PLACE_ONLY emits no copper, so there is nothing to heal — and letting it
# run would fire one bounded A* leg per pad into a throwaway file anyway.
if not PLACE_ONLY:
    heal_unconnected()


# ---------------------------------------------------------------------------
# Emit the .kicad_pcb
# ---------------------------------------------------------------------------

TEMPLATE = (KICAD_LIB.parent / "template" / "RaspberryPi-HAT"
            / "RaspberryPi-HAT.kicad_pcb")


def template_header():
    """Everything from a real board file up to its net list."""
    txt = TEMPLATE.read_text()
    end = txt.index("\t(net ")
    return txt[:end]


def seg_sexp(net, width, layer, pts):
    out = []
    for a, b in zip(pts, pts[1:]):
        out.append(
            f'\t(segment\n\t\t(start {a[0]:.3f} {a[1]:.3f})'
            f'\n\t\t(end {b[0]:.3f} {b[1]:.3f})\n\t\t(width {width})'
            f'\n\t\t(layer "{layer}")\n\t\t(net {NET_ID[net]})'
            f'\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
    return out


def label(text, x, y, size=1.3, layer="F.SilkS", rot_deg=0):
    justify = "\n\t\t\t\t(justify mirror)" if layer.startswith("B.") else ""
    return (f'\t(gr_text "{text}"\n\t\t(at {x} {y} {rot_deg})'
            f'\n\t\t(layer "{layer}")\n\t\t(uuid "{uuid.uuid4()}")'
            f'\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})'
            f'\n\t\t\t\t(thickness {size*0.18:.3f})\n\t\t\t){justify}'
            '\n\t\t)\n\t)')


def build_pcb():
    parts = [template_header()]
    parts += [f'\t(net {i} "{n}")\n' for i, n in enumerate([""] + NETS)]

    for c in C.values():
        parts.append(c.src.rstrip() + "\n")

    # edge cuts — one rect on Edge.Cuts
    parts.append(
        f'\t(gr_rect\n\t\t(start 0 0)\n\t\t(end {BOARD_W} {BOARD_H})'
        '\n\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type solid)\n\t\t)'
        '\n\t\t(fill no)\n\t\t(layer "Edge.Cuts")'
        f'\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')

    for l in [
        label("SOMA BASE CARRIER v1.5", 60, 108, 1.8),
        label("12V IN", 16, 45, 1.0), label("5V IN", 16, 33.5, 1.0),
        label("XT60", 10.5, 10.5, 1.0),
        label("PWR-ON", 10, 55, 1.0),
        label("TVS", 24, 63, 1.0),
        label("BUS-A x2 (STS3215)", 38, 4.6, 1.0),
        label("G", 30, 13.8, 1.0), label("V", 32.54, 13.8, 1.0),
        label("D", 35.08, 13.8, 1.0),
        label("G", 45, 13.8, 1.0), label("V", 47.54, 13.8, 1.0),
        label("D", 50.08, 13.8, 1.0),
        label("ESTOP", 31.3, 100, 1.0),
        label("MINI-360", 26, 25.2, 1.0),
        label("OLED G-3V3-SCL-SDA", 47.8, 99.5, 1.0),
        label("IMU GY-521", 93, 44, 1.0),
        label("NEO G-D-5V", 128, 56.5, 1.0),
        label("JOG G-3V-SW-B-A", 19, 99.5, 1.0),
        label("SPARE 5V-G-3V3", 69, 74.5, 1.0),
        label("IR", 128, 32, 1.0), label("TEMP", 127, 72, 1.0),
        label("Q1 EBC", 128, 70.5, 1.0),
        label("BUZ", 70, 90, 1.0),
        label("DevKitC-1 USB->W", 85, 52.5, 1.0),
        label("TOP=J1 BOT=J3", 103, 52.6, 1.0),
        label("PWR", 75.4, 68, 1.0), label("STAT", 82, 56.5, 1.0),
        label("10A", 17, 70.5, 1.0),
        label("CAN G-H-L", 82, 101.5, 1.0),
        label("12V MOT x2", 105.5, 111, 1.0),
        label("ESTOP-NC", 84, 73.5, 1.0),
        label("FIT JUMPER OR NC E-STOP", 106, 73.5, 1.0),
        # v1.5 additions
        label("ONE 5V SRC ONLY", 16, 26.5, 1.0),
        label("Q2 TAB=D", 20, 78, 1.0),
        label("74AHCT125", 116.6, 43.5, 1.0),
        label("D6 OPT 3V6", 56, 33.5, 1.0),
        label("BZ FLYBK", 80, 108, 1.0),
        label("github.com/Riyu-D1/Vector", 35, 105, 1.0, "B.SilkS"),
    ]:
        parts.append(l + "\n")

    for net, w, layer, pts in SEG:
        parts.extend(s + "\n" for s in seg_sexp(net, w, layer, pts))
    for x, y, net in VIA:
        parts.append(
            f'\t(via\n\t\t(at {x:.3f} {y:.3f})\n\t\t(size {VIA_DIA})'
            f'\n\t\t(drill {VIA_DRILL})'
            f'\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net {NET_ID[net]})'
            f'\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')

    # GND pours on BOTH layers — full board, 0.5mm clearance, 0.3 min
    # width, solid pad connect (ROUTING_GUIDE 3a).  fill_zones.py emits
    # the filled_polygon geometry; in the GUI, B re-fills.
    for zlayer in ("B.Cu", "F.Cu"):
        parts.append(
            f'\t(zone\n\t\t(net {NET_ID["GND"]})\n\t\t(net_name "GND")'
            f'\n\t\t(layer "{zlayer}")'
            f'\n\t\t(uuid "{uuid.uuid4()}")\n\t\t(name "GND")'
            '\n\t\t(hatch full 0.508)'
            '\n\t\t(connect_pads thru_hole_only\n\t\t\t(clearance 0.5)\n\t\t)'
            '\n\t\t(min_thickness 0.3)'
            '\n\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname "")\n\t\t)'
            '\n\t\t(fill yes\n\t\t\t(thermal_gap 0.5)\n\t\t\t(thermal_bridge_width 0.65)'
            '\n\t\t\t(island_removal_mode 1)\n\t\t\t(island_area_min 10.0)\n\t\t)'
            f'\n\t\t(polygon\n\t\t\t(pts\n\t\t\t\t(xy 0.5 0.5)'
            f'\n\t\t\t\t(xy {BOARD_W-0.5} 0.5)'
            f'\n\t\t\t\t(xy {BOARD_W-0.5} {BOARD_H-0.5})'
            f'\n\t\t\t\t(xy 0.5 {BOARD_H-0.5})\n\t\t\t)\n\t\t)\n\t)\n')

    # GND stitching vias every ~15 mm where free (0.6 via / 0.3 drill):
    # skip cells within another net's mark halo or copper, and pads.
    def _gnd_via_free(gx, gy):
        for (px, py, hx, hy, prr, kind, _l, _n) in PADS:
            if kind == "circle":
                if (gx - px) ** 2 + (gy - py) ** 2 <= (prr + 1.6) ** 2:
                    return False
            elif abs(gx - px) <= hx + 1.6 and abs(gy - py) <= hy + 1.6:
                return False
        r = int(1.3 / GRID) + 1
        cx, cy = cell((gx, gy))
        for ln in LNAME:
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if obstacles[ln].get((cx + dx, cy + dy)) not in (
                            None, "GND"):
                        return False
        return True

    for gx in range(10, int(BOARD_W) - 5, 15):
        for gy in range(10, int(BOARD_H) - 5, 15):
            if _gnd_via_free(gx, gy):
                parts.append(
                    f'\t(via\n\t\t(at {gx} {gy})\n\t\t(size 0.6)'
                    '\n\t\t(drill 0.3)'
                    '\n\t\t(layers "F.Cu" "B.Cu")'
                    f'\n\t\t(net {NET_ID["GND"]})'
                    f'\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')

    parts.append('\t(embedded_fonts no)\n)\n')
    return "".join(parts)


def build_pro():
    return """{
  "board": {"design_settings": {}, "ipc2581": {}, "layers": []},
  "boards": [],
  "cvpcb": {"equivalence_files": []},
  "libraries": {"loaded_footprint_libraries": [], "loaded_symbol_libraries": []},
  "meta": {"filename": "soma-carrier-v15.kicad_pro", "version": 1},
  "net_settings": {"classes": [], "class_patterns": [], "meta": {"version": 3}},
  "project": {"files": []},
  "schematic": {"annotate_start_num": 0, "drawing": {}, "legacy_lib_dir": "",
                "legacy_lib_list": [], "meta": {"version": 1},
                "net_format_name": "", "page_layout_descr_file": "",
                "plot_directory": "", "spice_adjust_passive_values": false,
                "spice_command_net": "spice", "spice_external_command": "",
                "spice_model_current_sheet_as_root": false,
                "spice_save_all_currents": false,
                "spice_save_all_voltages": false, "subpart_first_id": 65,
                "subpart_id_separator": 0},
  "sheets": [],
  "text_variables": {}
}
"""


if __name__ == "__main__":
    # PLACE_ONLY/ONLY write a side file so a placement or probe run can
    # never clobber a routed soma-carrier-v15.kicad_pcb.
    name = "soma-carrier-v15.placeonly.kicad_pcb" if (PLACE_ONLY or ONLY) \
        else "soma-carrier-v15.kicad_pcb"
    (OUT / name).write_text(build_pcb())
    (OUT / "soma-carrier-v15.kicad_pro").write_text(build_pro())
    print(f"wrote {OUT/name}")
    for ref, c in C.items():
        print(f"  {ref}: {len(c.pads)} pads at {c.x},{c.y}")
        if os.environ.get("PAD_DUMP"):
            for n, (px, py) in sorted(c.pads.items(),
                                      key=lambda t: int(t[0])):
                print(f"      {ref}.{n} = ({px:.2f},{py:.2f})")
