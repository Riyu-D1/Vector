"""final2/run_mjcf_f2.py - drive the F2 MuJoCo scene (same checks as sim stage):
load scene.xml, HOLD at home, sweep each joint to its range ends, TCP site check.
Run: ~/Vector-wt/sim/.venv-mj/bin/python final2/run_mjcf_f2.py
"""
import os
import mujoco
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
m = mujoco.MjModel.from_xml_path(os.path.join(HERE, "mjcf", "scene.xml"))
d = mujoco.MjData(m)
print("nbody", m.nbody, "njnt", m.njnt, "nu", m.nu)

joint_names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(m.njnt)]
act_names = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i) for i in range(m.nu)]
print("joints", joint_names)
print("acts", act_names)
tcp_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, "tcp")

def settle(ctrl, steps=2000):
    d.ctrl[:] = ctrl
    for _ in range(steps):
        mujoco.mj_step(m, d)

# ---- HOLD at home ----
mujoco.mj_resetDataKeyframe(m, d, 0)
mujoco.mj_forward(m, d)
print("tcp site @keyframe0", np.round(d.site_xpos[tcp_id], 4).tolist(), "(want [0.2338,0,0.1992])")
settle(np.zeros(m.nu))
err = max(abs(d.qpos[i]) for i in range(m.njnt))
print("HOLD max joint error %.4f rad (%s)" % (err, joint_names[int(np.argmax(np.abs(d.qpos)))]))
print("HOLD qpos", np.round(d.qpos, 4).tolist())
print("HOLD finite", bool(np.all(np.isfinite(d.qpos))))
print("tcp site", np.round(d.site_xpos[tcp_id], 4).tolist(), "(want ~[0.2338,0,0.1992])")

# ---- per-joint sweeps to both range ends ----
ok = True
for ai, an in enumerate(act_names):
    for tgt in (m.actuator_ctrlrange[ai][0], m.actuator_ctrlrange[ai][1]):
        mujoco.mj_resetDataKeyframe(m, d, 0)
        ctrl = np.zeros(m.nu)
        ctrl[ai] = tgt
        settle(ctrl)
        jid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, an)
        got = d.qpos[m.jnt_qposadr[jid]]
        e = abs(got - tgt)
        fin = bool(np.all(np.isfinite(d.qpos)))
        ok &= e < 0.01 and fin
        print("SWEEP %s -> %+.4f reached %+.4f err %.4f finite %s" % (an, tgt, got, e, fin))
print("SWEEP", "PASS" if ok else "FAIL")
