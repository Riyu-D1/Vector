/*
 * Pure planner that turns a part's pin set into ordered primitive ops for
 * the symbol-editor tab: sch_PrimitivePin for pins, sch_PrimitiveRectangle
 * for the body box, sch_PrimitiveText for the name/designator labels.
 *
 * Replaces the lib_Symbol.updateDocumentSource write: in 3.2.209 the live
 * document is the segmented DOCHEAD format, so the "1.0"-doctype line
 * grammar we generated was accepted (returned true) but silently dropped —
 * the symbol stayed empty.  Drawing primitives on the open symbol tab is
 * the documented route: api-types.d.ts marks sch_PrimitivePin as
 * symbol-editor-only, and the bundled examples draw exactly this way.
 *
 * Symbol-editor units are the schematic grid (10 mil) — the same units the
 * old 1.0 grammar and schplan.ts use, so the geometry is shared verbatim.
 */

import { symbolLayout, type SymbolPin } from './eda-source';
import { PARTS } from './parts-table';
import { symbolPins } from './schplan';
import type { PartData } from './board-data-types';

export const SYM_PIN_LEN = 10;
const BOX_HALF_W = 50;

export interface SymPinOp {
	kind: 'pin';
	num: string;
	name: string;
	x: number; y: number;          // connection-point (outer) end, 10mil
	rot: number;                   // 0: body extends +x (left pins), 180: -x (right pins)
	len: number;
}

export interface SymRectOp {
	kind: 'rect';
	x: number; y: number;          // top-left corner (min x, max y — SCH frame is +Y up)
	w: number; h: number;
}

export interface SymTextOp {
	kind: 'text';
	x: number; y: number;
	s: string;
}

export type SymOp = SymPinOp | SymRectOp | SymTextOp;

function pinOrder(a: string, b: string): number {
	const na = parseInt(a, 10); const nb = parseInt(b, 10);
	if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
	return a < b ? -1 : a > b ? 1 : 0;
}

/** The {num,name} pin list a symbol must carry for `part`, in fp-domain
 *  numbering (system footprint numbering for sys matches — identical to
 *  the list buildLibrary feeds the schematic/plan). */
export function symbolPinList(part: PartData, pm?: Record<string, string>): SymbolPin[] {
	const spec = PARTS[part.ref];
	const netOf = new Map(part.pads.map(p => [p.num, p.net]));
	const nameOf = (kicadNum: string) =>
		spec?.pinNames?.[kicadNum] ?? (netOf.get(kicadNum) || 'NC');
	const mapped = pm
		? { ...part, pads: part.pads.map(p => ({ ...p, num: pm[p.num] ?? p.num })) }
		: part;
	const inv = pm ? new Map(Object.entries(pm).map(([k, v]) => [v, k])) : undefined;
	return symbolPins(mapped).map(n => {
		const orig = inv?.get(n) ?? n;
		return { num: n, name: nameOf(orig) };
	});
}

/** Deduplication key — parts with an identical fp-domain pin set share one
 *  library symbol (same rule the orchestrator applies). */
export function symbolKey(pinList: SymbolPin[]): string {
	return JSON.stringify(pinList);
}

/** Ordered ops: pins first, then the body rectangle, then label texts. */
export function symbolOps(designatorPrefix: string, symName: string, pins: SymbolPin[]): SymOp[] {
	const ordered = pins.map(p => p.num).sort(pinOrder);
	const byNum = new Map(pins.map(p => [p.num, p]));
	const { H, left, right } = symbolLayout(pins.length, ordered);
	const ops: SymOp[] = [];
	const yTop = -H / 2 + 10;
	left.forEach((n, i) => ops.push({
		kind: 'pin', num: n, name: byNum.get(n)?.name ?? n,
		x: -BOX_HALF_W - SYM_PIN_LEN, y: yTop + i * 10, rot: 0, len: SYM_PIN_LEN,
	}));
	right.forEach((n, j) => ops.push({
		kind: 'pin', num: n, name: byNum.get(n)?.name ?? n,
		x: BOX_HALF_W + SYM_PIN_LEN, y: -yTop - j * 10, rot: 180, len: SYM_PIN_LEN,
	}));
	ops.push({ kind: 'rect', x: -BOX_HALF_W, y: H / 2, w: 2 * BOX_HALF_W, h: H });
	ops.push({ kind: 'text', x: -BOX_HALF_W, y: H / 2 + 12, s: symName });
	ops.push({ kind: 'text', x: -BOX_HALF_W, y: -H / 2 - 12, s: `${designatorPrefix}?` });
	return ops;
}
