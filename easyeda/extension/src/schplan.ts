/*
 * Pure schematic-layout planner — no `eda` calls, fully unit-testable.
 *
 * Produces, for every part: symbol placement (x,y in schematic units),
 * the position/direction of every pin, and for every connected pin a
 * wire stub plus the net-flag / net-port to hang on its end.
 *
 * Schematic units are the same as symbol sources: 10 mil grid
 * (PIN_PITCH 10 etc. — see eda-source.ts).
 */

import type { BoardData, PartData } from './board-data-types';
import { BLOCKS, GROUND_NETS, PARTS, POWER_NETS } from './parts-table';
import { symbolLayout } from './eda-source';

export const STUB_LEN = 24;
const COL_W = 300;
const BLOCK_GAP = 90;
const SLOT_V = 46;          // vertical padding per component slot
const MAX_COL_H = 900;
const ORIGIN_X = 200;
const ORIGIN_Y = 200;

export type PinNetKind = 'power' | 'ground' | 'signal' | 'nc';

export interface SchPin {
	num: string;
	x: number; y: number;       // connection point
	dir: -1 | 1;                // outward direction
	net: string;
	kind: PinNetKind;
	stubEndX: number; stubEndY: number;
}

export interface SchComp {
	ref: string;
	value: string;
	cx: number; cy: number;     // symbol centre
	w: number; h: number;
	pins: SchPin[];
}

export interface SchBlockBox {
	title: string;
	x: number; y: number; w: number; h: number;
}

export interface SchPlan {
	comps: SchComp[];
	headers: SchBlockBox[];
	wires: Array<[number, number, number, number]>;
	labels: Array<{ x: number; y: number; net: string; kind: PinNetKind }>;
}

export function pinKind(net: string): PinNetKind {
	if (!net) return 'nc';
	if (GROUND_NETS.has(net)) return 'ground';
	if (POWER_NETS.has(net)) return 'power';
	return 'signal';
}

export function symbolPins(part: PartData): string[] {
	return part.pads.filter(p => p.type !== 'np_thru_hole').map(p => p.num)
		.sort((a, b) => {
			const na = parseInt(a, 10); const nb = parseInt(b, 10);
			if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
			return a < b ? -1 : 1;
		});
}

export function planSchematic(data: BoardData): SchPlan {
	const comps: SchComp[] = [];
	const headers: SchBlockBox[] = [];
	const wires: Array<[number, number, number, number]> = [];
	const labels: SchPlan['labels'] = [];
	const byRef = new Map(data.parts.map(p => [p.ref, p]));

	let colX = ORIGIN_X;
	for (const block of BLOCKS) {
		const blockRefs = Object.keys(PARTS).filter(r => PARTS[r].block === block.id && byRef.has(r));
		if (blockRefs.length === 0) continue;
		const startX = colX;
		let curY = ORIGIN_Y;
		let colMaxY = ORIGIN_Y;
		let blockCols = 0;
		for (const ref of blockRefs) {
			const part = byRef.get(ref)!;
			const pinNums = symbolPins(part);
			const { L, H, left, right } = symbolLayout(pinNums.length, pinNums);
			const slotH = H + SLOT_V;
			if (curY + slotH > ORIGIN_Y + MAX_COL_H && curY > ORIGIN_Y) {
				colX += COL_W;
				blockCols++;
				curY = ORIGIN_Y;
			}
			const cy = curY + slotH / 2;
			const pins: SchPin[] = [];
			const padNet = new Map(part.pads.map(p => [p.num, p.net]));
			const yTop = -H / 2 + 10;
			left.forEach((n, i) => {
				const x = colX - 60; const y = cy + yTop + i * 10;
				const net = padNet.get(n) ?? '';
				const kind = pinKind(net);
				pins.push({ num: n, x, y, dir: -1, net, kind, stubEndX: x - STUB_LEN, stubEndY: y });
			});
			right.forEach((n, j) => {
				const x = colX + 60; const y = cy - yTop - j * 10;
				const net = padNet.get(n) ?? '';
				const kind = pinKind(net);
				pins.push({ num: n, x, y, dir: 1, net, kind, stubEndX: x + STUB_LEN, stubEndY: y });
			});
			comps.push({ ref, value: part.value, cx: colX, cy, w: 120, h: H, pins });
			curY += slotH;
			if (curY > colMaxY) colMaxY = curY;
		}
		const blockW = (blockCols + 1) * COL_W;
		headers.push({
			title: block.title,
			x: startX - 140, y: ORIGIN_Y - 60,
			w: blockW - 40, h: colMaxY - ORIGIN_Y + 90,
		});
		colX += blockW + BLOCK_GAP;
	}
	for (const c of comps) {
		for (const p of c.pins) {
			if (p.kind === 'nc') continue;
			wires.push([p.x, p.y, p.stubEndX, p.stubEndY]);
			labels.push({ x: p.stubEndX, y: p.stubEndY, net: p.net, kind: p.kind });
		}
	}
	return { comps, headers, wires, labels };
}
