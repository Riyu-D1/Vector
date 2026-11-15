/*
 * SOMA Carrier v1.3 — EasyEDA Pro rebuild extension.
 *
 * Menu entries declared in extension.json call the exported functions
 * below by name. `run` executes the full rebuild; `about` shows info.
 */

import { runSomaBuild, runDiagnostics } from './run';
import extensionConfig from '../extension.json' with { type: 'json' };

export function activate(status?: 'onStartupFinished', arg?: string): void {
	void status;
	void arg;
}

export function run(): void {
	void runSomaBuild();
}

export function diagnose(): void {
	void runDiagnostics();
}

export function about(): void {
	eda.sys_Dialog.showInformationMessage(
		`SOMA Carrier v1.3 rebuild extension v${extensionConfig.version}.\n\n` +
		'Creates a new project "SOMA Carrier v1.3 (EasyEDA)", builds the schematic,\n' +
		'generates the PCB (135x115 mm, 2 layers) with replicated v1.3 routing,\n' +
		'and saves. Source: soma-carrier-v13.kicad_pcb (KiCad 10).',
		'SOMA Carrier v1.3',
	);
}
