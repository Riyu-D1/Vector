"""parts.py - render manifest for the FULLCHECK per-part FEA set.

Binding mode / peak / SF / hotspot coordinates are the converged values
reported in FULLCHECK.md check 4 and the fc_analyze *.run.log / R9 *_r9.txt
analyses.  `allow` is the PETG-CF allowable for the binding criterion
(in-layer VM 25, layer-normal tension 12.5, compression 15, interlayer
shear 8 MPa).  Colour field is always nodal von Mises; red = 12.5 MPa
(the in-layer SF2 gate).

Wrist entries use the binding R9 case at 0.25 kg (p25): l4 rolled, l5 keel,
gf rolled, cr bolt-bound rolled.
"""

FC = "fullcheck/fea"
R9 = "refine/fea"

PARTS = [
    # ---------------- fullcheck/fea (non-wrist, worst 0.25 kg pose) --------
    dict(key="base_plate", frd=FC + "/base_plate_d.frd", mode="shear",
         peak=0.002, allow=8.0, sf=3462.0, xyz=(18.3, 15.5, 5.5),
         note="cl=5.0 flat 14 mm desk diaphragm; raw maxVM 0.03 MPa"),
    dict(key="base_link", frd=FC + "/base_link.frd", mode="comp",
         peak=0.200, allow=15.0, sf=75.2, xyz=(41.1, 0.7, 79.0)),
    dict(key="base_reinf", frd=FC + "/base_reinf.frd", mode="comp",
         peak=0.949, allow=15.0, sf=15.8, xyz=(15.1, 26.9, 81.0)),
    dict(key="j1_cradle", frd=FC + "/j1_cradle.frd", mode="comp",
         peak=0.002, allow=15.0, sf=7636.0, xyz=(16.7, -6.5, 26.1)),
    dict(key="yaw_limit", frd=FC + "/yaw_limit_f.frd", mode="shear",
         peak=0.027, allow=8.0, sf=300.8, xyz=(-4.4, 9.9, 84.5),
         note="converged cl=1.0 (SF 311 -> 301)"),
    dict(key="link1", frd=FC + "/link1_h.frd", mode="comp",
         peak=4.358, allow=15.0, sf=3.44, xyz=(-10.2, -15.7, 88.0),
         note="refined 393k->318k-node run; coarse norm 3.34 -> comp 3.44"),
    dict(key="upper_out", frd=FC + "/upper_out.frd", mode="comp",
         peak=2.388, allow=15.0, sf=6.28, xyz=(-36.0, -32.1, 170.2)),
    dict(key="upper_back", frd=FC + "/upper_back.frd", mode="comp",
         peak=2.668, allow=15.0, sf=5.62, xyz=(-36.3, 32.1, 170.3)),
    dict(key="dogleg_l", frd=FC + "/dogleg_l_g.frd", mode="comp",
         peak=4.496, allow=15.0, sf=3.34, xyz=(10.5, -36.6, 232.9),
         note="refined cl 2.0->1.4"),
    dict(key="dogleg_r", frd=FC + "/dogleg_r_g.frd", mode="comp",
         peak=4.656, allow=15.0, sf=3.22, xyz=(10.4, 36.6, 233.0),
         note="refined cl 2.0->1.4; min binding SF of the set"),
    dict(key="fore_l2", frd=FC + "/fore_l2_g.frd", mode="comp",
         peak=4.344, allow=15.0, sf=3.45, xyz=(50.6, -36.6, 202.9),
         note="refined cl 2.0->1.4"),
    dict(key="fore_r2", frd=FC + "/fore_r2_g.frd", mode="comp",
         peak=1.495, allow=15.0, sf=10.0, xyz=(117.2, 36.6, 218.8),
         note="refined cl 2.0->1.4"),
    dict(key="j4_cradle", frd=FC + "/j4_cradle.frd", mode="comp",
         peak=0.018, allow=15.0, sf=841.0, xyz=(96.4, 30.3, 229.7)),
    dict(key="front_spacer_j2", frd=FC + "/front_spacer_j2.frd", mode="comp",
         peak=2.090, allow=15.0, sf=7.18, xyz=(-23.6, -31.6, 155.5)),
    dict(key="back_spacer_j2", frd=FC + "/back_spacer_j2.frd", mode="comp",
         peak=0.632, allow=15.0, sf=23.7, xyz=(-38.7, 28.1, 132.3)),
    dict(key="front_spacer_j3", frd=FC + "/front_spacer_j3.frd", mode="comp",
         peak=0.834, allow=15.0, sf=18.0, xyz=(-9.4, -31.6, 273.7)),
    dict(key="back_spacer_j3", frd=FC + "/back_spacer_j3.frd", mode="comp",
         peak=0.348, allow=15.0, sf=43.0, xyz=(-38.7, 28.1, 281.4)),
    dict(key="flange_j2", frd=FC + "/flange_j2.frd", mode="comp",
         peak=0.528, allow=15.0, sf=28.4, xyz=(-22.9, 30.6, 132.8)),
    dict(key="flange_j3", frd=FC + "/flange_j3.frd", mode="comp",
         peak=0.189, allow=15.0, sf=79.4, xyz=(-17.4, 30.6, 281.0)),
    dict(key="cy2_housing", frd=FC + "/cy2_housing.frd", mode="comp",
         peak=0.019, allow=15.0, sf=787.0, xyz=(22.9, 12.4, 43.5)),
    dict(key="cy2_carrier", frd=FC + "/cy2_carrier.frd", mode="shear",
         peak=0.112, allow=8.0, sf=71.7, xyz=(1.3, 7.8, 48.6)),
    dict(key="cy2_out_flange", frd=FC + "/cy2_out_flange.frd", mode="norm",
         peak=0.409, allow=12.5, sf=30.5, xyz=(3.2, 6.2, 53.8)),
    dict(key="cy3_housing", frd=FC + "/cy3_housing.frd", mode="norm",
         peak=0.008, allow=12.5, sf=1663.0, xyz=(-20.0, 16.7, 44.6)),
    dict(key="cy3_carrier", frd=FC + "/cy3_carrier.frd", mode="shear",
         peak=0.054, allow=8.0, sf=146.9, xyz=(-3.3, -6.3, 52.0)),
    dict(key="cy3_out_flange", frd=FC + "/cy3_out_flange.frd", mode="comp",
         peak=0.244, allow=15.0, sf=61.5, xyz=(3.2, 6.2, 53.8)),
    # ---------------- refine/fea (R9 wrist, binding case @0.25 kg) ---------
    dict(key="w_link4", frd=R9 + "/l4_scrann_p25_roll.frd",
         mode="in-layer VM", peak=10.66, allow=25.0, sf=2.35,
         xyz=(14.0, 13.5, -1.6),
         note="R9 rolled p25; arm-root vertex. Keel p25: 10.27 (SF 2.43)"),
    dict(key="w_link5", frd=R9 + "/l5_scrann_p25.frd",
         mode="interlayer tau", peak=3.12, allow=8.0, sf=2.56,
         xyz=(26.2, 13.2, -6.2),
         note="R9 keel p25; lip edge. SF 1.96 vs 6.1 MPa lower bound"),
    dict(key="w_grip_frame", frd=R9 + "/gf_scrann_p25_roll.frd",
         mode="in-layer VM", peak=8.29, allow=25.0, sf=3.02,
         xyz=(114.1, -12.5, -12.0),
         note="R9 rolled p25; tau 2.33 (SF 3.43)"),
    dict(key="w_j4_cradle", frd=R9 + "/cr_bolt_p25_roll.frd",
         mode="VM", peak=2.30, allow=15.0, sf=6.0, sf_disp=">6",
         xyz=(-4.5, 29.5, 1.5),
         note="R9 pin-seat under ~25 N journal reaction; "
              "<=2.4 MPa filtered all directions"),
]

MODE_LABEL = {"vm": "von Mises", "norm": "layer-normal tension",
              "comp": "compression", "shear": "interlayer shear",
              "in-layer VM": "in-layer von Mises",
              "interlayer tau": "interlayer shear",
              "VM": "von Mises"}
