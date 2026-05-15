# City High Bands — Design Brief (Phase 1)

## North Star

> A program at the peak of its run deserves a site that quietly says so.

The site should feel like a well-printed concert program — confident typography, generous space, a few strong photographs, no clutter. Restraint signals quality. The program is the spectacle; the chrome shouldn't be.

## Audience priorities (in order)

1. **Prospective students & their parents** — 8th graders deciding instruments; high schoolers transferring in. Need: "What is this program? Who teaches it? How do I join? Will I be welcomed?"
2. **Current band families** — Need: calendar, concert info, forms/announcements, who-to-email.
3. **Alumni & community supporters** — Need: a way to feel proud, give money, sign up for parking lot clean-ups.
4. **Press / festival adjudicators / peer programs** — Need: bios, recent results, recordings.

The current site fails #1 catastrophically (the homepage is one donation link). #1 is the biggest design win available.

## Three reference points

I'm not copying any of these — they're directional. Each contributes one quality.

### 1. Interlochen Center for the Arts (interlochen.org)
**Takeaway: gravitas through photography.** Big, slow-feeling hero images of musicians actually playing. Generous serif headlines. Calm color. The site feels like a place serious music happens — without ever using the word "serious."

### 2. Sō Percussion (sopercussion.com)
**Takeaway: editorial typography over decoration.** A bold display type doing 80% of the visual work, with minimal supporting graphics. Concert programs presented as cleanly typeset listings, not bulleted text. Demonstrates that "modern" doesn't require gradients/illustrations.

### 3. The Juilliard School (juilliard.edu/music)
**Takeaway: ensemble-as-product information architecture.** Each ensemble has a parallel-structured page: conductor, description, repertoire, audition path. Visitors learn the *shape* of the program by browsing. We'll borrow that template approach for our 8 ensembles.

(Decoy / what NOT to imitate: most high school band sites — Squarespace-template marching photos with stripey gradients, "Welcome to our band!" copy, 14 things on the homepage. We're aiming above that.)

## Color system

A restrained palette anchored by Little Hawk red, but the red is an *accent*, never a background.

| Token | Hex | Use |
|---|---|---|
| `--ink` | `#11151A` | Body text, headlines |
| `--paper` | `#FAF8F4` | Page background (warm off-white, not pure) |
| `--paper-2` | `#F1ECE2` | Section banding |
| `--rule` | `#D8D1C2` | Hairline dividers |
| `--muted` | `#6B6358` | Captions, meta, dates |
| `--hawk` | `#A6192E` | Little Hawk red — links, buttons, headline accents only |
| `--hawk-dark` | `#7A1222` | Hover state |
| `--ink-inverse` | `#FAF8F4` | Text on dark hero overlays |

Dark mode deferred to Phase 2 (low priority for a content site like this).

## Typography

Two families. Both free on Google Fonts. Both have stylistic range that scales from a poster headline to an 11-px caption.

- **Display: Fraunces** (serif, optical-size variable). Used for H1/H2 and hero pull quotes. Set headlines tight, low-contrast weight, slight optical-size bump on the largest sizes.
- **Body & UI: Inter** (sans, variable). Used everywhere else. Set body at 17–18px, generous line height (1.65).

Type scale (rem, mobile → desktop):
```
display    2.5 → 4.5   Fraunces 500
h1         2.0 → 3.0   Fraunces 500
h2         1.5 → 2.0   Fraunces 500
h3         1.2 → 1.4   Inter 600
body       1.0 → 1.08  Inter 400
small      0.875       Inter 500
meta       0.8125      Inter 500, --muted, uppercase letter-spacing 0.06em
```

## Layout primitives

- **Max content width: 72ch** for prose, **1240px** for layouts with imagery.
- Generous vertical rhythm — sections separated by 5–8rem of space, not borders.
- Hero images: cinematic 21:9 on desktop, 4:5 on mobile (taller, portrait-oriented for thumb scrolling).
- Cards: zero rounded corners, single hairline border, no shadows. (Soft shadows are the "Squarespace look" we're avoiding.)

## Interaction & motion

- Subtle: a 200ms fade on link/hover, a 400ms reveal on scroll for hero sections. No parallax. No animated illustrations.
- All motion respects `prefers-reduced-motion`.

## Accessibility (non-negotiable, Phase 1)

- WCAG 2.2 AA contrast minimum on all text — red on paper passes; never use red as background under light text.
- All images get real `alt` text during the curation pass (this is a known gap in the current export).
- Keyboard navigable; visible focus rings using `--hawk` outline.
- No icon-only buttons without aria-labels.

## Out-of-scope for design Phase 1

- Custom illustrations / mascot art (defer).
- Animated/video hero (defer — single still photo is enough).
- Newsletter signup (no newsletter exists yet).
- Search UI styling — Pagefind ships with reasonable defaults.
