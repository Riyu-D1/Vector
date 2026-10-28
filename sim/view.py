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
# demo waypoints: (J1,J2,J3,J4,J5,J6 in degrees, finger in mm, move seconds, hold seconds). All inside the joint ranges.
DEMO = [
 (0,0,0,0,0,0,0,1.5,0.5),
 (50,0,0,0,0,0,0,2.0,0.3), (-50,0,0,0,0,0,0,3.0,0.3), (0,0,0,0,0,0,0,2.0,0.3),
 (0,-40,0,0,0,0,0,2.0,0.3), (0,35,0,0,0,0,0,3.0,0.3), (0,0,0,0,0,0,0,2.0,0.3),
 (0,0,-70,0,0,0,0,2.0,0.3), (0,0,20,0,0,0,0,3.0,0.3), (0,0,0,0,0,0,0,2.0,0.3),
 (0,0,0,50,0,0,0,1.5,0.2), (0,0,0,-50,0,0,0,2.5,0.2), (0,0,0,0,0,0,0,1.5,0.2),
 (0,0,0,0,50,0,0,1.5,0.2), (0,0,0,0,-50,0,0,2.5,0.2), (0,0,0,0,0,0,0,1.5,0.2),
 (0,0,0,0,0,170,0,2.5,0.2), (0,0,0,0,0,-170,0,4.0,0.2), (0,0,0,0,0,0,0,2.5,0.3),
 (0,0,0,0,0,0,12.5,1.0,0.4), (0,0,0,0,0,0,0,1.0,0.4), (0,0,0,0,0,0,12.5,1.0,0.4), (0,0,0,0,0,0,0,1.0,0.4),
 # combined "pick and place" style moves
 (40,-30,-50,25,-20,60,12.5,3.0,0.3),
 (40,-30,-50,25,-20,60,0,1.0,0.3),
 (-40,10,-30,-25,20,-60,0,3.5,0.3),
 (-40,10,-30,-25,20,-60,12.5,1.0,0.3),
 (0,-20,-90,30,0,0,12.5,3.0,0.3),
 (0,0,0,0,0,0,0,3.0,1.0),
]
def demo_target(t):
    tot = sum(w[7] + w[8] for w in DEMO); t = t % tot
    prev = np.zeros(7); k = 0
    for w in DEMO:
        tgt = np.array([D(x) for x in w[:6]] + [w[6] / 1000.0])
        if t < w[7]:
            u = 0.5 - 0.5 * np.cos(np.pi * t / w[7]); return prev + (tgt - prev) * u, k
        t -= w[7]
        if t < w[8]: return tgt, k
        t -= w[8]; prev = tgt; k += 1
    return prev, k
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
