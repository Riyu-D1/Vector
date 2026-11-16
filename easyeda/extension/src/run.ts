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
	let i = 0;
	for (const c of plan.comps) {
		report(25 + Math.round(22 * i / plan.comps.length), `part ${i + 1}/${plan.comps.length}: ${c.ref}`);
		i++;
		const dev = devices.get(c.ref);
		if (!dev) { warnings.push(`${c.ref}: skipped — no device`); continue; }
		const comp = await call(`sch create ${c.ref}`, eda.sch_PrimitiveComponent.create(
			{ libraryType: LIB_DEVICE, libraryUuid: dev.lib, uuid: dev.uuid },
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
		'lib_Footprint.openInEditor', 'lib_Footprint.getRenderImage',
		'lib_Footprint.updateDocumentSource',
		'lib_Symbol.create', 'lib_Symbol.search', 'lib_Symbol.get', 'lib_Symbol.modify',
		'lib_Symbol.openInEditor', 'lib_Symbol.updateDocumentSource', 'lib_Symbol.getRenderImage',
		'lib_Device.create', 'lib_Device.search', 'lib_Device.get', 'lib_Device.modify',
		'lib_Device.getByLcscIds', 'lib_Device.delete',
		'dmt_EditorControl.openDocument', 'dmt_EditorControl.closeDocument',
		'dmt_EditorControl.activateDocument', 'dmt_SelectControl.getCurrentDocumentInfo',
		'dmt_EditorControl.waitForDocumentReady', 'dmt_EditorControl.getDocumentReadyState',
		'dmt_Project.createProject', 'dmt_Project.waitForReady',
		'dmt_Schematic.createSchematic', 'dmt_Schematic.getSchematicInfo',
		'dmt_Pcb.createPcb', 'dmt_Board.createBoard',
		'pcb_Document.save', 'pcb_Document.importChanges',
		'pcb_PrimitivePad.create', 'pcb_PrimitivePad.getAll',
		'pcb_PrimitivePolyline.create', 'pcb_PrimitiveComponent.create',
		'pcb_PrimitiveComponent.getAll', 'pcb_PrimitiveComponent.getAllPinsByPrimitiveId',
		'pcb_PrimitiveLine.create',
		'pcb_MathPolygon.createPolygon', 'sch_PrimitiveComponent.create',
		'sch_PrimitiveComponent.getAllPinsByPrimitiveId',
		'sch_Document.save', 'sch_PrimitivePin.create', 'sch_PrimitivePin.getAll',
		'sch_PrimitiveRectangle.create', 'sch_PrimitiveText.create',
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

	/* ---- symbol draw round trip (KEEP — do not delete) ----
	 *  Same editor-tab path as footprints: open the empty symbol, print
	 *  the full live source, draw pins/box/text via sch_Primitive*, save,
	 *  reread + count pins, close, REOPEN and count again — only the
	 *  reopen proves the library write persisted. */
	report(55, 'Diagnostics: symbol draw round-trip');
	const symName = `SOMA-DIAG-KEEP-SYM-${Math.floor(Math.random() * 90000) + 10000}`;
	const symUuid = await call('diag lib_Symbol.create', eda.lib_Symbol.create(libUuid, symName), 10000);
	log(`create symbol ${symName} -> ${symUuid ? symUuid.slice(0, 8) + '…' : 'FAIL'} (${ms()})`);
	if (symUuid) {
		const tabId2 = await call('diag symbol openInEditor', eda.lib_Symbol.openInEditor(symUuid, libUuid), 15000, true);
		log(`symbol openInEditor -> ${tabId2 ? 'tab ' + tabId2 : 'FAIL'} (${ms()})`);
		let drew = false;
		if (tabId2) {
			await call('diag symbol activate', eda.dmt_EditorControl.activateDocument(tabId2), 8000, true);
			const info = await waitActiveDoc(symUuid, 8000, 'diag sym', tabId2);
			log(`active doc -> ${info ? `type=${info.documentType} uuid=${info.uuid?.slice(0, 8)}` : 'MISMATCH/timeout'} (${ms()})`);
			if (info) {
				const src0 = await call('diag pre-draw getDocumentSource', eda.sys_FileManager.getDocumentSource(), 10000, true);
				log(`EMPTY SOURCE (${typeof src0 === 'string' ? src0.length : 0} chars): ${typeof src0 === 'string' ? src0 : 'FAIL'} (${ms()})`);
				const pinList = [{ num: '1', name: 'P1' }, { num: '2', name: 'P2' }];
				const ops = symbolOps('TP', symName, pinList);
				let ok = 0, fail = 0;
				for (const op of ops) {
					if (op.kind === 'pin') {
						const r = await call(`diag pin ${op.num}`,
							eda.sch_PrimitivePin.create(op.x, op.y, op.num, op.name, op.rot, op.len,
								null, PIN_SHAPE_NONE, PIN_TYPE_PASSIVE), 8000, fail > 0);
						r ? ok++ : fail++;
					}
					else if (op.kind === 'rect') {
						const r = await call('diag rect',
							eda.sch_PrimitiveRectangle.create(op.x, op.y, op.w, op.h, 0, 0), 8000, true);
						r ? ok++ : fail++;
					}
					else {
						const r = await call('diag text',
							eda.sch_PrimitiveText.create(op.x, op.y, op.s, 0, null, null, 8), 8000, true);
						r ? ok++ : fail++;
					}
				}
				log(`drew ${ok} symbol primitives (${fail} failed) (${ms()})`);
				const n = await symbolPinCount('diag sym');
				log(`sch_PrimitivePin.getAll -> ${n} pins (${ms()})`);
				const src1 = await call('diag post-draw getDocumentSource', eda.sys_FileManager.getDocumentSource(), 10000, true);
				const pinRecs = typeof src1 === 'string' ? (src1.match(/"PIN"/g) ?? []).length : 0;
				log(`post-draw source ${typeof src1 === 'string' ? src1.length : 0} chars, ${pinRecs} PIN recs | head: ${typeof src1 === 'string' ? src1.slice(0, 160) : 'FAIL'} (${ms()})`);
				const saved = await call('diag sch_Document.save', eda.sch_Document.save(), 15000);
				log(`sch_Document.save -> ${saved} (${ms()})`);
				const pushed = typeof src1 === 'string' && src1.length > 0
					? await call('diag updateDocumentSource(live)', eda.lib_Symbol.updateDocumentSource(symUuid, libUuid, src1), 15000, true)
					: undefined;
				log(`updateDocumentSource(live source) -> ${pushed} (${ms()})`);
				drew = true;
			}
			const closed = await call('diag symbol close', eda.dmt_EditorControl.closeDocument(tabId2), 8000, true);
			log(`closeDocument -> ${closed} (${ms()})`);
		}
		if (drew) {
			// reopen + count — the only real persistence proof
			const tabId3 = await call('diag symbol reopen', eda.lib_Symbol.openInEditor(symUuid, libUuid), 15000, true);
			if (tabId3) {
				await call('diag reopen activate', eda.dmt_EditorControl.activateDocument(tabId3), 8000, true);
				const info3 = await waitActiveDoc(symUuid, 8000, 'diag sym', tabId3);
				const n3 = info3 ? await symbolPinCount('diag sym') : -1;
				const src3 = info3 ? await call('diag reopen getDocumentSource', eda.sys_FileManager.getDocumentSource(), 10000, true) : undefined;
				const pin3 = typeof src3 === 'string' ? (src3.match(/"PIN"/g) ?? []).length : 0;
				log(`REOPENED -> ${n3} pins via getAll, ${pin3} PIN recs in ${typeof src3 === 'string' ? src3.length : 0}-char source (${ms()})`);
				await call('diag reopen close', eda.dmt_EditorControl.closeDocument(tabId3), 8000, true);
			}
			else log('reopen -> FAIL');
		}
		const item = await call('diag lib_Symbol.get', eda.lib_Symbol.get(symUuid, libUuid), 10000);
		log(`symbol lib get -> ${dump(item)} (${ms()})`);
		const img = await call('diag symbol getRenderImage', eda.lib_Symbol.getRenderImage({ symbolUuid: symUuid, libraryUuid: libUuid }), 15000, true);
		log(`symbol getRenderImage -> ${img && typeof (img as Blob).size === 'number' ? `blob ${(img as Blob).size}b` : dump(img)} (${ms()})`);
		log(`symbol ${symName} KEPT for inspection`);
	}

	/** Await p and return the raw result or the full error — diag needs
	 *  the error payload and the exact call args in the report. */
	const attempt = async <T>(desc: string, p: Promise<T> | undefined, timeoutMs: number): Promise<{ hit: boolean; val?: T }> => {
		if (!p || typeof p.then !== 'function') { log(`${desc} -> api unavailable (${ms()})`); return { hit: false }; }
		try {
			const val = await Promise.race([
				p,
				new Promise<T>((_r, rej) => setTimeout(() => rej(new Error(`timeout after ${timeoutMs}ms`)), timeoutMs)),
			]);
			return { hit: val !== undefined && val !== null && val !== false, val };
		}
		catch (e) { log(`${desc} -> FAIL ${errText(e)} (${ms()})`); return { hit: false }; }
	};

	/* ---- device create from the DRAWN symbol + footprint ----
	 *  v1.3's device.create against a system-footprint association failed
	 *  with an "[object Object]" payload (a resolved error object, not a
	 *  rejection).  With all footprints drawn into the personal library the
	 *  association is internal — figure out which libraryUuid arg the
	 *  create accepts: the search-hit value, the discovered lib uuid, the
	 *  literal "SOMA", or undefined.  A create only wins on a uuid string;
	 *  anything else is printed verbatim. */
	report(80, 'Diagnostics: device from drawn items');
	let devUuid: string | undefined;
	let devLib: string | undefined;
	if (fpUuid && symUuid) {
		const fpHitLib = (await call('diag fp search-hit', eda.lib_Footprint.search(diagName, libUuid), 8000, true))
			?.find(h => norm(h.name) === norm(diagName))?.libraryUuid;
		const symHitLib = (await call('diag sym search-hit', eda.lib_Symbol.search(symName, libUuid), 8000, true))
			?.find(h => norm(h.name) === norm(symName))?.libraryUuid;
		log(`personal-lib search-hit libraryUuid -> fp=${fpHitLib ?? 'none'} sym=${symHitLib ?? 'none'} (discovered libUuid=${libUuid})`);
		const devName = `SOMA-DIAG-KEEP-DEV-${Math.floor(Math.random() * 90000) + 10000}`;
		const cands: Array<string | undefined> = [];
		for (const c of [symHitLib, fpHitLib, libUuid, 'SOMA', undefined]) if (!cands.includes(c)) cands.push(c);
		const shapes: Array<[string, (l: string | undefined) => DeviceAssoc]> = [
			['ref', l => ({
				symbol: { uuid: symUuid, libraryUuid: l ?? libUuid },
				footprint: { uuid: fpUuid, libraryUuid: l ?? libUuid },
			})],
			['flat', () => ({ symbolUuid: symUuid, footprintUuid: fpUuid })],
		];
		outer:
		for (const cand of cands) {
			for (const [shapeName, mkAssoc] of shapes) {
				const r = await attempt(`lib_Device.create(lib=${cand ?? 'undefined'},assoc=${shapeName})`,
					eda.lib_Device.create(cand as string, devName, undefined, mkAssoc(cand), undefined, { designator: 'TP', addIntoBom: true, addIntoPcb: true }), 12000);
				if (r.hit && typeof r.val === 'string' && r.val) {
					log(`  -> uuid ${r.val.slice(0, 8)} via lib=${cand ?? 'undefined'} assoc=${shapeName} (${ms()})`);
					devUuid = r.val; devLib = cand ?? libUuid;
					break outer;
				}
				log(`  lib=${cand ?? 'undefined'} assoc=${shapeName} -> ${r.hit ? 'non-uuid result ' + dump(r.val) : 'FAIL'} (${ms()})`);
			}
		}
		if (devUuid) {
			const dg = await attempt(`lib_Device.get('${devUuid.slice(0, 8)}…','${devLib}')`, eda.lib_Device.get(devUuid, devLib), 8000);
			const assoc = (dg.val as ILIB_DeviceItem | undefined)?.association;
			log(`device read -> sym=${assoc?.symbol?.uuid ?? 'NONE'} fp=${assoc?.footprint?.uuid ?? 'NONE'} (${ms()})`);
			log(`device ${devName} KEPT for inspection`);
		}
		else log('device create FAILED on every libraryUuid variant — build devices will fail too');
	}
	else log('skipping device test — drawn footprint/symbol missing');

	/* ---- downstream path: project -> schematic -> importChanges -> pcb ----
	 *  The library phase proves nothing about the build's second half, so
	 *  exercise it end-to-end with the diag device: a real project, one
	 *  schematic component, an importChanges into a linked PCB, a pad
	 *  count on the imported component, one track, then save.  Everything
	 *  is KEPT (SOMA-DIAG-KEEP-PROJ-*) for inspection. */
	report(88, 'Diagnostics: project/sch/pcb round-trip');
	if (devUuid) {
		const projName = `SOMA-DIAG-KEEP-PROJ-${Math.floor(Math.random() * 90000) + 10000}`;
		const pr = await attempt('dmt_Project.createProject', eda.dmt_Project.createProject(projName), 20000);
		log(`createProject -> ${pr.hit ? pr.val : 'FAIL'} (${ms()})`);
		let schU: string | undefined;
		if (pr.hit && typeof pr.val === 'string') {
			await attempt('dmt_Project.waitForReady', eda.dmt_Project.waitForReady(pr.val, 15000), 20000);
			await sleep(800);
			const sr = await attempt('dmt_Schematic.createSchematic', eda.dmt_Schematic.createSchematic('SOMA-DIAG-SCH'), 15000);
			log(`createSchematic -> ${sr.hit ? sr.val : 'FAIL'} (${ms()})`);
			if (sr.hit && typeof sr.val === 'string') schU = sr.val;
		}
		if (schU) {
			await sleep(1500);
			const schInfo = await call('diag getSchematicInfo', eda.dmt_Schematic.getSchematicInfo(schU), 8000, true);
			const pageUuid = schInfo?.page?.[0]?.uuid;
			if (pageUuid) {
				const t = await call('diag open sch page', eda.dmt_EditorControl.openDocument(pageUuid), 10000, true);
				const di = await waitActiveDoc(pageUuid, 8000, 'diag sch', t);
				log(`sch page active -> ${di ? `type=${di.documentType}` : 'MISMATCH/timeout'} (${ms()})`);
			}
			else log('schematic has no page uuid — component may land elsewhere');
			const comp = await attempt(`sch_PrimitiveComponent.create(dev=${devUuid.slice(0, 8)},lib=${devLib})`,
				eda.sch_PrimitiveComponent.create({ libraryType: LIB_DEVICE, libraryUuid: devLib ?? libUuid, uuid: devUuid }, 600, 600, undefined, 0, false, true, true), 15000);
			const compVal = comp.val as ISCH_PrimitiveComponent | undefined;
			const pid = comp.hit ? compVal?.getState_PrimitiveId?.() : undefined;
			log(`sch comp create -> ${comp.hit && pid ? `pid=${String(pid).slice(0, 12)}` : `FAIL ${dump(comp.val)}`} (${ms()})`);
			if (pid) {
				const pins = await attempt('sch comp pins', eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(pid), 8000);
				log(`sch comp pins -> ${Array.isArray(pins.val) ? pins.val.length : 'FAIL'} (${ms()})`);
			}
			const sv = await attempt('sch_Document.save', eda.sch_Document.save(), 15000);
			log(`sch save -> ${sv.val} (${ms()})`);
			const pr2 = await attempt('dmt_Pcb.createPcb', eda.dmt_Pcb.createPcb('SOMA-DIAG-PCB'), 15000);
			log(`createPcb -> ${pr2.hit ? pr2.val : 'FAIL'} (${ms()})`);
			if (pr2.hit && typeof pr2.val === 'string') {
				const pcbU = pr2.val;
				await sleep(1200);
				const bd = await attempt('dmt_Board.createBoard', eda.dmt_Board.createBoard(schU, pcbU), 15000);
				log(`createBoard -> ${bd.hit ? bd.val : 'FAIL'} (${ms()})`);
				const pt = await call('diag open pcb', eda.dmt_EditorControl.openDocument(pcbU), 15000, true);
				const pdi = await waitActiveDoc(pcbU, 10000, 'diag pcb', pt);
				log(`pcb active -> ${pdi ? `type=${pdi.documentType} uuid=${pdi.uuid?.slice(0, 8)}` : 'MISMATCH/timeout'} (${ms()})`);
				const imp = await attempt('pcb_Document.importChanges(sch,force=true)', eda.pcb_Document.importChanges(schU, true), 30000);
				log(`importChanges -> ${imp.val} (${ms()})`);
				const comps = (await call('diag pcb comps', eda.pcb_PrimitiveComponent.getAll(), 15000, true)) ?? [];
				log(`pcb components -> ${comps.length} (${ms()})`);
				for (const c of comps.slice(0, 4)) {
					const cpid = c.getState_PrimitiveId?.();
					const cpads = cpid ? await call('diag pcb comp pins', eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId?.(cpid), 8000, true) : undefined;
					log(`  pcb comp ${c.getState_Designator?.() ?? '?'} pads=${Array.isArray(cpads) ? cpads.length : 'FAIL'} (${ms()})`);
				}
				const tr = await attempt('pcb_PrimitiveLine.create track', eda.pcb_PrimitiveLine.create('DIAG', LAYER.TOP as TPCB_LayersOfLine, 0, 0, 500, 500, 10), 8000);
				log(`track create -> ${tr.hit ? 'ok' : 'FAIL'} (${ms()})`);
				const psv = await attempt('pcb_Document.save', eda.pcb_Document.save(), 20000);
				log(`pcb save -> ${psv.val} (${ms()})`);
			}
			log(`project ${projName} KEPT — schematic + pcb artifacts inside`);
		}
	}
	else log('skipping e2e — no device');

	/* ---- system-library info probes (read-only; footprints no longer
	 *  used from here — kept because the hits dump useful uuids) ---- */
	report(95, 'Diagnostics: system library (info)');
	if (sysLibUuid) {
		const sr = await attempt(`lib_Footprint.search('hdr-th_2p','${sysLibUuid}')`,
			eda.lib_Footprint.search('hdr-th_2p', sysLibUuid) as Promise<ILIB_FootprintSearchItem[]>, 10000);
		const hits = sr.val;
		log(`sys search -> ${Array.isArray(hits) ? hits.length + ' hits' : dump(hits)} (${ms()})`);
		for (const h of (hits ?? []).slice(0, 5)) {
			log(`  hit ${h.name} uuid=${h.uuid ?? 'NONE'} lib=${h.libraryUuid ?? 'NONE'}`);
		}
		const devs = await attempt(`lib_Device.getByLcscIds(['C2564','C118536'])`,
			eda.lib_Device.getByLcscIds(['C2564', 'C118536']), 10000);
		const devList = devs.val;
		log(`getByLcscIds -> ${Array.isArray(devList) ? devList.length + ' hits' : dump(devList)} (${ms()})`);
		for (const d of devList ?? []) {
			log(`  dev ${d.name} uuid=${d.uuid} lib=${d.libraryUuid} sym=${d.symbol?.name}@${d.symbol?.uuid} fp=${d.footprint?.name}@${d.footprint?.uuid} fplib=${d.footprint?.libraryUuid}`);
		}
	}
	else log('no system library uuid — all footprints drawn (expected on this build)');

	report(100, 'Diagnostics done');
	try { eda.sys_LoadingAndProgressBar.destroyProgressBar(); } catch { /* noop */ }
	eda.sys_Dialog.showInformationMessage(lines.join('\n'), 'SOMA diagnostics');
}

/* ---------------- entry ---------------- */

export async function runSomaBuild(): Promise<void> {
	warnings.length = 0;
	info.length = 0;
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
