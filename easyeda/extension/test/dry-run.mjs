#!/usr/bin/env node
/*
 * Dry-run of the full SOMA v1.3 build against a mocked `eda` API.
 * Prints the counts the real run would issue — verify the pipeline end
 * to end without EasyEDA.  Bundle first (same as run-tests):
 *
 *   ../_research/easyeda-api-sdk/node_modules/.bin/esbuild \
 *     easyeda/extension/test/dry-run.mjs --bundle --format=esm \
 *     --platform=node --outfile=/tmp/dry-run.bundle.mjs
 *   node /tmp/dry-run.bundle.mjs
 */

import { BOARD_DATA } from '../src/board-data.ts';
import { fpKeyOf } from '../src/syslib-match.ts';
import { symbolKey, symbolPinList } from '../src/symdraw.ts';

const calls = [];
const n = name => calls.filter(c => c[0] === name).length;
let uidSeq = 0;

let activeDoc;
let fpPadCount = 0;
let symPinCount = 0;
const symPinsSaved = new Map();
const devAssoc = new Map();
const persistSym = () => { if (activeDoc?.documentType === 'Symbol') symPinsSaved.set(activeDoc.uuid, symPinCount); };

const projectItem = {
	uuid: 'proj-uuid', name: 'soma-carrier-v13', friendlyName: 'SOMA Carrier v1.3 (EasyEDA)',
	data: [{
		itemType: 'Board', name: 'Board_1',
		schematic: { itemType: 'Schematic', uuid: 'sch-uuid', name: 'SCH_Main', page: [{ uuid: 'p1' }] },
		pcb: { itemType: 'PCB', uuid: 'pcb-uuid', name: 'PCB_Main' },
	}],
};

const mk = name => (...a) => {
	calls.push([name, a]);
	if (/^(lib_(Footprint|Symbol|Device)|dmt_(Project|Schematic|Pcb|Board))\./.test(name) && /create/i.test(name)) {
		const id = 'uuid-' + (++uidSeq);
		if (name === 'lib_Device.create') {
			const assoc = a[3] ?? {};
			devAssoc.set(id, {
				symbol: { uuid: assoc.symbol?.uuid ?? assoc.symbolUuid },
				footprint: { uuid: assoc.footprint?.uuid ?? assoc.footprintUuid },
			});
		}
		return Promise.resolve(id);
	}
	if (name === 'lib_Footprint.openInEditor' || name === 'lib_Symbol.openInEditor') {
		activeDoc = { documentType: name.includes('Symbol') ? 'Symbol' : 'Footprint', uuid: a[0], tabId: 'tab-' + (++uidSeq) };
		fpPadCount = 0;
		symPinCount = symPinsSaved.get(a[0]) ?? 0;
		return Promise.resolve(activeDoc.tabId);
	}
	if (name === 'dmt_EditorControl.openDocument') {
		activeDoc = { documentType: 'doc', uuid: a[0], tabId: 'tab-' + (++uidSeq) };
		return Promise.resolve(activeDoc.tabId);
	}
	if (name === 'dmt_EditorControl.closeDocument') { activeDoc = undefined; return Promise.resolve(true); }
	if (name === 'dmt_SelectControl.getCurrentDocumentInfo') return Promise.resolve(activeDoc);
	if (name === 'dmt_Project.getCurrentProjectInfo') return Promise.resolve(projectItem);
	if (name === 'lib_Symbol.updateDocumentSource') { persistSym(); return Promise.resolve(true); }
	if (name === 'sch_Document.save') { persistSym(); return Promise.resolve(true); }
	if (name === 'sys_FileManager.getDocumentSource') {
		return Promise.resolve(activeDoc?.documentType === 'Symbol' ? '"PIN" '.repeat(symPinCount) : '');
	}
	if (name === 'pcb_PrimitivePad.getAll') {
		return Promise.resolve(Array.from({ length: activeDoc?.documentType === 'Footprint' ? fpPadCount : 0 }));
	}
	if (name === 'sch_PrimitivePin.getAll') {
		return Promise.resolve(Array.from({ length: activeDoc?.documentType === 'Symbol' ? symPinCount : 0 }));
	}
	if (name === 'sch_PrimitivePin.create') { if (activeDoc?.documentType === 'Symbol') symPinCount++; return Promise.resolve({ id: 1 }); }
	if (name === 'pcb_PrimitivePad.create') { if (activeDoc?.documentType === 'Footprint') fpPadCount++; return Promise.resolve({ id: 1 }); }
	if (name === 'lib_Device.get') return Promise.resolve({ uuid: a[0], description: '', association: devAssoc.get(a[0]) });
	if (name.endsWith('.search')) return Promise.resolve([]);
	if (name === 'lib_LibrariesList.getPersonalLibraryUuid') return Promise.resolve('lib-uuid');
	if (name === 'lib_LibrariesList.getSystemLibraryUuid') return Promise.resolve('syslib-uuid');
	if (name.endsWith('.get')) return Promise.resolve({ uuid: a[0], description: '' });
	if (name === 'pcb_MathPolygon.createPolygon') return { polygon: a[0] };
	if (name === 'pcb_Drc.check') return Promise.resolve([]);
	return Promise.resolve(true);
};

const compStub = () => ({
	getState_PrimitiveId: () => 'pid' + Math.random().toString(36).slice(2),
	getState_UniqueId: () => 'uid-' + (++uidSeq),
});

globalThis.eda = {
	sys_LoadingAndProgressBar: { showProgressBar: () => {}, destroyProgressBar: () => {} },
	sys_Dialog: { showInformationMessage: (...a) => calls.push(['dialog', a]) },
	sys_Log: { add: () => {} },
	sys_FileManager: {
		getDocumentSource: mk('sys_FileManager.getDocumentSource'),
		setDocumentSource: mk('sys_FileManager.setDocumentSource'),
	},
	sys_FileSystem: { saveFile: mk('sys_FileSystem.saveFile') },
	lib_LibrariesList: {
		getPersonalLibraryUuid: mk('lib_LibrariesList.getPersonalLibraryUuid'),
		getSystemLibraryUuid: mk('lib_LibrariesList.getSystemLibraryUuid'),
	},
	lib_Footprint: {
		search: mk('lib_Footprint.search'), create: mk('lib_Footprint.create'),
		get: mk('lib_Footprint.get'), modify: mk('lib_Footprint.modify'),
		openInEditor: mk('lib_Footprint.openInEditor'),
	},
	lib_Symbol: {
		search: mk('lib_Symbol.search'), create: mk('lib_Symbol.create'),
		get: mk('lib_Symbol.get'), modify: mk('lib_Symbol.modify'),
		openInEditor: mk('lib_Symbol.openInEditor'),
		updateDocumentSource: mk('lib_Symbol.updateDocumentSource'),
	},
	lib_Device: {
		search: mk('lib_Device.search'), create: mk('lib_Device.create'),
		get: mk('lib_Device.get'), modify: mk('lib_Device.modify'),
	},
	dmt_Project: { getCurrentProjectInfo: mk('dmt_Project.getCurrentProjectInfo'), createProject: mk('dmt_Project.createProject') },
	dmt_Schematic: {
		createSchematic: mk('dmt_Schematic.createSchematic'),
		createSchematicPage: mk('dmt_Schematic.createSchematicPage'),
		getSchematicInfo: () => Promise.resolve({ page: [{ uuid: 'p1' }] }),
		deleteSchematic: mk('dmt_Schematic.deleteSchematic'),
	},
	dmt_Pcb: { createPcb: mk('dmt_Pcb.createPcb'), deletePcb: mk('dmt_Pcb.deletePcb') },
	dmt_Board: { createBoard: mk('dmt_Board.createBoard'), getAllBoardsInfo: () => Promise.resolve([projectItem.data[0]]) },
	dmt_EditorControl: {
		openDocument: mk('dmt_EditorControl.openDocument'),
		closeDocument: mk('dmt_EditorControl.closeDocument'),
		activateDocument: mk('dmt_EditorControl.activateDocument'),
	},
	dmt_SelectControl: { getCurrentDocumentInfo: mk('dmt_SelectControl.getCurrentDocumentInfo') },
	sch_PrimitiveComponent: {
		create: async (...a) => { calls.push(['sch_PrimitiveComponent.create', a]); return compStub(); },
		modify: mk('sch_PrimitiveComponent.modify'),
		getAll: async () => [],
		getAllPinsByPrimitiveId: async () => [],
		createNetFlag: mk('createNetFlag'), createNetPort: mk('createNetPort'),
	},
	sch_PrimitiveAttribute: { createNetLabel: mk('createNetLabel') },
	sch_PrimitiveWire: { create: mk('sch_PrimitiveWire.create') },
	sch_PrimitiveRectangle: { create: mk('sch_PrimitiveRectangle.create') },
	sch_PrimitiveText: { create: mk('sch_PrimitiveText.create') },
	sch_PrimitivePin: { create: mk('sch_PrimitivePin.create'), getAll: mk('sch_PrimitivePin.getAll') },
	sch_Document: { save: mk('sch_Document.save') },
	pcb_Document: { save: mk('pcb_Document.save'), importChanges: mk('importChanges') },
	pcb_PrimitiveComponent: {
		getAll: async () => [],
		create: async (...a) => { calls.push(['pcb_PrimitiveComponent.create', a]); return compStub(); },
		modify: mk('pcb_PrimitiveComponent.modify'),
		getAllPinsByPrimitiveId: async () => [{ getState_PadNumber: () => '1', setState_Net: () => {}, done: async () => {} }],
	},
	pcb_PrimitivePolyline: { create: mk('pcb_PrimitivePolyline.create'), getAll: mk('pcb_PrimitivePolyline.getAll') },
	pcb_PrimitivePad: { create: mk('pcb_PrimitivePad.create'), getAll: mk('pcb_PrimitivePad.getAll') },
	pcb_PrimitiveLine: { create: mk('pcb_PrimitiveLine.create'), getAll: mk('pcb_PrimitiveLine.getAll') },
	pcb_PrimitiveVia: { create: mk('pcb_PrimitiveVia.create'), getAll: mk('pcb_PrimitiveVia.getAll') },
	pcb_PrimitivePour: { create: mk('pcb_PrimitivePour.create'), getAll: mk('pcb_PrimitivePour.getAll') },
	pcb_PrimitiveString: { create: mk('pcb_PrimitiveString.create') },
	pcb_MathPolygon: { createPolygon: mk('pcb_MathPolygon.createPolygon') },
	pcb_Drc: { check: mk('pcb_Drc.check') },
	pcb_ManufactureData: { getGerberFile: mk('pcb_ManufactureData.getGerberFile') },
};

const { runSomaBuild } = await import('../src/run.ts');
await runSomaBuild();

const fpKeys = new Set(BOARD_DATA.parts.map(p => fpKeyOf(p.footprint, p.rot)));
const symSet = new Set(BOARD_DATA.parts.map(p => symbolKey(symbolPinList(p))));
const dialog = String(calls.find(c => c[0] === 'dialog')?.[1]?.[0] ?? '');

console.log('=== SOMA v1.3 dry run (mocked eda) ===');
console.log(`footprints:  ${n('lib_Footprint.create')} created (${fpKeys.size} unique keys)`);
console.log(`symbols:     ${n('lib_Symbol.create')} created (${symSet.size} unique pin sets, ${n('sch_PrimitivePin.create')} pins drawn)`);
console.log(`devices:     ${n('lib_Device.create')} created, ${n('lib_Device.get')} verified`);
console.log(`project:     createProject=${n('dmt_Project.createProject')} (must be 0), getCurrentProjectInfo=${n('dmt_Project.getCurrentProjectInfo')}`);
console.log(`schematic:   ${n('sch_PrimitiveComponent.create')} comps, ${n('sch_PrimitiveWire.create')} stubs, ${n('createNetLabel')} netlabels, ${n('createNetFlag')} flags, ${n('createNetPort')} ports`);
console.log(`pcb:         importChanges=${n('importChanges')}, ${n('pcb_PrimitiveComponent.create')} comps placed`);
console.log(`copper:      ${n('pcb_PrimitiveLine.create')} tracks, ${n('pcb_PrimitiveVia.create')} vias, ${n('pcb_PrimitivePour.create')} pours, ${n('pcb_PrimitivePolyline.create')} polylines (fp silk + outline)`);
console.log(`pads:        ${n('pcb_PrimitivePad.create')} (26 footprint keys + 4 mounting holes)`);
console.log(`finish:      DRC checks=${n('pcb_Drc.check')}, gerber=${n('pcb_ManufactureData.getGerberFile')}, saveFile=${n('sys_FileSystem.saveFile')}`);
console.log('--- final dialog ---');
console.log(dialog);
process.exit(0);
