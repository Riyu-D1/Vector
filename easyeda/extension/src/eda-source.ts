/*
 * Generators for EasyEDA Pro "document source" payloads used with
 * eda.lib_Symbol.updateDocumentSource / eda.lib_Footprint.updateDocumentSource.
 *
 * The grammar was extracted from the app-bundled system library
 * (easyeda-std.elib, docType 2 SYMBOL "1.0" / docType 4 FOOTPRINT "1.3")
 * — see easyeda/_research.  If the created library item reports a newer
 * DOCTYPE version we reuse its own DOCTYPE line verbatim.
 *
 * Coordinates inside these sources are mil, +Y up — identical convention
 * to PCB document sources.  All inputs are in the KiCad frame and pass
 * through coords.ts so FLIP_Y applies to everything consistently.
 */

import { prot, px, py } from './coords';
import type { PartData, SilkItem } from './board-data-types';

export interface SymbolPin {
	num: string;
	name: string;
}

/* ------------------------------------------------------------------ *
 *  SYMBOL source  (DOCTYPE "SYMBOL" "1.0")
 * ------------------------------------------------------------------ */

const PIN_LEN = 10;
const PIN_PITCH = 10;
const BOX_HALF_W = 50;

/**
 * DIP-style pin arrangement: pins sorted by number (numeric when
 * possible); first half go on the left top->bottom, rest on the right
 * bottom->top.
 */
export function symbolLayout(pinCount: number, pinNums: string[]) {
	const L = Math.ceil(pinCount / 2);
	const H = Math.max(1, L - 1) * PIN_PITCH + 20;      // box height
	const left = pinNums.slice(0, L);
	const right = pinNums.slice(L);
	return { L, H, left, right };
}

function pinSort(nums: string[]): string[] {
	return [...nums].sort((a, b) => {
		const na = parseInt(a, 10); const nb = parseInt(b, 10);
		if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
		return a < b ? -1 : a > b ? 1 : 0;
	});
}

export function symbolSource(symName: string, designatorPrefix: string, pins: SymbolPin[]): string {
	const ordered = pinSort(pins.map(p => p.num));
	const { L, H, left, right } = symbolLayout(pins.length, ordered);
	const byNum = new Map(pins.map(p => [p.num, p]));
	const lines: string[] = [];
	let e = 0;
	const nid = () => `e${++e}`;

	lines.push('["DOCTYPE","SYMBOL","1.0"]');
	lines.push('["HEAD",{"symbolType":2,"originX":0,"originY":0,"version":"3.2.209.8a704eab"}]');
	lines.push('["LINESTYLE","st1",null,null,null,null]');
	lines.push('["FONTSTYLE","st2",null,null,null,null,null,null,null,null,null,0]');
	lines.push('["FONTSTYLE","st3",null,null,null,null,0,0,0,0,2,0]');
	lines.push('["FONTSTYLE","st4",null,null,null,null,0,0,0,0,2,2]');
	lines.push(`["PART","${symName}.1",{"BBOX":[${-BOX_HALF_W - PIN_LEN - 10},${-H / 2 - 8},${BOX_HALF_W + PIN_LEN + 10},${H / 2 + 8}]}]`);
	lines.push(`["ATTR","${nid()}","","Symbol","${symName}",false,false,null,null,0,"st2",0]`);
	lines.push(`["ATTR","${nid()}","","Designator","${designatorPrefix}?",false,false,null,null,0,"st2",0]`);

	const emitPin = (num: string, x: number, y: number, rot: number) => {
		const p = byNum.get(num);
		const pname = (p?.name ?? num).replace(/"/g, '');
		const pid = nid();
		lines.push(`["PIN","${pid}",1,1,${x},${y},${PIN_LEN},${rot},null,0,0,1]`);
		lines.push(`["ATTR","${nid()}","${pid}","NAME","${pname}",false,false,null,null,0,"st3",0]`);
		lines.push(`["ATTR","${nid()}","${pid}","NUMBER","${num}",false,false,null,null,0,"st4",0]`);
		lines.push(`["ATTR","${nid()}","${pid}","Pin Type","IN",false,false,null,null,0,"st2",0]`);
	};
	const yTop = -H / 2 + 10;
	left.forEach((n, i) => emitPin(n, -BOX_HALF_W - PIN_LEN, yTop + i * PIN_PITCH, 0));
	right.forEach((n, j) => emitPin(n, BOX_HALF_W + PIN_LEN, -yTop - j * PIN_PITCH, 180));

	// box outline
	const bx1 = -BOX_HALF_W; const bx2 = BOX_HALF_W; const by1 = -H / 2; const by2 = H / 2;
	lines.push(`["POLY","${nid()}",[${bx1},${by1},${bx1},${by2}],0,"st1",0]`);
	lines.push(`["POLY","${nid()}",[${bx1},${by2},${bx2},${by2}],0,"st1",0]`);
	lines.push(`["POLY","${nid()}",[${bx2},${by2},${bx2},${by1}],0,"st1",0]`);
	lines.push(`["POLY","${nid()}",[${bx2},${by1},${bx1},${by1}],0,"st1",0]`);
	return lines.join('\n');
}

/* ------------------------------------------------------------------ *
 *  FOOTPRINT source  (DOCTYPE "FOOTPRINT" "1.3")
 * ------------------------------------------------------------------ */

const LAYER_TOP_SILK = 3;
const LAYER_COURTYARD = 48;
const LAYER_TOP_CU = 1;
const LAYER_MULTI = 12;

function padRecord(eid: string, part: PartData, pad: PartData['pads'][number]): string {
	const x = px(pad.lx); const y = py(pad.ly); const rot = prot(pad.rot);
	if (pad.type === 'smd') {
		const shape = pad.shape === 'circle' ? 'ELLIPSE'
			: pad.shape === 'oval' ? 'OVAL' : 'RECT';
		return `["PAD","${eid}",0,"",${LAYER_TOP_CU},"${pad.num}",${x},${y},${rot},null,["${shape}",${px(pad.w)},${px(pad.h)}],[],0,0,0,1,0,2,2,0,0,0]`;
	}
	// thru-hole on multi layer
	const shape = pad.shape === 'circle' ? 'ELLIPSE'
		: pad.shape === 'rect' || pad.shape === 'roundrect' ? 'RECT' : 'OVAL';
	const hole = pad.drillOval
		? `["SLOT",${px(pad.drillX)},${px(pad.drillY)}]`
		: `["ROUND",${px(pad.drillX)},${px(pad.drillY)}]`;
	return `["PAD","${eid}",0,"",${LAYER_MULTI},"${pad.num}",${x},${y},${rot},${hole},["${shape}",${px(pad.w)},${px(pad.h)}],[],0,0,0,1,0,2,2,0,0,0]`;
}

function silkRecords(part: PartData, nid: () => string): { lines: string[]; min: number[]; max: number[] } {
	const lines: string[] = [];
	const min = [Infinity, Infinity];
	const max = [-Infinity, -Infinity];
	const grow = (x: number, y: number) => {
		if (x < min[0]) min[0] = x;
		if (y < min[1]) min[1] = y;
		if (x > max[0]) max[0] = x;
		if (y > max[1]) max[1] = y;
	};
	for (const p of part.pads) { grow(p.lx - p.w / 2, p.ly - p.h / 2); grow(p.lx + p.w / 2, p.ly + p.h / 2); }
	for (const s of part.silk) {
		const w = px(s.w) || 6;
		if (s.k === 'l') {
			lines.push(`["POLY","${nid()}",0,"",${LAYER_TOP_SILK},${w},[${px(s.x1!)},${py(s.y1!)},"L",${px(s.x2!)},${py(s.y2!)}],0]`);
			grow(s.x1!, s.y1!); grow(s.x2!, s.y2!);
		}
		else if (s.k === 'c') {
			lines.push(`["POLY","${nid()}",0,"",${LAYER_TOP_SILK},${w},["CIRCLE",${px(s.x!)},${py(s.y!)},${px(s.r!)}],0]`);
			grow(s.x! - s.r!, s.y! - s.r!); grow(s.x! + s.r!, s.y! + s.r!);
		}
		else if (s.k === 'a' || s.k === 'p') {
			const pts = s.pts ?? [];
			if (pts.length >= 2) {
				const segs = pts.map(q => `${px(q[0])},${py(q[1])}`).join(',"L",');
				lines.push(`["POLY","${nid()}",0,"",${LAYER_TOP_SILK},${w},[${segs}],0]`);
				for (const q of pts) grow(q[0], q[1]);
			}
		}
	}
	return { lines, min, max };
}

export function footprintSource(fpName: string, designatorPrefix: string, part: PartData): string {
	const lines: string[] = [];
	let e = 0;
	const nid = () => `e${++e}`;

	lines.push('["DOCTYPE","FOOTPRINT","1.3"]');
	lines.push('["CANVAS",0,0,"mil",5,5,5,5,5,5,2]');
	lines.push('["ACTIVE_LAYER",1]');
	for (const pad of part.pads) {
		if (pad.type === 'np_thru_hole') continue; // handled as board-level NPTH
		lines.push(padRecord(nid(), part, pad));
	}
	const { lines: sl, min, max } = silkRecords(part, nid);
	lines.push(...sl);
	if (Number.isFinite(min[0])) {
		const cx1 = px(min[0]) - 15; const cy1 = py(max[1]) - 15;
		const cx2 = px(max[0]) + 15; const cy2 = py(min[1]) + 15;
		lines.push(`["POLY","${nid()}",0,"",${LAYER_COURTYARD},2,[${cx1},${cy1},"L",${cx1},${cy2},"L",${cx2},${cy2},"L",${cx2},${cy1},"L",${cx1},${cy1}],0]`);
	}
	lines.push(`["ATTR","${nid()}",0,"",${LAYER_TOP_SILK},null,null,"Footprint","${fpName}",0,0,"default",45,6,0,0,3,0,0,0,0,0]`);
	lines.push(`["ATTR","${nid()}",0,"",${LAYER_TOP_SILK},null,null,"Designator","${designatorPrefix}?",0,0,"default",45,6,0,0,3,0,0,0,0,0]`);
	return lines.join('\n');
}
