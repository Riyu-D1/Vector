# Stage 6 — firmware + software: Steadywin GIM CAN protocol
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply to every step.
> Work dir for every command unless the step says otherwise: `~/Vector-wt/knuckle`.
> `PY=/Users/deepakdiwan/soma/.venv/bin/python` — type this first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = the output must match (numbers may differ by ±0.05 unless stated). If it does not match: re-run once, then do the "If not" line.


**Goal:** replace the custom-ESC CAN protocol with the GIM protocol (spec §11), keep the `can_bus.h` API, update params, all tests pass.
Reference files (TESTED, copy verbatim): `~/Vector/stages/code/fw/gim_proto.h`, `gim_proto.c`, `gim_proto.py`, `test_gim_proto.py`.
**Branch:** `arm-knuckle`, tag `stage-6-done`. **Inputs:** stage 5 commit.

## Steps
1. `cd ~/Vector-wt/knuckle && /usr/bin/git describe --tags --abbrev=0` → `stage-5-done`.
2. `cd software/robot-os && python3 -m pytest -q 2>&1 | tail -1` → `41 passed` (baseline).
3. Copy: `cd ~/Vector-wt/knuckle && F=~/Vector/stages/code/fw && cp $F/gim_proto.c $F/gim_proto.h firmware/shared/ && cp $F/gim_proto.py software/robot-os/soma_arm/ && cp $F/test_gim_proto.py software/robot-os/tests/`
4. `cd software/robot-os && python3 -m pytest -q 2>&1 | tail -1` → `50 passed` (designer ran this: 50 passed).
5. `firmware/base-node/src/shared_impl.cpp`: add one line `#include "../../shared/gim_proto.c"` next to the other shared includes.
6. `firmware/base-node/src/can_bus.cpp` — keep every function name/signature in can_bus.h. Change bodies only:
   - `#include "../../shared/gim_proto.h"`; add `static const float KTG[CAN_N_JOINTS] = ARM_GIM_KTG;` and `static uint8_t last_node = 0;`
   - init: `TWAI_TIMING_CONFIG_500KBITS()` [U — if GIM-protocol.pdf says 1 Mbit keep `_1MBITS`].
   - `tx_frame(id, b, 8)` with id = node (standard id, no function code).
   - `can_send_pdo2(node,pos,vel)` → `gim_enc_position(b, pos, 20)`; set `last_node = node`. `vel` unused.
   - `can_send_pdo3`, `can_send_ping`, `can_sdo_*` → `return true;` (no-op).
   - `can_enable_all` → for each node: `gim_enc_simple(b, GIM_CMD_CLEAR_ERR)` send, then `GIM_CMD_START` send. `can_disable_all` → `GIM_CMD_STOP` each. `can_estop_broadcast` → `GIM_CMD_ESTOP` then `GIM_CMD_STOP` each node. `can_send_nmt` → map NMT_ENABLE/DISABLE/ESTOP to these, return true.
   - `can_bus_poll`: for each received frame with dlc 8: node = `m.identifier` if it is 1..3 else `last_node`; `gim_dec_reply(m.data, 8, KTG[idx], NULL, &s->pos, &s->vel, &s->iq, NULL)`; set `last_rx_ms`, `online`. If byte1 ≠ 0 set `s->status |= 0x8`.
   - housekeeping unchanged.
7. `cad/arm/arm_params.py`: add `GIM = {"models": ("GIM4305-10", "GIM4310-36", "GIM4310-10-GDS"), "can_ids": (1, 2, 3), "ktg": (0.62, 3.46, 0.96)}` [ktg U]; set KIN `j2_z 150, l_upper 150, l_fore 130, j5_dx 79, tip_dx 158.61`; JOINT limits from kp.LIM (CAD frame). In `gen_params.py` emit `#define ARM_GIM_KTG {0.62f, 3.46f, 0.96f}` and `#define ARM_GIM_CAN_IDS {1, 2, 3}` into arm_params_gen.h. Before changing j2_z, read how `cad/arm/parts.py` defines the old j2_z reference and write it in STATUS.
8. `cd cad/arm && python3 gen_params.py` → output contains `BASE_Z=150.0mm L1=150.0 L2=130.0 L3=158.61 (tip x ~439mm)`; run twice → `/usr/bin/git diff --stat` unchanged after the 2nd run (idempotent).
9. **GATE** `cd ~/Vector-wt/knuckle/software/robot-os && python3 -m pytest -q 2>&1 | tail -1` → `50 passed` (or more; 0 failed). Plus `grep -c ARM_GIM_KTG firmware/shared/arm_params_gen.h` → `1`. Firmware compile: only if `pio` exists (`which pio`): `cd firmware/base-node && pio run 2>&1 | tail -1` → `SUCCESS`; if pio missing write `pio not installed, compile not checked` in STATUS.
   Fallback: kinematics test failing after step 7 → 20 min/3 tries, then revert arm_params.py KIN only (`/usr/bin/git checkout cad/arm/arm_params.py`), re-add only the GIM dict, note in STATUS.

Files: the 4 gim files, shared_impl.cpp, can_bus.cpp, arm_params.py, gen_params.py, the 2 generated files, STATUS.
## Status + commit (always the last steps)
S.1 Append to `docs/STATUS-knuckle.md` (create it if missing, first line `# STATUS — knuckle arm (branch arm-knuckle)`) a section:
```
## Stage 6 — <today's date> — PASS or FAIL
- Gate lines: <paste every line that ends in PASS/FAIL/BAD from this stage>
- Files added/changed: <list from `/usr/bin/git status --short`>
- Fallbacks used: <none | list>
- UNVERIFIED values touched: <none | list>
- Questions for Riyansh: <none | list>
```
S.2 Command: `cd ~/Vector-wt/knuckle && /usr/bin/git status --short`
Expected: only the files this stage names, plus `docs/STATUS-knuckle.md`. NO `out/`, NO `.stl`, NO `__pycache__`. If not: delete/unstage the extra paths (do not commit them).
S.3 Command: `/usr/bin/git add -A <the paths from S.2> && /usr/bin/git commit -m "stage 6: GIM CAN protocol firmware and params"`
Expected: `[arm-knuckle <hash>] stage 6: GIM CAN protocol firmware and params`
S.4 Command: `/usr/bin/git tag stage-6-done && /usr/bin/git push origin arm-knuckle --tags`
Expected: ends with `* [new tag]         stage-6-done -> stage-6-done`. If push is rejected: run `/usr/bin/git pull --ff-only origin arm-knuckle` once and push again; if still rejected write `BLOCKED: push` in STATUS and stop.
S.5 STOP. Do not start the next stage.

