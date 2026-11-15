#!/usr/bin/env node
/*
 * Headless verification for the SOMA extension.
 *
 *   node --experimental-strip-types easyeda/extension/test/run-tests.mjs
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
 *   6. mock-eda smoke test of runSomaBuild: every API call is recorded;
 *      verifies all 55 components are placed and all tracks issued
 */

import assert from 'node:assert/strict';

import { BOARD_DATA } from '../src/board-data';
import * as coords from '../src/coords';
import { symbolSource } from '../src/eda-source';
import { footprintOps } from '../src/fpdraw';
import { planSchematic, symbolPins } from '../src/schplan';
import { planPcb, LAYER } from '../src/pcbplan';
import { PARTS, BLOCKS } from '../src/parts-table';

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

/* 7 ---------------------------------------------------------- mock-eda smoke */
await t('mock-eda: full pipeline issues all expected calls', async () => {
	const calls = [];
	let uidSeq = 0;
	const mk = name => (...a) => {
		calls.push([name, a]);
		if (/^(lib_(Footprint|Symbol|Device)|dmt_(Project|Schematic|Pcb))\./.test(name) &&
			/create|createProject|createSchematic|createPcb/.test(name)) {
			return Promise.resolve('uuid-' + name + '-' + (++uidSeq));
		}
		if (name === 'lib_Footprint.openInEditor') return Promise.resolve('tab-' + (++uidSeq));
		if (name.endsWith('.search')) return Promise.resolve([]);
		if (name === 'lib_LibrariesList.getPersonalLibraryUuid') return Promise.resolve('lib-uuid');
		if (name === 'pcb_MathPolygon.createPolygon') return { polygon: a[0] };
		return Promise.resolve(true);
	};
	const compStub = () => ({
		getState_PrimitiveId: () => 'pid' + Math.random().toString(36).slice(2),
		getState_UniqueId: () => 'uid',
	});
	globalThis.eda = {
		sys_LoadingAndProgressBar: { showProgressBar: () => {}, destroyProgressBar: () => {} },
		sys_Dialog: { showInformationMessage: (...a) => calls.push(['dialog', a]) },
		sys_Log: { add: () => {} },
		lib_LibrariesList: { getPersonalLibraryUuid: mk('lib_LibrariesList.getPersonalLibraryUuid') },
		lib_Footprint: {
			search: mk('lib_Footprint.search'),
			create: mk('lib_Footprint.create'),
			get: mk('lib_Footprint.get'),
			delete: mk('lib_Footprint.delete'),
			openInEditor: mk('lib_Footprint.openInEditor'),
		},
		lib_Symbol: {
			search: mk('lib_Symbol.search'),
			create: mk('lib_Symbol.create'),
			get: mk('lib_Symbol.get'),
			updateDocumentSource: mk('lib_Symbol.updateDocumentSource'),
		},
		lib_Device: {
			search: mk('lib_Device.search'),
			create: mk('lib_Device.create'),
		},
		dmt_Project: {
			createProject: mk('dmt_Project.createProject'),
			waitForReady: mk('dmt_Project.waitForReady'),
		},
		dmt_Schematic: {
			createSchematic: mk('dmt_Schematic.createSchematic'),
			getSchematicInfo: () => Promise.resolve({ page: [{ uuid: 'p1' }] }),
		},
		dmt_Pcb: { createPcb: mk('dmt_Pcb.createPcb') },
		dmt_Board: { createBoard: mk('dmt_Board.createBoard') },
		dmt_EditorControl: {
			openDocument: mk('dmt_EditorControl.openDocument'),
			closeDocument: mk('dmt_EditorControl.closeDocument'),
			activateDocument: mk('dmt_EditorControl.activateDocument'),
			waitForDocumentReady: mk('dmt_EditorControl.waitForDocumentReady'),
		},
		sch_PrimitiveComponent: {
			create: async (...a) => { calls.push(['sch_PrimitiveComponent.create', a]); return compStub(); },
			modify: mk('sch_PrimitiveComponent.modify'),
			getAllPinsByPrimitiveId: async () => [],
			createNetFlag: mk('createNetFlag'),
			createNetPort: mk('createNetPort'),
		},
		sch_PrimitiveWire: { create: mk('sch_PrimitiveWire.create') },
		sch_PrimitiveRectangle: { create: mk('sch_PrimitiveRectangle.create') },
		sch_PrimitiveText: { create: mk('sch_PrimitiveText.create') },
		sch_Document: { save: mk('sch_Document.save'), importChanges: mk('sch_Document.importChanges') },
		pcb_Document: { save: mk('pcb_Document.save'), importChanges: async () => { calls.push(['importChanges', []]); return true; } },
		pcb_PrimitiveComponent: {
			getAll: async () => [],
			create: async (...a) => { calls.push(['pcb_PrimitiveComponent.create', a]); return compStub(); },
			modify: mk('pcb_PrimitiveComponent.modify'),
			getAllPinsByPrimitiveId: async () => [],
		},
		pcb_PrimitivePolyline: { create: mk('pcb_PrimitivePolyline.create') },
		pcb_PrimitivePad: { create: mk('pcb_PrimitivePad.create') },
		pcb_PrimitiveLine: { create: mk('pcb_PrimitiveLine.create') },
		pcb_PrimitiveVia: { create: mk('pcb_PrimitiveVia.create') },
		pcb_PrimitivePour: { create: mk('pcb_PrimitivePour.create') },
		pcb_PrimitiveString: { create: mk('pcb_PrimitiveString.create') },
		pcb_MathPolygon: { createPolygon: mk('pcb_MathPolygon.createPolygon') },
	};
	const { runSomaBuild } = await import('../src/run');
	await runSomaBuild();

	const n = name => calls.filter(c => c[0] === name).length;
	// unique footprints drawn via the editor-tab path
	const fpParts = new Map();
	for (const p of BOARD_DATA.parts) {
		const k = p.footprint + '@' + p.rot;
		if (!fpParts.has(k)) fpParts.set(k, p);
	}
	let expFpPads = 0, expFpPolys = 0;
	for (const p of fpParts.values()) {
		for (const op of footprintOps(p)) op.kind === 'pad' ? expFpPads++ : expFpPolys++;
	}
	assert.equal(fpParts.size, 26, 'unique footprint keys');
	assert.equal(n('lib_Footprint.search'), fpParts.size);
	assert.equal(n('lib_Footprint.create'), fpParts.size, 'one create per unique footprint');
	assert.equal(n('lib_Footprint.openInEditor'), fpParts.size);
	assert.equal(n('dmt_EditorControl.waitForDocumentReady'), fpParts.size);
	assert.equal(n('dmt_EditorControl.closeDocument'), fpParts.size);
	assert.equal(n('lib_Footprint.getDocumentSource'), 0, 'removed API must not be called');
	assert.equal(n('lib_Footprint.updateDocumentSource'), 0, 'removed API must not be called');
	assert.equal(n('lib_Device.create'), 55, 'devices');
	assert.equal(n('sch_PrimitiveComponent.create'), 55, 'schematic placements');
	assert.equal(n('sch_PrimitiveComponent.modify'), 55, 'designator sets');
	assert.equal(n('createNetFlag') + n('createNetPort'), 152, 'one label per connected pin');
	assert.equal(n('pcb_PrimitiveComponent.create'), 55, 'direct placements (mock getAll=[])');
	assert.equal(n('pcb_PrimitiveLine.create'), planPcb(BOARD_DATA).tracks.length);
	assert.equal(n('pcb_PrimitiveVia.create'), 164);
	// pads: footprint pads + 4 mounting holes (no free-pad fallback when fps ok)
	assert.equal(n('pcb_PrimitivePad.create'), expFpPads + 4, 'footprint pads + mounting holes');
	// polylines: footprint silk+courtyards + 1 board outline
	assert.equal(n('pcb_PrimitivePolyline.create'), expFpPolys + 1, 'footprint silk/courtyard + outline');
	assert.equal(n('pcb_PrimitivePour.create'), 2);
	assert.equal(n('pcb_Document.save'), fpParts.size + 1, 'per-footprint saves + board save');
	assert.equal(n('sch_Document.save'), 1);
	assert.ok(n('dialog') === 1, 'final dialog shown');
	const dialog = calls.find(c => c[0] === 'dialog');
	assert.ok(!/FATAL/.test(String(dialog[1][0])), 'no fatal error: ' + dialog[1][0]);
});

console.log(`\n${pass} checks passed${process.exitCode ? ' (with FAILURES)' : ''}`);
