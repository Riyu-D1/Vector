"""SOMA arm — full assembly in home pose + STEP/STL export.

Kinematic chain (home pose = arm vertical, +Z up):
    base → J1 turret (yaw) → J2 shoulder pitch → upper arm → J3 elbow pitch
    → forearm → J4 wrist pitch → J5 roll + face module → gripper

Placement note: modules are positioned by axis location; end-plate bolt
patterns between joints and links are unified in the mechanical refinement
pass — this export establishes envelope, stackup, and reach.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from build123d import Pos, Rot, Compound, export_step, export_stl

from params import (
    JOINTS, LINKS, SERVO_SM, SERVO_LG, SERVO_XL, SEA_J2, SEA_J3, ELEC
)
from lib.servo import make_servo
from lib.joint import make_pitch_joint
from lib.links import make_link
from lib.base import make_base
from lib.wrist import make_wrist
from lib.gripper import make_gripper

OUT = os.path.join(os.path.dirname(__file__), "export")
os.makedirs(OUT, exist_ok=True)


def save(name: str, part):
    export_step(part, f"{OUT}/{name}.step")
    export_stl(part, f"{OUT}/{name}.stl")
    return part


def main():
    children = []

    # ---- J1 base + turret --------------------------------------------------
    base = make_base(SERVO_SM)
    save("j1_base_housing", base.housing)
    save("j1_turret", base.turret)
    save("j1_servo", base.servo)
    children += [
        Compound(children=[base.housing]).locate(Pos(0, 0, 0)),
        Compound(children=[base.turret]).locate(Pos(0, 0, 0)),
    ]
    turret_top_z = 55 - 2 + 6  # h - lip + turret_t
    turret_top_z = base.turret.bounding_box().max.Z

    # ---- J2 shoulder (SEA) -------------------------------------------------
    j2 = make_pitch_joint(SERVO_XL, SEA_J2)
    j2_foot = j2.bracket.bounding_box().min.Z
    z_j2 = turret_top_z - j2_foot          # axis z such that foot sits on turret
    save("j2_bracket", j2.bracket)
    save("j2_yoke", j2.yoke)
    save("j2_servo", j2.servo)
    children.append(Compound(children=[j2.bracket]).locate(Pos(0, 0, z_j2)))
    children.append(Compound(children=[j2.yoke]).locate(Pos(0, 0, z_j2)))
    children.append(Compound(children=[j2.servo]).locate(
        Pos(0, 0, z_j2) * Rot(0, 0, -90)   # spline face toward +Y cheek
    ))
    if j2.sea:
        save("j2_sea_spring", j2.sea.spring)
        save("j2_sea_hub", j2.sea.output_hub)
        save("j2_sea_cap", j2.sea.encoder_cap)
        save("j2_sea_adapter", j2.sea.horn_adapter)

    # ---- upper arm link ----------------------------------------------------
    upper = make_link(LINKS.upper_arm, width=44, height=40)
    save("upper_arm", upper.part)
    z_upper = z_j2 + 8                       # link bottom plate over yoke rail
    children.append(Compound(children=[upper.part]).locate(Pos(0, 0, z_upper)))

    # ---- J3 elbow (SEA) ----------------------------------------------------
    j3 = make_pitch_joint(SERVO_LG, SEA_J3)
    j3_foot = j3.bracket.bounding_box().min.Z
    z_j3 = z_upper + LINKS.upper_arm - j3_foot
    save("j3_bracket", j3.bracket)
    save("j3_yoke", j3.yoke)
    save("j3_servo", j3.servo)
    children.append(Compound(children=[j3.bracket]).locate(Pos(0, 0, z_j3)))
    children.append(Compound(children=[j3.yoke]).locate(Pos(0, 0, z_j3)))
    children.append(Compound(children=[j3.servo]).locate(Pos(0, 0, z_j3) * Rot(0, 0, -90)))
    if j3.sea:
        save("j3_sea_spring", j3.sea.spring)
        save("j3_sea_hub", j3.sea.output_hub)
        save("j3_sea_cap", j3.sea.encoder_cap)
        save("j3_sea_adapter", j3.sea.horn_adapter)

    # ---- forearm link ------------------------------------------------------
    fore = make_link(LINKS.forearm, width=40, height=36)
    save("forearm", fore.part)
    z_fore = z_j3 + 8
    children.append(Compound(children=[fore.part]).locate(Pos(0, 0, z_fore)))

    # ---- wrist/face + gripper ----------------------------------------------
    wrist = make_wrist(SERVO_SM)
    z_j4 = z_fore + LINKS.forearm + wrist.j4_bracket.bounding_box().max.Z * -1
    save("wrist_j4_bracket", wrist.j4_bracket)
    save("wrist_j5_shell", wrist.j5_shell)
    save("faceplate", wrist.faceplate)
    save("j4_servo", wrist.j4_servo)
    save("j5_servo", wrist.j5_servo)
    children.append(Compound(children=[wrist.j4_bracket]).locate(Pos(0, 0, z_j4)))
    children.append(
        Compound(children=[wrist.j5_shell]).locate(Pos(0, 0, z_j4 + 45))
    )
    children.append(
        Compound(children=[wrist.faceplate]).locate(Pos(0, 0, z_j4 + 75))
    )

    grip = make_gripper()
    save("gripper_palm", grip.palm)
    save("gripper_finger_l", grip.finger_l)
    save("gripper_finger_r", grip.finger_r)
    save("gripper_spool", grip.spool)
    save("gripper_idler", grip.idler_arm)
    children.append(Compound(children=[grip.palm]).locate(Pos(0, -14, z_j4 + 70)))
    children.append(Compound(children=[grip.finger_l]).locate(Pos(0, -14, z_j4 + 85)))
    children.append(Compound(children=[grip.finger_r]).locate(Pos(0, -14, z_j4 + 85)))

    # ---- assembly export + report ------------------------------------------
    asm = Compound(children=children)
    export_step(asm, f"{OUT}/SOMA_assembly.step")
    export_stl(asm, f"{OUT}/SOMA_assembly.stl")

    bb = asm.bounding_box()
    print("\n=== SOMA assembly ===")
    print(f"envelope: {bb.size.X:.0f} × {bb.size.Y:.0f} × {bb.size.Z:.0f} mm")
    print(f"height ≈ {bb.size.Z:.0f} mm  (spec ~400 mm)")
    print(f"parts exported to {OUT}/")


if __name__ == "__main__":
    main()
