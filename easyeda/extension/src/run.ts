/*
 * Orchestrates the SOMA Carrier v1.3 rebuild inside EasyEDA Pro 3.2.
 *
 * Pipeline:
 *   1. generate symbols + footprints in the personal library
 *      (sources produced by eda-source.ts from extractor data)
 *   2. create project + schematic + pcb + board link
 *   3. place schematic components, wire stubs + net flags/ports
 *   4. importChanges into PCB, position components, draw outline,
 *      mounting holes, replicated tracks, vias and GND pours
 *   5. save both documents and report a summary
 *
 * Everything that can fail without aborting the build is collected in
 * `warnings` and shown in the final dialog.
 */

import { BOARD_DATA } from './board-data';
import { footprintSource, symbolSource } from './eda-source';
import { PARTS } from './parts-table';
import { LAYER, planPcb } from './pcbplan';
import { planSchematic, STUB_LEN, symbolPins } from './schplan';
import type { PartData } from './board-data-types';

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

/* Ambient enum values from the bundled v3.2 API — used as literals so the
 * bundle never references enum objects that may not exist at runtime. */
const LIB_DEVICE = '3' as ELIB_LibraryType.DEVICE;
const PAD_ELLIPSE = 'ELLIPSE' as EPCB_PrimitivePadShapeType.ELLIPSE;
const HOLE_ROUND = 'ROUND' as EPCB_PrimitivePadHoleType.ROUND;
const POUR_SOLID = 'solid' as EPCB_PrimitivePourFillMethod.SOLID;
const ALIGN_LEFT_TOP = 1 as EPCB_PrimitiveStringAlignMode.LEFT_TOP;

const warnings: string[] = [];
const info: string[] = [];

function report(p: number, title: string): void {
	try { eda.sys_LoadingAndProgressBar.showProgressBar(p, title); } catch { /* noop */ }
}

function designatorPrefix(ref: string): string {
	if (ref.startsWith('DS')) return 'TP';
	if (ref === 'IR1') return 'J';
	if (ref === 'BZ1') return 'BZ';
	const m = /^[A-Z]+/.exec(ref);
	return m ? m[0] : 'U';
}

function partPinNames(part: PartData): Map<string, string> {
	const spec = PARTS[part.ref];
	const m = new Map<string, string>();
	for (const pad of part.pads) {
		if (pad.type === 'np_thru_hole') continue;
		m.set(pad.num, spec?.pinNames?.[pad.num] ?? (pad.net || 'NC'));
	}
	return m;
}

/* ---------------- library generation ---------------- */

async function buildLibrary(libUuid: string): Promise<{
	devices: Map<string, { uuid: string; fpUuid: string }>;
	fpCount: number; symCount: number;
}> {
	const devices = new Map<string, { uuid: string; fpUuid: string }>();
	// footprints deduplicated by (footprint type, rotation) — identical
	// baked geometry produces identical source
	const fpByKey = new Map<string, string>();
	const symByKey = new Map<string, string>();
	const parts = BOARD_DATA.parts;
	let done = 0;
	for (const part of parts) {
		report(2 + Math.round(20 * done / parts.length), `Library ${part.ref}`);
		done++;
		try {
			const fpKey = `${part.footprint}@${part.rot}`;
			const fpName = `SOMA-${part.footprint}-R${part.rot}`;
			let fpUuid = fpByKey.get(fpKey);
			if (!fpUuid) {
				const fpSrc = footprintSource(fpName, designatorPrefix(part.ref), part);
				fpUuid = await eda.lib_Footprint.create(libUuid, fpName);
				if (!fpUuid) throw new Error('footprint create returned no uuid');
				const tpl = await eda.lib_Footprint.getDocumentSource(fpUuid, libUuid);
				const src = tpl?.startsWith('["DOCTYPE","FOOTPRINT","')
					? fpSrc.replace(/\["DOCTYPE","FOOTPRINT","[^"]*"\]/, tpl.split('\n')[0])
					: fpSrc;
				const ok = await eda.lib_Footprint.updateDocumentSource(fpUuid, libUuid, src);
				if (ok === false) warnings.push(`${part.ref}: footprint updateDocumentSource returned false`);
				fpByKey.set(fpKey, fpUuid);
			}
			const pinNames = partPinNames(part);
			const pins = symbolPins(part).map(n => ({ num: n, name: pinNames.get(n) ?? n }));
			const symKey = JSON.stringify(pins);
			let symUuid = symByKey.get(symKey);
			if (!symUuid) {
				const symSrc = symbolSource(`SOMA-${part.ref}`, designatorPrefix(part.ref), pins);
				symUuid = await eda.lib_Symbol.create(libUuid, `SOMA-${part.ref}`);
				if (!symUuid) throw new Error('symbol create returned no uuid');
				const tpl = await eda.lib_Symbol.getDocumentSource(symUuid, libUuid);
				const src = tpl?.startsWith('["DOCTYPE","SYMBOL","')
					? symSrc.replace(/\["DOCTYPE","SYMBOL","[^"]*"\]/, tpl.split('\n')[0])
					: symSrc;
				const ok = await eda.lib_Symbol.updateDocumentSource(symUuid, libUuid, src);
				if (ok === false) warnings.push(`${part.ref}: symbol updateDocumentSource returned false`);
				symByKey.set(symKey, symUuid);
			}
			const devUuid = await eda.lib_Device.create(libUuid, `SOMA-${part.ref}`, undefined, {
				symbol: { uuid: symUuid, libraryUuid: libUuid },
				footprint: { uuid: fpUuid, libraryUuid: libUuid },
			});
			if (!devUuid) throw new Error('device create returned no uuid');
			devices.set(part.ref, { uuid: devUuid, fpUuid });
		}
		catch (err) {
			warnings.push(`${part.ref}: library build failed — ${String(err)}`);
		}
	}
	info.push(`library: ${fpByKey.size} footprints, ${symByKey.size} symbols, ${devices.size} devices`);
	return { devices, fpCount: fpByKey.size, symCount: symByKey.size };
}

/* ---------------- schematic ---------------- */

async function buildSchematic(
	devices: Map<string, { uuid: string; fpUuid: string }>,
	libUuid: string,
): Promise<Map<string, string>> {
	const plan = planSchematic(BOARD_DATA);
	const uniqueIds = new Map<string, string>();
	// measured pin positions override the plan (defence against symbol
	// origin assumptions)
	const realPins = new Map<string, Map<string, { x: number; y: number; dir: -1 | 1 }>>();
	let i = 0;
	for (const c of plan.comps) {
		report(25 + Math.round(22 * i / plan.comps.length), `Schematic ${c.ref}`);
		i++;
		const dev = devices.get(c.ref);
		if (!dev) { warnings.push(`${c.ref}: skipped — no device`); continue; }
		try {
			const comp = await eda.sch_PrimitiveComponent.create(
				{ libraryType: LIB_DEVICE, libraryUuid: libUuid, uuid: dev.uuid },
				c.cx, c.cy, undefined, 0, false, true, true,
			);
			if (!comp) { warnings.push(`${c.ref}: sch create returned undefined`); continue; }
			const pid = comp.getState_PrimitiveId?.();
			if (pid) {
				await eda.sch_PrimitiveComponent.modify(pid, { designator: c.ref, name: c.value });
				try {
					const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId?.(pid);
					if (pins?.length) {
						const m = new Map<string, { x: number; y: number; dir: -1 | 1 }>();
						for (const pin of pins) {
							const num = pin.getState_PinNumber?.();
							const x = pin.getState_X?.();
							const y = pin.getState_Y?.();
							const rot = pin.getState_Rotation?.() ?? 0;
							if (num !== undefined && x !== undefined && y !== undefined) {
								// pin rot 0 points +x (into the box) -> stub extends -x
								m.set(String(num), { x, y, dir: rot === 180 ? 1 : -1 });
							}
						}
						realPins.set(c.ref, m);
					}
				}
				catch { /* pin measurement optional */ }
			}
			const uid = comp.getState_UniqueId?.();
			if (uid) uniqueIds.set(c.ref, uid);
		}
		catch (err) {
			warnings.push(`${c.ref}: schematic place failed — ${String(err)}`);
		}
	}
	for (const c of plan.comps) {
		for (const p of c.pins) {
			if (p.kind === 'nc') continue;
			try {
				const real = realPins.get(c.ref)?.get(p.num);
				const px0 = real?.x ?? p.x;
				const py0 = real?.y ?? p.y;
				const dir = real?.dir ?? p.dir;
				const ex = px0 + dir * STUB_LEN;
				// stub carries the net name itself — connectivity survives even
				// if the netflag/netport decoration fails
				await eda.sch_PrimitiveWire.create([px0, py0, ex, py0], p.net);
				if (p.kind === 'ground') {
					await eda.sch_PrimitiveComponent.createNetFlag('Ground', p.net, ex, py0);
				}
				else if (p.kind === 'power') {
					await eda.sch_PrimitiveComponent.createNetFlag('Power', p.net, ex, py0);
				}
				else {
					await eda.sch_PrimitiveComponent.createNetPort('BI', p.net, ex, py0, dir === -1 ? 180 : 0);
				}
			}
			catch (err) {
				warnings.push(`${c.ref}.${p.num}: stub/label failed — ${String(err)}`);
			}
		}
	}
	for (const h of plan.headers) {
		try {
			await eda.sch_PrimitiveRectangle.create(h.x, h.y, h.w, h.h, 0, 0, '#888888');
			await eda.sch_PrimitiveText.create(h.x + 10, h.y + 14, h.title, 0, '#000000', undefined, 12, true);
		}
		catch { /* cosmetic */ }
	}
	return uniqueIds;
}

/* ---------------- PCB ---------------- */

async function buildPcb(
	uniqueIds: Map<string, string>,
	libUuid: string,
	devices: Map<string, { uuid: string; fpUuid: string }>,
): Promise<void> {
	const plan = planPcb(BOARD_DATA);

	try {
		const comps = await eda.pcb_PrimitiveComponent.getAll();
		const wanted = new Map(plan.placements.map(p => [p.ref, p]));
		for (const comp of comps) {
			const d = comp.getState_Designator();
			if (!d) continue;
			const pl = wanted.get(d);
			if (!pl) continue;
			wanted.delete(d);
			try {
				comp.setState_X(pl.x);
				comp.setState_Y(pl.y);
				if (comp.setState_Rotation) comp.setState_Rotation(pl.rot);
				if (comp.setState_Layer) comp.setState_Layer(pl.layer as TPCB_LayersOfComponent);
				await comp.done();
			}
			catch (err) { warnings.push(`${d}: move failed — ${String(err)}`); }
		}
		for (const [ref, pl] of wanted) {
			const part = BOARD_DATA.parts.find(pp => pp.ref === ref);
			const dev = devices.get(ref);
			if (!part || !dev) { warnings.push(`${ref}: missing after importChanges and no device — not placed`); continue; }
			warnings.push(`${ref}: missing after importChanges — creating directly`);
			try {
				const comp = await eda.pcb_PrimitiveComponent.create(
					{ libraryType: '4' as ELIB_LibraryType.FOOTPRINT, libraryUuid: libUuid, uuid: dev.fpUuid },
					pl.layer as TPCB_LayersOfComponent, pl.x, pl.y, 0, false,
				);
				const pid = comp?.getState_PrimitiveId?.();
				if (pid) {
					await eda.pcb_PrimitiveComponent.modify(pid, {
						designator: ref, name: part.value,
						uniqueId: uniqueIds.get(ref) ?? null,
					});
					const pins = await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId?.(pid) ?? [];
					const netByNum = new Map(part.pads.map(p => [p.num, p.net]));
					for (const pin of pins) {
						const num = pin.getState_PadNumber?.();
						const net = num ? netByNum.get(String(num)) : undefined;
						if (net) {
							try { (pin as IPCB_PrimitivePad).setState_Net(net); await (pin as IPCB_PrimitivePad).done?.(); }
							catch { /* ratsnest may show these pads unconnected */ }
						}
					}
				}
			}
			catch (err) { warnings.push(`${ref}: direct create failed — ${String(err)}`); }
		}
	}
	catch (err) {
		warnings.push(`component placement failed — ${String(err)}`);
	}

	// board outline
	try {
		const poly = eda.pcb_MathPolygon.createPolygon(plan.outlinePolygon);
		await eda.pcb_PrimitivePolyline.create('', LAYER.BOARD_OUTLINE, poly as IPCB_Polygon, plan.outlineWidth);
	}
	catch (err) {
		warnings.push(`outline failed — ${String(err)}`);
	}

	for (const h of plan.holes) {
		try {
			await eda.pcb_PrimitivePad.create(LAYER.MULTI, '', h.x, h.y, 0,
				[PAD_ELLIPSE, h.size, h.size], '',
				[HOLE_ROUND, h.drill], 0, 0, 0, false);
		}
		catch (err) { warnings.push(`mounting hole at ${h.x},${h.y} — ${String(err)}`); }
	}

	let terr = 0;
	for (let k = 0; k < plan.tracks.length; k++) {
		const t = plan.tracks[k];
		try {
			await eda.pcb_PrimitiveLine.create(t.net, t.layer as TPCB_LayersOfLine, t.x1, t.y1, t.x2, t.y2, t.w);
		}
		catch { terr++; }
		if (k % 50 === 49) {
			report(55 + Math.round(30 * (k + 1) / plan.tracks.length), `Tracks ${k + 1}/${plan.tracks.length}`);
			await sleep(0);
		}
	}
	info.push(`tracks placed: ${plan.tracks.length - terr}/${plan.tracks.length} (${terr} failed, ${plan.skippedTracks} degenerate skipped)`);
	if (terr) warnings.push(`${terr} track segments failed to create`);

	for (const v of plan.vias) {
		try {
			await eda.pcb_PrimitiveVia.create(v.net, v.x, v.y, v.drill, v.size);
		}
		catch (err) { warnings.push(`via ${v.net} @${v.x},${v.y} — ${String(err)}`); }
	}

	for (const zn of plan.pours) {
		try {
			const poly = eda.pcb_MathPolygon.createPolygon(zn.polygon);
			await eda.pcb_PrimitivePour.create(zn.net, zn.layer as TPCB_LayersOfCopper,
				poly as IPCB_Polygon, POUR_SOLID);
		}
		catch (err) { warnings.push(`pour ${zn.net} layer ${zn.layer} — ${String(err)}`); }
	}

	for (const t of plan.texts) {
		try {
			await eda.pcb_PrimitiveString.create(t.layer as TPCB_LayersOfImage, t.x, t.y, t.text,
				'default', t.h, 8, ALIGN_LEFT_TOP, t.rot, false, 0, false, false);
		}
		catch { /* cosmetic */ }
	}
}

/* ---------------- entry ---------------- */

export async function runSomaBuild(): Promise<void> {
	warnings.length = 0;
	info.length = 0;
	const started = Date.now();
	report(1, 'SOMA v1.3: starting');
	try {
		const T = <X>(pr: Promise<X>, ms = 6000): Promise<X | undefined> =>
			Promise.race([pr.catch(() => undefined), new Promise<undefined>((r) => setTimeout(() => r(undefined), ms))]);
		const diag: string[] = [];
		let ws: any;
		try { ws = await T((eda as any).dmt_Workspace.getCurrentWorkspaceInfo()); } catch { ws = undefined; }
		diag.push('workspace=' + (ws ? (ws.name || ws.uuid) : 'timeout/none'));
		report(1, 'Finding library: personal');
		let libUuid: string | undefined = await T(eda.lib_LibrariesList.getPersonalLibraryUuid());
		let libSrc = 'personal';
		diag.push('personal=' + (libUuid || 'none'));
		let libList: Array<{ name: string; uuid: string }> = [];
		if (!libUuid) {
			report(1, 'Finding library: list');
			libList = (await T(eda.lib_LibrariesList.getAllLibrariesList())) || [];
			const sys = await T(eda.lib_LibrariesList.getSystemLibraryUuid(), 3000);
			diag.push('others=' + (libList.map((l) => l.name).join('|') || 'none'));
			const pick = libList.find((l) => l && l.uuid && l.uuid !== sys);
			if (pick) { libUuid = pick.uuid; libSrc = 'library "' + pick.name + '"'; }
		}
		if (!libUuid) {
			report(1, 'Finding library: project');
			libUuid = await T(eda.lib_LibrariesList.getProjectLibraryUuid());
			libSrc = 'project library';
			diag.push('project=' + (libUuid || 'none'));
		}
		if (!libUuid) {
			eda.sys_Dialog.showInformationMessage('No writable library found. ' + diag.join('; '), 'SOMA Carrier v1.3');
			try { eda.sys_LoadingAndProgressBar.destroyProgressBar(); } catch { /* noop */ }
			return;
		}
		info.push('Using ' + libSrc + ' (' + diag.join('; ') + ')');
		report(2, 'Library: ' + libSrc + ' - building parts');
		const { devices } = await buildLibrary(libUuid);
		if (devices.size === 0) throw new Error('no devices could be created');

		report(23, 'Creating project');
		const projectUuid = await eda.dmt_Project.createProject('SOMA Carrier v1.3 (EasyEDA)');
		if (!projectUuid) throw new Error('createProject failed');
		await eda.dmt_Project.waitForReady(projectUuid, 15000);
		await sleep(800);

		const schUuid = await eda.dmt_Schematic.createSchematic('SOMA Carrier v1.3');
		if (!schUuid) throw new Error('createSchematic failed');
		await sleep(1500);
		try {
			const infoSch = await eda.dmt_Schematic.getSchematicInfo(schUuid);
			const pageUuid = infoSch?.page?.[0]?.uuid;
			if (pageUuid) await eda.dmt_EditorControl.openDocument(pageUuid);
		}
		catch { /* schematic likely already open */ }
		await sleep(500);

		const uniqueIds = await buildSchematic(devices, libUuid);
		try { await eda.sch_Document.save(); } catch { warnings.push('schematic save returned an error'); }
		report(48, 'Schematic saved');

		const pcbUuid = await eda.dmt_Pcb.createPcb('SOMA Carrier v1.3');
		if (!pcbUuid) throw new Error('createPcb failed');
		await sleep(1500);
		await eda.dmt_Board.createBoard(schUuid, pcbUuid);
		await sleep(800);
		await eda.dmt_EditorControl.openDocument(pcbUuid);
		await sleep(800);
		report(50, 'Importing to PCB');
		const imported = await eda.pcb_Document.importChanges(schUuid, true);
		if (!imported) warnings.push('importChanges returned false — components may be missing');
		await sleep(800);

		await buildPcb(uniqueIds, libUuid, devices);
		report(93, 'Saving PCB');
		try { await eda.pcb_Document.save(); } catch { warnings.push('pcb save returned an error'); }
	}
	catch (err) {
		warnings.push(`FATAL: ${String(err)}`);
	}
	finally {
		try { eda.sys_LoadingAndProgressBar.destroyProgressBar(); } catch { /* noop */ }
	}
	const secs = Math.round((Date.now() - started) / 1000);
	const msg = [
		`SOMA Carrier v1.3 rebuild finished in ${secs}s.`,
		'',
		...info.map(s => `• ${s}`),
		warnings.length ? `${warnings.length} warnings:` : 'No warnings.',
		...warnings.slice(0, 30).map(s => `• ${s}`),
		warnings.length > 30 ? `• … and ${warnings.length - 30} more` : '',
		'',
		'See REPORT_EASYEDA.md for verification notes and known gaps.',
	].filter(s => s !== '').join('\n');
	eda.sys_Dialog.showInformationMessage(msg, 'SOMA Carrier v1.3');
}
