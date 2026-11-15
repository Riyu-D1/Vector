#!/usr/bin/env node
/*
 * Build the .eext without npm install — reuses the vendored SDK's
 * node_modules (easyeda/_research/easyeda-api-sdk) for esbuild + jszip.
 *
 *   node easyeda/extension/build.mjs
 *
 * Output: easyeda/extension/dist/soma-carrier-v13-builder_v1.0.0.eext
 */

import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SDK = path.resolve(HERE, '../_research/easyeda-api-sdk');
const require = createRequire(path.join(SDK, 'package.json'));

const esbuild = require('esbuild');
const JSZip = require('jszip');

const manifest = JSON.parse(fs.readFileSync(path.join(HERE, 'extension.json'), 'utf-8'));
const outDir = path.join(HERE, 'dist');
fs.mkdirSync(outDir, { recursive: true });

await esbuild.build({
	entryPoints: { index: path.join(HERE, 'src/index.ts') },
	outdir: outDir,
	bundle: true,
	minify: false,
	sourcemap: false,
	platform: 'browser',
	format: 'iife',
	globalName: 'edaEsbuildExportName',
	treeShaking: true,
	logLevel: 'warning',
});

const zip = new JSZip();
zip.file('extension.json', fs.readFileSync(path.join(HERE, 'extension.json')));
zip.file('dist/index.js', fs.readFileSync(path.join(outDir, 'index.js')));

const eext = path.join(outDir, `${manifest.name}_v${manifest.version}.eext`);
const buf = await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE', compressionOptions: { level: 9 } });
fs.writeFileSync(eext, buf);
console.log(`built ${eext} (${buf.length} bytes)`);
