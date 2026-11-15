/*
 * Orchestrates the SOMA Carrier v1.3 rebuild inside EasyEDA Pro 3.2.
 *
 * Pipeline:
 *   1. resolve footprints per (footprint,rotation) key:
 *      - verified system-library matches from syslib-match.ts are placed
 *        directly (device association + pcb_PrimitiveComponent.create
 *        accept foreign-library uuids), with a rotation + origin offset
 *        so their pads land on the KiCad pad positions;
 *      - the 5 unmatched keys are drawn on an open footprint-editor tab
 *        (pcb_PrimitivePad / pcb_PrimitivePolyline + pcb_Document.save),
 *        after activateDocument + a getCurrentDocumentInfo uuid check —
 *        waitForDocumentReady has no handler in 3.2.209 and hangs;
 *      - drawn footprints/symbols get a `soma:v1.2-*` description tag via
 *        lib_*.modify so re-runs skip work they already did (pad counts
 *        are verified inside the doc before and after drawing).
 *   2. reuse-or-create symbols (fp-domain pin numbering so pin->pad
 *      import maps to the right copper) + devices in a writable library
 *   3. create project + schematic + pcb + board link
 *   4. place schematic components, wire stubs + net flags/ports
 *   5. importChanges into PCB, position components (with sys-fp
 *      offsets), draw outline, mounting holes, replicated tracks, vias
 *      and GND pours
 *   6. save both documents and report a summary
 *
 * Every eda call is time-bounded via `call()` — a hung RPC surfaces as a
 * warning instead of freezing the run.  Re-runs are safe: existing
 * library items are looked up by title and reused, so the 重复数据
 * error cannot occur.  If a footprint ends up with no usable content the
 * part falls back to board-level free pads, so copper/net connectivity
 * is preserved either way.
 */

import { BOARD_DATA } from './board-data';
import { symbolSource } from './eda-source';
import { footprintOps, FP_LAYER } from './fpdraw';
import { PARTS } from './parts-table';
import { LAYER, planPcb } from './pcbplan';
import { planSchematic, STUB_LEN, symbolPins } from './schplan';
import { prot, px, py, polygonSource } from './coords';
import { CUSTOM_KEYS, fpKeyOf, SYS_FP_MATCH } from './syslib-match';
import type { BoardData, PartData } from './board-data-types';

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

/* Ambient enum values from the bundled v3.2 API — used as literals so the
 * bundle never references enum objects that may not exist at runtime. */
const LIB_DEVICE = '3' as ELIB_LibraryType.DEVICE;
const LIB_FOOTPRINT = '4' as ELIB_LibraryType.FOOTPRINT;
const PAD_ELLIPSE = 'ELLIPSE' as EPCB_PrimitivePadShapeType.ELLIPSE;
const PAD_RECT = 'RECT' as EPCB_PrimitivePadShapeType.RECTANGLE;
const PAD_OVAL = 'OVAL' as EPCB_PrimitivePadShapeType.OBLONG;
const HOLE_ROUND = 'ROUND' as EPCB_PrimitivePadHoleType.ROUND;
const HOLE_SLOT = 'SLOT' as EPCB_PrimitivePadHoleType.SLOT;
const POUR_SOLID = 'solid' as EPCB_PrimitivePourFillMethod.SOLID;
const ALIGN_LEFT_TOP = 1 as EPCB_PrimitiveStringAlignMode.LEFT_TOP;

const warnings: string[] = [];
const info: string[] = [];

function report(p: number, title: string): void {
	try { eda.sys_LoadingAndProgressBar.showProgressBar(p, title); } catch { /* noop */ }
}

function slog(msg: string, type?: ESYS_LogType): void {
	try { eda.sys_Log.add(`[SOMA] ${msg}`, type); } catch { /* noop */ }
}

function errText(e: unknown): string {
	if (e instanceof Error) return e.message;
	try { const s = JSON.stringify(e); return s && s !== '{}' ? s : String(e); }
	catch { return String(e); }
}

function warn(msg: string): void {
	warnings.push(msg);
	slog(`WARN ${msg}`, 'warn' as ESYS_LogType);
}

/* Time-bounded API call.  Rejects/timeouts become `undefined` + a warning
 * (soft=true logs only).  The underlying RPC keeps running in the
 * background — we just stop waiting for it. */
async function call<T>(name: string, p: Promise<T> | undefined, ms = 12000, soft = false): Promise<T | undefined> {
	if (!p || typeof (p as Promise<T>).then !== 'function') {
		if (!soft) warn(`${name}: api unavailable`);
		else slog(`${name}: api unavailable (soft)`);
		return undefined;
	}
	try {
		return await Promise.race<T>([
			p,
			new Promise<T>((_r, rej) => setTimeout(() => rej(new Error(`timeout after ${ms}ms`)), ms)),
		]);
	}
	catch (e) {
		const msg = `${name}: ${errText(e)}`;
		if (soft) slog(`soft-fail ${msg}`, 'warn' as ESYS_LogType);
		else warn(msg);
		return undefined;
	}
}

/* ---------------- helpers ---------------- */

function designatorPrefix(ref: string): string {
	if (ref.startsWith('DS')) return 'TP';
	if (ref === 'IR1') return 'J';
	if (ref === 'BZ1') return 'BZ';
	const m = /^[A-Z]+/.exec(ref);
	return m ? m[0] : 'U';
}

function partPinNames(part: PartData): Map<string, string> {
	const spec = PARTS[part.ref];
	const m = new Map<string, string>();
	for (const pad of part.pads) {
		if (pad.type === 'np_thru_hole') continue;
		m.set(pad.num, spec?.pinNames?.[pad.num] ?? (pad.net || 'NC'));
	}
	return m;
}

const norm = (s: string) => s.toLowerCase();

/** search() returns fuzzy matches — only accept an exact (case-insensitive)
 *  name hit so we never reuse an unrelated footprint. */
async function findItem(kind: 'footprint' | 'symbol' | 'device', name: string, libUuid: string): Promise<string | undefined> {
	const api = kind === 'footprint' ? eda.lib_Footprint : kind === 'symbol' ? eda.lib_Symbol : eda.lib_Device;
	const res = await call(`lib_${kind}.search "${name}"`,
		api.search(name, libUuid) as Promise<ILIB_FootprintSearchItem[] | undefined>, 8000, true);
	const hit = res?.find(i => norm(i.name) === norm(name));
	return hit?.uuid;
}

/** ILIB_*.get() returns METADATA ONLY — there is no dataStr field on the
 *  item interface in this build (verified against the handler map in
 *  pro-ui 3.2.198 and api-types.d.ts).  Content readback only works via
 *  sys_FileManager.getDocumentSource() on an open+active tab, or
 *  lib_*.getRenderImage() for a coarse non-empty check. */
async function getItemDesc(kind: 'footprint' | 'symbol' | 'device', uuid: string, libUuid: string): Promise<string> {
	const api = kind === 'footprint' ? eda.lib_Footprint : kind === 'symbol' ? eda.lib_Symbol : eda.lib_Device;
	const item = await call(`lib_${kind}.get`,
		api.get(uuid, libUuid) as Promise<{ description?: string } | undefined>, 8000, true);
	return item?.description ?? '';
}

/* Markers written via lib_*.modify(description=...) after verified work —
 * the only persistent readback channel that exists in 3.2.209. */
const TAG_FP_DRAWN = 'soma:v1.2-drawn';
const TAG_SYM_SRC = 'soma:v1.2-src';

/** Poll getCurrentDocumentInfo until the ACTIVE document is ours —
 *  matched by doc uuid OR by the tab id we activated (in 3.2.209 an
 *  openInEditor tab id equals the library-doc uuid, but accept either).
 *  waitForDocumentReady/getDocumentReadyState have NO handlers in
 *  3.2.209 (calls hang forever) — activate-then-poll is the only working
 *  readiness path.  Lazy tabs load on activation, so the caller must call
 *  activateDocument() first. */
async function waitActiveDoc(uuid: string, msMax = 9000, label = 'doc', tabId?: string): Promise<IDMT_EditorDocumentItem | undefined> {
	const t0 = Date.now();
	let last: IDMT_EditorDocumentItem | undefined;
	while (Date.now() - t0 < msMax) {
		const info = await call(`${label} getCurrentDocumentInfo`,
			Promise.resolve(eda.dmt_SelectControl.getCurrentDocumentInfo()), 4000, true);
		if (info) {
			last = info;
			if (info.uuid === uuid || (tabId !== undefined && info.tabId === tabId)) return info;
		}
		await sleep(400);
	}
	slog(`${label}: active doc never became ${uuid.slice(0, 8)} (last=${last ? `${last.documentType}:${last.uuid?.slice(0, 8)} tab=${last.tabId}` : 'none'})`, 'warn' as ESYS_LogType);
	return undefined;
}

/* ---------------- pad-number domain mapping ---------------- */

/** Resolved footprint reference for one (footprint,rotation) key. */
interface FpRef {
	kind: 'sys' | 'drawn';
	uuid: string;
	libUuid: string;
	rot: number;                    // placement rotation for sys footprints
	dx: number; dy: number;         // placement origin offset (mil)
	pm?: Record<string, string>;    // kicad pad num -> fp pad num
	name: string;
}

function fpKeyOfPart(part: PartData): string {
	return fpKeyOf(part.footprint, part.rot);
}

/** Re-number a part's pads into footprint-domain numbering (identity for
 *  custom-drawn footprints; the system footprint's numbering for sys
 *  matches).  Symbol pins, schematic stubs and PCB net assignment must all
 *  speak fp-domain numbers so pin->pad import maps to the right copper. */
function mappedPart(part: PartData, fpRefs: Map<string, FpRef>): PartData {
	const pm = fpRefs.get(fpKeyOfPart(part))?.pm;
	if (!pm) return part;
	return { ...part, pads: part.pads.map(p => ({ ...p, num: pm[p.num] ?? p.num })) };
}

function mappedBoard(data: BoardData, fpRefs: Map<string, FpRef>): BoardData {
	return { ...data, parts: data.parts.map(p => mappedPart(p, fpRefs)) };
}

/* ---------------- footprint drawing (editor-tab path) ---------------- */

type FpState = 'sys' | 'ok' | 'empty' | 'missing';

/** Count pads already inside the open footprint doc — verifies primitives
 *  actually landed in THIS editor (previously a missing active-doc check
 *  could have sent them to whatever document had focus). */
async function footprintPadCount(label: string): Promise<number> {
	const pads = await call(`${label} pad.getAll`, eda.pcb_PrimitivePad.getAll(), 8000, true);
	return Array.isArray(pads) ? pads.length : -1;
}

/** Draw pads/silk for `part` inside the footprint editor tab.
 *  Sequence: openInEditor -> activateDocument (lazy tabs only load when
 *  activated) -> poll getCurrentDocumentInfo until this footprint is the
 *  active doc -> draw -> count pads -> save -> close -> tag description.
 *  Returns true only if the primitives landed and the doc saved. */
async function drawFootprint(part: PartData, fpUuid: string, libUuid: string, fpName: string, label: string): Promise<boolean> {
	const wantPads = footprintOps(part).filter(o => o.kind === 'pad').length;
	const tabId = await call(`${label} openInEditor`, eda.lib_Footprint.openInEditor(fpUuid, libUuid), 15000);
	if (!tabId) return false;
	let ok = false;
	try {
		// activate FIRST: a lazy-opened tab never finishes loading otherwise
		await call(`${label} activateDocument`, eda.dmt_EditorControl.activateDocument(tabId), 8000, true);
		const info = await waitActiveDoc(fpUuid, 9000, label, tabId);
		if (!info) {
			warn(`${label}: footprint doc never became active — leaving it empty`);
			return false;
		}
		slog(`${label}: active doc ${info.documentType}:${info.uuid?.slice(0, 8)} tab ${info.tabId}`);
		const before = await footprintPadCount(label);
		if (before >= wantPads) {
			// already populated (e.g. drawn by an earlier run that never got
			// tagged) — do NOT draw again or pads would duplicate
			slog(`${label}: ${before} pads already present — skipping redraw`);
			await call(`${label} pcb_Document.save`, eda.pcb_Document.save(), 15000, true);
			await call(`${label} tag`, eda.lib_Footprint.modify(fpUuid, libUuid, fpName, undefined, TAG_FP_DRAWN, undefined), 8000, true);
			return true;
		}
		let drawn = 0, failed = 0;
		for (const op of footprintOps(part)) {
			if (op.kind === 'pad') {
				const shape = op.shape[0] === 'RECT'
					? [PAD_RECT, op.shape[1], op.shape[2], 0] as TPCB_PrimitivePadShape
					: op.shape[0] === 'ELLIPSE'
						? [PAD_ELLIPSE, op.shape[1], op.shape[2]] as TPCB_PrimitivePadShape
						: [PAD_OVAL, op.shape[1], op.shape[2]] as TPCB_PrimitivePadShape;
				const hole = op.hole
					? (op.hole[0] === 'SLOT' ? [HOLE_SLOT, op.hole[1], op.hole[2]] : [HOLE_ROUND, op.hole[1]]) as TPCB_PrimitivePadHole
					: null;
				const r = await call(`${label} pad ${op.num}`,
					eda.pcb_PrimitivePad.create(op.layer as TPCB_LayersOfPad, op.num, op.x, op.y, op.rot,
						shape, '', hole, 0, 0, 0, op.plated, 0), 8000, failed > 0);
				r ? drawn++ : failed++;
			}
			else {
				let poly: IPCB_Polygon | undefined;
				try { poly = eda.pcb_MathPolygon.createPolygon(op.pts as TPCB_PolygonSourceArray) as IPCB_Polygon; }
				catch { poly = undefined; }
				if (!poly) { failed++; slog(`${label}: createPolygon failed`, 'warn' as ESYS_LogType); continue; }
				const r = await call(`${label} polyline`,
					eda.pcb_PrimitivePolyline.create('', op.layer as TPCB_LayersOfLine, poly, op.w), 8000, failed > 0);
				r ? drawn++ : failed++;
			}
		}
		slog(`${label}: drew ${drawn} primitives (${failed} failed)`);
		const after = await footprintPadCount(label);
		slog(`${label}: pads in doc ${before} -> ${after} (want ${wantPads})`);
		// save even if some prims failed — partial geometry beats losing all
		const saved = await call(`${label} pcb_Document.save`, eda.pcb_Document.save(), 15000);
		if (!saved) warn(`${label}: footprint save failed`);
		ok = after >= wantPads && drawn > 0 && failed === 0 && saved !== false && saved !== undefined;
		if (ok) {
			await call(`${label} tag`, eda.lib_Footprint.modify(fpUuid, libUuid, fpName, undefined, TAG_FP_DRAWN, undefined), 8000, true);
		}
	}
	finally {
		const closed = await call(`${label} closeDocument`, eda.dmt_EditorControl.closeDocument(tabId), 8000, true);
		if (!closed) warn(`${label}: footprint tab did not close — close it manually if it is still open`);
	}
	return ok;
}

/* ---------------- library generation ---------------- */

async function buildLibrary(libUuid: string, sysLibUuid: string | undefined): Promise<{
	devices: Map<string, { uuid: string }>;
	fpRefs: Map<string, FpRef>;
	fpState: Map<string, FpState>;
}> {
	const devices = new Map<string, { uuid: string }>();
	// footprints deduplicated by (footprint type, rotation)
	const fpRefs = new Map<string, FpRef>();
	const fpState = new Map<string, FpState>();
	const symByKey = new Map<string, string>();
	const parts = BOARD_DATA.parts;
	let done = 0;
	let symVerified = false;
	for (const part of parts) {
		report(2 + Math.round(20 * done / parts.length), `Library ${part.ref} (${part.footprint})`);
		done++;
		slog(`library ${part.ref} ${part.footprint}@${part.rot}`);
		const fpKey = fpKeyOfPart(part);
		const fpName = `SOMA-${part.footprint}-R${Math.round(part.rot)}`;

		let fpRef = fpRefs.get(fpKey);
		if (!fpRef) {
			const m = sysLibUuid ? SYS_FP_MATCH[fpKey] : undefined;
			if (m) {
				// system-library footprint — verify it is reachable, then use
				// it directly (no copying needed: device associations and
				// pcb_PrimitiveComponent.create both accept foreign lib uuids)
				const probe = await call(`sysfp get ${m.sysFpName}`,
					eda.lib_Footprint.get(m.sysFpUuid, sysLibUuid!) as Promise<ILIB_FootprintItem | undefined>, 8000, true);
				if (probe) {
					fpRef = { kind: 'sys', uuid: m.sysFpUuid, libUuid: sysLibUuid!, rot: m.rot, dx: m.dx, dy: m.dy, pm: m.padmap, name: m.sysFpName };
					fpState.set(fpKey, 'sys');
					slog(`${part.ref}: system footprint ${m.sysFpName} (rot ${m.rot}, off ${m.dx},${m.dy})`);
				}
				else warn(`${part.ref}: system footprint ${m.sysFpName} unreachable — falling back to custom draw`);
			}
			if (!fpRef) {
				// custom-draw path (unmatched keys, or sys fp probe failed)
				let fpUuid = await findItem('footprint', fpName, libUuid);
				if (!fpUuid) {
					fpUuid = await call(`lib_Footprint.create ${fpName}`, eda.lib_Footprint.create(libUuid, fpName), 10000);
					if (!fpUuid) fpUuid = await findItem('footprint', fpName, libUuid); // duplicate-title → it already exists
				}
				if (!fpUuid) {
					warn(`${part.ref}: no footprint uuid for ${fpName} (${CUSTOM_KEYS[fpKey] ?? 'custom'})`);
					fpState.set(fpKey, 'missing');
				}
				else {
					const desc = await getItemDesc('footprint', fpUuid, libUuid);
					if (desc.includes(TAG_FP_DRAWN)) {
						fpState.set(fpKey, 'ok');
					}
					else {
						slog(`${part.ref}: drawing footprint ${fpName}`);
						fpState.set(fpKey, await drawFootprint(part, fpUuid, libUuid, fpName, `${part.ref} ${fpName}`) ? 'ok' : 'empty');
					}
					if (fpState.get(fpKey) === 'ok') {
						fpRef = { kind: 'drawn', uuid: fpUuid, libUuid, rot: 0, dx: 0, dy: 0, name: fpName };
					}
				}
			}
			if (fpRef) fpRefs.set(fpKey, fpRef);
		}

		// symbol — deduplicated by pin-set (fp-domain numbering so the
		// device pin->pad map lands on the right copper)
		let symUuid: string | undefined;
		const mapped = mappedPart(part, fpRefs);
		const pinNames = partPinNames(part);
		const pm = fpRef?.pm;
		const pinList = symbolPins(mapped).map(n => {
			const orig = pm ? (Object.keys(pm).find(k => pm[k] === n) ?? n) : n;
			return { num: n, name: pinNames.get(orig) ?? orig };
		});
		const symKey = JSON.stringify(pinList);
		symUuid = symByKey.get(symKey);
		if (!symUuid) {
			const symName = `SOMA-${part.ref}`;
			symUuid = await findItem('symbol', symName, libUuid);
			if (!symUuid) {
				symUuid = await call(`lib_Symbol.create ${symName}`, eda.lib_Symbol.create(libUuid, symName), 10000);
				if (!symUuid) symUuid = await findItem('symbol', symName, libUuid);
			}
			if (!symUuid) warn(`${part.ref}: no symbol uuid for ${symName}`);
			else {
				symByKey.set(symKey, symUuid);
				const desc = await getItemDesc('symbol', symUuid, libUuid);
				if (!desc.includes(TAG_SYM_SRC)) {
					const src = symbolSource(symName, designatorPrefix(part.ref), pinList);
					const ok = await call(`lib_Symbol.updateDocumentSource ${symName}`,
						eda.lib_Symbol.updateDocumentSource(symUuid, libUuid, src), 15000);
					if (!ok) warn(`${part.ref}: symbol source write failed — symbol may be empty`);
					else {
						await call(`lib_Symbol.modify tag`, eda.lib_Symbol.modify(symUuid, libUuid, symName, undefined, TAG_SYM_SRC, undefined), 8000, true);
						// verify ONE symbol end-to-end per run (open + read source)
						if (!symVerified) {
							symVerified = true;
							const ok2 = await verifySymbolSource(symUuid, libUuid, pinList.length, `${part.ref} symverify`);
							if (!ok2) warn('first symbol readback found no pins — symbols may still be empty; check Diagnostics output');
						}
					}
				}
			}
		}

		// device — reuse by name, else create with symbol+footprint association
		const devName = `SOMA-${part.ref}`;
		let devUuid = await findItem('device', devName, libUuid);
		if (devUuid && fpRef) {
			// existing device from an older run may point at a stale/empty
			// footprint — check the association and rebuild if it mismatches
			const dev = await call(`lib_Device.get ${devName}`,
				eda.lib_Device.get(devUuid, libUuid) as Promise<ILIB_DeviceItem | undefined>, 8000, true);
			const assocFp = dev?.association?.footprint?.uuid;
			const assocSym = dev?.association?.symbol?.uuid;
			if (assocFp && fpRef && assocFp !== fpRef.uuid) {
				slog(`${part.ref}: device assoc ${assocFp?.slice(0, 8)} != ${fpRef.uuid.slice(0, 8)} — rebuilding device`);
				await call(`lib_Device.delete ${devName}`, eda.lib_Device.delete(devUuid, libUuid), 8000, true);
				devUuid = undefined;
			}
			else if (assocSym && symUuid && assocSym !== symUuid) {
				slog(`${part.ref}: device symbol assoc mismatch — rebuilding device`);
				await call(`lib_Device.delete ${devName}`, eda.lib_Device.delete(devUuid, libUuid), 8000, true);
				devUuid = undefined;
			}
		}
		if (!devUuid && symUuid && fpRef) {
			devUuid = await call(`lib_Device.create ${devName}`, eda.lib_Device.create(libUuid, devName, undefined, {
				symbol: { uuid: symUuid, libraryUuid: libUuid },
				footprint: { uuid: fpRef.uuid, libraryUuid: fpRef.libUuid },
			}), 10000);
			if (!devUuid) devUuid = await findItem('device', devName, libUuid);
		}
		if (devUuid && fpRef) devices.set(part.ref, { uuid: devUuid });
		else warn(`${part.ref}: no device (sym=${!!symUuid} fp=${!!fpRef} dev=${!!devUuid}) — schematic/board will fall back`);
	}
	const drawnOk = [...fpState.values()].filter(s => s === 'ok').length;
	const sysOk = [...fpState.values()].filter(s => s === 'sys').length;
	info.push(`library: ${sysOk} system + ${drawnOk} drawn footprints, ${symByKey.size} symbols, ${devices.size} devices`);
	return { devices, fpRefs, fpState };
}

/** Open a symbol tab and count PIN records in its document source — the
 *  only real content readback in this build. */
async function verifySymbolSource(symUuid: string, libUuid: string, wantPins: number, label: string): Promise<boolean> {
	const tabId = await call(`${label} openInEditor`, eda.lib_Symbol.openInEditor(symUuid, libUuid), 15000, true);
	if (!tabId) return false;
	try {
		await call(`${label} activateDocument`, eda.dmt_EditorControl.activateDocument(tabId), 8000, true);
		const info = await waitActiveDoc(symUuid, 8000, label, tabId);
		if (!info) return false;
		const src = await call(`${label} getDocumentSource`, eda.sys_FileManager.getDocumentSource(), 10000, true);
		const pins = typeof src === 'string' ? (src.match(/"PIN"/g) ?? []).length : 0;
		slog(`${label}: source ${typeof src === 'string' ? src.length : 0} chars, ${pins} PIN records (want ${wantPins})`);
		return pins >= wantPins;
	}
	finally {
		await call(`${label} closeDocument`, eda.dmt_EditorControl.closeDocument(tabId), 8000, true);
	}
}

/* ---------------- schematic ---------------- */

async function buildSchematic(
	devices: Map<string, { uuid: string }>,
	libUuid: string,
	fpRefs: Map<string, FpRef>,
): Promise<Map<string, string>> {
	// feed fp-domain pad numbers so stub labels land on pins whose numbers
	// match the footprint pads (matters for non-identity padmaps — K1)
	const plan = planSchematic(mappedBoard(BOARD_DATA, fpRefs));
	const uniqueIds = new Map<string, string>();
	const realPins = new Map<string, Map<string, { x: number; y: number; dir: -1 | 1 }>>();
	let i = 0;
	for (const c of plan.comps) {
		report(25 + Math.round(22 * i / plan.comps.length), `Schematic ${c.ref}`);
		i++;
		const dev = devices.get(c.ref);
		if (!dev) { warnings.push(`${c.ref}: skipped — no device`); continue; }
		const comp = await call(`sch create ${c.ref}`, eda.sch_PrimitiveComponent.create(
			{ libraryType: LIB_DEVICE, libraryUuid: libUuid, uuid: dev.uuid },
			c.cx, c.cy, undefined, 0, false, true, true,
		), 15000);
		if (!comp) { warn(`${c.ref}: sch create failed`); continue; }
		const pid = comp.getState_PrimitiveId?.();
		if (pid) {
			await call(`sch modify ${c.ref}`, eda.sch_PrimitiveComponent.modify(pid, { designator: c.ref, name: c.value }), 8000, true);
			const pins = await call(`sch pins ${c.ref}`,
				eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId?.(pid), 8000, true);
			if (pins?.length) {
				const m = new Map<string, { x: number; y: number; dir: -1 | 1 }>();
				for (const pin of pins) {
					const num = pin.getState_PinNumber?.();
					const x = pin.getState_X?.();
					const y = pin.getState_Y?.();
					const rot = pin.getState_Rotation?.() ?? 0;
					if (num !== undefined && x !== undefined && y !== undefined) {
						// pin rot 0 points +x (into the box) -> stub extends -x
						m.set(String(num), { x, y, dir: rot === 180 ? 1 : -1 });
					}
				}
				realPins.set(c.ref, m);
			}
		}
		const uid = comp.getState_UniqueId?.();
		if (uid) uniqueIds.set(c.ref, uid);
	}
	for (const c of plan.comps) {
		for (const p of c.pins) {
			if (p.kind === 'nc') continue;
			const real = realPins.get(c.ref)?.get(p.num);
			const px0 = real?.x ?? p.x;
			const py0 = real?.y ?? p.y;
			const dir = real?.dir ?? p.dir;
			const ex = px0 + dir * STUB_LEN;
			// stub carries the net name itself — connectivity survives even
			// if the netflag/netport decoration fails
			await call(`sch stub ${c.ref}.${p.num}`, eda.sch_PrimitiveWire.create([px0, py0, ex, py0], p.net), 8000, true);
			if (p.kind === 'ground') {
				await call(`sch flag ${c.ref}.${p.num}`, eda.sch_PrimitiveComponent.createNetFlag('Ground', p.net, ex, py0), 8000, true);
			}
			else if (p.kind === 'power') {
				await call(`sch flag ${c.ref}.${p.num}`, eda.sch_PrimitiveComponent.createNetFlag('Power', p.net, ex, py0), 8000, true);
			}
			else {
				await call(`sch port ${c.ref}.${p.num}`,
					eda.sch_PrimitiveComponent.createNetPort('BI', p.net, ex, py0, dir === -1 ? 180 : 0), 8000, true);
			}
		}
	}
	for (const h of plan.headers) {
		await call('sch header', eda.sch_PrimitiveRectangle.create(h.x, h.y, h.w, h.h, 0, 0, '#888888'), 6000, true);
		await call('sch header text', eda.sch_PrimitiveText.create(h.x + 10, h.y + 14, h.title, 0, '#000000', undefined, 12, true), 6000, true);
	}
	return uniqueIds;
}

/* ---------------- PCB ---------------- */

/** Free-pad copper fallback for a part whose footprint has no content:
 *  absolute-positioned pads + silk + designator directly on the board. */
async function drawPartFreePads(part: PartData, topLayer: number): Promise<void> {
	let ok = 0, fail = 0;
	for (const pad of part.pads) {
		if (pad.type === 'np_thru_hole') continue;
		const smd = pad.type === 'smd';
		const shape: TPCB_PrimitivePadShape = pad.shape === 'rect' || pad.shape === 'roundrect'
			? [PAD_RECT, px(pad.w), px(pad.h), 0]
			: pad.shape === 'circle'
				? [PAD_ELLIPSE, px(pad.w), px(pad.h)]
				: [PAD_OVAL, px(pad.w), px(pad.h)];
		const hole: TPCB_PrimitivePadHole | null = smd ? null
			: pad.drillOval ? [HOLE_SLOT, px(pad.drillX), px(pad.drillY)] : [HOLE_ROUND, px(pad.drillX)];
		const r = await call(`freepad ${part.ref}.${pad.num}`, eda.pcb_PrimitivePad.create(
			(smd ? topLayer : LAYER.MULTI) as TPCB_LayersOfPad, pad.num, px(pad.ax), py(pad.ay), prot(pad.rot),
			shape, pad.net || '', hole, 0, 0, 0, !smd, 0), 8000, fail > 2);
		r ? ok++ : fail++;
	}
	for (const s of part.silk) {
		const w = px(s.w) || 6;
		let pts: Array<'L' | number> | undefined;
		if (s.k === 'l' && s.ax1 !== undefined) pts = [px(s.ax1), py(s.ay1!), 'L', px(s.ax2!), py(s.ay2!)];
		else if ((s.k === 'a' || s.k === 'p') && s.apts && s.apts.length >= 2) pts = polygonSource(s.apts);
		if (!pts) continue;
		try {
			const poly = eda.pcb_MathPolygon.createPolygon(pts as TPCB_PolygonSourceArray);
			if (poly) await call(`freesilk ${part.ref}`, eda.pcb_PrimitivePolyline.create('', LAYER.TOP_SILK as TPCB_LayersOfLine, poly, w), 6000, true);
		}
		catch { /* cosmetic */ }
	}
	try {
		await call(`freedes ${part.ref}`, eda.pcb_PrimitiveString.create(
			LAYER.TOP_SILK as TPCB_LayersOfImage, px(part.x), py(part.y), part.ref,
			'default', 45, 6, ALIGN_LEFT_TOP, prot(part.rot), false, 0, false, false), 6000, true);
	}
	catch { /* cosmetic */ }
	info.push(`${part.ref}: free-pad fallback (${ok} pads${fail ? `, ${fail} failed` : ''})`);
}

async function buildPcb(
	uniqueIds: Map<string, string>,
	devices: Map<string, { uuid: string }>,
	fpRefs: Map<string, FpRef>,
	fpState: Map<string, FpState>,
): Promise<void> {
	const plan = planPcb(BOARD_DATA);
	const partByRef = new Map(BOARD_DATA.parts.map(p => [p.ref, p]));
	// per-ref placement transform: system footprints carry a rotation +
	// origin offset so their pads land on the KiCad pad positions
	const placeOf = (ref: string) => {
		const part = partByRef.get(ref);
		const pl = plan.placements.find(p => p.ref === ref);
		const fpRef = part ? fpRefs.get(fpKeyOfPart(part)) : undefined;
		if (!pl) return undefined;
		return { pl, part, fpRef, x: pl.x + (fpRef?.dx ?? 0), y: pl.y + (fpRef?.dy ?? 0), rot: fpRef?.rot ?? 0 };
	};

	// components already imported by importChanges — move to v1.3 positions
	try {
		const comps = await call('pcb getAll components', eda.pcb_PrimitiveComponent.getAll(), 15000) ?? [];
		const wanted = new Map(plan.placements.map(p => [p.ref, p]));
		for (const comp of comps) {
			const d = comp.getState_Designator();
			if (!d) continue;
			const pl = wanted.get(d);
			if (!pl) continue;
			wanted.delete(d);
			const t = placeOf(d)!;
			try {
				comp.setState_X(t.x);
				comp.setState_Y(t.y);
				if (comp.setState_Rotation) comp.setState_Rotation(t.rot);
				if (comp.setState_Layer) comp.setState_Layer(pl.layer as TPCB_LayersOfComponent);
				await comp.done();
			}
			catch (err) { warnings.push(`${d}: move failed — ${errText(err)}`); }
			// an imported component whose footprint stayed empty has no
			// copper — overlay free pads so nets still connect
			const part = t.part;
			const st = part ? fpState.get(fpKeyOfPart(part)) : undefined;
			if (part && st !== 'ok' && st !== 'sys') {
				warnings.push(`${d}: imported component has empty footprint — drawing free pads`);
				await drawPartFreePads(part, pl.layer);
			}
		}
		for (const [ref, pl] of wanted) {
			const t = placeOf(ref);
			if (!t?.part) continue;
			const part = t.part;
			const dev = devices.get(ref);
			const st = fpState.get(fpKeyOfPart(part));
			const fpRef = t.fpRef;
			if (st !== 'ok' && st !== 'sys') {
				warnings.push(`${ref}: footprint has no content — drawing free pads`);
				await drawPartFreePads(part, pl.layer);
				continue;
			}
			if (!fpRef || !dev) { warnings.push(`${ref}: no device/footprint — drawing free pads`); await drawPartFreePads(part, pl.layer); continue; }
			const comp = await call(`pcb create ${ref}`, eda.pcb_PrimitiveComponent.create(
				{ libraryType: LIB_FOOTPRINT, libraryUuid: fpRef.libUuid, uuid: fpRef.uuid },
				pl.layer as TPCB_LayersOfComponent, t.x, t.y, t.rot, false,
			), 15000);
			const pid = comp?.getState_PrimitiveId?.();
			if (!pid) { warnings.push(`${ref}: direct create failed — drawing free pads`); await drawPartFreePads(part, pl.layer); continue; }
			await call(`pcb modify ${ref}`, eda.pcb_PrimitiveComponent.modify(pid, {
				designator: ref, name: part.value,
				uniqueId: uniqueIds.get(ref) ?? null,
			}), 8000, true);
			const pins = await call(`pcb pins ${ref}`, eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId?.(pid), 8000, true) ?? [];
			// fp-domain pad numbering (system numbering for sys footprints)
			const mapped = mappedPart(part, fpRefs);
			const netByNum = new Map(mapped.pads.map(p => [p.num, p.net]));
			for (const pin of pins) {
				const num = pin.getState_PadNumber?.();
				const net = num ? netByNum.get(String(num)) : undefined;
				if (net) {
					try { (pin as IPCB_PrimitivePad).setState_Net(net); await (pin as IPCB_PrimitivePad).done?.(); }
					catch { /* ratsnest may show these pads unconnected */ }
				}
			}
		}
	}
	catch (err) {
		warnings.push(`component placement failed — ${errText(err)}`);
	}

	// board outline
	try {
		const poly = eda.pcb_MathPolygon.createPolygon(plan.outlinePolygon);
		await eda.pcb_PrimitivePolyline.create('', LAYER.BOARD_OUTLINE, poly as IPCB_Polygon, plan.outlineWidth);
	}
	catch (err) {
		warnings.push(`outline failed — ${errText(err)}`);
	}

	for (const h of plan.holes) {
		const r = await call(`mounting hole @${h.x},${h.y}`, eda.pcb_PrimitivePad.create(LAYER.MULTI, '', h.x, h.y, 0,
			[PAD_ELLIPSE, h.size, h.size], '',
			[HOLE_ROUND, h.drill], 0, 0, 0, false), 8000, true);
		if (!r) warnings.push(`mounting hole at ${h.x},${h.y} failed`);
	}

	let terr = 0;
	for (let k = 0; k < plan.tracks.length; k++) {
		const t = plan.tracks[k];
		const r = await call(`track ${k}`, eda.pcb_PrimitiveLine.create(t.net, t.layer as TPCB_LayersOfLine, t.x1, t.y1, t.x2, t.y2, t.w), 8000, terr > 5);
		if (!r) terr++;
		if (k % 50 === 49) {
			report(55 + Math.round(30 * (k + 1) / plan.tracks.length), `Tracks ${k + 1}/${plan.tracks.length}`);
			await sleep(0);
		}
	}
	info.push(`tracks placed: ${plan.tracks.length - terr}/${plan.tracks.length} (${terr} failed, ${plan.skippedTracks} degenerate skipped)`);
	if (terr) warnings.push(`${terr} track segments failed to create`);

	for (const v of plan.vias) {
		const r = await call(`via ${v.net}`, eda.pcb_PrimitiveVia.create(v.net, v.x, v.y, v.drill, v.size), 8000, true);
		if (!r) warnings.push(`via ${v.net} @${v.x},${v.y} failed`);
	}

	for (const zn of plan.pours) {
		try {
			const poly = eda.pcb_MathPolygon.createPolygon(zn.polygon);
			const r = await call(`pour ${zn.net}`, eda.pcb_PrimitivePour.create(zn.net, zn.layer as TPCB_LayersOfCopper,
				poly as IPCB_Polygon, POUR_SOLID), 15000);
			if (!r) warnings.push(`pour ${zn.net} layer ${zn.layer} failed`);
		}
		catch (err) { warnings.push(`pour ${zn.net} layer ${zn.layer} — ${errText(err)}`); }
	}

	for (const t of plan.texts) {
		await call('silk text', eda.pcb_PrimitiveString.create(t.layer as TPCB_LayersOfImage, t.x, t.y, t.text,
			'default', t.h, 8, ALIGN_LEFT_TOP, t.rot, false, 0, false, false), 6000, true);
	}
}

/* ---------------- library discovery ---------------- */

async function findWritableLib(diag: string[]): Promise<{ libUuid: string; libSrc: string } | undefined> {
	report(1, 'Finding library: personal');
	let libUuid = await call('getPersonalLibraryUuid', eda.lib_LibrariesList.getPersonalLibraryUuid(), 8000, true);
	let libSrc = 'personal library';
	diag.push(`personal=${libUuid || 'none'}`);
	if (!libUuid) {
		report(1, 'Finding library: list');
		const libList = (await call('getAllLibrariesList', eda.lib_LibrariesList.getAllLibrariesList(), 8000, true)) || [];
		const sys = await call('getSystemLibraryUuid', eda.lib_LibrariesList.getSystemLibraryUuid(), 4000, true);
		diag.push(`libraries=${libList.map(l => l.name).join('|') || 'none'}`);
		const pick = libList.find(l => l && l.uuid && l.uuid !== sys);
		if (pick) { libUuid = pick.uuid; libSrc = `library "${pick.name}"`; }
	}
	if (!libUuid) {
		report(1, 'Finding library: project');
		libUuid = await call('getProjectLibraryUuid', eda.lib_LibrariesList.getProjectLibraryUuid(), 8000, true);
		libSrc = 'project library';
	}
	diag.push(`using=${libUuid ? libSrc : 'NONE'}`);
	return libUuid ? { libUuid, libSrc } : undefined;
}

/* ---------------- diagnostics ---------------- */

function apiPresent(path: string): boolean {
	try {
		let o: unknown = eda;
		for (const seg of path.split('.')) o = (o as Record<string, unknown>)?.[seg];
		return typeof o === 'function';
	}
	catch { return false; }
}

/** Diagnostics v1.2: creates SOMA-DIAG-KEEP-* items and does NOT delete
 *  them, so results can be inspected afterwards (EasyEDA library panel,
 *  or read-only sqlite inspection of SOMA.elib).
 *
 *  Readback reality in 3.2.209 (from the pro-ui handler map):
 *   - ILIB_*.get()/search() return metadata only — no dataStr field.
 *     The v1.1 "dataStr EMPTY/missing" verify was a false negative.
 *   - lib_*.getDocumentSource has NO registered handler — calls hang.
 *   - waitForDocumentReady/getDocumentReadyState have NO handlers — calls
 *     hang (this caused the ~15 s stall in the v1.1 diagnostic).
 *   - Real readback: openInEditor + activateDocument + poll
 *     dmt_SelectControl.getCurrentDocumentInfo (uuid/type check) +
 *     sys_FileManager.getDocumentSource() on the active doc.
 */
export async function runDiagnostics(): Promise<void> {
	const lines: string[] = [];
	const t0 = Date.now();
	const log = (s: string) => { lines.push(s); slog(`diag ${s}`); };
	const ms = () => `${Math.round((Date.now() - t0) / 100) / 10}s`;
	const dump = (o: unknown) => {
		try { return JSON.stringify(o, null, 0)?.slice(0, 400) ?? String(o); }
		catch { return String(o); }
	};

	report(5, 'Diagnostics: API probe');
	const probes = [
		'lib_LibrariesList.getPersonalLibraryUuid', 'lib_LibrariesList.getAllLibrariesList',
		'lib_LibrariesList.getSystemLibraryUuid',
		'lib_Footprint.create', 'lib_Footprint.search', 'lib_Footprint.get', 'lib_Footprint.modify',
		'lib_Footprint.openInEditor', 'lib_Footprint.copy', 'lib_Footprint.getRenderImage',
		'lib_Footprint.updateDocumentSource',
		'lib_Symbol.create', 'lib_Symbol.search', 'lib_Symbol.get', 'lib_Symbol.modify',
		'lib_Symbol.openInEditor', 'lib_Symbol.updateDocumentSource', 'lib_Symbol.getRenderImage',
		'lib_Device.create', 'lib_Device.search', 'lib_Device.get', 'lib_Device.getByLcscIds', 'lib_Device.delete',
		'dmt_EditorControl.openDocument', 'dmt_EditorControl.closeDocument',
		'dmt_EditorControl.activateDocument', 'dmt_SelectControl.getCurrentDocumentInfo',
		'dmt_EditorControl.waitForDocumentReady', 'dmt_EditorControl.getDocumentReadyState',
		'pcb_Document.save', 'pcb_PrimitivePad.create', 'pcb_PrimitivePad.getAll',
		'pcb_PrimitivePolyline.create', 'pcb_PrimitiveComponent.create',
		'pcb_MathPolygon.createPolygon', 'sch_PrimitiveComponent.create',
		'sys_FileManager.getDocumentSource', 'sys_FileManager.setDocumentSource',
	];
	for (const p of probes) log(`${apiPresent(p) ? 'OK     ' : 'MISSING'} eda.${p}`);

	report(15, 'Diagnostics: libraries');
	const useLib = await findWritableLib(lines);
	log(`library: ${useLib ? `${useLib.libSrc} ${useLib.libUuid}` : 'NONE — cannot continue'}`);
	const sysLibUuid = await call('diag getSystemLibraryUuid', eda.lib_LibrariesList.getSystemLibraryUuid(), 8000, true);
	log(`system library uuid -> ${sysLibUuid ?? 'NONE'} (${ms()})`);
	if (!useLib) {
		report(100, 'Diagnostics done');
		eda.sys_Dialog.showInformationMessage(lines.join('\n'), 'SOMA diagnostics');
		try { eda.sys_LoadingAndProgressBar.destroyProgressBar(); } catch { /* noop */ }
		return;
	}
	const libUuid = useLib.libUuid;

	/* ---- footprint round trip (KEEP — do not delete) ---- */
	report(25, 'Diagnostics: footprint round-trip');
	const diagName = `SOMA-DIAG-KEEP-${Math.floor(Math.random() * 90000) + 10000}`;
	let fpUuid = await call('diag lib_Footprint.create', eda.lib_Footprint.create(libUuid, diagName), 10000);
	log(`create footprint ${diagName} -> ${fpUuid ? fpUuid.slice(0, 8) + '…' : 'FAIL'} (${ms()})`);
	let tabId: string | undefined;
	if (fpUuid) {
		tabId = await call('diag openInEditor', eda.lib_Footprint.openInEditor(fpUuid, libUuid), 15000);
		log(`openInEditor -> ${tabId ? 'tab ' + tabId : 'FAIL'} (${ms()})`);
	}
	if (tabId && fpUuid) {
		const act = await call('diag activateDocument', eda.dmt_EditorControl.activateDocument(tabId), 8000);
		log(`activateDocument -> ${act} (${ms()})`);
		const info = await waitActiveDoc(fpUuid, 10000, 'diag', tabId);
		log(`active doc -> ${info ? `type=${info.documentType} uuid=${info.uuid?.slice(0, 8)} tab=${info.tabId}` : 'MISMATCH/timeout'} (${ms()})`);
		if (info) {
			const pad = await call('diag pcb_PrimitivePad.create', eda.pcb_PrimitivePad.create(
				LAYER.MULTI as TPCB_LayersOfPad, '1', 0, 0, 0,
				[PAD_ELLIPSE, 60, 60], '', [HOLE_ROUND, 30], 0, 0, 0, true, 0), 8000);
			log(`pad.create -> ${pad ? 'ok id=' + String(pad.getState_PrimitiveId?.()).slice(0, 12) : 'FAIL'} (${ms()})`);
			try {
				const poly = eda.pcb_MathPolygon.createPolygon([0, 0, 'L', 100, 0, 'L', 100, 100, 'L', 0, 100, 'L', 0, 0] as TPCB_PolygonSourceArray);
				const pl = await call('diag polyline', eda.pcb_PrimitivePolyline.create('', FP_LAYER.TOP_SILK as TPCB_LayersOfLine, poly as IPCB_Polygon, 8), 8000);
				log(`polyline.create -> ${pl ? 'ok' : 'FAIL'} (${ms()})`);
			}
			catch (e) { log(`polyline.create -> THROW ${errText(e)} (${ms()})`); }
			const padCount = await call('diag pad.getAll', eda.pcb_PrimitivePad.getAll(), 8000, true);
			log(`pad.getAll -> ${Array.isArray(padCount) ? padCount.length + ' pads' : 'FAIL'} (${ms()})`);
			const src = await call('diag sys_FileManager.getDocumentSource', eda.sys_FileManager.getDocumentSource(), 10000, true);
			log(`docSource -> ${typeof src === 'string' ? `${src.length} chars` : 'FAIL'} ${typeof src === 'string' ? '| ' + src.slice(0, 90) : ''} (${ms()})`);
			const saved = await call('diag pcb_Document.save', eda.pcb_Document.save(), 15000);
			log(`save -> ${saved} (${ms()})`);
			const closed = await call('diag closeDocument', eda.dmt_EditorControl.closeDocument(tabId), 8000);
			log(`closeDocument -> ${closed} (${ms()})`);
		}
		const item = await call('diag lib_Footprint.get', eda.lib_Footprint.get(fpUuid, libUuid), 10000);
		log(`lib get -> ${dump(item)} (${ms()})`);
		const hits = await call('diag lib_Footprint.search', eda.lib_Footprint.search('SOMA-DIAG-KEEP', libUuid), 8000, true);
		log(`lib search -> ${Array.isArray(hits) ? hits.length + ' hits: ' + dump(hits[0]) : 'FAIL'} (${ms()})`);
		const img = await call('diag getRenderImage', eda.lib_Footprint.getRenderImage({ footprintUuid: fpUuid, libraryUuid: libUuid }), 15000, true);
		log(`getRenderImage -> ${img && typeof (img as Blob).size === 'number' ? `blob ${(img as Blob).size}b` : dump(img)} (${ms()})`);
		log(`footprint ${diagName} KEPT for inspection`);
	}

	/* ---- symbol round trip (KEEP — do not delete) ---- */
	report(55, 'Diagnostics: symbol round-trip');
	const symName = `SOMA-DIAG-KEEP-SYM-${Math.floor(Math.random() * 90000) + 10000}`;
	const symUuid = await call('diag lib_Symbol.create', eda.lib_Symbol.create(libUuid, symName), 10000);
	log(`create symbol ${symName} -> ${symUuid ? symUuid.slice(0, 8) + '…' : 'FAIL'} (${ms()})`);
	if (symUuid) {
		const src = symbolSource(symName, 'TP', [{ num: '1', name: 'P1' }, { num: '2', name: 'P2' }]);
		log(`source head -> ${src.split('\n')[0]} | ${src.length} chars`);
		const ok = await call('diag symbol updateDocumentSource', eda.lib_Symbol.updateDocumentSource(symUuid, libUuid, src), 15000);
		log(`symbol updateDocumentSource -> ${ok} (${ms()})`);
		const tabId2 = await call('diag symbol openInEditor', eda.lib_Symbol.openInEditor(symUuid, libUuid), 15000, true);
		log(`symbol openInEditor -> ${tabId2 ? 'tab ' + tabId2 : 'FAIL'} (${ms()})`);
		if (tabId2) {
			await call('diag symbol activate', eda.dmt_EditorControl.activateDocument(tabId2), 8000, true);
			const info = await waitActiveDoc(symUuid, 8000, 'diag sym', tabId2);
			log(`active doc -> ${info ? `type=${info.documentType} uuid=${info.uuid?.slice(0, 8)}` : 'MISMATCH/timeout'} (${ms()})`);
			const src2 = await call('diag sys_FileManager.getDocumentSource', eda.sys_FileManager.getDocumentSource(), 10000, true);
			const pinCount = typeof src2 === 'string' ? (src2.match(/"PIN"/g) ?? []).length : 0;
			log(`symbol docSource -> ${typeof src2 === 'string' ? `${src2.length} chars, ${pinCount} PIN recs` : 'FAIL'} (${ms()})`);
			await call('diag symbol close', eda.dmt_EditorControl.closeDocument(tabId2), 8000, true);
		}
		const item = await call('diag lib_Symbol.get', eda.lib_Symbol.get(symUuid, libUuid), 10000);
		log(`symbol lib get -> ${dump(item)} (${ms()})`);
		const img = await call('diag symbol getRenderImage', eda.lib_Symbol.getRenderImage({ symbolUuid: symUuid, libraryUuid: libUuid }), 15000, true);
		log(`symbol getRenderImage -> ${img && typeof (img as Blob).size === 'number' ? `blob ${(img as Blob).size}b` : dump(img)} (${ms()})`);
		log(`symbol ${symName} KEPT for inspection`);
	}

	/* ---- system-library probes ---- */
	report(80, 'Diagnostics: system library');
	if (sysLibUuid) {
		const hits = await call('diag sys search hdr-th_2p', eda.lib_Footprint.search('hdr-th_2p', sysLibUuid), 10000, true);
		log(`sys search 'hdr-th_2p' -> ${Array.isArray(hits) ? hits.length + ' hits ' + hits.slice(0, 3).map(h => h.name).join('|') : 'FAIL'} (${ms()})`);
		const m = SYS_FP_MATCH['PinHeader_1x02_P2.54mm_Vertical@0'];
		const probe = await call('diag sys fp get', eda.lib_Footprint.get(m.sysFpUuid, sysLibUuid), 8000, true);
		log(`sys fp get ${m.sysFpName} -> ${probe ? dump(probe) : 'FAIL'} (${ms()})`);
		const copyName = `SOMA-DIAG-KEEP-COPY-${Math.floor(Math.random() * 90000) + 10000}`;
		const copyUuid = await call('diag lib_Footprint.copy',
			eda.lib_Footprint.copy(m.sysFpUuid, sysLibUuid, libUuid, undefined, copyName), 15000, true);
		log(`lib_Footprint.copy -> ${copyUuid ? copyUuid.slice(0, 8) + '… (' + copyName + ')' : 'FAIL'} (${ms()})`);
		const devs = await call('diag getByLcscIds', eda.lib_Device.getByLcscIds(['C2564', 'C118536']), 10000, true);
		log(`lib_Device.getByLcscIds -> ${Array.isArray(devs) ? devs.length + ' hits ' + devs.slice(0, 2).map(d => d.name).join('|') : dump(devs)} (${ms()})`);
	}

	report(100, 'Diagnostics done');
	try { eda.sys_LoadingAndProgressBar.destroyProgressBar(); } catch { /* noop */ }
	eda.sys_Dialog.showInformationMessage(lines.join('\n'), 'SOMA diagnostics');
}

/* ---------------- entry ---------------- */

export async function runSomaBuild(): Promise<void> {
	warnings.length = 0;
	info.length = 0;
	const started = Date.now();
	report(1, 'SOMA v1.3: starting');
	slog('build start');
	try {
		const diag: string[] = [];
		const ws = await call('getCurrentWorkspaceInfo',
			(eda as { dmt_Workspace?: { getCurrentWorkspaceInfo?: () => Promise<unknown> } }).dmt_Workspace?.getCurrentWorkspaceInfo?.(), 6000, true);
		diag.push(`workspace=${ws ? ((ws as { name?: string; uuid?: string }).name || (ws as { uuid?: string }).uuid) : 'timeout/none'}`);

		const lib = await findWritableLib(diag);
		info.push(...diag.filter(Boolean));
		if (!lib) {
			eda.sys_Dialog.showInformationMessage(`No writable library found.\n${diag.join('\n')}`, 'SOMA Carrier v1.3');
			return;
		}
		const { libUuid, libSrc } = lib;
		slog(`library ${libSrc} ${libUuid}`);
		const sysLibUuid = await call('getSystemLibraryUuid', eda.lib_LibrariesList.getSystemLibraryUuid(), 8000, true);
		info.push(`system library: ${sysLibUuid ? sysLibUuid.slice(0, 8) + '…' : 'NONE — all footprints custom-drawn'}`);
		report(2, `Library: ${libSrc} — building parts`);
		const { devices, fpRefs, fpState } = await buildLibrary(libUuid, sysLibUuid);
		const usable = [...fpState.values()].filter(s => s === 'ok' || s === 'sys').length;
		if (devices.size === 0 && usable === 0) {
			warn('no library items usable — continuing with free-pad PCB only');
		}

		report(23, 'Creating project');
		const projectUuid = await call('createProject', eda.dmt_Project.createProject('SOMA Carrier v1.3 (EasyEDA)'), 20000);
		if (!projectUuid) throw new Error('createProject failed');
		await call('waitForReady', eda.dmt_Project.waitForReady(projectUuid, 15000), 20000, true);
		await sleep(800);

		let uniqueIds = new Map<string, string>();
		let schUuid: string | undefined;
		if (devices.size > 0) {
			report(24, 'Creating schematic');
			schUuid = await call('createSchematic', eda.dmt_Schematic.createSchematic('SOMA Carrier v1.3'), 15000);
			if (!schUuid) throw new Error('createSchematic failed');
			await sleep(1500);
			const infoSch = await call('getSchematicInfo', eda.dmt_Schematic.getSchematicInfo(schUuid), 8000, true);
			const pageUuid = infoSch?.page?.[0]?.uuid;
			if (pageUuid) {
				const schTab = await call('open schematic page', eda.dmt_EditorControl.openDocument(pageUuid), 10000, true);
				const schDoc = await waitActiveDoc(pageUuid, 8000, 'sch', schTab);
				if (!schDoc) warn('schematic page did not become active — symbols/wires may land elsewhere');
			}
			await sleep(300);

			uniqueIds = await buildSchematic(devices, libUuid, fpRefs);
			const schSaved = await call('sch_Document.save', eda.sch_Document.save(), 15000);
			if (!schSaved) warnings.push('schematic save failed');
			report(48, 'Schematic saved');
		}
		else {
			warn('no devices — schematic skipped (free-pad PCB only)');
		}

		report(49, 'Creating PCB');
		const pcbUuid = await call('createPcb', eda.dmt_Pcb.createPcb('SOMA Carrier v1.3'), 15000);
		if (!pcbUuid) throw new Error('createPcb failed');
		await sleep(1500);
		await call('createBoard', eda.dmt_Board.createBoard(schUuid, pcbUuid), 15000, true);
		await sleep(800);
		const pcbTab = await call('open pcb', eda.dmt_EditorControl.openDocument(pcbUuid), 15000);
		const pcbDoc = await waitActiveDoc(pcbUuid, 10000, 'pcb', pcbTab);
		if (!pcbDoc) warn('pcb document did not become active — board primitives may land elsewhere');
		if (schUuid) {
			report(50, 'Importing to PCB');
			const imported = await call('importChanges', eda.pcb_Document.importChanges(schUuid, true), 30000);
			if (!imported) warnings.push('importChanges failed — components may be missing');
			await sleep(800);
		}

		await buildPcb(uniqueIds, devices, fpRefs, fpState);
		report(93, 'Saving PCB');
		const pcbSaved = await call('pcb_Document.save', eda.pcb_Document.save(), 20000);
		if (!pcbSaved) warnings.push('pcb save failed');
	}
	catch (err) {
		warn(`FATAL: ${errText(err)}`);
	}
	finally {
		try { eda.sys_LoadingAndProgressBar.destroyProgressBar(); } catch { /* noop */ }
	}
	const secs = Math.round((Date.now() - started) / 1000);
	const msg = [
		`SOMA Carrier v1.3 rebuild finished in ${secs}s.`,
		'',
		...info.map(s => `• ${s}`),
		warnings.length ? `${warnings.length} warnings:` : 'No warnings.',
		...warnings.slice(0, 30).map(s => `• ${s}`),
		warnings.length > 30 ? `• … and ${warnings.length - 30} more` : '',
		'',
		'Details in the system log (prefix [SOMA]). See REPORT_EASYEDA.md for notes.',
	].filter(s => s !== '').join('\n');
	eda.sys_Dialog.showInformationMessage(msg, 'SOMA Carrier v1.3');
}
