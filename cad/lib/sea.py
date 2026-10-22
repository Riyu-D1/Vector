"""Series-elastic actuator (SEA) cartridge — the spring is the sensor.

Layout along the joint axis (+Z out):
    servo horn  →  horn adapter  →  spring disc hub
    spring disc outer ring  →  output hub flange (link mount + bearing
    journal + center magnet pocket)
    static cap bolted to the joint bracket → AS5600 facing the magnet,
    and the cap's bore carries the bearing that supports the output hub.

So the torque path is:  servo → spring → link.
And the measurement is:  encoder(output angle) − servo(encoder angle) = Δθ,
τ = k·Δθ.
"""

from dataclasses import dataclass
import math

from build123d import (
    Box, Cylinder, Pos, Rot, Axis, fillet, chamfer,
    Locations, Part, Compound,
)

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import SEASpec, BEARINGS, TOL


@dataclass
class SEAParts:
    spring: Part        # printed flexure disc (PETG/nylon recommended)
    output_hub: Part    # output flange: bearing journal + magnet pocket
    encoder_cap: Part   # static cap: bearing seat + AS5600 shelf + cover
    horn_adapter: Part  # spline bore → bolts to spring hub
    spec: SEASpec


def make_spring_disc(spec: SEASpec) -> Part:
    """Flexure torsion spring: hub + N tangential beams + outer ring.

    Tangential spokes bend when the hub twists relative to the ring —
    a well-proven printed SEA geometry (same family as flex-coupler /
    spiral-spring SEA discs). Print flat; no supports needed.

    k ∝ n_arms · arm_w · disc_t³ / beam_len³  — tune in params.
    """
    r_ring_inner = spec.disc_r - spec.ring_w
    t = spec.disc_t

    # Outer ring and hub.
    ring = Cylinder(spec.disc_r, t) - Cylinder(r_ring_inner, t)
    hub = Cylinder(spec.hub_r, t)

    # Tangential flexure beams: each beam is tangent to the hub circle,
    # spanning from the hub surface to the ring inner face.
    beam_len = math.sqrt(max(r_ring_inner**2 - spec.hub_r**2, 1.0))
    embed = 1.5  # overlap into hub + ring so the union is solid
    beams = []
    for i in range(spec.n_arms):
        th = i * 2 * math.pi / spec.n_arms
        # tangent point on the hub circle
        tx, ty = spec.hub_r * math.cos(th), spec.hub_r * math.sin(th)
        # tangent direction (perpendicular to radius)
        dx, dy = -math.sin(th), math.cos(th)
        cx = tx + dx * beam_len / 2
        cy = ty + dy * beam_len / 2
        beam = (
            Pos(cx, cy, t / 2)
            * Rot(0, 0, math.degrees(math.atan2(dy, dx)))
            * Box(beam_len + 2 * embed, spec.arm_w, t)
        )
        beams.append(beam)

    disc = hub + ring
    for b in beams:
        disc += b

    # Spring hub → horn-adapter bolt pattern (4× M3 clearance on hub face).
    bolt_r = spec.hub_r * 0.6
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        disc -= Pos(bolt_r * math.cos(th), bolt_r * math.sin(th), t / 2) * Cylinder(
            1.6, t + 2
        )
    # Center clearance for the spline boss nose.
    disc -= Cylinder(4.5, t + 2)
    # Output-ring → link bolt pattern (4× M3 on the ring).
    mid_r = spec.disc_r - spec.ring_w / 2
    for i in range(4):
        th = i * math.pi / 2
        disc -= Pos(mid_r * math.cos(th), mid_r * math.sin(th), t / 2) * Cylinder(
            1.6, t + 2
        )
    return disc


def make_output_hub(spec: SEASpec) -> Part:
    """Flange that bolts onto the spring's outer ring; carries the bearing
    journal (+Z side) and the encoder magnet pocket on the axis."""
    t = spec.disc_t
    b_id, b_od, b_w = BEARINGS[spec.bearing]
    flange_h = 4.0
    journal_h = b_w + 1.0

    hub = Cylinder(spec.disc_r - spec.ring_w / 2 - 1, flange_h)      # link flange
    journal = Pos(0, 0, flange_h) * Cylinder((b_id - TOL.slip) / 2, journal_h)
    part = hub + journal

    # Center magnet pocket (diametric magnet, press fit).
    part -= Pos(0, 0, flange_h + journal_h - spec.magnet_h) * Cylinder(
        (spec.magnet_d - TOL.press) / 2, spec.magnet_h + 0.5
    )
    # Link bolt circle matches the spring ring pattern.
    mid_r = spec.disc_r - spec.ring_w / 2
    for i in range(4):
        th = i * math.pi / 2
        part -= Pos(mid_r * math.cos(th), mid_r * math.sin(th), flange_h / 2) * Cylinder(
            1.6, flange_h + journal_h + 2
        )
    return part


def make_encoder_cap(spec: SEASpec) -> Part:
    """Static cover over the cartridge: bearing seat + AS5600 shelf + bolts
    back to the joint bracket. Also the joint's protective cover."""
    b_id, b_od, b_w = BEARINGS[spec.bearing]
    cap_t = 3.0
    skirt_h = spec.disc_t + 8.0

    # Cap shell: rim around the disc + top plate.
    shell = Cylinder(spec.disc_r + TOL.loose + TOL.wall, skirt_h) - Cylinder(
        spec.disc_r + TOL.loose, skirt_h - cap_t
    )
    top = Pos(0, 0, skirt_h - cap_t) * Cylinder(
        spec.disc_r + TOL.loose + TOL.wall, cap_t
    )
    cap = shell + top

    # Bearing pocket in the top plate (blind bore, bearing pressed from inside).
    cap -= Pos(0, 0, skirt_h - cap_t - b_w) * Cylinder(
        (b_od + TOL.slip) / 2, b_w + 0.5
    )

    # AS5600 shelf: recess for the breakout under the magnet, plus wire slot.
    cap -= Pos(0, 0, skirt_h - cap_t - b_w - 3.2) * Cylinder(4.2, 3.2)
    cap -= Pos(0, 11.0, skirt_h - cap_t - b_w - 1.6) * Box(4, 22, 1.6)

    # 4× M3 mounting holes around the rim to the joint bracket.
    mount_r = spec.disc_r + TOL.loose + TOL.wall / 2
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        cap -= Pos(mount_r * math.cos(th), mount_r * math.sin(th), skirt_h - 2) * Cylinder(
            1.6, 4
        )
    return cap


def make_horn_adapter(spec: SEASpec, spline_d: float = 5.9) -> Part:
    """Spline-bore adapter: servo horn → spring hub. Print in PETG; the
    spline pocket is a snug press + center M3 bolt into the servo shaft."""
    t = spec.disc_t
    hub = Cylinder(spec.hub_r - 0.5, t)
    # Spline pocket (circular approximation — VERIFY spline OD; a printed
    # broached spline can come later if slip shows up under torque).
    hub -= Cylinder((spline_d - TOL.press) / 2, 2.5)
    hub -= Cylinder(1.5, t + 2)  # M3 center bolt clearance
    bolt_r = spec.hub_r * 0.6
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        hub -= Pos(bolt_r * math.cos(th), bolt_r * math.sin(th), t / 2) * Cylinder(
            1.6, t + 2
        )
    return hub


def make_cartridge(spec: SEASpec, spline_d: float = 5.9) -> SEAParts:
    """All four cartridge pieces, modeled at the joint origin (axis +Z)."""
    spring = make_spring_disc(spec)
    hub = Pos(0, 0, spec.disc_t) * make_output_hub(spec)
    cap = Pos(0, 0, spec.disc_t + 4.0) * make_encoder_cap(spec)
    adapter = Pos(0, 0, -spec.disc_t) * make_horn_adapter(spec, spline_d)
    return SEAParts(spring, hub, cap, adapter, spec)


if __name__ == "__main__":
    from params import SEA_J2, SEA_J3
    for name, s in (("J2", SEA_J2), ("J3", SEA_J3)):
        parts = make_cartridge(s)
        for label, p in (
            ("spring", parts.spring), ("hub", parts.output_hub),
            ("cap", parts.encoder_cap), ("adapter", parts.horn_adapter),
        ):
            bb = p.bounding_box()
            vol = p.volume
            print(
                f"{name} {label:8s} bbox "
                f"{bb.size.X:.1f}×{bb.size.Y:.1f}×{bb.size.Z:.1f} mm  "
                f"vol {vol/1000:.1f} cm³"
            )
