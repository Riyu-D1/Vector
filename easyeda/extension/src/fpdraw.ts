/*
 * Pure planner that turns a part's footprint geometry (extractor data,
 * KiCad frame) into a list of EasyEDA primitive-create operations that can
 * be executed inside an open footprint-editor tab via pcb_PrimitivePad /
 * pcb_PrimitivePolyline.
 *
 * Replaces the old updateDocumentSource path: in EasyEDA Pro 3.2.209 the
 * extension-API handler map has no LIB_Footprint.getDocumentSource
 * (calls hang forever) and updateDocumentSource only accepts the segmented
 * 3.0 wire format — drawing primitives on an open footprint tab is the
 * documented, robust route.
 *
 * Footprint-editor coordinates are the same convention as PCB documents:
 * mil, +Y up — coords.ts applies FLIP_Y consistently.
 */

import { polygonSource, prot, px, py } from './coords';
import type { PartData } from './board-data-types';

export const FP_LAYER = {
	TOP_CU: 1,
	TOP_SILK: 3,
	MULTI: 12,
} as const;

export type PadShape = 'ELLIPSE' | 'RECT' | 'OVAL';

export interface FpPadOp {
	kind: 'pad';
	layer: number;                    // 12 multi (thru) | 1 top (smd)
	num: string;
	x: number; y: number;             // mil
	rot: number;
	shape: [PadShape, number, number];
	hole: ['ROUND' | 'SLOT', number, number] | null;
	plated: boolean;                  // metallization flag
}

export interface FpPolyOp {
	kind: 'poly';
	layer: number;                    // 3 silk | 48 courtyard
	pts: Array<'L' | number>;         // polygon source for pcb_MathPolygon
	w: number;                        // stroke width (mil)
}

export type FpOp = FpPadOp | FpPolyOp;

function padShape(pad: PartData['pads'][number]): PadShape {
	if (pad.shape === 'circle') return 'ELLIPSE';
	if (pad.shape === 'rect' || pad.shape === 'roundrect') return 'RECT';
	return 'OVAL';
}

function circlePoly(cx: number, cy: number, r: number, seg = 16): Array<'L' | number> {
	const pts: number[][] = [];
	for (let i = 0; i <= seg; i++) {
		const a = (i / seg) * Math.PI * 2;
		pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
	}
	return polygonSource(pts);
}

/** Ordered ops: pads first, then silk polylines. */
export function footprintOps(part: PartData): FpOp[] {
	const ops: FpOp[] = [];

	for (const pad of part.pads) {
		if (pad.type === 'np_thru_hole') continue;   // board-level NPTH, not in footprint
		const x = px(pad.lx); const y = py(pad.ly);
		const smd = pad.type === 'smd';
		ops.push({
			kind: 'pad',
			layer: smd ? FP_LAYER.TOP_CU : FP_LAYER.MULTI,
			num: pad.num,
			x, y,
			// pad.rot is absolute (component rot + pad local rot); inside the
			// footprint doc the component rotation is already baked into lx/ly
			rot: prot(pad.rot - part.rot),
			shape: [padShape(pad), px(pad.w), px(pad.h)],
			hole: smd ? null
				: pad.drillOval
					? ['SLOT', px(pad.drillX), px(pad.drillY)]
					: ['ROUND', px(pad.drillX), px(pad.drillX)],
			plated: !smd,
		});
	}

	for (const s of part.silk) {
		const w = px(s.w) || 6;
		if (s.k === 'l') {
			ops.push({ kind: 'poly', layer: FP_LAYER.TOP_SILK, w,
				pts: [px(s.x1!), py(s.y1!), 'L', px(s.x2!), py(s.y2!)] });
		}
		else if (s.k === 'c') {
			ops.push({ kind: 'poly', layer: FP_LAYER.TOP_SILK, w,
				pts: circlePoly(s.x!, s.y!, s.r!) });
		}
		else if (s.k === 'a' || s.k === 'p') {
			const pts = s.pts ?? [];
			if (pts.length >= 2) {
				ops.push({ kind: 'poly', layer: FP_LAYER.TOP_SILK, w, pts: polygonSource(pts) });
			}
		}
	}

	// No courtyard polyline: layer 48 (component shape) is not creatable via
	// the primitive API (TPCB_LayersOfLine tops out at DRILL_DRAWING).
	return ops;
}
