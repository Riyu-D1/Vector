/*
 * Coordinate transforms between the KiCad board frame and EasyEDA Pro.
 *
 * KiCad:    millimetres, +X right, +Y down, rotations CCW.
 * EasyEDA:  PCB documents store coordinates in mil (see CANVAS record and
 *           the pro-api docs "数据单位为 mil"), +X right, +Y UP (right-up
 *           positive — "右上方为 XY 的正方向").
 *
 * So every board point maps as (x, -y) * MIL_PER_MM and every rotation
 * angle maps as -deg.  The single FLIP_Y switch disables the mirror in
 * case a future EDA version changes the convention — see README.
 */

export const MIL_PER_MM = 1000 / 25.4;   // 39.3700787...

export const FLIP_Y = true;

export function mm2mil(v: number): number {
	const r = Math.round(v * MIL_PER_MM * 1000) / 1000;
	return r === 0 ? 0 : r;   // normalise -0
}

export function px(x: number): number {
	return mm2mil(x);
}

export function py(y: number): number {
	const r = FLIP_Y ? -mm2mil(y) : mm2mil(y);
	return r === 0 ? 0 : r;   // normalise -0
}

export function prot(deg: number): number {
	const r = (FLIP_Y ? -deg : deg) % 360;
	return r < 0 ? r + 360 : r;
}

/** Convert a KiCad mm polygon [[x,y],...] to an EDA mil source array:
 *  [x0,y0,'L', x1,y1, x2,y2, ...] — 'L' after the first vertex, then the
 *  vertex run, matching real dataStr polygons.  A 'L' must always be
 *  followed by >=2 numbers or the app rejects the polygon. */
export function polygonSource(pts: number[][]): Array<'L' | number> {
	const out: Array<'L' | number> = [];
	for (let i = 0; i < pts.length; i++) {
		if (i === 1) out.push('L');
		out.push(px(pts[i][0]), py(pts[i][1]));
	}
	return out;
}
