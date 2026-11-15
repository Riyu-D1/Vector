/* Types for the extractor output embedded in board-data.ts.
 * All coordinates are in the KiCad board frame: millimetres, +X right,
 * +Y down, rotations CCW. See coords.ts for the EasyEDA conversion.
 */

export interface PadData {
	num: string;
	type: 'thru_hole' | 'smd' | 'np_thru_hole' | string;
	shape: string;                    // circle | rect | oval | roundrect | custom
	net: string;                      // '' = unconnected
	ax: number; ay: number;           // absolute board position (mm)
	lx: number; ly: number;           // local, component rotation already applied
	rot: number;                      // absolute pad rotation (KiCad frame)
	w: number; h: number;             // copper size (mm)
	drillX: number; drillY: number;   // drill (mm)
	drillOval: boolean;
	layers: string[];
}

export interface SilkItem {
	k: 'l' | 'c' | 'a' | 'p';
	x1?: number; y1?: number; x2?: number; y2?: number;
	x?: number; y?: number; r?: number;
	pts?: number[][];
	ax1?: number; ay1?: number; ax2?: number; ay2?: number;
	ax?: number; ay?: number;
	apts?: number[][];
	w: number;
}

export interface PartData {
	ref: string;
	value: string;
	footprint: string;
	x: number; y: number; rot: number;
	side: 'F' | 'B';
	pads: PadData[];
	silk: SilkItem[];
}

export interface TrackData {
	net: string; layer: string;
	x1: number; y1: number; x2: number; y2: number; w: number;
}

export interface ViaData {
	net: string; x: number; y: number; drill: number; size: number;
}

export interface ZoneData {
	net: string; layer: string; pts: number[][];
}

export interface HoleData {
	x: number; y: number; drill: number; size: number;
}

export interface SilkTextData {
	text: string; x: number; y: number; rot: number;
	layer: string; h: number;
}

export interface BoardData {
	meta: {
		source: string;
		kicadVersion: string;
		generated: string;
		counts: Record<string, number>;
	};
	outline: number[][];
	mountingHoles: HoleData[];
	zones: ZoneData[];
	nets: string[];
	parts: PartData[];
	tracks: TrackData[];
	vias: ViaData[];
	silkText: SilkTextData[];
}
