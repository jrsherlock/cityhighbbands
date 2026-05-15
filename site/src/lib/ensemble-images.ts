/**
 * Cover artwork for each ensemble's card / hero.
 *
 * Source assets live at `public/assets/ensembles/<slug>.webp`. Conversion
 * pipeline: ingest original PNG/JPG → resize to 1200px wide → WebP @ q=80
 * via Astro's bundled `sharp`. Yielded ~97% size reduction (30 MB of source
 * PNGs → ~960 KB of WebP) for the initial set of 8 covers.
 *
 * To swap a cover, drop a new file in the folder and re-run:
 *   node --input-type=module -e "import('sharp').then(...)"
 * (or just replace the .webp directly if you already have one at a reasonable
 * size). The path below stays the same.
 */

export const ensembleImages: Record<string, string> = {
  'wind-ensemble':   `/assets/ensembles/wind-ensemble.webp`,
  'symphony-band':   `/assets/ensembles/symphony-band.webp`,
  'concert-band':    `/assets/ensembles/concert-band.webp`,
  'marching-band':   `/assets/ensembles/marching-band.webp`,
  'jazz-ensemble':   `/assets/ensembles/jazz-ensemble.webp`,
  'jazz-lab':        `/assets/ensembles/jazz-lab.webp`,
  'jazz-collective': `/assets/ensembles/jazz-collective.webp`,
  'jazz-workshop':   `/assets/ensembles/jazz-workshop.webp`,
};

export function ensembleImage(slug: string): string {
  return ensembleImages[slug] ?? '';
}
