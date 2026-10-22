"""Series-elastic actuator (SEA) cartridge — the spring is the sensor.

Stackup along the joint axis (+Z out, z=0 at the spring mid-plane):
    servo horn  →  horn adapter  →  spring HUB (centre)
    spring outer RING  →  output flange (bolts sandwich ring between
    flange and ring)  →  flange's journal stub rises into the cap bearing
    cap = small centre cover bolted to the joint bracket: carries the
    output bearing + AS5600 facing the journal's diametric magnet.

Torque path:  servo → spring → output flange → yoke.
Measurement : encoder(output angle) − servo(own encoder) = Δθ, τ = k·Δθ.

v2 change: the output flange is accessible OUTSIDE the cap bolt circle —
the cap only covers the centre (journal/encoder), leaving the flange's
link-bolt circle exposed at the rim. The yoke can actually reach it.
"""

from dataclasses import dataclass
import math

from build123d import Box, Cylinder, Pos, Rot, fillet, Part

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import SEASpec, BEARINGS, TOL


@dataclass
class SEAParts:
    spring: Part        # printed flexure disc (PETG/nylon recommended)
    output_hub: Part    # output flange: bolt ring + bearing journal + magnet
    encoder_cap: Part   # static centre cover: bearing seat + AS5600 shelf
    horn_adapter: Part  # spline bore → bolts to spring hub
    spec: SEASpec
    stack_h: float      # total axial height of the cartridge


def make_spring_disc(spec: SEASpec) -> Part:
    """Flexure torsion spring: hub + N tangential beams + outer ring."""
    r_ring_inner = spec.disc_r - spec.ring_w
    t = spec.disc_t

    ring = Cylinder(spec.disc_r, t) - Cylinder(r_ring_inner, t)
    hub = Cylinder(spec.hub_r, t)

    beam_len = math.sqrt(max(r_ring_inner**2 - spec.hub_r**2, 1.0))
    embed = 1.5
    disc = hub + ring
    for i in range(spec.n_arms):
        th = i * 2 * math.pi / spec.n_arms
        tx, ty = spec.hub_r * math.cos(th), spec.hub_r * math.sin(th)
        dx, dy = -math.sin(th), math.cos(th)
        cx, cy = tx + dx * beam_len / 2, ty + dy * beam_len / 2
        disc += (
            Pos(cx, cy, t / 2)
            * Rot(0, 0, math.degrees(math.atan2(dy, dx)))
            * Box(beam_len + 2 * embed, spec.arm_w, t)
        )

    bolt_r = spec.hub_r * 0.6
    for i in range(4):  # hub → horn adapter
        th = i * math.pi / 2 + math.pi / 4
        disc -= Pos(bolt_r * math.cos(th), bolt_r * math.sin(th), t / 2) * Cylinder(
            1.6, t + 2
        )
    disc -= Cylinder(4.5, t + 2)                     # spline nose clearance
    mid_r = spec.disc_r - spec.ring_w / 2            # ring → output flange
    for i in range(4):
        th = i * math.pi / 2
        disc -= Pos(mid_r * math.cos(th), mid_r * math.sin(th), t / 2) * Cylinder(
            1.7, t + 2
        )
    return disc


def make_output_hub(spec: SEASpec) -> Part:
    """Output flange: sandwiches the spring ring (4×M3), carries the bearing
    journal + encoder magnet on axis, and presents an exposed link bolt
    circle at its rim (the yoke's drive plate bolts here)."""
    b_id, b_od, b_w = BEARINGS[spec.bearing]
    flange_h = 4.0
    journal_h = b_w + 1.0
    mid_r = spec.disc_r - spec.ring_w / 2

    hub = Cylinder(spec.disc_r - 0.5, flange_h)                # full flange
    journal = Pos(0, 0, flange_h) * Cylinder((b_id - TOL.slip) / 2, journal_h)
    part = hub + journal

    # Diametric magnet pocket at journal top.
    part -= Pos(0, 0, flange_h + journal_h - spec.magnet_h) * Cylinder(
        (spec.magnet_d - TOL.press) / 2, spec.magnet_h + 0.5
    )
    # Ring sandwich bolts: M3 through-holes at mid_r (thread the ring side).
    for i in range(4):
        th = i * math.pi / 2
        part -= Pos(mid_r * math.cos(th), mid_r * math.sin(th), 0) * Cylinder(
            1.6, flange_h + journal_h + 2
        )
    # Yoke bolt circle — exposed rim outside the cap radius.
    yoke_r = spec.disc_r - 3.0
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        part -= Pos(yoke_r * math.cos(th), yoke_r * math.sin(th), 0) * Cylinder(
            1.3, flange_h + 1     # M2.5 tap/heat-set from the top face
        )
    return part


def make_encoder_cap(spec: SEASpec) -> Part:
    """Static centre cap: covers only the journal/encoder zone, leaving the
    output flange's rim bolt circle accessible. Bolts to the bracket cheek."""
    b_id, b_od, b_w = BEARINGS[spec.bearing]
    cap_r = spec.disc_r - spec.ring_w - 4.0     # stays inside the yoke bolts
    cap_t = 3.0
    # Height = adapter + spring + flange + journal + air, measured from the
    # cheek outer face the cap bolts to.
    skirt_h = 2 * spec.disc_t + 4.0 + b_w + 4.0

    cap = Cylinder(cap_r, skirt_h) - Cylinder(cap_r - TOL.wall, skirt_h - cap_t)
    cap += Pos(0, 0, skirt_h - cap_t) * Cylinder(cap_r, cap_t)

    # Bearing pocket (blind bore from inside).
    cap -= Pos(0, 0, skirt_h - cap_t - b_w - 0.5) * Cylinder(
        (b_od + TOL.slip) / 2, b_w + 0.5
    )
    # AS5600 recess + wire slot.
    cap -= Pos(0, 0, skirt_h - cap_t - b_w - 3.6) * Cylinder(5.0, 3.2)
    cap -= Pos(0, cap_r - 4, skirt_h - cap_t - b_w - 1.8) * Box(4, 10, 1.8)

    # 3× M3 rim bolts down to the bracket cheek.
    for i in range(3):
        th = i * 2 * math.pi / 3 + math.pi / 6
        cap -= Pos(
            (cap_r - TOL.wall / 2) * math.cos(th),
            (cap_r - TOL.wall / 2) * math.sin(th),
            skirt_h - 2,
        ) * Cylinder(1.6, 4)
    # Soften only the top outer rim — blanket fillets on the cut edges fail.
    from build123d import Axis, GeomType
    rim = cap.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1]
    return fillet(rim, 0.8)


def make_horn_adapter(spec: SEASpec, spline_d: float = 5.9) -> Part:
    """Spline-bore adapter: servo horn → spring hub."""
    t = spec.disc_t
    hub = Cylinder(spec.hub_r - 0.5, t)
    hub -= Cylinder((spline_d - TOL.press) / 2, 2.5)
    hub -= Cylinder(1.5, t + 2)
    bolt_r = spec.hub_r * 0.6
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        hub -= Pos(bolt_r * math.cos(th), bolt_r * math.sin(th), t / 2) * Cylinder(
            1.6, t + 2
        )
    return hub


def make_cartridge(spec: SEASpec, spline_d: float = 5.9) -> SEAParts:
    """All cartridge pieces at the joint origin, axis +Z, spring at z=0..t."""
    t = spec.disc_t
    spring = make_spring_disc(spec)
    hub = Pos(0, 0, t) * make_output_hub(spec)
    cap = make_encoder_cap(spec)                 # placed from z = 0 upward
    adapter = Pos(0, 0, -t) * make_horn_adapter(spec, spline_d)
    stack = t + 4.0 + 4.0 + 5.0                  # disc + flange + journal + cap top
    return SEAParts(spring, hub, cap, adapter, spec, stack)


def make_horn_flange(spline_d: float = 5.9, r: float = 13.0) -> Part:
    """Rigid-joint output flange: spline bore + 4×M3 bolt circle at r=9.
    Used on joints without an SEA (J1, J4, J5, gripper drive)."""
    flange = Cylinder(r, 4.0)
    flange -= Cylinder((spline_d - TOL.press) / 2, 2.5)
    flange -= Cylinder(1.5, 6)
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        flange -= Pos(9 * math.cos(th), 9 * math.sin(th), 2) * Cylinder(1.6, 6)
    return flange


if __name__ == "__main__":
    from params import SEA_J2, SEA_J3
    for name, s in (("J2", SEA_J2), ("J3", SEA_J3)):
        parts = make_cartridge(s)
        for label, p in (
            ("spring", parts.spring), ("hub", parts.output_hub),
            ("cap", parts.encoder_cap), ("adapter", parts.horn_adapter),
        ):
            bb = p.bounding_box()
            print(
                f"{name} {label:8s} bbox "
                f"{bb.size.X:.1f}×{bb.size.Y:.1f}×{bb.size.Z:.1f} mm  "
                f"vol {p.volume/1000:.1f} cm³"
            )
