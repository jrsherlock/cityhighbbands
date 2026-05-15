# cityhighband.com -- Content Export for Site Rebuild

This is a clean export of every page from the current cityhighband.com site,
ready to use as the content seed for a modern rebuild (Next.js, Astro, Hugo,
SvelteKit, or anything else that ingests Markdown).

## What was crawled

- **Source:** https://www.cityhighband.com/ (Jimdo-hosted)
- **Pages:** 79 (from the site's own sitemap.xml)
- **Images:** 968 unique, deduplicated by URL hash
- **Total size:** see `du -sh assets/`

## Folder layout

```
pages/                              <- one .md per source page, mirroring URL paths
  index.md                          <- homepage (was https://www.cityhighband.com/)
  about.md
  directors.md
  bach-parent-volunteers.md
  parking-lot-clean-ups.md
  private-lessons.md
  city-high-music-department.md
  concert-bands.md                  <- the section landing pages live alongside
  concert-bands/                       their child folders, named the same
    concert-band.md
    symphony-band.md
    symphony-band/
      1987-1999.md
    wind-ensemble.md
  marching-band-pep-band.md
  marching-band-pep-band/
    pep-band-music.md
    pre-game-music.md
  city-high-jazz.md
  city-high-jazz/
    jazz-collective.md
    jazz-ensemble.md
    jazz-ensemble/1998-2010.md
    jazz-lab.md
    jazz-workshop.md
  media-1.md
  media-1/
    pictures.md
    pictures/2010-2011-concert-bands.md
    ... (lots of year-archived photo pages)
  archives-past-results.md
  archives-past-results/
    1980-1981.md   ...all the way up to...   2024-2025.md
assets/
  images/                           <- every image, hashed filename
site-map.json                       <- machine-readable index of all pages
PAGES_INDEX.md                      <- human-readable index, grouped by section
README.md                           <- this file
```

## Markdown file format

Every page has YAML frontmatter, then a clean Markdown body. Example:

```markdown
---
title: "Directors"
slug: "directors"
source_url: "https://www.cityhighband.com/directors/"
hero_original: "https://image.jimcdn.com/.../image.jpg"
breadcrumb: []
depth: 0
---

# Directors

![Mr. Mike Kowbel](/assets/images/910b4da8bd-image.jpg)

**Mr. Mike Kowbel** is in his seventh year...
```

Frontmatter fields:

- `title`: cleaned page title (Jimdo's " - The School That Leads" suffix stripped)
- `slug`: URL-safe page identifier
- `source_url`: original URL on cityhighband.com
- `description`: meta description if the original page had one
- `hero_original`: OG image URL on the original site (not downloaded; reference only)
- `breadcrumb`: list of parent path segments (e.g. ["city-high-jazz"])
- `depth`: nesting depth (0 = top-level)

Image paths use a root-relative form (`/assets/images/...`) which works
naturally with Next.js `public/`, Astro `public/`, Hugo `static/`, etc.

## What you actually get out of this for the rebuild

1. **All content as plain Markdown** -- no Jimdo markup, no inline styles, no
   tracking scripts, no Cloudflare email obfuscation (those are decoded to real
   `mailto:` links).
2. **All images locally cached** with stable hashed filenames, so links won't
   rot if Jimdo CDN paths change or the legacy site goes away.
3. **A site-map.json** you can feed to a Next.js `getStaticPaths` /
   `generateStaticParams`, or to an Astro content collection schema, to
   auto-generate routes from the export.
4. **Internal links rewritten to relative paths** so they don't keep pointing
   at the old domain after migration.

## Suggested rebuild stacks

Given that the site is content-heavy and updates occasionally (band program,
archives, parent volunteer signups), most things in the Jamstack space fit:

- **Astro + Astro Content Collections**: probably the lowest-friction match.
  Drop `pages/*.md` into `src/content/pages/` with the existing frontmatter
  schema, and Astro routes + renders them. Great Lighthouse scores out of the
  box, mobile-first by default.
- **Next.js (App Router) + MDX**: more flexible if you want React components
  embedded in pages (calendars, sign-up widgets, donation embeds). Slightly
  more setup overhead.
- **Hugo**: fastest build times by far, very mature for school/org sites,
  but theming is its own language.
- **SvelteKit**: nice DX if anyone on the team prefers Svelte; comparable
  to Next.js in feature surface.

For hosting, Vercel, Netlify, and Cloudflare Pages all give you free tiers
that easily cover a school band site's traffic, plus automatic HTTPS,
preview deploys on git branches, and instant rollbacks. Cloudflare Pages
in particular pairs well if you keep the existing Cloudflare DNS.

## Things worth knowing before you start designing

- The `/city-high-music-department/` page is a hub linking to three sister
  sites: a Jimdo-hosted orchestras site, cityhighchoirs.com, and a Google
  Sites music office page. Worth deciding early whether the rebuild
  consolidates those or just links out.
- The `/about/` page on the live site has no real content (just Jimdo's
  default placeholder text); that's not a missed extraction, that's how the
  source is.
- Email currently flows through Jimdo MX; if the rebuild drops Jimdo
  entirely, the band's existing inboxes need to migrate (or DNS needs to
  keep pointing MX at Jimdo while web moves elsewhere -- they can be
  separated).
- DMARC is published as `p=none` with no reporting addresses. Cheap win
  during the rebuild: add a real DMARC policy with `rua` reporting.
- The donation link on the homepage uses MySchoolBucks
  (`myschoolbucks.com/ver2/prdembd?ref=...`) -- preserve that exactly
  in the rebuild so existing donation flows don't break.

## Known limitations of the export

- Photo gallery pages (`media-1/pictures/...`) only capture the images that
  Jimdo serves in the rendered HTML. If any galleries lazy-load additional
  images via JS that this static crawler didn't trigger, those won't be
  here. Spot-check those pages against the live site before deleting it.
- The hero `og:image` field in frontmatter references the original Jimdo
  CDN URL (not downloaded locally) because it's often a tiny crop variant
  of an image already captured elsewhere. Easy to download in bulk later
  if needed.
- Some `j-text` modules contain Jimdo's bold-everywhere styling; the
  Markdown preserves bold faithfully but you may want to strip a lot of it
  during the redesign for cleaner typography.

## Reproduce / re-crawl

The extractor is at `/home/claude/extract.py`. It's resumable (skips pages
that already have non-trivial `.md` output) and honors the site's 5-second
robots.txt crawl delay. Run with `python3 extract.py [start] [end]` to
process a slice (1-indexed inclusive), or no args for the whole site.
