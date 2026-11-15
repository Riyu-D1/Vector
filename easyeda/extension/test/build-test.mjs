#!/usr/bin/env node
/* Bundle the test suite with esbuild (SDK node_modules) and run it. */
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SDK = path.resolve(HERE, '../../_research/easyeda-api-sdk');
const require = createRequire(path.join(SDK, 'package.json'));
const esbuild = require('esbuild');

const out = path.join(HERE, 'dist', 'run-tests.js');
fs.mkdirSync(path.dirname(out), { recursive: true });
await esbuild.build({
	entryPoints: { 'run-tests': path.join(HERE, 'run-tests.mjs') },
	outdir: path.dirname(out),
	bundle: true,
	platform: 'node',
	format: 'esm',
	logLevel: 'warning',
});
const r = spawnSync(process.execPath, [out], { stdio: 'inherit' });
process.exit(r.status ?? 1);
