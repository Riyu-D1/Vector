"""SOMA arm viewer.  mjpython sim/view.py manual   -> arm holds home; move joints with the Control panel sliders (double-click + ctrl+right-drag to perturb)
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
        for _ in range(int(0.02 / m.opt.timestep)):
            mujoco.mj_step(m, d)
        v.sync(); time.sleep(0.02)
