"""toolchg/tc_analysis.py - Task 1/4c numbers: mass + static torque impact
of the coupling, driven by soma_arm.gravity (the tested D9 model).

  Scenarios, all J6-out mass re-point-massed from tc_parts volumes:
    stock      - D6 grip body as shipped (gravity.py PARTS)
    tool_swap  - master + grip tool (each tool carries its STS3215)
    finger_swap- D6 grip stays on arm; tools are passive finger sets

  Poses: AB (arm horizontal = worst J2/J3/J4 gravity), home, reach.
Run:  python3 tc_analysis.py   (numpy only; no CAD env needed)"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "software", "robot-os"))
from soma_arm import config
from soma_arm import gravity as G

G9 = 9.81

# ---- J6-out mass scenarios (kg, grip-body local centroid mm in the grip
# frame: x = tool dir, z = lateral, y = up; the grip frame origin sits on
# the J6 axis).  Stock numbers verbatim from gravity.PARTS rows 'grip'.
GRIP_ORIGIN_MM = np.array([276.1, 0.0, 72.5])   # AB pose grip origin
STOCK = [(m, (np.array(c) - GRIP_ORIGIN_MM) / 1000.0)
         for b, m, c in G.PARTS if b == "grip"]

def _centroid(parts):
    m = sum(p[0] for p in parts)
    return m, sum(p[0] * p[1] for p in parts) / m

m_stock, c_stock = _centroid(STOCK)
print("stock J6-out: %.4f kg, centroid %s m" % (m_stock, c_stock.round(4)))

# tool-swap J6-out = tc_master + grip tool (print vols * rho*infill +
# vendor servo/gear/racks/fingers + pogo/screws [U estimates])
RHO = 1.31e-3 * 0.6          # g/mm3 printed effective [U same as ap6]
def pv(cm3):
    return cm3 * RHO         # cm3*1000 mm3 * g/mm3 / 1000 -> kg

# volumes from build_toolchg printout (cm3), centroids in W mm
# (D12 re-measured on the fixed geometry: 7.33/23.52/2.35/1.27/1.53)
MASTER_V, MASTER_C = 7.33, np.array([69.0, 0.0, -17.0])
GRIP_V, GRIP_C = 23.52, np.array([95.0, 0.0, -30.0])
RACK_V, RACK_C = 2.35, np.array([131.0, 0.0, -17.0])
FING_V, FING_C = 1.27, np.array([142.0, 0.0, -17.0])
GEAR_V, GEAR_C = 1.53, np.array([131.0, 0.0, -17.0])
SV_M, SV_C = 0.055, np.array([102.0, 0.0, -33.0])     # STS3215 + plug
GEAR_M = 0.008
parts_ts = [
    (pv(MASTER_V), MASTER_C), (pv(GRIP_V), GRIP_C), (SV_M, SV_C),
    (GEAR_M, GEAR_C), (pv(RACK_V), RACK_C), (pv(RACK_V), RACK_C),
    (pv(FING_V), FING_C), (pv(FING_V), FING_C),
    (0.002, np.array([76.0, 0.0, -17.0])),            # pogo+pads+screws [U]
]
# W (a,b,h) mm -> grip-local m: the grip body origin is the J6 joint,
# which sits at W a=53.0, b=0, h=-17.0 (verified via kinematics: J6 at
# world (149.4,0,199.2) = W (53,0,-17)).  Stock J6-out centroid lands at
# W (104.3, 0, -25) - on the g-servo mass, sanity OK.
W_ORIGIN = np.array([53.0, 0.0, -17.0])
def wl(p):
    return (p - W_ORIGIN) / 1000.0

m_ts, c_ts = _centroid([(m, wl(c)) for m, c in parts_ts])
print("tool-swap J6-out: %.4f kg, centroid %s m" % (m_ts, c_ts.round(4)))

# finger-swap: the arm permanently carries the whole grip mechanism; the
# swapped finger set comes back on board when a grip tool is docked, so
# J6-out while gripping = stock + master.  Carrying a passive tool (pen)
# it is stock - racks - fingers - gear + master + tool.
m_fs = m_stock + pv(MASTER_V)
print("finger-swap J6-out while gripping: %.4f kg" % m_fs)

# ---------- torque impact at key poses ----------
POSES = {
    "AB (horiz)": np.array([0.0, math.pi / 2, -math.pi / 2, 0, 0, 0]),
    "home": np.zeros(6),
    "reach": np.array([0.0, math.radians(60), math.radians(-70), 0, 0, 0]),
}

def delta_report(name, dm_grip, dc_m, tcp_dx):
    """dm_grip: added kg on grip body at centroid offset dc_m (m, +x fwd);
    tcp_dx: TCP shift +x (m) applied to the payload lever."""
    print("\n== %s ==" % name)
    for pname, q in POSES.items():
        tau0 = G.gravity_torques(q, 0.5)
        geo, tcp, T = G._joint_geometry(q)
        gvec = np.array([0.0, 0.0, -G9])
        # grip-body frame
        Og, Rg = T["grip"][:3, 3], T["grip"][:3, :3]
        c_world = Og + Rg @ (c_stock + dc_m)
        tcp2 = tcp + Rg @ np.array([tcp_dx, 0.0, 0.0])
        tau = tau0.copy()
        for i in range(6):
            p_i, a_i = geo[i]
            tau[i] += dm_grip * np.dot(np.cross(c_world - p_i, gvec), a_i)
            tau[i] += 0.5 * np.dot(np.cross(tcp2 - tcp, gvec), a_i)
        ratio = [abs(tau[i]) / (0.8 * config.RATED_TORQUE_NM[i])
                 for i in range(6)]
        print("  %-11s J2 %.3f->%.3f  J3 %.3f->%.3f  J4 %.3f->%.3f"
              "  worst ratio %.2f (J%d)"
              % (pname, tau0[1], tau[1], tau0[2], tau[2], tau0[3], tau[3],
                 max(ratio), int(np.argmax(ratio)) + 1))

# tool-swap: replace stock grip mass by tool-swap mass at new centroid
dm = m_ts - m_stock
dc = c_ts - c_stock
delta_report("TOOL SWAP (each tool has its servo)", dm, dc, 0.012)
# finger-swap: keep stock, add master only (tools passive)
delta_report("FINGER SWAP (arm keeps grip mech)", pv(MASTER_V),
             wl(MASTER_C) - c_stock, 0.012)

# ---------- payload bound shift (the operative margin) ----------
print("\n== max_payload (80%% derated) ==")
q = POSES["reach"]
mp0, lim0, _ = G.max_payload(q)
print("stock reach-pose max payload %.3f kg (limit J%d)" % (mp0, lim0 + 1))
# tool-swap: delta torque scales the bound by delta-link-torque / k
geo, tcp, T = G._joint_geometry(q)
gvec = np.array([0.0, 0.0, -G9])
Og, Rg = T["grip"][:3, 3], T["grip"][:3, :3]
c_world = Og + Rg @ c_ts
k2 = float(np.dot(np.cross(tcp - geo[1][0], gvec), geo[1][1]))
dt = dm * float(np.dot(np.cross(c_world - geo[1][0], gvec), geo[1][1]))
print("tool-swap: d_tau_J2 %+.4f Nm -> d_payload %+.3f kg"
      % (dt, -dt / abs(k2)))
