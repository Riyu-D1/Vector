# wrist2/patches

`robot-os-d6-wrist2.patch` — snapshot of the D6 `software/robot-os` changes
(config, kinematics, gravity tables, tests) as committed on `arm-wrist2`.
The patch is documentation only: the same edits are applied directly in this
branch (the stage allows editing `software/` on `arm-wrist2` itself). Regenerate
with `git diff a5234b3 -- software/robot-os/`.

Geometry deltas the patch encodes:

| item | D5 | D6 |
|---|---|---|
| J4→J5 | 37.6 mm | 30.6 mm |
| J5→J6 | 19.2 mm (nominal) | 22.4 mm |
| J6→TCP | 75.0 mm | 84.4 mm |
| TCP h vs J4 axis | 0 | −17.0 mm (roll-axis keel) |
| TCP home (x,z) | (228.2, 216.2) | (233.8, 199.2) |
| J4→TCP | 131.8 | 137.4 mm |

`kinematics.py` now back-projects the J4 anchor with the 2-vector
`(w3a, w3z)` = W_J5 + W_J6 + T_TCP instead of the scalar `l3` — required
because the D6 TCP hangs 17 mm below the J4 pitch axis.
`gravity.py` `_PARTS` wrist rows use the measured D6 volumes/masses and
AB-pose centroids; `_ORIGIN_AB_MM` wrist5/grip move with the new axes.
