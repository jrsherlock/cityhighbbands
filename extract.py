#!/usr/bin/env python3
"""
cityhighband.com -> modern-site seed content exporter.

Crawls every URL in sitemap.xml, extracts content per Jimdo module,
converts to Markdown with frontmatter, downloads images, builds site map.
"""
import os, re, json, time, hashlib, urllib.parse, pathlib, sys
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify as md

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
SITE = "https://www.cityhighband.com"
EXPORT = pathlib.Path("/home/claude/chb_export")
PAGES = EXPORT / "pages"
ASSETS = EXPORT / "assets" / "images"
PAGES.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)

CRAWL_DELAY = 5.0  # respect robots.txt
image_cache = {}   # url -> local relative path


def fetch(url, binary=False):
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urlopen(req, timeout=30) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", errors="replace")


def url_to_path(url):
    """Map https://.../foo/bar/  ->  foo/bar.md  (and homepage -> index.md)."""
    p = urllib.parse.urlparse(url).path.strip("/")
    if not p:
        return "index.md"
    parts = p.split("/")
    # Trailing slash: last part is the page name in its parent folder
    # We rebuild as parts[0..-1]/parts[-1].md so /concert-bands/symphony-band/ -> concert-bands/symphony-band.md
    return "/".join(parts) + ".md"


def slugify(s):
    s = re.sub(r"[^\w\-]+", "-", s.strip().lower())
    return re.sub(r"-+", "-", s).strip("-")


def download_image(img_url):
    """Download an image once, cache it, return relative path from a page file."""
    if not img_url or img_url.startswith("data:"):
        return None
    # Normalize Jimdo CDN URLs (drop transf cropping params to get originals when possible)
    norm = img_url
    if norm in image_cache:
        return image_cache[norm]
    try:
        parsed = urllib.parse.urlparse(norm)
        # Try to get a sensible filename
        basename = os.path.basename(parsed.path) or "image"
        if not re.search(r"\.(jpe?g|png|gif|webp|svg|bmp)$", basename, re.I):
            basename = basename + ".jpg"
        # Hash to dedupe and avoid collisions
        h = hashlib.sha1(norm.encode()).hexdigest()[:10]
        safe_name = f"{h}-{slugify(os.path.splitext(basename)[0])[:60]}{os.path.splitext(basename)[1].lower()}"
        local = ASSETS / safe_name
        if not local.exists():
            data = fetch(norm, binary=True)
            local.write_bytes(data)
        rel = "/assets/images/" + safe_name
        image_cache[norm] = rel
        return rel
    except Exception as e:
        print(f"   ! image fetch failed: {img_url} ({e})")
        return None


def decode_cf_email(hex_str):
    """Decode Cloudflare's /cdn-cgi/l/email-protection#<hex> obfuscated emails."""
    try:
        r = int(hex_str[:2], 16)
        return "".join(chr(int(hex_str[i:i+2], 16) ^ r) for i in range(2, len(hex_str), 2))
    except Exception:
        return None


def unprotect_emails(soup):
    """Replace Cloudflare-obfuscated email links with real mailto: links."""
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/cdn-cgi/l/email-protection" in href:
            hex_part = href.split("#", 1)[1] if "#" in href else ""
            email = decode_cf_email(hex_part)
            if email:
                a["href"] = f"mailto:{email}"
                if a.get_text(strip=True) in ("[email protected]", ""):
                    a.string = email
    # Inline obfuscated spans: <a class="__cf_email__" data-cfemail="...">...
    for span in soup.find_all(attrs={"data-cfemail": True}):
        email = decode_cf_email(span["data-cfemail"])
        if email:
            span.replace_with(email)


def extract_page(html, source_url):
    """Pull a Jimdo page apart into {title, h1, breadcrumb, modules, raw_md}."""
    soup = BeautifulSoup(html, "lxml")
    unprotect_emails(soup)
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""
    # Strip the " - The School That Leads" suffix
    page_title = re.sub(r"\s*-\s*The School That Leads\s*$", "", page_title).strip()

    # Meta description
    desc = ""
    md_tag = soup.find("meta", attrs={"name": "description"})
    if md_tag and md_tag.get("content"):
        desc = md_tag["content"].strip()

    # OG image (used as the page hero on many Jimdo themes)
    og_image = ""
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        og_image = og["content"].strip()

    content = soup.find(id="content_area")
    if not content:
        return {"title": page_title, "description": desc, "og_image": og_image,
                "blocks": [], "images": []}

    blocks = []
    images = []
    h1_found = None

    for mod in content.select(".j-module"):
        classes = mod.get("class", [])
        kind = next((c for c in classes if c.startswith("j-") and c != "j-module"), "j-unknown")

        if kind == "j-text":
            # Convert the module's HTML to Markdown; drop edit/admin scriptlets
            for s in mod.find_all(["script", "style"]):
                s.decompose()
            html_chunk = str(mod)
            # Rewrite image src in this chunk via download
            chunk_soup = BeautifulSoup(html_chunk, "lxml")
            for img in chunk_soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src:
                    src = urllib.parse.urljoin(source_url, src)
                    local = download_image(src)
                    if local:
                        img["src"] = local
                        images.append({"original": src, "local": local, "alt": img.get("alt","")})
            # Rewrite internal links to relative .md paths (best-effort)
            for a in chunk_soup.find_all("a"):
                href = a.get("href")
                if href and href.startswith(SITE):
                    a["href"] = urllib.parse.urlparse(href).path
            md_text = md(str(chunk_soup), heading_style="ATX", bullets="-").strip()
            # Capture first H1 we see as the page's primary H1
            for h1 in chunk_soup.find_all("h1"):
                if not h1_found:
                    h1_found = h1.get_text(strip=True)
            if md_text:
                blocks.append({"type": "text", "markdown": md_text})

        elif kind == "j-imageSubtitle":
            img = mod.find("img")
            caption_el = mod.find(class_=re.compile("caption|subtitle"))
            src = None
            alt = ""
            if img:
                src = img.get("src") or img.get("data-src")
                alt = img.get("alt", "")
            if src:
                src = urllib.parse.urljoin(source_url, src)
                local = download_image(src)
                if local:
                    caption = caption_el.get_text(strip=True) if caption_el else ""
                    blocks.append({"type": "image", "src": local, "alt": alt, "caption": caption,
                                   "original": src})
                    images.append({"original": src, "local": local, "alt": alt, "caption": caption})

        elif kind == "j-hr":
            blocks.append({"type": "hr"})

        elif kind in ("j-spacing", "j-spacer"):
            continue

        else:
            # Unknown / less-common module: render as Markdown best-effort
            for s in mod.find_all(["script", "style"]):
                s.decompose()
            chunk_soup = BeautifulSoup(str(mod), "lxml")
            for img in chunk_soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src:
                    src = urllib.parse.urljoin(source_url, src)
                    local = download_image(src)
                    if local:
                        img["src"] = local
                        images.append({"original": src, "local": local, "alt": img.get("alt","")})
            for a in chunk_soup.find_all("a"):
                href = a.get("href")
                if href and href.startswith(SITE):
                    a["href"] = urllib.parse.urlparse(href).path
            md_text = md(str(chunk_soup), heading_style="ATX", bullets="-").strip()
            if md_text:
                blocks.append({"type": kind, "markdown": md_text})

    return {"title": page_title or h1_found or "",
            "h1": h1_found or page_title,
            "description": desc,
            "og_image": og_image,
            "blocks": blocks,
            "images": images}


def render_markdown(meta, page):
    """Combine blocks into a single Markdown file with YAML frontmatter."""
    fm = ["---"]
    fm.append(f"title: {json.dumps(page['title'])}")
    fm.append(f"slug: {json.dumps(meta['slug'])}")
    fm.append(f"source_url: {json.dumps(meta['url'])}")
    if page.get("description"):
        fm.append(f"description: {json.dumps(page['description'])}")
    if page.get("og_image"):
        fm.append(f"hero_original: {json.dumps(page['og_image'])}")
    fm.append(f"breadcrumb: {json.dumps(meta['breadcrumb'])}")
    fm.append(f"depth: {meta['depth']}")
    fm.append("---")
    fm.append("")

    body = []
    if page.get("h1"):
        body.append(f"# {page['h1']}")
        body.append("")
    for b in page["blocks"]:
        if b["type"] == "text":
            body.append(b["markdown"])
            body.append("")
        elif b["type"] == "image":
            cap = f" \"{b['caption']}\"" if b.get("caption") else ""
            alt = b.get("alt") or b.get("caption") or ""
            body.append(f"![{alt}]({b['src']}{cap})")
            body.append("")
        elif b["type"] == "hr":
            body.append("---")
            body.append("")
        else:
            body.append(b.get("markdown", ""))
            body.append("")
    return "\n".join(fm + body).rstrip() + "\n"


def main():
    tree = ET.parse("/home/claude/chb/sitemap.xml")
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [u.text for u in tree.getroot().findall("sm:url/sm:loc", ns)]

    # Optional CLI: start_index end_index (1-indexed inclusive)
    start = int(sys.argv[1]) - 1 if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else len(urls)
    urls_slice = urls[start:end]
    print(f"Crawling URLs {start+1}..{end} of {len(urls)} from sitemap")

    site_map = []
    failures = []

    for i, url in enumerate(urls_slice, start + 1):
        rel_path = url_to_path(url)
        parts = rel_path[:-3].split("/") if rel_path != "index.md" else ["index"]
        slug = parts[-1]
        breadcrumb = parts[:-1] if parts != ["index"] else []
        depth = len(breadcrumb)
        out = PAGES / rel_path

        # Skip if already exported with non-trivial content
        if out.exists() and out.stat().st_size > 400:
            print(f"[{i:>2}/{len(urls)}] SKIP (already exported) {url}")
            site_map.append({"url": url, "path": rel_path, "title": "", "skipped": True,
                             "breadcrumb": breadcrumb, "depth": depth})
            continue
        try:
            print(f"[{i:>2}/{len(urls)}] {url}")
            html = fetch(url)
            page = extract_page(html, url)
            meta = {"url": url, "slug": slug, "breadcrumb": breadcrumb, "depth": depth}
            text = render_markdown(meta, page)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text)
            site_map.append({
                "url": url,
                "path": rel_path,
                "title": page["title"],
                "description": page.get("description", ""),
                "breadcrumb": breadcrumb,
                "depth": depth,
                "image_count": len(page["images"]),
                "block_count": len(page["blocks"]),
            })
        except Exception as e:
            print(f"   ! FAILED: {e}")
            failures.append({"url": url, "error": str(e)})
        if i < end:
            time.sleep(CRAWL_DELAY)

    # Merge into existing site-map if present
    site_map_file = EXPORT / "site-map.json"
    if site_map_file.exists():
        existing = json.loads(site_map_file.read_text())
        by_url = {e["url"]: e for e in existing}
        for e in site_map:
            by_url[e["url"]] = e
        site_map = [by_url[u] for u in urls if u in by_url]
    site_map_file.write_text(json.dumps(site_map, indent=2))

    if failures:
        (EXPORT / "failures.json").write_text(json.dumps(failures, indent=2))

    print(f"\nDone with slice. {len(site_map)} pages tracked, {len(failures)} failures, {len(image_cache)} images this run.")


if __name__ == "__main__":
    main()
