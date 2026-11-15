/*
 * Pure PCB-build planner — converts the extracted KiCad board data into
 * the exact argument lists for the EasyEDA primitive APIs. No `eda`
 * calls here so the whole plan is unit-testable in node.
 *
 * All outputs are already in EDA board units (mil, +Y up via coords.ts).
 */

import { polygonSource, prot, px, py } from './coords';
import type { BoardData } from './board-data-types';

export const LAYER = {
	TOP: 1,
	BOTTOM: 2,
	TOP_SILK: 3,
	BOARD_OUTLINE: 11,
	MULTI: 12,
} as const;

export function edaLayer(kicadLayer: string): number {
	if (kicadLayer === 'F.Cu') return LAYER.TOP;
	if (kicadLayer === 'B.Cu') return LAYER.BOTTOM;
	if (kicadLayer === 'F.SilkS') return LAYER.TOP_SILK;
	if (kicadLayer === 'B.SilkS') return 4;
	if (kicadLayer === 'Edge.Cuts') return LAYER.BOARD_OUTLINE;
	return LAYER.TOP;
}

export interface PlacementOp { ref: string; x: number; y: number; rot: number; layer: number }
export interface LineOp { net: string; layer: number; x1: number; y1: number; x2: number; y2: number; w: number }
export interface ViaOp { net: string; x: number; y: number; drill: number; size: number }
export interface PourOp { net: string; layer: number; polygon: Array<'L' | number> }
export interface HoleOp { x: number; y: number; drill: number; size: number }
export interface TextOp { text: string; layer: number; x: number; y: number; rot: number; h: number }

export interface PcbPlan {
	placements: PlacementOp[];
	outlinePolygon: Array<'L' | number>;
	outlineWidth: number;
	holes: HoleOp[];
	tracks: LineOp[];
	vias: ViaOp[];
	pours: PourOp[];
	texts: TextOp[];
	skippedTracks: number;
}

export function planPcb(data: BoardData): PcbPlan {
	const placements: PlacementOp[] = data.parts.map(p => ({
		ref: p.ref,
		x: px(p.x), y: py(p.y), rot: 0,
		layer: p.side === 'B' ? LAYER.BOTTOM : LAYER.TOP,
	}));

	// outline: rectangle -> closed polygon (repeat first point)
	const o = data.outline;
	let outlinePolygon: Array<'L' | number> = [];
	if (o.length === 4) {
		const pts = [...o, o[0]];
		outlinePolygon = polygonSource(pts);
	}

	const holes: HoleOp[] = data.mountingHoles.map(h => ({
		x: px(h.x), y: py(h.y), drill: px(h.drill), size: px(Math.max(h.size, h.drill)),
	}));

	let skippedTracks = 0;
	const tracks: LineOp[] = [];
	for (const t of data.tracks) {
		if (t.x1 === t.x2 && t.y1 === t.y2) { skippedTracks++; continue; }
		tracks.push({
			net: t.net, layer: edaLayer(t.layer),
			x1: px(t.x1), y1: py(t.y1), x2: px(t.x2), y2: py(t.y2),
			w: px(t.w),
		});
	}

	const vias: ViaOp[] = data.vias.map(v => ({
		net: v.net, x: px(v.x), y: py(v.y),
		drill: px(v.drill), size: px(v.size),
	}));

	const pours: PourOp[] = data.zones.map(z => ({
		net: z.net || 'GND',
		layer: edaLayer(z.layer),
		polygon: polygonSource([...z.pts, z.pts[0]]),
	}));

	const texts: TextOp[] = data.silkText.map(t => ({
		text: t.text, layer: edaLayer(t.layer),
		x: px(t.x), y: py(t.y), rot: prot(t.rot), h: px(t.h),
	}));

	return {
		placements, outlinePolygon, outlineWidth: 4,
		holes, tracks, vias, pours, texts, skippedTracks,
	};
}
