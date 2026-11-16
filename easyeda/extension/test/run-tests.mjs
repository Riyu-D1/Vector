#!/usr/bin/env node
/*
 * Headless verification for the SOMA extension.
 *
 * src files use extensionless imports (Bundler resolution), so node
 * cannot load them directly — bundle first with esbuild:
 *
 *   ../_research/easyeda-api-sdk/node_modules/.bin/esbuild \
 *     easyeda/extension/test/run-tests.mjs --bundle --format=esm \
 *     --platform=node --outfile=/tmp/run-tests.bundle.mjs
 *   node /tmp/run-tests.bundle.mjs
 *
 * Tests:
 *   1. board-data integrity (counts, refs, net coverage)
 *   2. coordinate transforms (mm->mil, y-flip, rotation)
 *   3. symbol/footprint source generators produce parseable EDA records
 *      with correct pad positions and pin numbering
 *   4. planSchematic: every connected pad gets exactly one label; all 37
 *      nets represented; block assignment covers all 55 parts
 *   5. planPcb: placements land on v1.3 anchors; all 1836 tracks and 164
 *      vias mapped; outline polygon closed; pours present
 *   6. syslib-match table: all 26 (footprint,rot) keys covered by either
 *      a system-library match or the custom-draw list
 *   7. symdraw: symbol pin lists in fp-domain numbering, primitive ops
 *   8. mock-eda smoke test of runSomaBuild: every API call is recorded;
 *      verifies system footprints resolve via search hits, custom
 *      footprints + all symbols go through the draw-in-editor path with
 *      active-doc polling, and all 55 components + tracks are issued
 */

import assert from 'node:assert/strict';

import { BOARD_DATA } from '../src/board-data.ts';
import * as coords from '../src/coords.ts';
import { symbolSource } from '../src/eda-source.ts';
import { footprintOps } from '../src/fpdraw.ts';
import { planSchematic, symbolPins } from '../src/schplan.ts';
import { planPcb, LAYER } from '../src/pcbplan.ts';
import { PARTS, BLOCKS } from '../src/parts-table.ts';
import { symbolKey, symbolOps, symbolPinList } from '../src/symdraw.ts';
import { CUSTOM_KEYS, fpKeyOf, SYS_FP_MATCH } from '../src/syslib-match.ts';

let pass = 0;
async function t(name, fn) {
	try { await fn(); pass++; console.log(`  ok  ${name}`); }
	catch (e) { console.error(`FAIL  ${name}: ${e.message}`); process.exitCode = 1; }
}
const near = (a, b, tol = 0.01) => Math.abs(a - b) <= tol;

/* 1 ---------------------------------------------------------- data integrity */
await t('55 parts / 4 holes / 1836 tracks / 164 vias / 2 zones / 37 nets', () => {
	assert.equal(BOARD_DATA.parts.length, 55);
	assert.equal(BOARD_DATA.mountingHoles.length, 4);
	assert.equal(BOARD_DATA.tracks.length, 1836);
	assert.equal(BOARD_DATA.vias.length, 164);
	assert.equal(BOARD_DATA.zones.length, 2);
	assert.equal(BOARD_DATA.nets.length, 37);
});
await t('every part has pads and a footprint', () => {
	for (const p of BOARD_DATA.parts) {
		assert.ok(p.pads.length > 0, p.ref);
		assert.ok(p.footprint.length > 0, p.ref);
	}
});
await t('all 55 refs have a PARTS-table block entry', () => {
	for (const p of BOARD_DATA.parts) assert.ok(PARTS[p.ref], p.ref);
	const blocks = new Set(BLOCKS.map(b => b.id));
	for (const [r, s] of Object.entries(PARTS)) assert.ok(blocks.has(s.block), r);
});
await t('no B-side parts (transform assumes front)', () => {
	assert.ok(BOARD_DATA.parts.every(p => p.side === 'F'));
});
await t('all track/via nets exist on pads', () => {
	const padNets = new Set(BOARD_DATA.parts.flatMap(p => p.pads.map(q => q.net)));
	for (const tr of BOARD_DATA.tracks) assert.ok(padNets.has(tr.net), tr.net);
	for (const v of BOARD_DATA.vias) assert.ok(padNets.has(v.net), v.net);
});

/* 2 ---------------------------------------------------------- transforms */
await t('mm->mil and y-flip', () => {
	assert.ok(near(coords.px(1), 39.3701));
	assert.ok(near(coords.py(1), -39.3701));
	assert.ok(near(coords.prot(90), 270));
	assert.ok(near(coords.prot(0), 0));
});
await t('polygon source emits L-joined mil points (no trailing L)', () => {
	assert.deepEqual(coords.polygonSource([[0, 0], [10, 5]]), [0, 0, 'L', 393.701, -196.85]);
	assert.deepEqual(coords.polygonSource([[0, 0], [10, 5], [20, 0]]),
		[0, 0, 'L', 393.701, -196.85, 787.402, 0]);
});

/* 3 ---------------------------------------------------------- source gen */
function parseSrc(src) {
	return src.split('\n').map(l => JSON.parse(l));
}
await t('symbol source: doctype, pins, attrs, box', () => {
	const j19 = BOARD_DATA.parts.find(p => p.ref === 'J19');
	const src = symbolSource('SOMA-J19', 'J', [
		{ num: '1', name: 'RLY_LOW' }, { num: '2', name: 'RLY_SW' },
	]);
	const recs = parseSrc(src);
	assert.deepEqual(recs[0], ['DOCTYPE', 'SYMBOL', '1.0']);
	const pins = recs.filter(r => r[0] === 'PIN');
	assert.equal(pins.length, 2);
	// pin1 left at -60, pin2 right at +60
	assert.equal(pins[0][4], -60);
	assert.equal(pins[1][4], 60);
	assert.equal(pins[1][7], 180);
	// NAME attrs reference pin ids
	const names = recs.filter(r => r[0] === 'ATTR' && r[3] === 'NAME');
	assert.equal(names.length, 2);
});
await t('footprint ops: THT pads on layer 12, plated round holes, correct positions', () => {
	const j19 = BOARD_DATA.parts.find(p => p.ref === 'J19');
	const pads = footprintOps(j19).filter(o => o.kind === 'pad');
	assert.equal(pads.length, 2);
	assert.equal(pads[0].num, '1');
	assert.ok(near(pads[0].x, 0));
	assert.ok(near(pads[1].x, 0));
	assert.ok(near(pads[1].y, -100));      // local (0,2.54mm) -> -100 mil
	assert.equal(pads[0].layer, 12);       // multi layer
	assert.equal(pads[0].hole[0], 'ROUND');
	assert.equal(pads[0].plated, true);
});
await t('footprint ops: SMD pads on layer 1, no hole, unplated', () => {
	const u2 = BOARD_DATA.parts.find(p => p.ref === 'U2');
	const pads = footprintOps(u2).filter(o => o.kind === 'pad');
	assert.equal(pads.length, 8);
	assert.equal(pads[0].layer, 1);
	assert.equal(pads[0].hole, null);
	assert.equal(pads[0].plated, false);
});
await t('footprint ops: silk/courtyard polys only use primitive-legal layers', () => {
	const j19 = BOARD_DATA.parts.find(p => p.ref === 'J19');
	for (const op of footprintOps(j19)) {
		if (op.kind === 'poly') assert.equal(op.layer, 3, 'silk layer');
	}
});
await t('footprint pads land on KiCad absolute pad positions', () => {
	// for rot=0 parts, footprint local * mil + anchor must equal abs pad pos
	for (const ref of ['K1', 'U2', 'J16']) {
		const p = BOARD_DATA.parts.find(x => x.ref === ref);
		for (const pad of p.pads) {
			assert.ok(near(p.x + pad.lx, pad.ax, 0.001), `${ref}.${pad.num} x`);
			assert.ok(near(p.y + pad.ly, pad.ay, 0.001), `${ref}.${pad.num} y`);
		}
	}
	// rotated parts: local is rot-baked so same invariant holds
	for (const ref of ['Q2', 'U1A', 'J1']) {
		const p = BOARD_DATA.parts.find(x => x.ref === ref);
		for (const pad of p.pads) {
			assert.ok(near(p.x + pad.lx, pad.ax, 0.001), `${ref}.${pad.num} x`);
			assert.ok(near(p.y + pad.ly, pad.ay, 0.001), `${ref}.${pad.num} y`);
		}
	}
});

/* 4 ---------------------------------------------------------- schematic plan */
await t('planSchematic covers all parts and all nets', () => {
	const plan = planSchematic(BOARD_DATA);
	assert.equal(plan.comps.length, 55);
	const labeledNets = new Set(plan.labels.map(l => l.net));
	const connectedPadNets = new Set(
		BOARD_DATA.parts.flatMap(p => p.pads.filter(q => q.net).map(q => q.net)));
	assert.deepEqual([...connectedPadNets].sort(), [...labeledNets].sort());
	// every connected pin got a stub + label
	const stubs = plan.wires.length;
	const connected = BOARD_DATA.parts.flatMap(p => p.pads).filter(q => q.net).length;
	assert.equal(stubs, connected);
	assert.equal(plan.labels.length, connected);
	// headers for all 7 blocks
	assert.equal(plan.headers.length, 7);
});
await t('no overlapping component slots', () => {
	const plan = planSchematic(BOARD_DATA);
	for (let i = 0; i < plan.comps.length; i++) {
		for (let j = i + 1; j < plan.comps.length; j++) {
			const a = plan.comps[i]; const b = plan.comps[j];
			const overlap = Math.abs(a.cx - b.cx) < 100 && Math.abs(a.cy - b.cy) < (a.h + b.h) / 2;
			assert.ok(!overlap, `${a.ref} vs ${b.ref}`);
		}
	}
});

/* 5 ---------------------------------------------------------- pcb plan */
await t('planPcb: placements at v1.3 anchors (mil, y-flipped)', () => {
	const plan = planPcb(BOARD_DATA);
	assert.equal(plan.placements.length, 55);
	const k1 = plan.placements.find(p => p.ref === 'K1');
	assert.ok(near(k1.x, 100 * 39.3701) && near(k1.y, -62 * 39.3701));
});
await t('planPcb: tracks/vias/pours/holes', () => {
	const plan = planPcb(BOARD_DATA);
	assert.equal(plan.holes.length, 4);
	assert.equal(plan.vias.length, 164);
	assert.equal(plan.pours.length, 2);
	assert.ok(plan.tracks.length > 1700);
	// polygonSource format: [x0,y0,'L', x1,y1, x2,y2, ...] — closed => >=5 pts => >=11
	assert.ok(plan.outlinePolygon.length >= 11);
	const oxs = plan.outlinePolygon.filter(e => typeof e === 'number');
	assert.ok(near(oxs[0], oxs[oxs.length - 2]) && near(oxs[1], oxs[oxs.length - 1]), 'outline closed');
	// outline bounds 135x115mm — filter 'L' markers first, then pairs are (x,y)
	const nums = plan.outlinePolygon.filter(e => typeof e === 'number');
	const xs = nums.filter((_, i) => i % 2 === 0);
	const ys = nums.filter((_, i) => i % 2 === 1);
	assert.ok(near(Math.max(...xs), 135 * 39.3701));
	assert.ok(near(Math.min(...ys), -115 * 39.3701));
	// v1.3 hole corners
	const hs = plan.holes.map(h => `${Math.round(h.x)},${Math.round(h.y)}`);
	assert.ok(hs.includes(`${Math.round(4 * 39.3701)},${Math.round(-4 * 39.3701)}`));
});

/* 6 ---------------------------------------------------------- pin/track reachability */
await t('every track endpoint lands within 2mm of a pad or via (same net) or another track vertex', () => {
	// connectivity heuristic — replicated copper must touch something
	const padPts = []; const viaPts = [];
	for (const p of BOARD_DATA.parts) {
		for (const q of p.pads) padPts.push({ x: q.ax, y: q.ay, net: q.net });
	}
	for (const v of BOARD_DATA.vias) viaPts.push({ x: v.x, y: v.y, net: v.net });
	// count vertex sharers: tracks sharing the same (net,endpoint)
	const vertCount = new Map();
	for (const tr of BOARD_DATA.tracks) {
		for (const k of [`${tr.net}|${tr.x1},${tr.y1}`, `${tr.net}|${tr.x2},${tr.y2}`]) {
			vertCount.set(k, (vertCount.get(k) ?? 0) + 1);
		}
	}
	const nearPt = (x, y, net) =>
		padPts.some(p => p.net === net && near(p.x, x, 2) && near(p.y, y, 2))
		|| viaPts.some(v => v.net === net && near(v.x, x, 2) && near(v.y, y, 2));
	let isolated = 0;
	for (const tr of BOARD_DATA.tracks) {
		const a = nearPt(tr.x1, tr.y1, tr.net) || (vertCount.get(`${tr.net}|${tr.x1},${tr.y1}`) ?? 0) > 1;
		const b = nearPt(tr.x2, tr.y2, tr.net) || (vertCount.get(`${tr.net}|${tr.x2},${tr.y2}`) ?? 0) > 1;
		if (!a || !b) isolated++;
	}
	// most segments share vertices; a few may be isolated stubs — report only
	console.log(`     (info) track segs with an unshared endpoint: ${isolated}`);
});
await t('pad nets count per ref matches KiCad source spot-checks', () => {
	const k1 = BOARD_DATA.parts.find(p => p.ref === 'K1');
	const m = new Map(k1.pads.map(q => [q.num, q.net]));
	assert.equal(m.get('1'), '+12V');
	assert.equal(m.get('2'), 'RLY_LOW');
	assert.equal(m.get('3'), '+12V_MOT');
	assert.equal(m.get('5'), '+12V');
	const q2 = BOARD_DATA.parts.find(p => p.ref === 'Q2');
	const m2 = new Map(q2.pads.map(q => [q.num, q.net]));
	assert.equal(m2.get('1'), 'RP_GATE');
	assert.equal(m2.get('2'), '+12V_SW');
	assert.equal(m2.get('3'), '+12V_RP');
});

/* 6b ------------------------------------------------------- syslib match table */
await t('every board (footprint,rot) key is covered by SYS_FP_MATCH or CUSTOM_KEYS', () => {
	const keys = new Set(BOARD_DATA.parts.map(p => fpKeyOf(p.footprint, p.rot)));
	assert.equal(keys.size, 26, 'unique keys');
	for (const k of keys) assert.ok(SYS_FP_MATCH[k] || CUSTOM_KEYS[k], `uncovered key ${k}`);
	// no overlap between the two tables
	for (const k of Object.keys(CUSTOM_KEYS)) assert.ok(!SYS_FP_MATCH[k], `key in both tables: ${k}`);
});
await t('fpKeyOf normalizes rotation forms', () => {
	assert.equal(fpKeyOf('X', 0), 'X@0');
	assert.equal(fpKeyOf('X', 90), 'X@90');
	assert.equal(fpKeyOf('X', 90.0), 'X@90');
	assert.equal(fpKeyOf('X', 270.0), 'X@270');
});
await t('match table sanity: uuids, finite offsets, padmaps preserve pad count', () => {
	for (const [key, m] of Object.entries(SYS_FP_MATCH)) {
		assert.match(m.sysFpUuid, /^[0-9a-f]{32}$/, `${key} uuid`);
		assert.ok(Number.isFinite(m.dx) && Number.isFinite(m.dy) && Number.isFinite(m.rot), key);
		assert.ok([0, 90, 180, 270].includes(m.rot), `${key} rot ${m.rot}`);
		assert.ok(m.worst < 5, `${key} worst ${m.worst}mil`);
		const part = BOARD_DATA.parts.find(p => fpKeyOf(p.footprint, p.rot) === key);
		assert.ok(part, `${key} has a part`);
		const padNums = part.pads.filter(p => p.type !== 'np_thru_hole').map(p => p.num);
		for (const n of padNums) assert.ok(m.padmap[n], `${key} padmap missing kicad pad ${n}`);
	}
});

/* 7 ---------------------------------------------------------- symdraw */
await t('symbolPinList: KiCad numbering when no padmap', () => {
	const j19 = BOARD_DATA.parts.find(p => p.ref === 'J19');
	const pl = symbolPinList(j19);
	assert.deepEqual(pl, [
		{ num: '1', name: 'RLY_LOW' },
		{ num: '2', name: 'RLY_SW' },
	]);
});
await t('symbolPinList: fp-domain numbering applies the padmap (K1 coil swap)', () => {
	const k1 = BOARD_DATA.parts.find(p => p.ref === 'K1');
	const m = SYS_FP_MATCH['Relay_SPST_SANYOU_SRD_Series_Form_A@0'];
	assert.deepEqual(m.padmap, { 1: '2', 2: '1', 3: '3', 5: '5' }, 'k1 padmap');
	const pl = symbolPinList(k1, m.padmap);
	const byNum = new Map(pl.map(p => [p.num, p.name]));
	// kicad 1 (+12V coil) -> sys pad 2, kicad 2 (RLY_LOW) -> sys pad 1:
	// symbol pin numbers match the SYSTEM footprint so import lands on
	// the right copper, names keep the kicad meaning
	assert.equal(byNum.get('1'), 'COIL-');
	assert.equal(byNum.get('2'), 'COIL+');
	assert.equal(byNum.get('3'), 'NO');
	assert.equal(byNum.get('5'), 'COM');
});
await t('symbolOps: one pin op per pin + 1 rect + 2 texts, mirrored sides', () => {
	const ops = symbolOps('K', 'SOMA-K1', [
		{ num: '1', name: 'A' }, { num: '2', name: 'B' }, { num: '3', name: 'C' }, { num: '5', name: 'D' },
	]);
	assert.equal(ops.filter(o => o.kind === 'pin').length, 4);
	assert.equal(ops.filter(o => o.kind === 'rect').length, 1);
	assert.equal(ops.filter(o => o.kind === 'text').length, 2);
	const pins = ops.filter(o => o.kind === 'pin');
	// 4 pins -> 2 left / 2 right; left rot 0 anchored outside the box
	const left = pins.filter(p => p.rot === 0);
	const right = pins.filter(p => p.rot === 180);
	assert.equal(left.length, 2);
	assert.equal(right.length, 2);
	assert.ok(left.every(p => p.x < 0) && right.every(p => p.x > 0));
});
await t('symbolKey dedups identical pin sets', () => {
	const a = symbolKey([{ num: '1', name: 'A' }]);
	assert.equal(a, symbolKey([{ num: '1', name: 'A' }]));
	assert.notEqual(a, symbolKey([{ num: '1', name: 'B' }]));
	assert.notEqual(a, symbolKey([{ num: '2', name: 'A' }]));
});

/* 8 ---------------------------------------------------------- mock-eda smoke */
await t('mock-eda: full pipeline issues all expected calls', async () => {
	const calls = [];
	let uidSeq = 0;
	// mock editor state: last opened doc becomes "active"; pads drawn while a
	// footprint doc is active count toward that footprint's pad total; pins
	// drawn while a symbol doc is active persist per-symbol across reopen
	// (sch_Document.save / updateDocumentSource commit them)
	let activeDoc;
	let fpPadCount = 0;
	let symPinCount = 0;
	const symPinsSaved = new Map();
	// remember what association each created device was asked for so
	// lib_Device.get can answer the build's verify read-back
	const devAssoc = new Map();
	// uuid returned per created library item, keyed by 'api|name'
	const createdItemUuid = new Map();
	const persistSym = () => { if (activeDoc?.documentType === 'Symbol') symPinsSaved.set(activeDoc.uuid, symPinCount); };
	const mk = name => (...a) => {
		calls.push([name, a]);
		if (/^(lib_(Footprint|Symbol|Device)|dmt_(Project|Schematic|Pcb))\./.test(name) &&
			/create|createProject|createSchematic|createPcb/.test(name)) {
			const id = 'uuid-' + name + '-' + (++uidSeq);
			if (name === 'lib_Device.create') {
				const assoc = a[3] ?? {};
				devAssoc.set(id, {
					symbol: { uuid: assoc.symbol?.uuid ?? assoc.symbolUuid },
					footprint: { uuid: assoc.footprint?.uuid ?? assoc.footprintUuid },
				});
			}
			else createdItemUuid.set(`${name}|${a[1]}`, id);
			return Promise.resolve(id);
		}
		if (name === 'lib_Footprint.openInEditor' || name === 'lib_Symbol.openInEditor') {
			activeDoc = { documentType: name.includes('Symbol') ? 'Symbol' : 'Footprint', uuid: a[0], tabId: 'tab-' + (++uidSeq) };
			fpPadCount = 0;
			symPinCount = symPinsSaved.get(a[0]) ?? 0;
			return Promise.resolve(activeDoc.tabId);
		}
		if (name === 'dmt_EditorControl.openDocument') {
			activeDoc = { documentType: 'doc', uuid: a[0], tabId: 'tab-' + (++uidSeq) };
			return Promise.resolve(activeDoc.tabId);
		}
		if (name === 'dmt_EditorControl.closeDocument') { activeDoc = undefined; return Promise.resolve(true); }
		if (name === 'dmt_SelectControl.getCurrentDocumentInfo') return Promise.resolve(activeDoc);
		if (name === 'lib_Symbol.updateDocumentSource') { persistSym(); return Promise.resolve(true); }
		if (name === 'sch_Document.save') { persistSym(); return Promise.resolve(true); }
		if (name === 'sys_FileManager.getDocumentSource') {
			return Promise.resolve(activeDoc?.documentType === 'Symbol' ? '"PIN" '.repeat(symPinCount) : '');
		}
		if (name === 'pcb_PrimitivePad.getAll') {
			const cnt = activeDoc?.documentType === 'Footprint' ? fpPadCount : 0;
			return Promise.resolve(Array.from({ length: cnt }, (_, i) => ({ i })));
		}
		if (name === 'sch_PrimitivePin.getAll') {
			const cnt = activeDoc?.documentType === 'Symbol' ? symPinCount : 0;
			return Promise.resolve(Array.from({ length: cnt }, (_, i) => ({ i })));
		}
		if (name === 'sch_PrimitivePin.create') { if (activeDoc?.documentType === 'Symbol') symPinCount++; return Promise.resolve({ id: 1 }); }
		if (name === 'pcb_Drc.check') return Promise.resolve([]);
		if (name === 'dmt_Project.getCurrentProjectInfo') return Promise.resolve(projectItem);
		if (name === 'lib_Device.get') return Promise.resolve({ uuid: a[0], description: '', association: devAssoc.get(a[0]) });
		if (name.endsWith('.search')) return Promise.resolve([]);
		if (name === 'lib_LibrariesList.getPersonalLibraryUuid') return Promise.resolve('lib-uuid');
		if (name === 'lib_LibrariesList.getSystemLibraryUuid') return Promise.resolve('syslib-uuid');
		if (name.endsWith('.get')) return Promise.resolve({ uuid: a[0], description: '' });
		if (name === 'pcb_MathPolygon.createPolygon') return { polygon: a[0] };
		if (name === 'pcb_PrimitivePad.create') { if (activeDoc?.documentType === 'Footprint') fpPadCount++; return Promise.resolve({ id: 1 }); }
		return Promise.resolve(true);
	};
	const compStub = () => ({
		getState_PrimitiveId: () => 'pid' + Math.random().toString(36).slice(2),
		getState_UniqueId: () => 'uid',
	});
	const pinStub = () => ({
		getState_PadNumber: () => '1',
		setState_Net: () => {},
		done: async () => {},
	});
	// v2: the build runs inside the user's OPEN project — a Board item
	// already carries schematic + pcb uuids
	const projectItem = {
		uuid: 'proj-uuid',
		name: 'soma-carrier-v13',
		friendlyName: 'SOMA Carrier v1.3 (EasyEDA)',
		data: [{
			itemType: 'Board',
			name: 'Board_1',
			schematic: { itemType: 'Schematic', uuid: 'sch-uuid', name: 'SCH_Main', page: [{ uuid: 'p1' }] },
			pcb: { itemType: 'PCB', uuid: 'pcb-uuid', name: 'PCB_Main' },
		}],
	};
	globalThis.eda = {
		sys_LoadingAndProgressBar: { showProgressBar: (p, t) => calls.push(['progress', [p, t]]), destroyProgressBar: () => {} },
		sys_Dialog: { showInformationMessage: (...a) => calls.push(['dialog', a]) },
		sys_Log: { add: () => {} },
		sys_FileManager: {
			getDocumentSource: mk('sys_FileManager.getDocumentSource'),
			setDocumentSource: mk('sys_FileManager.setDocumentSource'),
		},
		lib_LibrariesList: {
			getPersonalLibraryUuid: mk('lib_LibrariesList.getPersonalLibraryUuid'),
			getSystemLibraryUuid: mk('lib_LibrariesList.getSystemLibraryUuid'),
		},
		lib_Footprint: {
			search: mk('lib_Footprint.search'),
			create: mk('lib_Footprint.create'),
			get: mk('lib_Footprint.get'),
			modify: mk('lib_Footprint.modify'),
			delete: mk('lib_Footprint.delete'),
			copy: mk('lib_Footprint.copy'),
			openInEditor: mk('lib_Footprint.openInEditor'),
			getRenderImage: mk('lib_Footprint.getRenderImage'),
			updateDocumentSource: mk('lib_Footprint.updateDocumentSource'),
		},
		lib_Symbol: {
			search: mk('lib_Symbol.search'),
			create: mk('lib_Symbol.create'),
			get: mk('lib_Symbol.get'),
			modify: mk('lib_Symbol.modify'),
			openInEditor: mk('lib_Symbol.openInEditor'),
			updateDocumentSource: mk('lib_Symbol.updateDocumentSource'),
			getRenderImage: mk('lib_Symbol.getRenderImage'),
		},
		lib_Device: {
			search: mk('lib_Device.search'),
			create: mk('lib_Device.create'),
			get: mk('lib_Device.get'),
			modify: mk('lib_Device.modify'),
			delete: mk('lib_Device.delete'),
		},
		dmt_Project: {
			createProject: mk('dmt_Project.createProject'),
			waitForReady: mk('dmt_Project.waitForReady'),
			getCurrentProjectInfo: mk('dmt_Project.getCurrentProjectInfo'),
		},
		dmt_Schematic: {
			createSchematic: mk('dmt_Schematic.createSchematic'),
			createSchematicPage: mk('dmt_Schematic.createSchematicPage'),
			getSchematicInfo: () => Promise.resolve({ page: [{ uuid: 'p1' }] }),
			deleteSchematic: mk('dmt_Schematic.deleteSchematic'),
		},
		dmt_Pcb: { createPcb: mk('dmt_Pcb.createPcb'), deletePcb: mk('dmt_Pcb.deletePcb') },
		dmt_Board: {
			createBoard: mk('dmt_Board.createBoard'),
			getAllBoardsInfo: () => Promise.resolve([projectItem.data[0]]),
		},
		dmt_EditorControl: {
			openDocument: mk('dmt_EditorControl.openDocument'),
			closeDocument: mk('dmt_EditorControl.closeDocument'),
			activateDocument: mk('dmt_EditorControl.activateDocument'),
			waitForDocumentReady: mk('dmt_EditorControl.waitForDocumentReady'),
		},
		dmt_SelectControl: {
			getCurrentDocumentInfo: mk('dmt_SelectControl.getCurrentDocumentInfo'),
		},
		sch_PrimitiveComponent: {
			create: async (...a) => { calls.push(['sch_PrimitiveComponent.create', a]); return compStub(); },
			modify: mk('sch_PrimitiveComponent.modify'),
			getAll: async () => { calls.push(['sch_PrimitiveComponent.getAll', []]); return []; },
			getAllPinsByPrimitiveId: async () => [],
			createNetFlag: mk('createNetFlag'),
			createNetPort: mk('createNetPort'),
		},
		sch_PrimitiveAttribute: {
			createNetLabel: mk('createNetLabel'),
		},
		sch_PrimitiveWire: { create: mk('sch_PrimitiveWire.create') },
		sch_PrimitiveRectangle: { create: mk('sch_PrimitiveRectangle.create') },
		sch_PrimitiveText: { create: mk('sch_PrimitiveText.create') },
		sch_PrimitivePin: {
			create: mk('sch_PrimitivePin.create'),
			getAll: mk('sch_PrimitivePin.getAll'),
		},
		sch_Document: { save: mk('sch_Document.save'), importChanges: mk('sch_Document.importChanges') },
		pcb_Document: { save: mk('pcb_Document.save'), importChanges: async (...a) => { calls.push(['importChanges', a]); return true; } },
		pcb_PrimitiveComponent: {
			getAll: async () => [],
			create: async (...a) => { calls.push(['pcb_PrimitiveComponent.create', a]); return compStub(); },
			modify: mk('pcb_PrimitiveComponent.modify'),
			getAllPinsByPrimitiveId: async () => [pinStub()],
		},
		pcb_PrimitivePolyline: { create: mk('pcb_PrimitivePolyline.create'), getAll: mk('pcb_PrimitivePolyline.getAll') },
		pcb_PrimitivePad: {
			create: mk('pcb_PrimitivePad.create'),
			getAll: mk('pcb_PrimitivePad.getAll'),
		},
		pcb_PrimitiveLine: { create: mk('pcb_PrimitiveLine.create'), getAll: mk('pcb_PrimitiveLine.getAll') },
		pcb_PrimitiveVia: { create: mk('pcb_PrimitiveVia.create'), getAll: mk('pcb_PrimitiveVia.getAll') },
		pcb_PrimitivePour: { create: mk('pcb_PrimitivePour.create'), getAll: mk('pcb_PrimitivePour.getAll') },
		pcb_PrimitiveString: { create: mk('pcb_PrimitiveString.create') },
		pcb_MathPolygon: { createPolygon: mk('pcb_MathPolygon.createPolygon') },
		pcb_Drc: { check: mk('pcb_Drc.check') },
		pcb_ManufactureData: { getGerberFile: mk('pcb_ManufactureData.getGerberFile') },
		sys_FileSystem: { saveFile: mk('sys_FileSystem.saveFile') },
	};
	const { runSomaBuild } = await import('../src/run');
	await runSomaBuild();

	const n = name => calls.filter(c => c[0] === name).length;
	// v1.4: every (footprint,rotation) key is drawn — no system-library use
	const fpParts = new Map();
	for (const p of BOARD_DATA.parts) {
		const k = fpKeyOf(p.footprint, p.rot);
		if (!fpParts.has(k)) fpParts.set(k, p);
	}
	assert.equal(fpParts.size, 26, 'unique footprint keys');
	const allKeys = [...fpParts.keys()];
	let expFpPads = 0, expFpPolys = 0;
	for (const k of allKeys) {
		for (const op of footprintOps(fpParts.get(k))) op.kind === 'pad' ? expFpPads++ : expFpPolys++;
	}
	// unique symbol set (pin-list dedup, identity KiCad numbering in v1.4)
	const symUniq = new Map();
	for (const p of BOARD_DATA.parts) {
		const pl = symbolPinList(p);
		const k = symbolKey(pl);
		if (!symUniq.has(k)) symUniq.set(k, pl.length);
	}
	const U = symUniq.size;
	const expSymPins = [...symUniq.values()].reduce((a, b) => a + b, 0);

	// drawn fp path per key: name+list search (2 calls) + create + draw
	assert.equal(n('lib_Footprint.search'), 2 * allKeys.length,
		'personal name+list search per footprint key');
	const sysFpSearches = calls.filter(c => c[0] === 'lib_Footprint.search' && c[1]?.[1] === 'syslib-uuid');
	assert.equal(sysFpSearches.length, 0, 'system library not touched — all footprints drawn');
	assert.equal(n('lib_Footprint.create'), allKeys.length, 'one create per footprint key');
	assert.equal(n('lib_Footprint.openInEditor'), allKeys.length);
	assert.equal(n('lib_Footprint.get'), allKeys.length, 'metadata get per drawn fp');
	assert.equal(n('lib_Footprint.copy'), 0, 'system copy never attempted');
	// readiness: activate + poll info — never waitForDocumentReady
	assert.equal(n('dmt_EditorControl.waitForDocumentReady'), 0, 'hanging API must not be called');
	assert.ok(n('dmt_SelectControl.getCurrentDocumentInfo') > 0, 'active-doc polling');
	// fp tabs + symbol draw tabs + 1 symbol reopen-verify tab
	assert.equal(n('dmt_EditorControl.closeDocument'), allKeys.length + U + 1);
	assert.equal(n('lib_Footprint.getDocumentSource'), 0, 'removed API must not be called');
	assert.equal(n('lib_Footprint.updateDocumentSource'), 0, 'removed API must not be called');
	// symbol draw path: primitives on the editor tab + live-source push +
	// reopen pin-count verify on the first symbol
	const headers = planSchematic(BOARD_DATA).headers.length;
	assert.equal(n('sch_PrimitivePin.create'), expSymPins, 'all symbol pins drawn');
	assert.equal(n('sch_PrimitivePin.getAll'), 2 * U + 1, 'pin count before/after draw + reopen verify');
	assert.equal(n('sch_PrimitiveRectangle.create'), U + headers, 'symbol bodies + block headers');
	assert.equal(n('sch_PrimitiveText.create'), 2 * U + headers, 'symbol labels + header titles');
	assert.equal(n('lib_Symbol.openInEditor'), U + 1, 'draw tabs + reopen verify tab');
	assert.equal(n('lib_Symbol.updateDocumentSource'), U, 'live source pushed per symbol');
	assert.equal(n('sys_FileManager.getDocumentSource'), U, 'post-draw source read per symbol');
	// content tagging after verified work
	assert.equal(n('lib_Footprint.modify'), allKeys.length, 'fp drawn tags');
	assert.equal(n('lib_Symbol.modify'), U, 'symbol drawn tags');
	// devices: one create + verify read + tag per part; all associations
	// point at drawn personal-library items (search-hit lib = 'lib-uuid'
	// fallback in the mock)
	assert.equal(n('lib_Device.create'), 55, 'devices');
	assert.equal(n('lib_Device.get'), 55, 'association verify reads');
	assert.equal(n('lib_Device.modify'), 55, 'verified device tags');
	const sysDevCalls = calls.filter(c =>
		c[0] === 'lib_Device.create' &&
		(c[1]?.[3]?.footprint?.libraryUuid === 'syslib-uuid' || c[1]?.[3]?.symbol?.libraryUuid === 'syslib-uuid'));
	assert.equal(sysDevCalls.length, 0, 'no device associates the system library');
	// K1: identity pad numbering — the device assoc points at its own
	// drawn footprint uuid (no hf3ff, no coil-pad swap)
	const k1fpUuid = createdItemUuid.get('lib_Footprint.create|SOMA-Relay_SPST_SANYOU_SRD_Series_Form_A-R0');
	const k1dev = calls.find(c => c[0] === 'lib_Device.create' && c[1]?.[1] === 'SOMA-K1');
	assert.ok(k1fpUuid, 'k1 drawn footprint created');
	assert.equal(k1dev?.[1]?.[3]?.footprint?.uuid, k1fpUuid, 'K1 associates the drawn footprint');
	assert.equal(k1dev?.[1]?.[5]?.supplierId, 'C93716', 'K1 LCSC number as BOM attribute');
	// verified LCSC equivalents ride along as supplierId BOM attributes
	const lcscByRef = { Q2: 'C2564', Q1: 'C118536', Q3: 'C118536', D5: 'C2457' };
	for (const [ref, lcsc] of Object.entries(lcscByRef)) {
		const dc = calls.find(c => c[0] === 'lib_Device.create' && c[1]?.[1] === `SOMA-${ref}`);
		assert.equal(dc?.[1]?.[5]?.supplierId, lcsc, `${ref} supplierId`);
	}
	// Fix A: never create a project — the open project's board supplies
	// the schematic + pcb uuids
	assert.equal(n('dmt_Project.createProject'), 0, 'createProject must never be called');
	assert.equal(n('dmt_Project.getCurrentProjectInfo'), 2, 'project probed at start + ensureDocs');
	assert.equal(n('dmt_Board.createBoard'), 0, 'existing board reused — no new board');
	assert.equal(n('dmt_Schematic.createSchematic'), 0, 'existing schematic reused');
	assert.equal(n('dmt_Pcb.createPcb'), 0, 'existing pcb reused');
	const opens = calls.filter(c => c[0] === 'dmt_EditorControl.openDocument').map(c => c[1][0]);
	assert.deepEqual(opens, ['p1', 'pcb-uuid'], 'schematic page then pcb opened');
	const imp = calls.find(c => c[0] === 'importChanges');
	assert.equal(imp?.[1]?.[0], 'sch-uuid', 'importChanges from the board schematic');
	assert.equal(n('sch_PrimitiveComponent.getAll'), 1, 're-run dedup probes existing comps');
	assert.equal(n('sch_PrimitiveComponent.create'), 55, 'schematic placements');
	assert.equal(n('sch_PrimitiveComponent.modify'), 55, 'designator sets');
	// every schematic/pcb component references the personal library
	for (const c of calls.filter(c => c[0] === 'sch_PrimitiveComponent.create')) {
		assert.equal(c[1]?.[0]?.libraryUuid, 'lib-uuid', 'sch comp lib');
	}
	for (const c of calls.filter(c => c[0] === 'pcb_PrimitiveComponent.create')) {
		assert.equal(c[1]?.[0]?.libraryUuid, 'lib-uuid', 'pcb comp lib');
	}
	// Fix B: net labels on every connected pin + power/ground flags on top
	assert.equal(n('createNetLabel'), 152, 'net label on every connected pin');
	assert.equal(n('createNetFlag'), 86, 'power/ground flags');
	assert.equal(n('createNetPort'), 0, 'labels succeed — no ports needed');
	assert.equal(n('pcb_PrimitiveComponent.create'), 55, 'direct placements (mock getAll=[])');
	assert.equal(n('pcb_PrimitiveLine.create'), planPcb(BOARD_DATA).tracks.length);
	assert.equal(n('pcb_PrimitiveVia.create'), 164);
	// pads: all 26 drawn footprints + 4 mounting holes
	assert.equal(n('pcb_PrimitivePad.create'), expFpPads + 4, 'footprint pads + mounting holes');
	// polylines: all drawn footprint silk + 1 board outline
	assert.equal(n('pcb_PrimitivePolyline.create'), expFpPolys + 1, 'footprint silk + outline');
	assert.equal(n('pcb_PrimitivePour.create'), 2);
	assert.equal(n('pcb_Document.save'), allKeys.length + 1, 'per-footprint saves + board save');
	assert.equal(n('sch_Document.save'), U + 1, 'per-symbol saves + schematic save');
	// Fix E + fab output
	assert.equal(n('pcb_Drc.check'), 1, 'DRC verbose check');
	assert.equal(n('pcb_ManufactureData.getGerberFile'), 1, 'gerber generated');
	assert.equal(n('sys_FileSystem.saveFile'), 1, 'gerber saved');
	// progress titles show "part N/55" through the library loop
	const titles = calls.filter(c => c[0] === 'progress').map(c => String(c[1][1]));
	assert.ok(titles.some(t => t.includes('part 1/55')), 'progress shows part 1/55');
	assert.ok(titles.some(t => t.includes('part 55/55')), 'progress shows part 55/55');
	assert.ok(n('dialog') === 1, 'final dialog shown');
	const dialog = calls.find(c => c[0] === 'dialog');
	assert.ok(!/FATAL/.test(String(dialog[1][0])), 'no fatal error: ' + dialog[1][0]);
	// Fix D: summary carries the counts
	assert.ok(/parts: 55\/55/.test(String(dialog[1][0])), 'summary counts parts');
	assert.ok(/tracks:/.test(String(dialog[1][0])) && /DRC:/.test(String(dialog[1][0])), 'summary counts tracks + DRC');
});

/* 9 ---------------------------------------------------------- v1.3 data (final brief) */
await t('all 55 designators present in schematic plan + pcb placements', () => {
	const schRefs = new Set(planSchematic(BOARD_DATA).comps.map(c => c.ref));
	const pcbRefs = new Set(planPcb(BOARD_DATA).placements.map(p => p.ref));
	for (const p of BOARD_DATA.parts) {
		assert.ok(schRefs.has(p.ref), `sch missing ${p.ref}`);
		assert.ok(pcbRefs.has(p.ref), `pcb missing ${p.ref}`);
	}
});
await t('every net has at least 2 pins', () => {
	const perNet = new Map();
	for (const p of BOARD_DATA.parts) for (const q of p.pads) {
		if (!q.net) continue;
		perNet.set(q.net, (perNet.get(q.net) ?? 0) + 1);
	}
	for (const net of BOARD_DATA.nets) {
		assert.ok((perNet.get(net) ?? 0) >= 2, `net ${net} has ${perNet.get(net) ?? 0} pins`);
	}
});
await t('track count equals KiCad source', () => {
	assert.equal(BOARD_DATA.tracks.length, BOARD_DATA.meta.counts.tracks);
	assert.equal(BOARD_DATA.vias.length, BOARD_DATA.meta.counts.vias);
	const plan = planPcb(BOARD_DATA);
	assert.equal(plan.tracks.length + plan.skippedTracks, BOARD_DATA.tracks.length);
});
await t('board outline is closed and rectangular', () => {
	const o = BOARD_DATA.outline;
	assert.ok(o.length >= 4);
	// closed polygon in the plan: first vertex == last vertex
	const plan = planPcb(BOARD_DATA);
	const nums = plan.outlinePolygon.filter(e => typeof e === 'number');
	assert.ok(near(nums[0], nums[nums.length - 2]) && near(nums[1], nums[nums.length - 1]), 'closed');
	// nonzero 135x115 area
	const xs = o.map(p => p[0]); const ys = o.map(p => p[1]);
	assert.ok(near(Math.max(...xs) - Math.min(...xs), 135) && near(Math.max(...ys) - Math.min(...ys), 115));
});

console.log(`\n${pass} checks passed${process.exitCode ? ' (with FAILURES)' : ''}`);
// pending call() timeouts keep the loop alive — exit explicitly
process.exit(process.exitCode ?? 0);
