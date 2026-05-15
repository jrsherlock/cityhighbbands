# cityhighbands.site

The new Iowa City High Bands website. Astro + Cloudflare Pages.

## Local dev

```bash
cd site
npm install
npm run dev            # http://localhost:4321
```

## Re-running the content migration

The Astro content collections are generated from the original Jimdo export by
`migrate.py` at the repo root. Re-run any time you want to refresh:

```bash
npm run migrate
# or, from repo root:
python3 migrate.py
```

The script wipes and rewrites `src/content/{ensembles,programs,seasons,directors,pages}/`
and writes a `migration-report.json` summarizing what landed where and what was
skipped.

## Deploying to Cloudflare Pages (staging URL)

One-time setup (Jim or the volunteer admin):

```bash
npm install -g wrangler
wrangler login                          # opens browser; sign in with the
                                        # Cloudflare account that owns DNS
```

Deploy:

```bash
cd site
npm run build
wrangler pages deploy dist --project-name=cityhighbands
```

Cloudflare returns a preview URL like `https://abc123.cityhighbands.pages.dev`
that anyone with the link can review. Once approved, point DNS at the project
to cut over the production domain — Jimdo email stays untouched.

## Stack

- **Astro 5** + content collections (`src/content/config.ts`).
- **Pagefind** (Phase 1, add when ready): `npx pagefind --site dist`.
- **Decap CMS** (Phase 1, add when ready): drop a `public/admin/config.yml`
  and `public/admin/index.html` pointing at the same content collections.

## Project layout

```
site/
  src/
    content/
      config.ts            Zod schemas for all collections
      ensembles/           8 ensemble entries (auto-generated)
      programs/            ~214 program entries (auto-generated)
      seasons/             45 season entries 1980–present (auto-generated)
      directors/           Director bios (auto-generated)
      pages/               Hand-curated free-form pages
    layouts/Base.astro     Shared header/footer/styling
    pages/
      index.astro          Homepage
      ensembles/index.astro
      ensembles/[slug].astro    Dynamic per-ensemble template
    styles/site.css        Single global stylesheet (no CSS framework)
  public/
    images/                Optimized photos (copied from export/)
  astro.config.mjs
  wrangler.toml            Cloudflare Pages config
```
