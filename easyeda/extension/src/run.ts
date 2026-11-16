/*
 * Orchestrates the SOMA Carrier v1.3 rebuild inside EasyEDA Pro 3.2.
 *
 * Pipeline:
 *   1. draw EVERY (footprint,rotation) key on an open footprint-editor
 *      tab (pcb_PrimitivePad / pcb_PrimitivePolyline + pcb_Document.save)
 *      after activateDocument + a getCurrentDocumentInfo uuid check —
 *      waitForDocumentReady has no handler in 3.2.209 and hangs.
 *      v1.4: system-library footprints are DISABLED — search hits
 *      resolve, but get/copy fail and lib_Device.create rejects a
 *      system-footprint association, so all 26 keys are drawn with
 *      KiCad-exact pads and identity pad numbering (the K1 coil-pad swap
 *      only applied to the abandoned hf3ff substitution — the drawn pads
 *      keep the KiCad numbers 1/2/3/5).  The syslib-match table and its
 *      resolution code stay behind USE_SYS_FOOTPRINTS (off by default);
 *   2. reuse-or-create symbols drawn on an open symbol-editor tab with
 *      sch_PrimitivePin/Rectangle/Text (KiCad pad numbering so pin->pad
 *      import maps to the right copper) + devices in a writable library —
 *      lib_Device.create is retried across the library-uuid variants this
 *      build reports (search-hit uuid vs list uuid vs the literal "SOMA")
 *      and each created device is read back and tagged `soma:v1.4-dev`;
 *   3. create project + schematic + pcb + board link
 *   4. place schematic components, wire stubs + net flags/ports
 *   5. importChanges into PCB, position components, draw outline,
 *      mounting holes, replicated tracks, vias and GND pours
 *   6. save both documents and report a summary
 *
 * Every eda call is time-bounded via `call()` — a hung RPC surfaces as a
 * warning instead of freezing the run.  Re-runs are resumable: items
 * verified by a previous run carry a description tag and are skipped, and
 * untagged items are looked up by title and reused/filled, so the 重复数据
 * error cannot occur.  If a footprint ends up with no usable content the
 * part falls back to board-level free pads, so copper/net connectivity
 * is preserved either way.
 */

import { BOARD_DATA } from './board-data';
import { footprintOps, FP_LAYER } from './fpdraw';
import { LAYER, planPcb } from './pcbplan';
import { planSchematic, STUB_LEN } from './schplan';
import { symbolKey, symbolOps, symbolPinList } from './symdraw';
import { prot, px, py, polygonSource } from './coords';
import { CUSTOM_KEYS, fpKeyOf, SYS_FP_MATCH, type SysFpMatch } from './syslib-match';
import { PARTS } from './parts-table';
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
const PIN_SHAPE_NONE = 'None' as ESCH_PrimitivePinShape.NONE;
const PIN_TYPE_PASSIVE = 'Passive' as ESCH_PrimitivePinType.PASSIVE;

/* v1.4: system-library footprints proved unusable in 3.2.209 HALF_OFFLINE
 * (search returns hits but get/copy fail, and lib_Device.create rejects a
 * system-footprint association).  Every key is drawn in the editor with
 * KiCad-exact pads — identity pad numbering everywhere.  The syslib-match
 * machinery stays for reference behind this flag. */
const USE_SYS_FOOTPRINTS = false;

const warnings: string[] = [];
const info: string[] = [];

/* Build counters for the final summary (Fix D). */
const stats: Record<string, number> = {};
function bump(key: string, n = 1): void { stats[key] = (stats[key] ?? 0) + n; }

/* The library uuid that API calls actually accept in HALF_OFFLINE is
 * murky: getAllLibrariesList gives one value, search hits on personal
 * items report the literal library NAME ("SOMA") as libraryUuid, and
 * lib_*.get reports "".  assocLibUuid caches the search-hit value — the
 * identity associations and item creates are most likely to accept.
 * devLibArg caches whichever candidate lib_Device.create first accepted
 * so the remaining 54 devices don't repeat dead attempts. */
let assocLibUuid: string | undefined;
let devLibArg: string | undefined;

function report(p: number, title: string): void {
	try { eda.sys_LoadingAndProgressBar.showProgressBar(p, title); } catch { /* noop */ }
}

function slog(msg: string, type?: ESYS_LogType): void {
	try { eda.sys_Log.add(`[SOMA] ${msg}`, type); } catch { /* noop */ }
}

/* v1.3 printed "[object Object]" for real API errors: some calls RESOLVE
 * with an error payload instead of rejecting, and some reject with an
 * object whose fields are non-enumerable (JSON.stringify -> "{}").  Dig
 * the usual message fields first, then enumerate own properties. */
function errText(e: unknown): string {
	if (e instanceof Error) return e.message;
	if (e !== null && typeof e === 'object') {
		const o = e as Record<string, unknown>;
		for (const k of ['message', 'msg', 'error', 'errMsg', 'reason', 'code']) {
			const v = o[k];
			if (typeof v === 'string' && v) return v;
			if (typeof v === 'number') return `${k}=${v}`;
		}
		try {
			const s = JSON.stringify(o);
			if (s && s !== '{}') return s;
		}
		catch { /* circular — fall through to property enumeration */ }
		try {
			const parts = Object.getOwnPropertyNames(o)
				.filter(k => typeof o[k] !== 'function')
				.map(k => `${k}=${typeof o[k] === 'object' ? JSON.stringify(o[k]) : String(o[k])}`);
			if (parts.length) return parts.join(' ');
		}
		catch { /* noop */ }
	}
	return String(e);
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

const norm = (s: string) => s.toLowerCase();

/** search() returns fuzzy matches — only accept an exact (case-insensitive)
 *  name hit so we never reuse an unrelated item.  A non-empty keyword can
 *  throw for lib_Symbol.search in this build (api-types.d.ts note) — on a
 *  miss the whole library is listed with an empty keyword and filtered by
 *  name, which also covers items keyword search fails to surface. */
async function findItem(kind: 'footprint' | 'symbol' | 'device', name: string, libUuid: string): Promise<string | undefined> {
	const api = kind === 'footprint' ? eda.lib_Footprint : kind === 'symbol' ? eda.lib_Symbol : eda.lib_Device;
	const res = await call(`lib_${kind}.search "${name}"`,
		api.search(name, libUuid) as Promise<ILIB_FootprintSearchItem[] | undefined>, 8000, true);
	const hit = res?.find(i => norm(i.name) === norm(name));
	if (hit?.uuid) {
		if (hit.libraryUuid) assocLibUuid = hit.libraryUuid;
		return hit.uuid;
	}
	const list = await call(`lib_${kind}.search '' list`,
		(kind === 'symbol'
			? eda.lib_Symbol.search('', libUuid, [], undefined, 300, 1)
			: kind === 'device'
				? eda.lib_Device.search('', libUuid, undefined, undefined, 300, 1)
				: eda.lib_Footprint.search('', libUuid, undefined, 300, 1)) as Promise<ILIB_FootprintSearchItem[] | undefined>,
		15000, true);
	const hit2 = list?.find(i => norm(i.name) === norm(name));
	if (hit2?.uuid && hit2.libraryUuid) assocLibUuid = hit2.libraryUuid;
	return hit2?.uuid;
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
 * the only persistent readback channel that exists in 3.2.209.  These
 * tags are what makes a re-run resumable: a tagged item is skipped
 * entirely instead of re-drawn/re-created.
 * Footprints drawn by v1.2/v1.3 stay trusted (same draw path);
 * `soma:v1.2-src` symbols are NOT trusted — that tag marked a write whose
 * grammar was silently dropped, so such symbols are redrawn; devices are
 * tagged `soma:v1.4-dev` only after their association reads back. */
const TAG_FP_DRAWN = 'soma:v1.4-drawn';
const TAG_FP_DRAWN_PREV = ['soma:v1.3-drawn', 'soma:v1.2-drawn'];
const TAG_SYM_DRAWN = 'soma:v1.4-drawn';
const TAG_SYM_DRAWN_PREV = ['soma:v1.3-drawn'];
const TAG_DEV_OK = 'soma:v1.4-dev';
const fpTagOk = (desc: string) => desc.includes(TAG_FP_DRAWN) || TAG_FP_DRAWN_PREV.some(t => desc.includes(t));
const symTagOk = (desc: string) => desc.includes(TAG_SYM_DRAWN) || TAG_SYM_DRAWN_PREV.some(t => desc.includes(t));

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

/* ---------------- system-library footprint resolution ---------------- */

/** Resolve a SYS_FP_MATCH entry to a live {uuid, libraryUuid}.
 *  lib_Footprint.get on the hardcoded uuid returned nothing in 3.2.209
 *  HALF_OFFLINE (v1.2 diag: `sys fp get -> FAIL`) while
 *  lib_Footprint.search returned 10 hits — so the search hit's own
 *  uuid + libraryUuid is the trustworthy identity.  get() stays as a
 *  last-chance fallback for builds where search is restricted. */
async function resolveSysFootprint(m: SysFpMatch, sysLibUuid: string, label: string): Promise<{ uuid: string; libraryUuid: string } | undefined> {
	const hits = await call(`${label} sysfp search ${m.sysFpName}`,
		eda.lib_Footprint.search(m.sysFpName, sysLibUuid) as Promise<ILIB_FootprintSearchItem[] | undefined>, 10000, true);
	const hit = hits?.find(h => norm(h.name) === norm(m.sysFpName));
	if (hit?.uuid) return { uuid: hit.uuid, libraryUuid: hit.libraryUuid || sysLibUuid };
	const item = await call(`${label} sysfp get ${m.sysFpName}`,
		eda.lib_Footprint.get(m.sysFpUuid, sysLibUuid) as Promise<ILIB_FootprintItem | undefined>, 8000, true);
	if (item) return { uuid: item.uuid || m.sysFpUuid, libraryUuid: item.libraryUuid || sysLibUuid };
	return undefined;
}

/* ---------------- devices ---------------- */

type DeviceAssoc = NonNullable<Parameters<typeof eda.lib_Device.create>[3]>;

/** lib_Device.create across the libraryUuid variants this build might
 *  accept.  v1.3 failed here with an "[object Object]" error: the create
 *  RESOLVES with an error payload rather than rejecting, so a result is
 *  only a win when it is a non-empty string.  Tried per candidate:
 *  the {uuid,libraryUuid} association form, then the flat same-library
 *  {symbolUuid,footprintUuid} form.  The winning outer arg is cached in
 *  devLibArg so later devices don't repeat dead attempts. */
async function createDevice(libUuid: string, devName: string, symUuid: string, fpRef: FpRef,
	prop: ILIB_DeviceExtendPropertyItem, label: string): Promise<{ uuid: string; lib: string } | undefined> {
	const symLib = assocLibUuid ?? libUuid;
	const fpLib = fpRef.kind === 'sys' ? fpRef.libUuid : symLib;
	const cands: Array<string | undefined> = [];
	for (const c of [devLibArg, symLib, libUuid, 'SOMA']) {
		if (c !== undefined && !cands.includes(c)) cands.push(c);
	}
	cands.push(undefined);   // last resort — let the API pick a default
	const shapes: Array<[string, (l: string | undefined) => DeviceAssoc]> = [
		['ref', l => ({
			symbol: { uuid: symUuid, libraryUuid: l ?? symLib },
			footprint: { uuid: fpRef.uuid, libraryUuid: fpRef.kind === 'sys' ? fpRef.libUuid : (l ?? fpLib) },
		})],
		['flat', () => ({ symbolUuid: symUuid, footprintUuid: fpRef.uuid })],
	];
	const errs: string[] = [];
	for (const cand of cands) {
		for (const [shapeName, mkAssoc] of shapes) {
			const r = await call(`${label} lib_Device.create lib=${cand ?? 'undefined'} assoc=${shapeName}`,
				eda.lib_Device.create(cand as string, devName, undefined, mkAssoc(cand), undefined, prop), 12000);
			if (typeof r === 'string' && r) {
				devLibArg = cand;
				slog(`${label}: device created via lib=${cand ?? 'undefined'} assoc=${shapeName}`);
				return { uuid: r, lib: cand ?? symLib };
			}
			if (r !== undefined) errs.push(`lib=${cand ?? 'undefined'}/${shapeName}: ${errText(r)}`);
		}
	}
	for (const e of errs) warn(`${label}: device create ${e}`);
	return undefined;
}

/** Create + read-back-verify a device.  `soma:v1.4-dev` is written only
 *  when lib_Device.get shows BOTH associations — that tag is what later
 *  runs trust for the resumable skip. */
async function deviceCreateVerified(libUuid: string, devName: string, symUuid: string, fpRef: FpRef,
	prop: ILIB_DeviceExtendPropertyItem, label: string): Promise<{ uuid: string; lib: string } | undefined> {
	const made = await createDevice(libUuid, devName, symUuid, fpRef, prop, label);
	if (!made) return undefined;
	const dev = await call(`${label} lib_Device.get`, eda.lib_Device.get(made.uuid, made.lib) as Promise<ILIB_DeviceItem | undefined>, 8000, true);
	const aSym = dev?.association?.symbol?.uuid;
	const aFp = dev?.association?.footprint?.uuid;
	if (aSym === symUuid && aFp === fpRef.uuid) {
		await call(`${label} lib_Device.modify tag`,
			eda.lib_Device.modify(made.uuid, made.lib, devName, undefined, undefined, TAG_DEV_OK, undefined), 8000, true);
	}
	else {
		warn(`${label}: device created but association unverified (sym=${aSym?.slice(0, 8) ?? 'none'} fp=${aFp?.slice(0, 8) ?? 'none'})`);
	}
	return made;
}

/* ---------------- symbol drawing (editor-tab path) ---------------- */

/** Count pins inside the open symbol doc — same role as pad.getAll for
 *  footprint docs; sch_PrimitivePin is symbol-editor-only. */
async function symbolPinCount(label: string): Promise<number> {
	const pins = await call(`${label} sch_PrimitivePin.getAll`, eda.sch_PrimitivePin.getAll(), 8000, true);
	return Array.isArray(pins) ? pins.length : -1;
}

/** Draw pins/box/labels inside the open symbol editor tab, then persist.
 *  Mirrors drawFootprint: openInEditor -> activateDocument -> active-doc
 *  uuid check -> primitives -> count -> save.
 *
 *  Persistence is attempted two ways because "save returned true but the
 *  library stayed empty" is exactly what burned the source-write path:
 *   1. sch_Document.save() — the sibling of pcb_Document.save() which is
 *      proven to persist a footprint-editor tab into the library;
 *   2. lib_Symbol.updateDocumentSource(liveDocSource) — the documented
 *      library write (openInEditor -> getDocumentSource ->
 *      updateDocumentSource): the live source IS the segmented DOCHEAD
 *      format the API accepts, unlike the 1.0-line grammar v1.2 sent.
 *  `ok` requires the pins to exist AND one persistence call to return
 *  true. */
async function drawSymbol(symName: string, symUuid: string, libUuid: string, part: PartData,
	pinList: Array<{ num: string; name: string }>, label: string): Promise<boolean> {
	const ops = symbolOps(designatorPrefix(part.ref), symName, pinList);
	const wantPins = pinList.length;
	const tabId = await call(`${label} openInEditor`, eda.lib_Symbol.openInEditor(symUuid, libUuid), 15000);
	if (!tabId) return false;
	let ok = false;
	try {
		await call(`${label} activateDocument`, eda.dmt_EditorControl.activateDocument(tabId), 8000, true);
		const info = await waitActiveDoc(symUuid, 9000, label, tabId);
		if (!info) {
			warn(`${label}: symbol doc never became active — leaving it empty`);
			return false;
		}
		slog(`${label}: active doc ${info.documentType}:${info.uuid?.slice(0, 8)} tab ${info.tabId}`);
		const before = await symbolPinCount(label);
		if (before >= wantPins) {
			slog(`${label}: ${before} pins already present — skipping redraw`);
		}
		else {
			let drawn = 0, failed = 0;
			for (const op of ops) {
				if (op.kind === 'pin') {
					const r = await call(`${label} pin ${op.num}`,
						eda.sch_PrimitivePin.create(op.x, op.y, op.num, op.name, op.rot, op.len,
							null, PIN_SHAPE_NONE, PIN_TYPE_PASSIVE), 8000, failed > 0);
					r ? drawn++ : failed++;
				}
				else if (op.kind === 'rect') {
					const r = await call(`${label} rect`,
						eda.sch_PrimitiveRectangle.create(op.x, op.y, op.w, op.h, 0, 0), 8000, true);
					r ? drawn++ : failed++;
				}
				else {
					const r = await call(`${label} text`,
						eda.sch_PrimitiveText.create(op.x, op.y, op.s, 0, null, null, 8), 8000, true);
					r ? drawn++ : failed++;
				}
			}
			slog(`${label}: drew ${drawn} symbol primitives (${failed} failed)`);
		}
		const after = await symbolPinCount(label);
		const src = await call(`${label} getDocumentSource`, eda.sys_FileManager.getDocumentSource(), 10000, true);
		const srcPins = typeof src === 'string' ? (src.match(/"PIN"/g) ?? []).length : 0;
		slog(`${label}: pins ${before} -> ${after} (want ${wantPins}); doc source ${typeof src === 'string' ? src.length : 0} chars, ${srcPins} PIN recs`);
		const saved = await call(`${label} sch_Document.save`, eda.sch_Document.save(), 15000);
		const pushed = typeof src === 'string' && src.length > 0
			? await call(`${label} updateDocumentSource`, eda.lib_Symbol.updateDocumentSource(symUuid, libUuid, src), 15000, true)
			: undefined;
		ok = after >= wantPins && wantPins > 0 && (saved === true || pushed === true);
		if (ok) {
			await call(`${label} tag`, eda.lib_Symbol.modify(symUuid, libUuid, symName, undefined, TAG_SYM_DRAWN, undefined), 8000, true);
		}
		else warn(`${label}: pins=${after}/${wantPins} save=${saved} libWrite=${pushed}`);
	}
	finally {
		const closed = await call(`${label} closeDocument`, eda.dmt_EditorControl.closeDocument(tabId), 8000, true);
		if (!closed) warn(`${label}: symbol tab did not close — close it manually if it is still open`);
	}
	return ok;
}

/** Reopen a drawn symbol and count pins — proves the library write
 *  persisted (the "updateDocumentSource true but empty" failure mode is
 *  invisible while the tab is still open). */
async function verifySymbolPersisted(symUuid: string, libUuid: string, wantPins: number, label: string): Promise<boolean> {
	const tabId = await call(`${label} openInEditor`, eda.lib_Symbol.openInEditor(symUuid, libUuid), 15000, true);
	if (!tabId) return false;
	try {
		await call(`${label} activateDocument`, eda.dmt_EditorControl.activateDocument(tabId), 8000, true);
		const info = await waitActiveDoc(symUuid, 8000, label, tabId);
		if (!info) return false;
		const n = await symbolPinCount(label);
		slog(`${label}: ${n} pins persisted (want ${wantPins})`);
		return n >= wantPins;
	}
	finally {
		await call(`${label} closeDocument`, eda.dmt_EditorControl.closeDocument(tabId), 8000, true);
	}
}

/* ---------------- library generation ---------------- */

async function buildLibrary(libUuid: string, sysLibUuid: string | undefined): Promise<{
	devices: Map<string, { uuid: string; lib: string }>;
	fpRefs: Map<string, FpRef>;
	fpState: Map<string, FpState>;
}> {
	const devices = new Map<string, { uuid: string; lib: string }>();
	// footprints deduplicated by (footprint type, rotation)
	const fpRefs = new Map<string, FpRef>();
	const fpState = new Map<string, FpState>();
	const symByKey = new Map<string, string>();
	const parts = BOARD_DATA.parts;
	let done = 0;
	let symVerified = false;
	for (const part of parts) {
		report(2 + Math.round(20 * done / parts.length), `part ${done + 1}/${parts.length}: ${part.ref}`);
		done++;
		slog(`library ${part.ref} ${part.footprint}@${part.rot}`);
		const fpKey = fpKeyOfPart(part);
		const fpName = `SOMA-${part.footprint}-R${Math.round(part.rot)}`;

		let fpRef = fpRefs.get(fpKey);
		if (!fpRef) {
			// USE_SYS_FOOTPRINTS=false in v1.4 — the system library is
			// unusable in HALF_OFFLINE (get/copy + device assoc all fail),
			// so every key goes through the proven draw-in-editor path.
			const m = USE_SYS_FOOTPRINTS && sysLibUuid ? SYS_FP_MATCH[fpKey] : undefined;
			if (m) {
				// system-library footprint — resolve via search (the call that
				// works on this build) and use the hit's own uuid +
				// libraryUuid: device associations and
				// pcb_PrimitiveComponent.create both accept foreign lib uuids
				const res = await resolveSysFootprint(m, sysLibUuid!, `${part.ref}`);
				if (res) {
					fpRef = { kind: 'sys', uuid: res.uuid, libUuid: res.libraryUuid, rot: m.rot, dx: m.dx, dy: m.dy, pm: m.padmap, name: m.sysFpName };
					fpState.set(fpKey, 'sys');
					slog(`${part.ref}: system footprint ${m.sysFpName} (rot ${m.rot}, off ${m.dx},${m.dy})`);
				}
				else warn(`${part.ref}: system footprint ${m.sysFpName} unresolvable — falling back to custom draw`);
			}
			if (!fpRef) {
				// draw-in-editor path — all 26 keys in v1.4: KiCad-exact
				// pads, identity pad numbering (no padmap)
				let fpUuid = await findItem('footprint', fpName, libUuid);
				if (!fpUuid) {
					fpUuid = await call(`lib_Footprint.create ${fpName}`, eda.lib_Footprint.create(libUuid, fpName), 10000);
					if (!fpUuid) fpUuid = await findItem('footprint', fpName, libUuid); // duplicate-title → it already exists
				}
				if (!fpUuid || typeof fpUuid !== 'string') {
					warn(`${part.ref}: no footprint uuid for ${fpName} (${CUSTOM_KEYS[fpKey] ?? 'custom'})`);
					fpState.set(fpKey, 'missing');
				}
				else {
					const desc = await getItemDesc('footprint', fpUuid, libUuid);
					if (fpTagOk(desc)) {
						slog(`${part.ref}: footprint ${fpName} verified earlier — skipping draw`);
						fpState.set(fpKey, 'ok');
					}
					else {
						slog(`${part.ref}: drawing footprint ${fpName}`);
						fpState.set(fpKey, await drawFootprint(part, fpUuid, libUuid, fpName, `${part.ref} ${fpName}`) ? 'ok' : 'empty');
					}
					if (fpState.get(fpKey) === 'ok') {
						fpRef = { kind: 'drawn', uuid: fpUuid, libUuid: assocLibUuid ?? libUuid, rot: 0, dx: 0, dy: 0, name: fpName };
					}
				}
			}
			if (fpRef) fpRefs.set(fpKey, fpRef);
		}

		// symbol — deduplicated by pin-set (KiCad pad numbering in v1.4:
		// drawn footprints use KiCad numbers so pin->pad import maps to the
		// right copper); drawn on an open symbol-editor tab — the
		// updateDocumentSource 1.0 grammar is silently dropped in 3.2.209
		let symUuid: string | undefined;
		const pinList = symbolPinList(part, fpRef?.pm);
		const symKey = symbolKey(pinList);
		symUuid = symByKey.get(symKey);
		if (!symUuid) {
			const symName = `SOMA-${part.ref}`;
			symUuid = await findItem('symbol', symName, libUuid);
			if (!symUuid) {
				symUuid = await call(`lib_Symbol.create ${symName}`, eda.lib_Symbol.create(libUuid, symName), 10000);
				if (!symUuid) symUuid = await findItem('symbol', symName, libUuid);
			}
			if (!symUuid || typeof symUuid !== 'string') {
				warn(`${part.ref}: no symbol uuid for ${symName}`);
				symUuid = undefined;
			}
			else {
				symByKey.set(symKey, symUuid);
				const desc = await getItemDesc('symbol', symUuid, libUuid);
				if (!symTagOk(desc)) {
					slog(`${part.ref}: drawing symbol ${symName} (${pinList.length} pins)`);
					const drawn = await drawSymbol(symName, symUuid, libUuid, part, pinList, `${part.ref} ${symName}`);
					if (!drawn) warn(`${part.ref}: symbol ${symName} may still be empty — device will lack pins`);
					else if (!symVerified) {
						symVerified = true;
						// persistence proof: reopen the FIRST drawn symbol and
						// count pins — "saved" alone proved nothing in v1.2
						const ok2 = await verifySymbolPersisted(symUuid, libUuid, pinList.length, `${part.ref} symverify`);
						if (!ok2) warn('first symbol reopened with no pins — library persistence unproven; check Diagnostics output');
					}
				}
			}
		}

		// device — tagged verified items are skipped outright (resumable);
		// an untagged legacy device has its association checked and is
		// rebuilt when it points at a stale footprint/symbol
		const devName = `SOMA-${part.ref}`;
		const spec = PARTS[part.ref];
		const prop: ILIB_DeviceExtendPropertyItem = {
			name: part.value,
			designator: designatorPrefix(part.ref),
			addIntoBom: true,
			addIntoPcb: true,
		};
		if (spec?.lcsc) prop.supplierId = spec.lcsc;   // verified LCSC equivalent — BOM attribute only
		let devUuid = await findItem('device', devName, libUuid);
		if (devUuid && typeof devUuid !== 'string') devUuid = undefined;
		if (devUuid && fpRef) {
			const desc = await getItemDesc('device', devUuid, libUuid);
			if (desc.includes(TAG_DEV_OK)) {
				slog(`${part.ref}: device verified earlier — skipping create`);
				devices.set(part.ref, { uuid: devUuid, lib: devLibArg ?? assocLibUuid ?? libUuid });
				continue;
			}
			const dev = await call(`lib_Device.get ${devName}`,
				eda.lib_Device.get(devUuid, libUuid) as Promise<ILIB_DeviceItem | undefined>, 8000, true);
			const assocFp = dev?.association?.footprint?.uuid;
			const assocSym = dev?.association?.symbol?.uuid;
			if (dev && assocFp === fpRef.uuid && (!symUuid || assocSym === symUuid)) {
				// association already correct — tag it so the next run skips
				await call(`lib_Device.modify ${devName} tag`,
					eda.lib_Device.modify(devUuid, libUuid, devName, undefined, undefined, TAG_DEV_OK, undefined), 8000, true);
				devices.set(part.ref, { uuid: devUuid, lib: devLibArg ?? assocLibUuid ?? libUuid });
				continue;
			}
			if (dev && (assocFp || assocSym)) {
				slog(`${part.ref}: device assoc sym=${assocSym?.slice(0, 8)} fp=${assocFp?.slice(0, 8)} mismatched — rebuilding`);
				await call(`lib_Device.delete ${devName}`, eda.lib_Device.delete(devUuid, libUuid), 8000, true);
				devUuid = undefined;
			}
			// unreadable association (get failed): keep the existing device —
			// deleting a possibly-good device on a flaky read is worse
			else if (!dev) {
				devices.set(part.ref, { uuid: devUuid, lib: devLibArg ?? assocLibUuid ?? libUuid });
				continue;
			}
			// assoc read ok but BOTH fields empty — fall through to rebuild
			else devUuid = undefined;
		}
		if (!devUuid && symUuid && fpRef) {
			const made = await deviceCreateVerified(libUuid, devName, symUuid, fpRef, prop, part.ref);
			if (made) devices.set(part.ref, made);
			else {
				// create may have succeeded while reporting an error —
				// recover the item by title before giving up
				const retry = await findItem('device', devName, libUuid);
				if (retry) devices.set(part.ref, { uuid: retry, lib: devLibArg ?? assocLibUuid ?? libUuid });
			}
		}
		if (!devices.has(part.ref)) {
			warn(`${part.ref}: no device (sym=${!!symUuid} fp=${!!fpRef}) — schematic/board will fall back`);
		}
	}
	const drawnOk = [...fpState.values()].filter(s => s === 'ok').length;
	const sysOk = [...fpState.values()].filter(s => s === 'sys').length;
	info.push(`library: ${drawnOk} drawn${sysOk ? ` + ${sysOk} system` : ''} footprints, ${symByKey.size} symbols, ${devices.size} devices`);
	return { devices, fpRefs, fpState };
}

/* ---------------- schematic ---------------- */

/* sch_PrimitiveAttribute.createNetLabel is typed "ADD since EDA v4" —
 * check presence once, then use it per pin with flag/port as fallback
 * (Fix B: net labels on pin ends, not drawn wires). */
let netLabelApi: boolean | undefined;
function hasNetLabelApi(): boolean {
	if (netLabelApi === undefined) {
		try {
			netLabelApi = typeof (eda as unknown as {
				sch_PrimitiveAttribute?: { createNetLabel?: unknown }
			}).sch_PrimitiveAttribute?.createNetLabel === 'function';
		}
		catch { netLabelApi = false; }
	}
	return netLabelApi;
}

/** Net-label one pin end: net label first (v2 primary), then the flag /
 *  port decoration as a second naming primitive.  Power and ground nets
 *  get their idiomatic flags in addition to the label. */
async function labelPinEnd(ref: string, num: string, kind: 'power' | 'ground' | 'signal', net: string, x: number, y: number, dir: -1 | 1): Promise<void> {
	let labeled = false;
	if (hasNetLabelApi()) {
		const r = await call(`sch netlabel ${ref}.${num}`,
			(eda as unknown as { sch_PrimitiveAttribute: { createNetLabel: (x: number, y: number, n: string) => Promise<unknown> } })
				.sch_PrimitiveAttribute.createNetLabel(x, y, net), 8000, true);
		if (r) { labeled = true; bump('netLabels'); }
	}
	if (kind === 'ground') {
		const r = await call(`sch flag ${ref}.${num}`, eda.sch_PrimitiveComponent.createNetFlag('Ground', net, x, y), 8000, true);
		if (r) { labeled = true; bump('netFlags'); }
	}
	else if (kind === 'power') {
		const r = await call(`sch flag ${ref}.${num}`, eda.sch_PrimitiveComponent.createNetFlag('Power', net, x, y), 8000, true);
		if (r) { labeled = true; bump('netFlags'); }
	}
	else if (!labeled) {
		const r = await call(`sch port ${ref}.${num}`,
			eda.sch_PrimitiveComponent.createNetPort('BI', net, x, y, dir === -1 ? 180 : 0), 8000, true);
		if (r) bump('netPorts');
	}
}

async function buildSchematic(
	devices: Map<string, { uuid: string; lib: string }>,
	libUuid: string,
	fpRefs: Map<string, FpRef>,
): Promise<Map<string, string>> {
	// feed fp-domain pad numbers so stub labels land on pins whose numbers
	// match the footprint pads (v1.4: identity — drawn pads carry KiCad
	// numbers; the padmap only matters if USE_SYS_FOOTPRINTS is enabled)
	const plan = planSchematic(mappedBoard(BOARD_DATA, fpRefs));
	const uniqueIds = new Map<string, string>();
	const realPins = new Map<string, Map<string, { x: number; y: number; dir: -1 | 1 }>>();

	// re-run dedup: components already on the sheet are reused, not doubled
	const existing = new Map<string, ISCH_PrimitiveComponent>();
	try {
		const comps = await call('sch getAll components', eda.sch_PrimitiveComponent.getAll?.(), 10000, true) ?? [];
		for (const c of comps) {
			const d = c.getState_Designator?.();
			if (d) existing.set(d, c);
		}
		if (existing.size) slog(`schematic already has ${existing.size} components — reusing by designator`);
	}
	catch { /* getAll unavailable — place everything */ }

	const readPins = async (ref: string, pid: string | undefined): Promise<void> => {
		if (!pid) return;
		const pins = await call(`sch pins ${ref}`,
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
			realPins.set(ref, m);
		}
	};

	let i = 0;
	for (const c of plan.comps) {
		report(25 + Math.round(22 * i / plan.comps.length), `part ${i + 1}/${plan.comps.length}: ${c.ref}`);
		i++;
		const old = existing.get(c.ref);
		if (old) {
			const pid = old.getState_PrimitiveId?.();
			await readPins(c.ref, pid);
			const uid = old.getState_UniqueId?.();
			if (uid) uniqueIds.set(c.ref, uid);
			bump('schCompsReused');
			continue;
		}
		const dev = devices.get(c.ref);
		if (!dev) { warnings.push(`${c.ref}: skipped — no device`); continue; }
		const comp = await call(`sch create ${c.ref}`, eda.sch_PrimitiveComponent.create(
			{ libraryType: LIB_DEVICE, libraryUuid: dev.lib, uuid: dev.uuid },
			c.cx, c.cy, undefined, 0, false, true, true,
		), 15000);
		if (!comp) { warn(`${c.ref}: sch create failed`); continue; }
		bump('schCompsPlaced');
		const pid = comp.getState_PrimitiveId?.();
		if (pid) {
			await call(`sch modify ${c.ref}`, eda.sch_PrimitiveComponent.modify(pid, { designator: c.ref, name: c.value }), 8000, true);
			await readPins(c.ref, pid);
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
			// if the netlabel/netflag decoration fails
			await call(`sch stub ${c.ref}.${p.num}`, eda.sch_PrimitiveWire.create([px0, py0, ex, py0], p.net), 8000, true);
			await labelPinEnd(c.ref, p.num, p.kind, p.net, ex, py0, dir);
		}
	}
	for (const h of plan.headers) {
		await call('sch header', eda.sch_PrimitiveRectangle.create(h.x, h.y, h.w, h.h, 0, 0, '#888888'), 6000, true);
		await call('sch header text', eda.sch_PrimitiveText.create(h.x + 10, h.y + 14, h.title, 0, '#000000', undefined, 12, true), 6000, true);
	}
	return uniqueIds;
}

/* ---------------- PCB ---------------- */

/** Pads a part should carry (board-level NPTH holes excluded, matching
 *  footprintOps).  Used to detect silently-empty footprints. */
function expectPads(part: PartData): number {
	return part.pads.filter(p => p.type !== 'np_thru_hole').length;
}

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
	devices: Map<string, { uuid: string; lib: string }>,
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
		bump('pcbCompsImported', comps.length);
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
			else if (part && expectPads(part) > 0) {
				// a "sys"/"ok" footprint that still yielded no copper (e.g.
				// a foreign-lib association that silently produced nothing)
				const pid = comp.getState_PrimitiveId?.();
				const pads = pid ? await call(`pcb pads ${d}`, eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId?.(pid), 8000, true) : undefined;
				if (Array.isArray(pads) && pads.length === 0) {
					warnings.push(`${d}: component landed with 0 pads — drawing free pads`);
					await drawPartFreePads(part, pl.layer);
				}
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
			if (pins.length === 0 && expectPads(part) > 0) {
				// component created but its footprint carries no copper
				warnings.push(`${ref}: placed component has 0 pads — drawing free pads`);
				await drawPartFreePads(part, pl.layer);
				continue;
			}
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

	// board outline — skip if one already exists (re-run safety)
	try {
		const existingOutline = await call('pcb existing outline',
			eda.pcb_PrimitivePolyline.getAll?.('', LAYER.BOARD_OUTLINE as TPCB_LayersOfLine), 8000, true);
		if (Array.isArray(existingOutline) && existingOutline.length > 0) {
			info.push(`board outline already present (${existingOutline.length} polys) — skipped`);
			bump('outlineReused');
		}
		else if (plan.outlinePolygon.length >= 8) {
			const poly = eda.pcb_MathPolygon.createPolygon(plan.outlinePolygon);
			const r = await call('board outline', eda.pcb_PrimitivePolyline.create('', LAYER.BOARD_OUTLINE, poly as IPCB_Polygon, plan.outlineWidth), 10000);
			if (r) bump('outline'); else warnings.push('outline create failed');
		}
	}
	catch (err) {
		warnings.push(`outline failed — ${errText(err)}`);
	}

	for (const h of plan.holes) {
		const r = await call(`mounting hole @${h.x},${h.y}`, eda.pcb_PrimitivePad.create(LAYER.MULTI, '', h.x, h.y, 0,
			[PAD_ELLIPSE, h.size, h.size], '',
			[HOLE_ROUND, h.drill], 0, 0, 0, false), 8000, true);
		if (!r) warnings.push(`mounting hole at ${h.x},${h.y} failed`);
		else bump('mountingHoles');
	}

	// tracks — on a re-run with the full count already on the board, skip
	// the redraw (a partial run still tops up to the KiCad segment count)
	let terr = 0;
	const existingTracks = await call('pcb existing tracks', eda.pcb_PrimitiveLine.getAll?.(), 10000, true);
	if (Array.isArray(existingTracks) && existingTracks.length >= plan.tracks.length && plan.tracks.length > 0) {
		info.push(`tracks already present (${existingTracks.length} >= ${plan.tracks.length}) — skipped redraw`);
		bump('tracksReused', existingTracks.length);
	}
	else for (let k = 0; k < plan.tracks.length; k++) {
		const t = plan.tracks[k];
		const r = await call(`track ${k}`, eda.pcb_PrimitiveLine.create(t.net, t.layer as TPCB_LayersOfLine, t.x1, t.y1, t.x2, t.y2, t.w), 8000, terr > 5);
		if (!r) terr++;
		if (k % 50 === 49) {
			report(55 + Math.round(30 * (k + 1) / plan.tracks.length), `Tracks ${k + 1}/${plan.tracks.length}`);
			await sleep(0);
		}
	}
	bump('tracksOk', plan.tracks.length - terr);
	bump('tracksFailed', terr);
	info.push(`tracks placed: ${plan.tracks.length - terr}/${plan.tracks.length} (${terr} failed, ${plan.skippedTracks} degenerate skipped)`);
	if (terr) warnings.push(`${terr} track segments failed to create`);

	const existingVias = await call('pcb existing vias', eda.pcb_PrimitiveVia.getAll?.(), 10000, true);
	if (Array.isArray(existingVias) && existingVias.length >= plan.vias.length && plan.vias.length > 0) {
		info.push(`vias already present (${existingVias.length}) — skipped redraw`);
		bump('viasReused', existingVias.length);
	}
	else for (const v of plan.vias) {
		const r = await call(`via ${v.net}`, eda.pcb_PrimitiveVia.create(v.net, v.x, v.y, v.drill, v.size), 8000, true);
		if (!r) warnings.push(`via ${v.net} @${v.x},${v.y} failed`);
		else bump('viasOk');
	}

	const existingPours = await call('pcb existing pours', eda.pcb_PrimitivePour.getAll?.(), 10000, true);
	for (const zn of plan.pours) {
		if (Array.isArray(existingPours) && existingPours.length >= plan.pours.length) {
			bump('poursReused');
			continue;
		}
		try {
			const poly = eda.pcb_MathPolygon.createPolygon(zn.polygon);
			const r = await call(`pour ${zn.net}`, eda.pcb_PrimitivePour.create(zn.net, zn.layer as TPCB_LayersOfCopper,
				poly as IPCB_Polygon, POUR_SOLID), 15000);
			if (!r) warnings.push(`pour ${zn.net} layer ${zn.layer} failed`);
			else {
				bump('poursOk');
				// rebuild the copper so the pour actually fills (Fix C)
				try { await call(`pour ${zn.net} rebuild`, (r as IPCB_PrimitivePour).rebuildCopperRegion?.(), 15000, true); }
				catch { /* rebuild optional */ }
			}
		}
		catch (err) { warnings.push(`pour ${zn.net} layer ${zn.layer} — ${errText(err)}`); }
	}

	for (const t of plan.texts) {
		await call('silk text', eda.pcb_PrimitiveString.create(t.layer as TPCB_LayersOfImage, t.x, t.y, t.text,
			'default', t.h, 8, ALIGN_LEFT_TOP, t.rot, false, 0, false, false), 6000, true);
	}
}

/* ---------------- project documents (Fix A) ---------------- */

interface ProjectDocs {
	boardName?: string;
	schUuid?: string;
	schName?: string;
	pcbUuid?: string;
	pcbName?: string;
}

/** Extract board / schematic / pcb refs from a getCurrentProjectInfo
 *  item tree.  Boards carry their own schematic+pcb; loose schematic or
 *  PCB items are used as fallbacks. */
function docsFromProject(proj: IDMT_ProjectItem | undefined): ProjectDocs {
	const docs: ProjectDocs = {};
	for (const item of (proj?.data ?? []) as unknown as Array<Record<string, unknown>>) {
		const t = String(item.itemType ?? '');
		if (t === 'Board' && !docs.boardName) {
			docs.boardName = item.name as string | undefined;
			const sch = item.schematic as IDMT_SchematicItem | undefined;
			const pcb = item.pcb as IDMT_PcbItem | undefined;
			docs.schUuid = sch?.uuid ?? docs.schUuid;
			docs.schName = sch?.name ?? docs.schName;
			docs.pcbUuid = pcb?.uuid ?? docs.pcbUuid;
			docs.pcbName = pcb?.name ?? docs.pcbName;
		}
		else if ((t === 'Schematic' || t === 'CBB Schematic') && !docs.schUuid) {
			docs.schUuid = item.uuid as string | undefined;
			docs.schName = item.name as string | undefined;
		}
		else if ((t === 'PCB' || t === 'CBB PCB') && !docs.pcbUuid) {
			docs.pcbUuid = item.uuid as string | undefined;
			docs.pcbName = item.name as string | undefined;
		}
	}
	return docs;
}

/** Merge boards listed by dmt_Board.getAllBoardsInfo — the project data
 *  tree does not always enumerate Board items. */
async function fillDocsFromBoards(docs: ProjectDocs): Promise<void> {
	const boards = await call('dmt_Board.getAllBoardsInfo', eda.dmt_Board.getAllBoardsInfo(), 8000, true);
	for (const b of boards ?? []) {
		if (!docs.boardName) docs.boardName = b.name;
		if (b.name === docs.boardName) {
			docs.schUuid = docs.schUuid ?? b.schematic?.uuid;
			docs.schName = docs.schName ?? b.schematic?.name;
			docs.pcbUuid = docs.pcbUuid ?? b.pcb?.uuid;
			docs.pcbName = docs.pcbName ?? b.pcb?.name;
		}
	}
}

/** Re-read the open project and merge anything new into `docs`. */
async function refreshDocs(projUuid: string, docs: ProjectDocs): Promise<void> {
	const proj = await call('getCurrentProjectInfo refresh', eda.dmt_Project.getCurrentProjectInfo(), 8000, true);
	if (proj && proj.uuid === projUuid) {
		const d2 = docsFromProject(proj);
		docs.boardName = docs.boardName ?? d2.boardName;
		docs.schUuid = docs.schUuid ?? d2.schUuid;
		docs.schName = docs.schName ?? d2.schName;
		docs.pcbUuid = docs.pcbUuid ?? d2.pcbUuid;
		docs.pcbName = docs.pcbName ?? d2.pcbName;
	}
	await fillDocsFromBoards(docs);
}

/* Try every create variant for the missing schematic / PCB / board,
 * logging which one actually worked (Fix A).  Never creates a project —
 * the user's open project is the only target.  Note: the boardName
 * argument of createSchematic/createPcb is a BOARD name (which board the
 * doc belongs to), not the document name — pass none. */
async function ensureProjectDocs(projUuid: string): Promise<ProjectDocs | undefined> {
	const proj = await call('getCurrentProjectInfo', eda.dmt_Project.getCurrentProjectInfo(), 10000);
	if (!proj?.uuid) return undefined;
	const docs = docsFromProject(proj);
	await fillDocsFromBoards(docs);
	slog(`project docs: board=${docs.boardName ?? 'none'} sch=${docs.schUuid?.slice(0, 8) ?? 'none'} pcb=${docs.pcbUuid?.slice(0, 8) ?? 'none'}`);

	const created: string[] = [];

	// empty project — the pair-create is one board, one schematic, one pcb
	if (!docs.schUuid && !docs.pcbUuid && !docs.boardName) {
		const bn = await call('dmt_Board.createBoard()', eda.dmt_Board.createBoard(), 15000, true);
		if (bn) { created.push(`dmt_Board.createBoard() -> "${bn}"`); await refreshDocs(projUuid, docs); }
	}
	if (!docs.schUuid) {
		const u = await call('dmt_Schematic.createSchematic()', eda.dmt_Schematic.createSchematic(), 15000);
		if (u) { docs.schUuid = u; created.push('dmt_Schematic.createSchematic()'); }
		else {
			const r = await call('dmt_SourceSchematic.addSchematic',
				eda.dmt_SourceSchematic?.addSchematic?.({ projectId: projUuid, schematicName: 'SOMA Carrier v1.3' } as IDMT_SourceSchematicAddSchematicOptions), 15000, true);
			if (r && (r as { ok?: boolean }).ok) {
				created.push('dmt_SourceSchematic.addSchematic');
				await refreshDocs(projUuid, docs);
			}
			if (!docs.schUuid) {
				const bn = await call('dmt_Board.createBoard() for sch', eda.dmt_Board.createBoard(), 15000, true);
				if (bn) { created.push('dmt_Board.createBoard()'); await refreshDocs(projUuid, docs); }
			}
		}
	}
	if (!docs.pcbUuid) {
		const u = await call('dmt_Pcb.createPcb()', eda.dmt_Pcb.createPcb(), 15000);
		if (u) { docs.pcbUuid = u; created.push('dmt_Pcb.createPcb()'); }
		else {
			const r = await call('dmt_SourcePcb.addPcb',
				eda.dmt_SourcePcb?.addPcb?.({ projectId: projUuid, pcbName: 'SOMA Carrier v1.3' } as IDMT_SourcePcbAddOptions), 15000, true);
			if (r && (r as { ok?: boolean }).ok) {
				created.push('dmt_SourcePcb.addPcb');
				await refreshDocs(projUuid, docs);
			}
			if (!docs.pcbUuid) {
				const bn = await call('dmt_Board.createBoard() for pcb', eda.dmt_Board.createBoard(), 15000, true);
				if (bn) { created.push('dmt_Board.createBoard()'); await refreshDocs(projUuid, docs); }
			}
		}
	}
	// link loose docs under a board so importChanges can see the pair
	if (!docs.boardName && docs.schUuid && docs.pcbUuid) {
		const bn = await call('dmt_Board.createBoard(sch,pcb)', eda.dmt_Board.createBoard(docs.schUuid, docs.pcbUuid), 15000, true);
		if (bn) { docs.boardName = bn; created.push(`dmt_Board.createBoard(sch,pcb) -> "${bn}"`); }
	}
	if (created.length) info.push(`created in project: ${created.join(' | ')}`);
	else info.push(`reusing project docs: board=${docs.boardName ?? 'none'} sch=${docs.schName ?? docs.schUuid?.slice(0, 8) ?? 'none'} pcb=${docs.pcbName ?? docs.pcbUuid?.slice(0, 8) ?? 'none'}`);
	return docs;
}

/* ---------------- DRC + fabrication output (Fixes C/E) ---------------- */

/** Flatten a verbose pcb_Drc.check result into [categoryCount, leafCount,
 *  first messages].  The verbose tree's top level is error CATEGORIES. */
function summarizeDrcTree(root: unknown): { categories: number; leaves: number; samples: string[] } {
	let leaves = 0;
	const samples: string[] = [];
	const seen = new Set<unknown>();
	const walk = (o: unknown, depth: number) => {
		if (o === null || o === undefined || typeof o !== 'object' || seen.has(o)) {
			if (typeof o === 'string' && o && samples.length < 12 && /error|violation|clearance|short|unrout|间距|短路|违规/i.test(o)) samples.push(o);
			return;
		}
		seen.add(o);
		if (Array.isArray(o)) { for (const v of o) walk(v, depth + 1); return; }
		const rec = o as Record<string, unknown>;
		const looksLikeError = ['message', 'error', 'errMsg', 'title', 'name', 'desc', 'description']
			.some(k => typeof rec[k] === 'string' && (rec[k] as string).length > 0);
		const hasChildren = ['children', 'items', 'errors', 'list', 'violationList', 'detail']
			.some(k => Array.isArray(rec[k]));
		if (looksLikeError && !hasChildren && depth > 0) {
			leaves++;
			if (samples.length < 12) {
				const msg = ['message', 'error', 'errMsg', 'desc', 'description', 'title', 'name']
					.map(k => rec[k]).find(v => typeof v === 'string' && v);
				const pos = [rec.x, rec.y].every(v => typeof v === 'number') ? ` @${rec.x},${rec.y}` : '';
				samples.push(`${String(msg)}${pos}`);
			}
			return;
		}
		for (const v of Object.values(rec)) if (typeof v === 'object') walk(v, depth + 1);
	};
	const categories = Array.isArray(root) ? root.length : 0;
	walk(root, 0);
	return { categories, leaves, samples };
}

async function runDrc(): Promise<void> {
	report(95, 'DRC check');
	if (typeof eda.pcb_Drc?.check !== 'function') { info.push('DRC: pcb_Drc.check API unavailable'); return; }
	const verbose = await call('pcb_Drc.check(verbose)', eda.pcb_Drc.check(true, false, true), 90000, true);
	if (Array.isArray(verbose)) {
		const s = summarizeDrcTree(verbose);
		bump('drcCategories', s.categories);
		bump('drcErrors', s.leaves || s.categories);
		if (s.categories === 0) { info.push('DRC: 0 violations'); return; }
		warnings.push(`DRC: ${s.leaves || s.categories} violation(s) in ${s.categories} categor${s.categories === 1 ? 'y' : 'ies'}`);
		for (const m of s.samples) warnings.push(`  DRC • ${m}`);
		return;
	}
	// verbose unsupported — fall back to the boolean gate
	const passed = await call('pcb_Drc.check(bool)', eda.pcb_Drc.check(true, false, false), 90000, true);
	if (passed === true) info.push('DRC: passed (boolean check)');
	else if (passed === false) { warnings.push('DRC: violations found (boolean check — see DRC panel)'); bump('drcErrors', -1); }
	else info.push('DRC: result unavailable');
}

async function exportFab(): Promise<void> {
	report(98, 'Gerber export');
	if (typeof (eda as { pcb_ManufactureData?: { getGerberFile?: unknown } }).pcb_ManufactureData?.getGerberFile !== 'function') {
		info.push('fab output: pcb_ManufactureData.getGerberFile unavailable — export via File menu');
		return;
	}
	const file = await call('pcb_ManufactureData.getGerberFile',
		(eda as { pcb_ManufactureData: { getGerberFile: (n?: string) => Promise<File | undefined> } })
			.pcb_ManufactureData.getGerberFile('SOMA-Carrier-v13_Gerber'), 120000, true);
	if (!file) { info.push('fab output: getGerberFile returned nothing — export via File > Export menu'); return; }
	// saveFile resolves void — await it directly so resolve != reject
	let ok = false;
	try {
		await Promise.race([
			eda.sys_FileSystem.saveFile(file, 'SOMA-Carrier-v13_Gerber.zip'),
			new Promise((_, rej) => setTimeout(() => rej(new Error('timeout after 30s')), 30000)),
		]);
		ok = true;
	}
	catch (e) { slog(`saveFile failed: ${errText(e)}`, 'warn' as ESYS_LogType); }
	info.push(ok
		? 'fab output: SOMA-Carrier-v13_Gerber.zip exported'
		: 'fab output: gerber generated but saveFile declined — use File > Export');
	bump('gerberExported', ok ? 1 : 0);
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

/** Diagnostics v1.4: creates SOMA-DIAG-KEEP-* items and does NOT delete
 *  them, so results can be inspected afterwards (EasyEDA library panel,
 *  or read-only sqlite inspection of SOMA.elib).
 *
 *  Covers: API surface -> library discovery -> footprint draw round-trip
 *  -> symbol draw+reopen round-trip -> lib_Device.create across the
 *  libraryUuid variants this build reports (search-hit / discovered /
 *  literal "SOMA" / undefined) with association read-back -> a kept
 *  end-to-end project (schematic + component + importChanges + PCB pad
 *  count + one track + save) -> read-only system-library info probes.
 *
 *  Readback reality in 3.2.209 (from the pro-ui handler map):
 *   - ILIB_*.get()/search() return metadata only — no dataStr field.
 *     The v1.1 "dataStr EMPTY/missing" verify was a false negative.
 *   - lib_*.getDocumentSource has NO registered handler — calls hang.
 *   - waitForDocumentReady/getDocumentReadyState have NO handlers — calls
 *     hang (this caused the ~15 s stall in the v1.1 diagnostic).
 *   - lib_Symbol.updateDocumentSource with the DOCTYPE/SYMBOL/1.0 line
 *     grammar returns true but leaves the library item EMPTY (v1.2
 *     failure).  Symbols are drawn on the live editor tab with
 *     sch_Primitive* — the same path proven for footprints.
 *   - Real readback: openInEditor + activateDocument + poll
 *     dmt_SelectControl.getCurrentDocumentInfo (uuid/type check) +
 *     sys_FileManager.getDocumentSource() / sch_PrimitivePin.getAll on
 *     the active doc, then CLOSE + REOPEN to prove persistence.
 */
export async function runDiagnostics(): Promise<void> {
	assocLibUuid = undefined;
	devLibArg = undefined;
	const lines: string[] = [];
	const t0 = Date.now();
	const deadline = t0 + 28000;                    // Fix F: hard 28 s budget
	const left = () => deadline - Date.now() > 1500;
	const to = (ms: number) => Math.max(1200, Math.min(ms, deadline - Date.now()));
	const log = (s: string) => { lines.push(s); slog(`diag ${s}`); };
	const ms = () => `${Math.round((Date.now() - t0) / 100) / 10}s`;

	report(5, 'Diagnostics: API probe');
	const probes = [
		'lib_LibrariesList.getPersonalLibraryUuid',
		'lib_Footprint.create', 'lib_Footprint.openInEditor',
		'lib_Symbol.create', 'lib_Symbol.openInEditor',
		'lib_Device.create', 'lib_Device.search', 'lib_Device.get',
		'dmt_EditorControl.openDocument', 'dmt_EditorControl.closeDocument',
		'dmt_EditorControl.activateDocument', 'dmt_SelectControl.getCurrentDocumentInfo',
		'dmt_Project.getCurrentProjectInfo',
		'dmt_Schematic.createSchematic', 'dmt_Schematic.getSchematicInfo',
		'dmt_Schematic.deleteSchematic',
		'dmt_Pcb.createPcb', 'dmt_Pcb.deletePcb',
		'dmt_Board.createBoard', 'dmt_Board.getAllBoardsInfo',
		'dmt_SourceBoard.addBoard', 'dmt_SourceSchematic.addSchematic', 'dmt_SourcePcb.addPcb',
		'pcb_Document.save', 'pcb_Document.importChanges',
		'pcb_PrimitivePad.create', 'pcb_PrimitivePad.getAll',
		'pcb_PrimitivePolyline.create', 'pcb_PrimitiveComponent.create',
		'pcb_PrimitiveComponent.getAll', 'pcb_PrimitiveComponent.getAllPinsByPrimitiveId',
		'pcb_PrimitiveLine.create', 'pcb_PrimitiveVia.create', 'pcb_PrimitivePour.create',
		'pcb_MathPolygon.createPolygon', 'sch_PrimitiveComponent.create',
		'sch_PrimitiveComponent.getAllPinsByPrimitiveId',
		'sch_PrimitiveAttribute.createNetLabel',
		'sch_Document.save', 'sch_PrimitivePin.create', 'sch_PrimitivePin.getAll',
		'sch_PrimitiveWire.create', 'sys_FileManager.getDocumentSource',
		'pcb_Drc.check', 'pcb_ManufactureData.getGerberFile', 'sys_FileSystem.saveFile',
	];
	for (const p of probes) log(`${apiPresent(p) ? 'OK     ' : 'MISSING'} eda.${p}`);

	report(15, 'Diagnostics: open project');
	const proj = await call('diag getCurrentProjectInfo', eda.dmt_Project.getCurrentProjectInfo(), to(5000), true);
	if (!proj?.uuid) {
		log(`getCurrentProjectInfo -> NONE (${ms()})`);
		log(">>> Open your project 'SOMA Carrier v1.3 (EasyEDA)' first — diagnostics tests inside the open project.");
		report(100, 'Diagnostics done');
		try { eda.sys_LoadingAndProgressBar.destroyProgressBar(); } catch { /* noop */ }
		eda.sys_Dialog.showInformationMessage(lines.join('\n'), 'SOMA diagnostics');
		return;
	}
	const docs = docsFromProject(proj);
	await fillDocsFromBoards(docs);
	log(`project "${proj.friendlyName ?? proj.name}" uuid=${proj.uuid.slice(0, 8)} (${ms()})`);
	log(`docs: board=${docs.boardName ?? 'none'} sch=${docs.schUuid?.slice(0, 8) ?? 'none'} pcb=${docs.pcbUuid?.slice(0, 8) ?? 'none'} (${ms()})`);

	report(30, 'Diagnostics: library');
	const libUuid = await call('diag getPersonalLibraryUuid', eda.lib_LibrariesList.getPersonalLibraryUuid(), to(5000), true);
	log(`personal library -> ${libUuid ?? 'NONE'} (${ms()})`);
	let devHit: ILIB_DeviceSearchItem | undefined;
	if (libUuid && left()) {
		const hits = await call('diag SOMA device search', eda.lib_Device.search('SOMA-', libUuid) as Promise<ILIB_DeviceSearchItem[] | undefined>, to(6000), true);
		devHit = hits?.[0];
		log(`SOMA devices -> ${hits?.length ?? 0} hits${devHit ? ` (first: ${devHit.name})` : ' — run Build once to create them'} (${ms()})`);
	}

	/* ---- chain A–C on a throwaway schematic + PCB inside the OPEN
	 *  project, deleted afterwards (Fix F).  No project is ever created. */
	let schU: string | undefined;
	let pcbU: string | undefined;
	let schTab: string | undefined;
	let pcbTab: string | undefined;
	try {
		if (left()) {
			report(50, 'Diagnostics: throwaway schematic');
			schU = await call('diag createSchematic', eda.dmt_Schematic.createSchematic(), to(8000), true);
			log(`createSchematic() -> ${schU ? schU.slice(0, 8) + '…' : 'FAIL'} (${ms()})`);
		}
		if (schU && left()) {
			const schInfo = await call('diag getSchematicInfo', eda.dmt_Schematic.getSchematicInfo(schU), to(5000), true);
			const pageUuid = schInfo?.page?.[0]?.uuid;
			log(`schematic page -> ${pageUuid ? pageUuid.slice(0, 8) + '…' : 'none'} (${ms()})`);
			if (pageUuid) {
				schTab = await call('diag open sch page', eda.dmt_EditorControl.openDocument(pageUuid), to(6000), true);
				const di = await waitActiveDoc(pageUuid, Math.min(5000, to(5000)), 'diag sch', schTab);
				log(`sch page active -> ${di ? `type=${di.documentType}` : 'MISMATCH/timeout'} (${ms()})`);
				if (di && devHit && left()) {
					const comp = await call('diag sch place', eda.sch_PrimitiveComponent.create(
						{ libraryType: LIB_DEVICE, libraryUuid: devHit.libraryUuid ?? libUuid ?? 'SOMA', uuid: devHit.uuid },
						600, 600, undefined, 0, false, true, true), to(8000), true);
					const pid = comp?.getState_PrimitiveId?.();
					log(`sch place -> ${comp && pid ? `pid=${String(pid).slice(0, 12)}` : 'FAIL'} (${ms()})`);
					if (pid) {
						const pins = await call('diag sch comp pins', eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId?.(pid), to(5000), true);
						log(`sch comp pins -> ${Array.isArray(pins) ? pins.length : 'FAIL'} (${ms()})`);
					}
				}
				else if (!devHit) log('sch place skipped — no SOMA device to place');
				const sv = await call('diag sch_Document.save', eda.sch_Document.save(), to(6000), true);
				log(`sch save -> ${sv} (${ms()})`);
			}
		}
		if (left()) {
			report(70, 'Diagnostics: throwaway PCB');
			pcbU = await call('diag createPcb', eda.dmt_Pcb.createPcb(), to(8000), true);
			log(`createPcb() -> ${pcbU ? pcbU.slice(0, 8) + '…' : 'FAIL'} (${ms()})`);
		}
		if (pcbU && left()) {
			pcbTab = await call('diag open pcb', eda.dmt_EditorControl.openDocument(pcbU), to(6000), true);
			const pdi = await waitActiveDoc(pcbU, Math.min(5000, to(5000)), 'diag pcb', pcbTab);
			log(`pcb active -> ${pdi ? `type=${pdi.documentType}` : 'MISMATCH/timeout'} (${ms()})`);
			if (pdi) {
				const tr = await call('diag track', eda.pcb_PrimitiveLine.create('DIAG', LAYER.TOP as TPCB_LayersOfLine, 0, 0, 500, 500, 10), to(5000), true);
				log(`track create -> ${tr ? 'ok' : 'FAIL'} (${ms()})`);
				const imp = await call('diag importChanges', schU ? eda.pcb_Document.importChanges(schU, true) : undefined, to(8000), true);
				log(`importChanges -> ${imp} (${ms()})`);
				const psv = await call('diag pcb_Document.save', eda.pcb_Document.save(), to(6000), true);
				log(`pcb save -> ${psv} (${ms()})`);
			}
		}
	}
	finally {
		// delete the throwaway docs so the user's project stays clean
		report(90, 'Diagnostics: cleanup');
		if (pcbTab) await call('diag close pcb tab', eda.dmt_EditorControl.closeDocument(pcbTab), 4000, true);
		if (schTab) await call('diag close sch tab', eda.dmt_EditorControl.closeDocument(schTab), 4000, true);
		if (pcbU) {
			const d = await call('diag deletePcb', eda.dmt_Pcb.deletePcb(pcbU), 6000, true);
			log(`deletePcb -> ${d} (${ms()})`);
		}
		if (schU) {
			const d = await call('diag deleteSchematic', eda.dmt_Schematic.deleteSchematic(schU), 6000, true);
			log(`deleteSchematic -> ${d} (${ms()})`);
		}
	}
	if (!left()) log(`NOTE: time budget exhausted at ${ms()} — remaining steps skipped`);

	report(100, 'Diagnostics done');
	try { eda.sys_LoadingAndProgressBar.destroyProgressBar(); } catch { /* noop */ }
	eda.sys_Dialog.showInformationMessage(lines.join('\n'), 'SOMA diagnostics');
}

/* ---------------- entry ---------------- */

export async function runSomaBuild(): Promise<void> {
	warnings.length = 0;
	info.length = 0;
	for (const k of Object.keys(stats)) delete stats[k];
	assocLibUuid = undefined;
	devLibArg = undefined;
	const started = Date.now();
	report(1, 'SOMA v1.3: starting');
	slog('build start');
	try {
		const diag: string[] = [];
		const ws = await call('getCurrentWorkspaceInfo',
			(eda as { dmt_Workspace?: { getCurrentWorkspaceInfo?: () => Promise<unknown> } }).dmt_Workspace?.getCurrentWorkspaceInfo?.(), 6000, true);
		diag.push(`workspace=${ws ? ((ws as { name?: string; uuid?: string }).name || (ws as { uuid?: string }).uuid) : 'timeout/none'}`);

		// ---- Fix A: the build targets the user's OPEN project — never
		// create one (dmt_Project.createProject fails in HALF_OFFLINE)
		const proj = await call('getCurrentProjectInfo', eda.dmt_Project.getCurrentProjectInfo(), 10000);
		if (!proj?.uuid) {
			report(100, 'No project open');
			eda.sys_Dialog.showInformationMessage(
				"Open your project 'SOMA Carrier v1.3 (EasyEDA)' first, then run Build again",
				'SOMA Carrier v1.3');
			return;
		}
		info.push(`project: ${proj.friendlyName ?? proj.name ?? proj.uuid}`);

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

		report(23, 'Checking project documents');
		const docs = await ensureProjectDocs(proj.uuid);
		if (!docs) throw new Error('getCurrentProjectInfo returned no project');
		let uniqueIds = new Map<string, string>();
		const schUuid = docs.schUuid;
		const pcbUuid = docs.pcbUuid;
		if (!pcbUuid) throw new Error('no PCB document in the open project (all create variants failed)');
		if (!schUuid) warn('no schematic document — schematic step skipped');

		if (devices.size > 0 && schUuid) {
			report(24, 'Opening schematic');
			const infoSch = await call('getSchematicInfo', eda.dmt_Schematic.getSchematicInfo(schUuid), 8000, true);
			let pageUuid = infoSch?.page?.[0]?.uuid;
			if (!pageUuid) {
				pageUuid = await call('createSchematicPage', eda.dmt_Schematic.createSchematicPage(schUuid), 10000, true);
			}
			if (pageUuid) {
				const schTab = await call('open schematic page', eda.dmt_EditorControl.openDocument(pageUuid), 10000, true);
				const schDoc = await waitActiveDoc(pageUuid, 8000, 'sch', schTab);
				if (!schDoc) warn('schematic page did not become active — symbols/wires may land elsewhere');
			}
			else warn('schematic has no page — symbols/wires may land elsewhere');
			await sleep(300);

			uniqueIds = await buildSchematic(devices, libUuid, fpRefs);
			const schSaved = await call('sch_Document.save', eda.sch_Document.save(), 15000);
			if (!schSaved) warnings.push('schematic save failed');
			report(48, 'Schematic saved');
		}
		else if (devices.size === 0) {
			warn('no devices — schematic skipped (free-pad PCB only)');
		}

		report(49, 'Opening PCB');
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

		await runDrc();
		await exportFab();
	}
	catch (err) {
		warn(`FATAL: ${errText(err)}`);
	}
	finally {
		try { eda.sys_LoadingAndProgressBar.destroyProgressBar(); } catch { /* noop */ }
	}
	const secs = Math.round((Date.now() - started) / 1000);
	const countLines = [
		`parts: ${(stats.schCompsPlaced ?? 0) + (stats.schCompsReused ?? 0)}/${BOARD_DATA.parts.length} schematic (${stats.schCompsReused ?? 0} reused), ${stats.pcbCompsImported ?? 0} imported to PCB`,
		`nets labeled: ${stats.netLabels ?? 0} labels + ${stats.netFlags ?? 0} flags + ${stats.netPorts ?? 0} ports`,
		`tracks: ${stats.tracksOk ?? 0} ok / ${stats.tracksFailed ?? 0} failed${stats.tracksReused ? ` (+${stats.tracksReused} existing)` : ''}`,
		`vias: ${stats.viasOk ?? 0}${stats.viasReused ? ` (+${stats.viasReused} existing)` : ''}`,
		`pours: ${stats.poursOk ?? 0}${stats.poursReused ? ` (+${stats.poursReused} existing)` : ''}`,
		`DRC: ${stats.drcErrors === undefined ? 'not run' : stats.drcErrors < 0 ? 'violations (boolean check)' : `${stats.drcErrors} violation(s) in ${stats.drcCategories ?? 0} categories`}`,
		`gerber: ${stats.gerberExported ? 'exported' : 'not exported'}`,
	];
	const msg = [
		`SOMA Carrier v1.3 rebuild finished in ${secs}s.`,
		'',
		...countLines,
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

