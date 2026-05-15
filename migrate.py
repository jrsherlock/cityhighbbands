#!/usr/bin/env python3
"""
City High Bands — content migration.

Parses the 79-page Markdown export at export/chb_export/pages/ into structured
content collections matching the Astro schema in site/src/content/config.ts.

Run:
    python3 migrate.py            # parse everything → site/src/content/
    python3 migrate.py --dry      # parse, print summary, write nothing
    python3 migrate.py --debug    # verbose per-page output

The script is idempotent: re-running rewrites the collections cleanly.
It is intentionally tolerant — pages that don't fit a known shape land in
`pages/` with their raw body, and a `migration-report.json` summarizes what
got parsed and what got punted.
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
EXPORT_DIR = ROOT / "export" / "chb_export" / "pages"
ASSETS_SRC = ROOT / "export" / "chb_export" / "assets" / "images"
OUT_DIR = ROOT / "site" / "src" / "content"
PUBLIC_IMAGES = ROOT / "site" / "public" / "images"
REPORT_PATH = ROOT / "migration-report.json"


# ── Models (kept simple — these become YAML in front-matter) ───────────────
@dataclass
class Piece:
    title: str
    composer: str = ""
    arranger: str = ""
    year: str = ""
    note: str = ""


@dataclass
class Program:
    """A single performance: a concert, a festival appearance, etc."""
    ensemble_slug: str
    event_name: str
    venue: str = ""
    date_raw: str = ""            # original string from page header
    date_iso: str = ""            # YYYY-MM-DD when parseable
    season: str = ""              # YYYY-YYYY when assigned
    program_title: str = ""       # the concert's theme/title if given
    pieces: list[Piece] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)  # e.g. "iba", "premiere"


@dataclass
class EnsembleMember:
    name: str
    grade: str = ""
    instrument: str = ""
    note: str = ""


@dataclass
class Season:
    year_range: str               # "2024-2025"
    start_year: int
    marching: dict = field(default_factory=dict)   # show name, results
    ensembles: dict = field(default_factory=dict)  # per-ensemble line items
    all_state: list[EnsembleMember] = field(default_factory=list)
    seiba: list[EnsembleMember] = field(default_factory=list)
    uni_honor: list[EnsembleMember] = field(default_factory=list)
    iowa_honor: list[EnsembleMember] = field(default_factory=list)
    all_state_jazz: list[EnsembleMember] = field(default_factory=list)
    awards: list[dict] = field(default_factory=list)  # {category, recipients[]}
    body_raw: str = ""            # unparsed remainder, for human review


@dataclass
class Director:
    slug: str
    name: str
    role: str = ""
    photo: str = ""
    email: str = ""
    bio: str = ""


@dataclass
class Ensemble:
    slug: str
    name: str
    category: str            # concert | marching | jazz
    conductors: list[str] = field(default_factory=list)
    summary: str = ""
    hero_image: str = ""


@dataclass
class FreePage:
    slug: str
    title: str
    breadcrumb: list[str] = field(default_factory=list)
    body: str = ""
    hero: str = ""
    source_url: str = ""


# ── Front-matter parser ────────────────────────────────────────────────────
FRONT_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def parse_front(text: str) -> tuple[dict, str]:
    m = FRONT_RE.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    meta = {}
    for line in raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            v = v.strip().strip('"').strip("'")
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                meta[k.strip()] = [s.strip().strip('"') for s in inner.split(",") if s.strip()] if inner else []
            else:
                meta[k.strip()] = v
    return meta, body


# ── Repertoire parser — handles Jimdo's dot-leader concert lists ──────────
# Lines look like:
#   Gavorkna Fanfare (1991)..................................Jack Stamp
#   Symphony No. 6..............................Vincent Persichetti
#   The Stars and Stripes Forever....John Philip Sousa
# Movement lines and chamber notes interspersed.
PIECE_RE = re.compile(
    r"""^
        (?P<title>.*?)                       # title (greedy non-dot)
        (?:\s*\((?P<year>[\d/]{4,9})\))?     # optional (1991) or (1955/1986)
        \s*\.{4,}                            # >=4 literal dots — the Jimdo dot leader
        \s*(?P<composer>.+?)                 # composer / arranger string (may contain dots)
        \s*$
    """,
    re.VERBOSE,
)
# Fallback for lines with composer wrapped in punctuation
SIMPLE_PIECE_RE = re.compile(r"^(?P<title>[^.]+?)\.{2,}(?P<composer>[^.]+)$")

# Concert headers like "## Mid-Winter Concert - February 26th, 2025"
CONCERT_HEADER_RE = re.compile(
    r"^##\s+(?P<event>.+?)\s*[-–]\s*(?P<date>[A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\s*$"
)
THEME_RE = re.compile(r'"(?P<theme>[^"]+)"')


def split_composer(raw: str) -> tuple[str, str]:
    """Composer string → (composer, arranger). Heuristic on '/arr.' or 'arr.' or 'tr.'"""
    s = raw.strip().strip("*")
    for sep in [" arr. ", "/arr. ", " tr. ", "/tr. ", "/ed. ", " ed. "]:
        if sep in s:
            comp, _, arr = s.partition(sep)
            return comp.strip(), arr.strip()
    return s, ""


def parse_concert_block(date_str: str, event_raw: str, lines: list[str]) -> Program:
    """Given the header info and the lines until the next ##, build a Program."""
    theme = ""
    tm = THEME_RE.search(event_raw)
    if tm:
        theme = tm.group("theme")
    event_clean = THEME_RE.sub("", event_raw).strip(" -—")

    program = Program(
        ensemble_slug="",   # caller sets
        event_name=event_clean or event_raw,
        date_raw=date_str.strip(),
        program_title=theme,
    )
    program.date_iso = parse_date(date_str)

    flags = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # flags / chamber notes / asterisks
        if re.match(r"^\\?\*+", line) or "Chamber Wind Ensemble" in line:
            if "Chamber" in line:
                flags.append("chamber")
            if "WORLD PREMIERE" in line.upper():
                flags.append("premiere")
            if "GRAMMY" in line.upper():
                flags.append("grammy")
            if "Senior gift" in line or "Memory" in line:
                flags.append("tribute")
            continue
        # movement / sub-section indented lines
        if line.startswith(("Mvt", "Movement", "          ", "               ", "                    ", "                         ", "                  ", "                        ", "                ", "                         ")) or re.match(r"^\s*Mvt\.?\s+\d", line):
            if program.pieces:
                program.pieces[-1].note += (line.strip() + " ")
            continue

        m = PIECE_RE.match(line)
        if not m:
            m = SIMPLE_PIECE_RE.match(line)
            if not m:
                continue
        title = m.group("title").strip(" *")
        year = m.group("year") if "year" in m.groupdict() and m.group("year") else ""
        composer_raw = m.group("composer").strip()
        composer, arranger = split_composer(composer_raw)
        if not title:
            continue
        program.pieces.append(Piece(
            title=title, composer=composer, arranger=arranger,
            year=year, note=""
        ))
    program.flags = sorted(set(flags))
    return program


MONTHS = {m.lower(): i for i, m in enumerate(
    ["January","February","March","April","May","June","July","August","September","October","November","December"],
    start=1
)}
ABBR = {m.lower(): i for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Sept","Oct","Nov","Dec"],
    start=1
)}
ABBR["sept"] = 9


def parse_date(s: str) -> str:
    s = s.replace("Feburary", "February").strip().rstrip(",")
    m = re.match(r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", s)
    if not m:
        return ""
    mon_name, day, year = m.group(1).lower(), int(m.group(2)), int(m.group(3))
    mon = MONTHS.get(mon_name) or ABBR.get(mon_name)
    if not mon:
        return ""
    try:
        return f"{year:04d}-{mon:02d}-{day:02d}"
    except Exception:
        return ""


def season_for_date(iso: str) -> str:
    """A concert in Feb 2026 belongs to the 2025-2026 season."""
    if not iso:
        return ""
    y, m, _ = iso.split("-")
    y, m = int(y), int(m)
    start = y if m >= 7 else y - 1
    return f"{start}-{start + 1}"


# ── Per-page parsers ───────────────────────────────────────────────────────

ENSEMBLE_MAP = {
    # slug-in-export : (canonical_slug, name, category)
    "concert-bands/wind-ensemble": ("wind-ensemble", "Wind Ensemble", "concert"),
    "concert-bands/symphony-band": ("symphony-band", "Symphony Band", "concert"),
    "concert-bands/concert-band": ("concert-band", "Concert Band", "concert"),
    "marching-band-pep-band": ("marching-band", "Little Hawk Marching Band", "marching"),
    "city-high-jazz/jazz-ensemble": ("jazz-ensemble", "Jazz Ensemble", "jazz"),
    "city-high-jazz/jazz-lab": ("jazz-lab", "Jazz Lab", "jazz"),
    "city-high-jazz/jazz-collective": ("jazz-collective", "Jazz Collective", "jazz"),
    "city-high-jazz/jazz-workshop": ("jazz-workshop", "Jazz Workshop", "jazz"),
}


def parse_ensemble_repertoire(meta: dict, body: str, ensemble_slug: str) -> list[Program]:
    """Walk an ensemble page; emit one Program per `## <event> - <date>` block."""
    programs: list[Program] = []
    lines = body.splitlines()
    cur_event, cur_date, cur_buf = None, None, []
    for line in lines:
        m = CONCERT_HEADER_RE.match(line.strip())
        if m:
            # flush previous
            if cur_event:
                p = parse_concert_block(cur_date, cur_event, cur_buf)
                p.ensemble_slug = ensemble_slug
                p.season = season_for_date(p.date_iso)
                programs.append(p)
            cur_event = m.group("event")
            cur_date = m.group("date")
            cur_buf = []
        else:
            cur_buf.append(line)
    if cur_event:
        p = parse_concert_block(cur_date, cur_event, cur_buf)
        p.ensemble_slug = ensemble_slug
        p.season = season_for_date(p.date_iso)
        programs.append(p)
    return programs


def parse_directors(body: str) -> list[Director]:
    """Split on `---` rule lines; each chunk is one director."""
    chunks = re.split(r"\n---\n", body)
    directors = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # First image: photo
        img_m = re.search(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)", chunk)
        photo = img_m.group("src") if img_m else ""
        # Bold name
        name_m = re.search(r"\*\*(?P<name>[^*]+?)\*\*\s*(?:is|currently)", chunk)
        if not name_m:
            name_m = re.search(r"\*\*(?P<name>(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+)\*\*", chunk)
        name = name_m.group("name").strip().rstrip(".") if name_m else ""
        # Email
        em_m = re.search(r"\[?([\w\.\-]+@iowacityschools\.org)\]?", chunk)
        email = em_m.group(1) if em_m else ""
        if not name:
            continue
        # Bio: drop the image markdown and the trailing mailto link
        bio = chunk
        if img_m:
            bio = bio.replace(img_m.group(0), "").strip()
        bio = re.sub(r"\[[^\]]+\]\(mailto:[^)]+\)", "", bio).strip()
        # Role inferred
        role = "Co-Director of Bands"
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        directors.append(Director(slug=slug, name=name, role=role, photo=photo, email=email, bio=bio))
    return directors


SEASON_SECTION_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
MEMBER_LINE_RE = re.compile(
    r"^(?P<name>[A-Z][\w\.\'\-]+(?:\s+[A-Z][\w\.\'\-]+)+)\s*"
    r"(?:\((?P<grade>[A-Za-z]+)\))?\s*"
    r"(?:[-–]\s*(?P<instrument>[^()]+?))?\s*"
    r"(?:\(\s*(?P<note>[^)]+)\s*\))?\s*$"
)
RESULTS_LINE_RE = re.compile(r"(Division 1|Class \w+|\d+(?:st|nd|rd|th)? Place|Selected|Best [A-Z][\w ]+)", re.I)


def parse_season(meta: dict, body: str, year_range: str) -> Season:
    sn = Season(year_range=year_range, start_year=int(year_range.split("-")[0]))
    current_section = None
    buf_lines: list[str] = []
    sections: dict[str, list[str]] = {}
    for line in body.splitlines():
        sm = SEASON_SECTION_RE.match(line)
        if sm:
            if current_section is not None:
                sections.setdefault(current_section, []).extend(buf_lines)
            current_section = sm.group("title").strip()
            buf_lines = []
        else:
            buf_lines.append(line)
    if current_section is not None:
        sections.setdefault(current_section, []).extend(buf_lines)

    for sec_title, raw_lines in sections.items():
        lines = [l.strip() for l in raw_lines if l.strip()]
        title_low = sec_title.lower()
        if "marching" in title_low and "all-state" not in title_low:
            theme_m = THEME_RE.search(sec_title)
            sn.marching["show"] = theme_m.group("theme") if theme_m else sec_title
            sn.marching["results"] = [l for l in lines if RESULTS_LINE_RE.search(l)]
            sn.marching["notes"] = [l for l in lines if l.startswith("Drum Majors")]
        elif title_low.startswith("all-state") and "jazz" not in title_low:
            for l in lines:
                m = MEMBER_LINE_RE.match(l)
                if m:
                    sn.all_state.append(EnsembleMember(
                        name=m.group("name").strip(),
                        grade=(m.group("grade") or "").strip(),
                        instrument=(m.group("instrument") or "").strip(),
                        note=(m.group("note") or "").strip(),
                    ))
        elif "all-state jazz" in title_low:
            for l in lines:
                m = MEMBER_LINE_RE.match(l)
                if m:
                    sn.all_state_jazz.append(EnsembleMember(
                        name=m.group("name").strip(),
                        grade=(m.group("grade") or "").strip(),
                        instrument=(m.group("instrument") or "").strip(),
                    ))
        elif "seiba" in title_low:
            for l in lines:
                m = MEMBER_LINE_RE.match(l)
                if m:
                    sn.seiba.append(EnsembleMember(
                        name=m.group("name").strip(),
                        grade=(m.group("grade") or "").strip(),
                        instrument=(m.group("instrument") or "").strip(),
                    ))
        elif "uni honor" in title_low:
            for l in lines:
                m = MEMBER_LINE_RE.match(l)
                if m:
                    sn.uni_honor.append(EnsembleMember(
                        name=m.group("name").strip(),
                        grade=(m.group("grade") or "").strip(),
                        instrument=(m.group("instrument") or "").strip(),
                    ))
        elif "iowa honor" in title_low or "university of iowa honor" in title_low:
            for l in lines:
                m = MEMBER_LINE_RE.match(l)
                if m:
                    sn.iowa_honor.append(EnsembleMember(
                        name=m.group("name").strip(),
                        grade=(m.group("grade") or "").strip(),
                        instrument=(m.group("instrument") or "").strip(),
                    ))
        elif title_low in ("wind ensemble", "symphony band", "concert band"):
            sn.ensembles[title_low] = [l for l in lines if l]
        elif "jazz ensemble" in title_low or "jazz collective" in title_low or "jazz lab" in title_low:
            sn.ensembles[title_low] = [l for l in lines if l]
        elif "award" in title_low or "gold key" in title_low or "louis armstrong" in title_low or "john philip sousa" in title_low or "director" in title_low:
            sn.awards.append({"category": sec_title, "recipients": lines})
        else:
            # unknown section — keep raw
            sn.awards.append({"category": sec_title, "recipients": lines})

    return sn


# ── YAML emitter (minimal — no PyYAML dependency) ──────────────────────────
def yaml_dump(v, indent=0) -> str:
    pad = "  " * indent
    if isinstance(v, dict):
        if not v:
            return " {}"
        out = ""
        for k, val in v.items():
            if isinstance(val, dict):
                if val:
                    out += f"\n{pad}{k}:" + yaml_dump(val, indent + 1)
                else:
                    out += f"\n{pad}{k}: {{}}"
            elif isinstance(val, list):
                if val:
                    out += f"\n{pad}{k}:" + yaml_dump(val, indent + 1)
                else:
                    out += f"\n{pad}{k}: []"
            else:
                out += f"\n{pad}{k}: {yaml_scalar(val)}"
        return out
    if isinstance(v, list):
        if not v:
            return " []"
        out = ""
        for item in v:
            if isinstance(item, dict):
                # first key inline with hyphen
                keys = list(item.keys())
                if not keys:
                    out += f"\n{pad}- {{}}"
                    continue
                first = keys[0]
                out += f"\n{pad}- {first}: {yaml_scalar(item[first])}"
                for k in keys[1:]:
                    val = item[k]
                    if isinstance(val, (list, dict)) and val:
                        out += f"\n{pad}  {k}:" + yaml_dump(val, indent + 2)
                    else:
                        out += f"\n{pad}  {k}: {yaml_scalar(val)}"
            else:
                out += f"\n{pad}- {yaml_scalar(item)}"
        return out
    return f" {yaml_scalar(v)}"


_DATEISH_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
# A string is "safe-bareword" if it contains only letters/digits/space and a
# few innocuous separators. Anything else gets JSON-quoted to avoid every
# YAML pitfall (tags via !, flow w/ []{}, aliases w/ &*, etc.).
_SAFE_BAREWORD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 _.\-/]*$")


def yaml_scalar(v) -> str:
    if v is None or v == "":
        return '""'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if (s == ""
            or _DATEISH_RE.match(s)
            or s.lower() in {"yes", "no", "on", "off", "true", "false", "null", "~"}
            or not _SAFE_BAREWORD_RE.match(s)):
        return json.dumps(s, ensure_ascii=False)
    return s


def write_entry(out_path: Path, data: dict, body: str = "") -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fm = "---" + yaml_dump(data) + "\n---\n"
    out_path.write_text(fm + (body or "") + "\n", encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    if not EXPORT_DIR.exists():
        sys.exit(f"export not found at {EXPORT_DIR}")

    files = sorted(EXPORT_DIR.rglob("*.md"))
    report = {
        "files_seen": len(files),
        "ensembles": 0,
        "programs": 0,
        "seasons": 0,
        "directors": 0,
        "pages": 0,
        "skipped": [],
        "warnings": [],
    }

    programs: list[Program] = []
    seasons: list[Season] = []
    directors: list[Director] = []
    pages: list[FreePage] = []
    ensembles: dict[str, Ensemble] = {}

    # First, seed ensembles from the map (so they exist even if their page is empty)
    for src, (slug, name, cat) in ENSEMBLE_MAP.items():
        ensembles[slug] = Ensemble(slug=slug, name=name, category=cat)

    for f in files:
        rel = f.relative_to(EXPORT_DIR).with_suffix("").as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_front(text)
        slug = meta.get("slug", rel.replace("/", "-"))
        title = meta.get("title", slug)
        breadcrumb = meta.get("breadcrumb", []) or []

        if args.debug:
            print(f"[{rel}] title={title!r}")

        # ── Ensembles + their programs
        ens_match = ENSEMBLE_MAP.get(rel)
        if ens_match:
            ens_slug, _, _ = ens_match
            ens = ensembles[ens_slug]
            # Conductor heuristic from headings like "## Mike Kowbel - Conductor"
            cond_m = re.search(r"##\s+([A-Z][a-zA-Z\.\s]+?)\s*[-–]\s*(?:Conductor|Director)", body)
            if cond_m:
                ens.conductors = [cond_m.group(1).strip()]
            # First image as hero
            img_m = re.search(r"!\[[^\]]*\]\(([^)]+)\)", body)
            if img_m:
                ens.hero_image = img_m.group(1)
            # Marching show themes are listed as `## 2024 - "Cirque do Soleil"`
            if ens.category == "marching":
                shows = re.findall(r"##\s+(\d{4})\s*[-–]\s*\"([^\"]+)\"", body)
                ens.summary = "; ".join(f"{y}: {t}" for y, t in shows[:5])
            # Repertoire
            ens_programs = parse_ensemble_repertoire(meta, body, ens_slug)
            programs.extend(ens_programs)
            report["programs"] += len(ens_programs)
            continue

        # ── Season archives
        if breadcrumb == ["archives-past-results"] or rel.startswith("archives-past-results/"):
            year_range = re.sub(r"-1$", "", slug)  # "2023-2024-1" → "2023-2024"
            if not re.match(r"^\d{4}-\d{4}$", year_range):
                report["skipped"].append({"file": rel, "reason": "season slug not YYYY-YYYY"})
                continue
            try:
                s = parse_season(meta, body, year_range)
                seasons.append(s)
                report["seasons"] += 1
            except Exception as e:
                report["warnings"].append({"file": rel, "error": str(e)})
            continue

        # ── Directors
        if slug == "directors":
            for d in parse_directors(body):
                directors.append(d)
                report["directors"] += 1
            continue

        # ── Section hubs we don't need to migrate as pages
        if slug in ("concert-bands", "city-high-jazz", "media-1", "archives-past-results"):
            report["skipped"].append({"file": rel, "reason": "section hub — replaced by index"})
            continue

        # ── Photo gallery pages — skip per "outdated content" guidance
        if rel.startswith("media-1/"):
            report["skipped"].append({"file": rel, "reason": "old photo gallery (pre-2017)"})
            continue

        # ── Symphony Band / Jazz Ensemble pre-2010 historical sub-pages
        if rel.endswith("/1987-1999") or rel.endswith("/1998-2010"):
            report["skipped"].append({"file": rel, "reason": "historical archive sub-page; folded into season archives"})
            continue

        # ── Pep band / pre-game music — small lists; keep as free pages but flag
        if rel.startswith("marching-band-pep-band/"):
            pages.append(FreePage(slug=slug, title=title, breadcrumb=breadcrumb, body=body.strip(), hero=meta.get("hero_original", ""), source_url=meta.get("source_url", "")))
            report["pages"] += 1
            continue

        # ── BACH / parent volunteer page → keep, re-title
        if slug == "bach-parent-volunteers":
            pages.append(FreePage(
                slug="bach",
                title="Band Associates of City High (BACH)",
                breadcrumb=["support"],
                body=body.strip(),
                hero=meta.get("hero_original", ""),
                source_url=meta.get("source_url", ""),
            ))
            report["pages"] += 1
            continue

        # ── Empty stubs → drop; flag for re-authoring
        if len(body.strip().splitlines()) <= 2:
            report["skipped"].append({"file": rel, "reason": "empty stub — re-author in Phase 1 design"})
            continue

        # ── Fallback: keep as free page
        pages.append(FreePage(
            slug=slug, title=title, breadcrumb=breadcrumb,
            body=body.strip(), hero=meta.get("hero_original", ""),
            source_url=meta.get("source_url", ""),
        ))
        report["pages"] += 1

    report["ensembles"] = len(ensembles)

    # ── Emit ──────────────────────────────────────────────────────────────
    if args.dry:
        print(json.dumps(report, indent=2))
        return

    # Wipe & rewrite output dirs we own
    for sub in ("ensembles", "programs", "seasons", "directors", "pages"):
        d = OUT_DIR / sub
        if d.exists():
            for p in d.glob("*.md"):
                p.unlink()
        d.mkdir(parents=True, exist_ok=True)

    for ens in ensembles.values():
        # slug is the filename — Astro derives entry.slug automatically, so we
        # omit it from frontmatter to satisfy the collection schema.
        d = asdict(ens); d.pop("slug", None)
        write_entry(OUT_DIR / "ensembles" / f"{ens.slug}.md", d, body="")

    for i, p in enumerate(programs):
        # filename: YYYY-MM-DD_ensemble-slug or fallback to index
        fname = (p.date_iso or f"undated-{i:03d}") + f"_{p.ensemble_slug}.md"
        data = asdict(p)
        # Pieces become list of dicts already via asdict
        write_entry(OUT_DIR / "programs" / fname, data)

    for s in seasons:
        write_entry(OUT_DIR / "seasons" / f"{s.year_range}.md", asdict(s))

    for d in directors:
        write_entry(OUT_DIR / "directors" / f"{d.slug}.md", {
            "name": d.name, "role": d.role,
            "photo": d.photo, "email": d.email,
        }, body=d.bio)

    for p in pages:
        write_entry(OUT_DIR / "pages" / f"{p.slug}.md", {
            "title": p.title,
            "breadcrumb": p.breadcrumb, "source_url": p.source_url, "hero": p.hero,
        }, body=p.body)

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"✓ wrote {report['ensembles']} ensembles, {report['programs']} programs, "
          f"{report['seasons']} seasons, {report['directors']} directors, {report['pages']} pages")
    print(f"  report → {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
