"""fea_link/loads.py - derive the J3-end resultant loads for the link-only FEA
from fea_arm3's parts_<case>.json (masses + posed centroids).

Model frame (same as fea/make_input.py): J2 axis = Y through (0,0,0);
J3 axis = Y through (UP_SPAN=126.7, 0, 0); +Z up in the AB (full-reach) pose.

Case A/B (AB pose, arm horizontal along +X): gravity -Z.  Loads at the J3
coupling ref node (126.7,0,0): Fz = -g * M_carry, My = +g * SUM m*(x - x_J3)
(all downstream mass + payload + masses carried at the J3 mount).  The J2-side
carried mass (J2 actuator body + bearing) is applied at the J2 bore patch.
Case C (home pose, link vertical): gravity along -X in the link frame;
the resultant force is axial (-X), the moment is the world-Y gravity moment.

Run:  python3 fea_link/loads.py            (prints the table, writes loads.json)
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
G = 9810.0          # mm/s^2  (mm-N-t units)
UP_SPAN = 126.7     # J2 -> J3 in link frame
PAYLOAD_KG = 0.5

# bodies carried by the link model boundary conditions:
DOWNSTREAM = {"fore", "wrist4", "wrist5", "grip", "finger_u", "finger_d"}
CARRIED_J3 = {"vendor_act_j3", "vendor_6803_j3"}   # bolt to the link at J3
CARRIED_J2 = {"vendor_act_j2", "vendor_6803_j2"}   # carried at the J2 mount
LINK_PARTS = {"upper_out", "upper_back", "back_spacer_j2", "back_spacer_j3"}


def case_numbers(js, pose):
    """Return dict of load values for one parts_<case>.json."""
    parts = js["parts"]
    j3x = js["joints"]["J3"]["pos"][0]     # posed x of J3 axis (world)
    j2x = js["joints"]["J2"]["pos"][0]
    j3z = js["joints"]["J3"]["pos"][2]
    j2z = js["joints"]["J2"]["pos"][2]
    tcp = js["tcp"]
    # downstream resultant: force = total weight; moment about the J3 Y axis
    # = sum m*g*dx (dx measured from the J3 axis in the horizontal direction).
    m_d, mx_d = 0.0, 0.0
    for nm, p in parts.items():
        if p["body"] in DOWNSTREAM:
            m_d += p["mass_kg"]
            dx = p["centroid"][0] - j3x      # world-x offset (AB pose lever arm)
            mx_d += p["mass_kg"] * dx
    m_pay = PAYLOAD_KG
    mx_pay = PAYLOAD_KG * (tcp[0] - j3x)
    m_c3 = sum(parts[n]["mass_kg"] for n in CARRIED_J3)
    mx_c3 = sum(parts[n]["mass_kg"] * (parts[n]["centroid"][0] - j3x) for n in CARRIED_J3)
    m_c2 = sum(parts[n]["mass_kg"] for n in CARRIED_J2)
    cx_c2 = sum(parts[n]["mass_kg"] * parts[n]["centroid"][0] for n in CARRIED_J2) / m_c2

    # Units: G [mm/s^2] * m [kg] * 1e-3 -> N ;  G * m*dx [kg*mm] * 1e-3 -> N.mm.
    f_tot = -G * 1e-3 * (m_d + m_c3 + m_pay)           # N
    m_y_mm = G * 1e-3 * (mx_d + mx_c3 + mx_pay)        # N.mm about +Y at J3
    d_app = m_y_mm / -f_tot                            # centre of action, mm
    f_act2 = -G * 1e-3 * m_c2                          # N at J2 bore
    if pose == "AB":
        # lever arms are world-x offsets; link frame x = world x + 20.
        # Force-only application at the downstream centre of action (J3 + d
        # along +X_link) reproduces the (F, M) wrench on the J3 bolt faces.
        out = {"grav": (0.0, 0.0, -G),
               "j3_cload": {"3": f_tot},
               "ref_app": [UP_SPAN + d_app, 0.0, 0.0],
               "m_y_mm": m_y_mm}
        # predicted J2-axis moment (link frame x = world x + 20):
        m_l = sum(parts[n]["mass_kg"] for n in LINK_PARTS)
        cx_l = sum(parts[n]["mass_kg"] * (parts[n]["centroid"][0] + 20.0)
                   for n in LINK_PARTS) / m_l          # link frame, mm
        m_j2 = (-f_tot * UP_SPAN + m_y_mm
                + G * 1e-3 * m_l * cx_l
                + G * 1e-3 * m_c2 * (cx_c2 + 20.0)) * 1e-3   # N.mm -> N.m
        out["m_j2_nm"] = m_j2
    else:  # C: home pose, link along +Z_world -> gravity is -X in link frame.
        # axial force -X at a ref point offset -Z (world +X side) by d.
        out = {"grav": (-G, 0.0, 0.0),
               "j3_cload": {"1": f_tot},
               "ref_app": [UP_SPAN, 0.0, -d_app],
               "m_y_mm": m_y_mm}
        # axial force has no arm about J2; only the downstream Y moment bends.
        out["m_j2_nm"] = m_y_mm * 1e-3
    out.update({"m_downstream_kg": m_d, "m_carried_j3_kg": m_c3,
                "m_carried_j2_kg": m_c2, "m_payload_kg": m_pay,
                "m_link_kg": sum(parts[n]["mass_kg"] for n in LINK_PARTS),
                "ref_j3": [UP_SPAN, 0.0, 0.0], "ref_j2": [0.0, 0.0, 0.0]})
    return out


def main():
    res = {}
    for case, fn in (("AB", "parts_AB.json"), ("C", "parts_C.json")):
        js = json.loads((HERE / "input" / fn).read_text())
        res[case] = case_numbers(js, case)
        print("case %s: m_downstream=%.4f kg  m_carriedJ3=%.4f  m_carriedJ2=%.4f  "
              "m_link=%.4f  payload=%.2f"
              % (case, res[case]["m_downstream_kg"], res[case]["m_carried_j3_kg"],
                 res[case]["m_carried_j2_kg"], res[case]["m_link_kg"], PAYLOAD_KG))
        print("  J3 force-only cload: %s at ref_app %s (m_y %.0f N.mm)"
              % ({k: round(v, 3) for k, v in res[case]["j3_cload"].items()},
                 [round(v, 1) for v in res[case]["ref_app"]], res[case]["m_y_mm"]))
        print("  gravity: %s   predicted J2 moment = %.3f N.m  (json moments: %s)"
              % (res[case]["grav"], res[case]["m_j2_nm"], js["moments_nm"]))
    (HERE / "input" / "loads.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
