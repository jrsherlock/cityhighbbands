import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Phase 1 ships to GitHub Pages at https://jrsherlock.github.io/cityhighbbands/.
// Set GH_PAGES=1 in CI; locally + on cityhighband.com we deploy at root.
const isPages = process.env.GH_PAGES === '1';

export default defineConfig({
  site: isPages ? 'https://jrsherlock.github.io' : 'https://cityhighband.com',
  base: isPages ? '/cityhighbbands/' : '/',
  integrations: [sitemap()],
  build: {
    inlineStylesheets: 'auto',
  },
  vite: {
    server: { host: true },
  },
});
