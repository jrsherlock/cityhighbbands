#!/usr/bin/env node
/**
 * GitHub Pages base-path postbuild rewriter.
 *
 * Astro respects `base` for emitted assets (`/cityhighbbands/_astro/...`) but
 * does NOT automatically prefix base on `href`/`src` attributes the developer
 * wrote in templates (e.g. `href="/program"` stays as-is). This script walks
 * dist/ after `astro build` and prefixes the base to every absolute-path
 * attribute that doesn't already start with it.
 *
 * Idempotent: re-running on already-rewritten HTML is a no-op.
 *
 * Skipped when GH_PAGES != '1' so local previews keep root-relative paths.
 */

import { readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { join, extname } from 'node:path';

if (process.env.GH_PAGES !== '1') {
  console.log('[rebase-html] GH_PAGES not set — skipping.');
  process.exit(0);
}

const BASE = '/cityhighbbands';
const DIST = new URL('../dist', import.meta.url).pathname;

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const s = statSync(p);
    if (s.isDirectory()) walk(p, out);
    else if (['.html', '.xml'].includes(extname(name))) out.push(p);
  }
  return out;
}

// Match  attr="/X..."  where attr is href|src|action and the path
// (a) starts with `/`,
// (b) is NOT already prefixed with our base,
// (c) starts with a letter or is the bare root `/`.
const RE = new RegExp(
  `(href|src|action)="(\\/)((?!cityhighbbands(?:\\/|"))(?:[a-zA-Z][^"]*)?)"`,
  'g'
);

let files = 0, hits = 0;
for (const file of walk(DIST)) {
  const src = readFileSync(file, 'utf8');
  const out = src.replace(RE, (_m, attr, _slash, rest) => {
    hits++;
    return `${attr}="${BASE}/${rest}"`;
  });
  if (out !== src) {
    writeFileSync(file, out);
    files++;
  }
}

console.log(`[rebase-html] rewrote ${hits} attributes across ${files} files (base=${BASE})`);
