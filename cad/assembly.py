"""SOMA arm — full assembly, posed, with STEP/STL export.

Home pose is a natural desk 'rest' stance (shoulder leaned, elbow folded,
wrist levelled) rather than a vertical tower — set joint angles in POSE.

Kinematic chain: base → J1 turret → J2 shoulder → upper arm → J3 elbow
→ forearm → J4 wrist pitch → J5 pod + face → gripper.

Joint modules own their ends: the visible link is the span BETWEEN
module faces (rail_top of the lower joint → foot_drop of the upper).
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from build123d import Pos, Rot, Compound, export_step, export_stl, Location

from params import (
    JOINTS, LINKS, SERVO_SM, SERVO_LG, SERVO_XL, SEA_J2, SEA_J3, ELEC, TOL
)
from lib.servo import make_servo
from lib.joint import make_pitch_joint
from lib.links import make_link
from lib.base import make_base
from lib.wrist import make_wrist
from lib.gripper import make_gripper
from lib.geom import y_cyl
from lib.case import make_case

OUT = os.path.join(os.path.dirname(__file__), "export")
os.makedirs(OUT, exist_ok=True)

# Home-pose joint angles (degrees, about each joint's Y axis).
POSE = {"J2": 15.0, "J3": 50.0, "J4": -45.0}


def save(name, part):
    export_step(part, f"{OUT}/{name}.step")
    export_stl(part, f"{OUT}/{name}.stl")


def rot_about(px, pz, deg):
    """Y-axis rotation about world point (px, 0, pz)."""
    return Pos(px, 0, pz) * Rot(0, deg, 0) * Pos(-px, 0, -pz)


def at(part, loc):
    return Compound(children=[part]).locate(loc)


def main():
    children = []

    # ---- electronics plinth -------------------------------------------------
    # The 150x160 carrier-PCB case the drum lands on. Case frame: front rim
    # at y=0; seat centre (75,88) at lid top z=40. In the arm frame the drum
    # axis is (0,0,0), and the case front faces +X (workspace side).
    case = make_case()
    save("case_tray", case.tray)
    save("case_lid", case.lid)
    M_case = Pos(88, -75, -40) * Rot(0, 0, 90)

    # ---- J1 base -----------------------------------------------------------
    base = make_base(SERVO_SM)
    save("j1_base_housing", base.housing)
    save("j1_turret", base.turret)
    save("j1_servo", base.servo)
    children += [at(case.tray, M_case), at(case.lid, M_case)]
    children += [at(base.housing, Pos(0, 0, 0)), at(base.turret, Pos(0, 0, 0)),
                 at(base.servo, base.servo_loc)]
    turret_top = base.top_z

    # ---- J2 shoulder (SEA) --------------------------------------------------
    j2 = make_pitch_joint(SERVO_XL, SEA_J2)
    z2 = turret_top + j2.foot_drop                # J2 axis height
    for n, p in (
        ("j2_bracket", j2.bracket), ("j2_yoke", j2.yoke),
        ("j2_servo", j2.servo), ("j2_sea_spring", j2.sea.spring),
        ("j2_sea_hub", j2.sea.output_hub), ("j2_sea_cap", j2.sea.encoder_cap),
        ("j2_sea_adapter", j2.sea.horn_adapter),
    ):
        save(n, p)

    # ---- link spans ----------------------------------------------------------
    z3 = z2 + LINKS.upper_arm                     # J3 axis
    j3 = make_pitch_joint(SERVO_LG, SEA_J3)
    upper_len = (z3 - j3.foot_drop) - (z2 + j2.rail_top)
    upper = make_link(upper_len, w0=48, h0=44, w1=42, h1=38)
    save("upper_arm", upper.part)

    z4 = z3 + LINKS.forearm                       # J4 axis
    wrist = make_wrist(SERVO_SM)
    j4 = wrist.j4
    fore_len = (z4 - j4.foot_drop) - (z3 + j3.rail_top)
    fore = make_link(fore_len, w0=42, h0=38, w1=38, h1=34)
    save("forearm", fore.part)

    save("wrist_j4_bracket", j4.bracket)
    save("wrist_j4_yoke", j4.yoke)
    save("wrist_j5_pod", wrist.j5_pod)
    save("wrist_neck", wrist.neck)
    save("wrist_faceplate", wrist.faceplate)
    save("j4_servo", j4.servo)
    save("j5_servo", wrist.j5_servo)

    grip = make_gripper()
    save("gripper_palm", grip.palm)
    save("gripper_finger_l", grip.finger_l)
    save("gripper_finger_r", grip.finger_r)
    save("gripper_spool", grip.spool)
    save("gripper_idler", grip.idler_arm)

    # ---- pose transforms -----------------------------------------------------
    T2 = rot_about(0, z2, POSE["J2"])
    p3 = (T2 * Pos(0, 0, z3)).position            # J3 axis after J2
    T3 = rot_about(p3.X, p3.Z, POSE["J3"])
    p4 = (T3 * T2 * Pos(0, 0, z4)).position       # J4 axis after J2+J3
    T4 = rot_about(p4.X, p4.Z, POSE["J4"])

    # ---- placements ----------------------------------------------------------
    # SEA stackup along +Y: spring origin sits one adapter-thickness outboard
    # of the +Y cheek outer face; the cap's skirt base is ON the face.
    cf2 = j2.bracket.bounding_box().size.Y / 2
    sea_off = Pos(0, cf2 + j2.sea.spec.disc_t, 0) * Rot(-90, 0, 0)
    cap_off = Pos(0, cf2, 0) * Rot(-90, 0, 0)

    children.append(at(j2.bracket, Pos(0, 0, z2)))                       # static
    children.append(at(j2.servo, Pos(0, 0, z2) * j2.servo_loc))
    children.append(at(j2.sea.encoder_cap, Pos(0, 0, z2) * cap_off))

    children.append(at(j2.yoke, T2 * Pos(0, 0, z2)))                     # moving
    children.append(at(j2.sea.horn_adapter, T2 * Pos(0, 0, z2) * sea_off))
    children.append(at(j2.sea.spring, T2 * Pos(0, 0, z2) * sea_off))
    children.append(at(j2.sea.output_hub, T2 * Pos(0, 0, z2) * sea_off))
    children.append(at(upper.part, T2 * Pos(0, 0, z2 + j2.rail_top)))

    # J3 static rides with the upper arm (J2-distal), moving side rotates too
    children.append(at(j3.bracket, T2 * Pos(0, 0, z3)))
    children.append(at(j3.servo, T2 * Pos(0, 0, z3) * j3.servo_loc))
    cf3 = j3.bracket.bounding_box().size.Y / 2
    sea_off3 = Pos(0, cf3 + j3.sea.spec.disc_t, 0) * Rot(-90, 0, 0)
    cap_off3 = Pos(0, cf3, 0) * Rot(-90, 0, 0)
    children.append(at(j3.sea.encoder_cap, T2 * Pos(0, 0, z3) * cap_off3))

    # J3 moving group
    children.append(at(j3.yoke, T3 * T2 * Pos(0, 0, z3)))
    children.append(at(j3.sea.horn_adapter, T3 * T2 * Pos(0, 0, z3) * sea_off3))
    children.append(at(j3.sea.spring, T3 * T2 * Pos(0, 0, z3) * sea_off3))
    children.append(at(j3.sea.output_hub, T3 * T2 * Pos(0, 0, z3) * sea_off3))
    children.append(at(fore.part, T3 * T2 * Pos(0, 0, z3 + j3.rail_top)))

    # J4 module — static side rides forearm; yoke carries pod+face+gripper
    children.append(at(j4.bracket, T3 * T2 * Pos(0, 0, z4)))
    children.append(at(j4.servo, T3 * T2 * Pos(0, 0, z4) * j4.servo_loc))
    children.append(at(j4.yoke, T4 * T3 * T2 * Pos(0, 0, z4)))

    pod_z = z4 + j4.rail_top
    children.append(at(wrist.j5_pod, T4 * T3 * T2 * Pos(0, 0, pod_z)))
    children.append(at(wrist.j5_servo, T4 * T3 * T2 * Pos(0, 0, pod_z + 8)))
    # The J5 output: neck bracket on the pod-top flange carries the whole
    # 'head' — visor on the leg, gripper as the forward beak under the chin.
    neck_z = pod_z + wrist.pod_l + 4
    children.append(at(wrist.neck, T4 * T3 * T2 * Pos(0, 0, neck_z)))
    face_y = -(SERVO_SM.body_d + 2 * TOL.wall + 2) / 2 - 3 - 1.5 - 2.5 - 0.3
    children.append(
        at(wrist.faceplate, T4 * T3 * T2 * Pos(0, face_y, neck_z + 2))
    )
    M_grip = T4 * T3 * T2 * Pos(0, face_y - 2, neck_z + 3) * Rot(105, 0, 0)
    children.append(at(grip.palm, M_grip))
    children.append(at(grip.finger_l, M_grip))
    children.append(at(grip.finger_r, M_grip))

    # ---- export + report -----------------------------------------------------
    asm = Compound(children=children)
    export_step(asm, f"{OUT}/SOMA_assembly.step")
    export_stl(asm, f"{OUT}/SOMA_assembly.stl")

    bb = asm.bounding_box()
    print("\n=== SOMA assembly (posed) ===")
    print(f"envelope: {bb.size.X:.0f} × {bb.size.Y:.0f} × {bb.size.Z:.0f} mm")
    print(f"axes: J2 z={z2:.0f}  J3 z={z3:.0f}  J4 z={z4:.0f}")
    print(f"upper link {upper_len:.0f} mm, fore link {fore_len:.0f} mm")
    print(f"parts exported to {OUT}/")


if __name__ == "__main__":
    main()
