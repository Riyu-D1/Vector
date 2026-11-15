/*
 * Generator for EasyEDA Pro SYMBOL document source used with
 * eda.lib_Symbol.updateDocumentSource.
 *
 * The grammar was extracted from the app-bundled system library
 * (easyeda-std.elib, docType 2 SYMBOL "1.0") — see easyeda/_research.
 * Symbols go through loadDocJsonByUuidAndPath which accepts this stored
 * ("1.0"-doctype) format directly.
 *
 * (Footprints are intentionally NOT generated as document source:
 *  v3.2.209 has no LIB_Footprint.getDocumentSource handler and
 *  updateDocumentSource only accepts the segmented 3.0 wire format.
 *  Footprints are drawn on an open footprint-editor tab via
 *  pcb_PrimitivePad/pcb_PrimitivePolyline — see fpdraw.ts + run.ts.)
 */

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
