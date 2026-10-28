"""SOMA arm viewer.  mjpython sim/view.py manual   -> arm holds home; move joints with the Control panel sliders (double-click + ctrl+right-drag to perturb)
                     mjpython sim/view.py demo     -> looping showcase routine: each axis alone, then combined moves, gripper open/close
                     mjpython sim/view.py sweep    -> each actuator swept through its range in turn (4 s each)
Close the window to quit.  The base is fixed to the world; there is no free base to drag."""
import sys, time, pathlib, numpy as np, mujoco, mujoco.viewer
mode = sys.argv[1] if len(sys.argv) > 1 else "manual"
m = mujoco.MjModel.from_xml_path(str(pathlib.Path(__file__).parent / "scene.xml")); d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, m.key("home").id)
jq = [m.jnt_qposadr[m.actuator_trnid[a, 0]] for a in range(m.nu)]
base = np.array([d.qpos[q] for q in jq]); d.ctrl[:] = base
lim = []
for a in range(m.nu):
    lo, hi = m.jnt_range[m.actuator_trnid[a, 0]]; lim.append((lo, hi))
SEG = 4.0
D = np.radians
# demo: a SERIES of coordinated routines, played back to back and looped. Each waypoint = (J1..J6 deg, finger mm, seconds to get there).
# One smooth closed spline passes through every waypoint, so all joints move together and the arm never stops between moves.
HOME = (0,0,0,0,0,0,0)
SERIES = {
 "1 pick and place": [(35,-25,-45,20,-15,50,12.5,2.2),(45,-35,-60,30,-20,90,12.5,1.5),(45,-35,-60,30,-20,90,0,0.8),
                      (10,-15,-40,10,10,20,0,2.0),(-35,-10,-45,-20,20,-60,0,2.4),(-40,-15,-50,-30,10,-90,12.5,1.2)],
 "2 wide sweep":      [(-60,-20,-40,25,0,-60,12.5,2.0),(-20,5,-20,-15,20,0,12.5,1.8),(20,-30,-60,30,-20,60,12.5,1.8),(60,0,-30,-25,25,120,12.5,2.0),(20,-30,-60,30,-20,60,12.5,2.0)],
 "3 reach and wave":  [(0,-45,-20,40,0,0,12.5,2.0),(0,-30,-10,-30,30,90,0,1.6),(15,-30,-10,30,-30,-90,12.5,1.6),(-15,-30,-10,-30,30,90,0,1.6),(15,-30,-10,30,-30,-90,12.5,1.6)],
 "4 fold and unfold":  [(0,-60,-120,45,0,0,0,2.6),(0,-90,-150,60,0,180,12.5,2.8),(30,-60,-100,30,-30,0,12.5,2.4),(0,-20,-60,0,0,0,0,2.4)],
}
_pts = [w for seq in SERIES.values() for w in seq] + [HOME + (3.0,)]
_W = [np.array([D(x) for x in w[:6]] + [w[6] / 1000.0]) for w in _pts]
_T = np.array([w[7] for w in _pts]); _TOT = _T.sum(); _CUM = np.concatenate([[0], np.cumsum(_T)])
def demo_target(t):
    n = len(_W); t = t % _TOT; k = min(int(np.searchsorted(_CUM, t, side="right")) - 1, n - 1)   # segment k: waypoint k-1 -> k
    i0 = (k - 1) % n; i1 = k; u = (t - _CUM[k]) / _T[k]
    pm, p0, p1, p2 = _W[(i0 - 1) % n], _W[i0], _W[i1], _W[(i1 + 1) % n]
    m0 = 0.5 * (p1 - pm); m1 = 0.5 * (p2 - p0)
    return ((2*u**3-3*u**2+1)*p0 + (u**3-2*u**2+u)*m0 + (-2*u**3+3*u**2)*p1 + (u**3-u**2)*m1), k
with mujoco.viewer.launch_passive(m, d) as v:
    t0 = time.time(); last = -1
    while v.is_running():
        t = time.time() - t0
        if mode == "sweep":
            i = int(t // SEG) % m.nu
            if i != last:
                print("sweeping:", m.actuator(i).name, f"range {np.degrees(lim[i][0]):.0f}..{np.degrees(lim[i][1]):.0f} deg", flush=True); last = i
            lo, hi = lim[i]; s = np.sin(2 * np.pi * (t % SEG) / SEG)
            tgt = base.copy(); tgt[i] = np.clip(base[i] + s * 0.9 * (hi - lo) / 2, lo, hi); d.ctrl[:] = tgt
        if mode == "demo":
            tgt, k = demo_target(t)
            if k != last: print("demo step", k, flush=True); last = k
            d.ctrl[:] = np.clip(tgt, [l[0] for l in lim], [l[1] for l in lim])
        for _ in range(int(0.02 / m.opt.timestep)):
            mujoco.mj_step(m, d)
        v.sync(); time.sleep(0.02)
