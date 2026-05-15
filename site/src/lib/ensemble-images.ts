/**
 * Stock photography placeholders for the ensemble cards and hero areas.
 *
 * Sourced from Unsplash's free CDN (https://unsplash.com/license — free for
 * commercial and non-commercial use, no attribution required). Hot-linked so
 * we don't bloat the repo with binary assets that are going to be replaced
 * with real City High photography as soon as the directors can supply them.
 *
 * To swap an image for a real photo:
 *   1. Drop the photo at `public/assets/ensembles/<slug>.jpg`
 *   2. Replace the URL below with `/assets/ensembles/<slug>.jpg`
 *     (the rebase-html postbuild script will prefix `/cityhighbbands/`
 *     automatically on GH Pages builds).
 */

const PARAMS = '?w=1000&auto=format&fit=crop&q=80';

export const ensembleImages: Record<string, string> = {
  // Concert & marching: hot-linked Unsplash photography.
  'wind-ensemble':    `https://images.unsplash.com/photo-1519892300165-cb5542fb47c7${PARAMS}`,
  'symphony-band':    `https://images.unsplash.com/photo-1485579149621-3123dd979885${PARAMS}`,
  'concert-band':     `https://images.unsplash.com/photo-1573871669414-010dbf73ca84${PARAMS}`,
  'marching-band':    `https://images.unsplash.com/photo-1511735111819-9a3f7709049c${PARAMS}`,
  // Jazz: local SVG placeholders with explicit jazz iconography, one per
  // ensemble (sax / trumpet / upright bass / piano). These were chosen over
  // hot-linked stock so each card is unambiguously jazz on first glance.
  // Swap with photography by replacing the URL with `/assets/ensembles/<slug>.jpg`.
  'jazz-ensemble':    `/assets/ensembles/jazz-ensemble.svg`,
  'jazz-lab':         `/assets/ensembles/jazz-lab.svg`,
  'jazz-collective':  `/assets/ensembles/jazz-collective.svg`,
  'jazz-workshop':    `/assets/ensembles/jazz-workshop.svg`,
};

export function ensembleImage(slug: string): string {
  return ensembleImages[slug] ?? '';
}
