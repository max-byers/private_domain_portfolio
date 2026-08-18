#!/usr/bin/env python3
"""Build iprescribeexercise.com's static HTML from the portfolio CSV source of truth.

Deterministic: reads the domain CSVs live on every run and regenerates the complete
site. Preserves the cloned Tailwind design system from index.html /
shoulder-rehab-basics.html exactly (same brand colors/fonts/header/footer markup) --
only the content regions and homepage data-driven sections are generated.

Href normalization note: internal_linking_posts/money_linking wrote hrefs into the
CSVs as bare relative paths with a trailing slash (e.g.
"blog/joint-specific-pain/some-post/"). That only resolves correctly from a page at
site-root depth. Since this domain's rolled taxonomy nests posts two levels deep
(blog/<category>/<post>), a same-format relative link written *inside* another post
would resolve relative to that post's own directory, not the site root, and 404.
Fixed here at render time only (never in the CSV): every internal href is rewritten
to be root-anchored (leading "/") with no trailing slash, which resolves correctly
regardless of the depth of the page containing the link.
"""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent
DOMAIN = Path(r"C:\Users\Max\Max OS\projects\private_domain_portfolio\iprescribeexercise.com")
POSTS_CSV = DOMAIN / "iprescribeexercise_posts.csv"
PAGES_CSV = DOMAIN / "iprescribeexercise_pages_content.csv"
SITE_STRUCTURE_TXT = DOMAIN / "iprescribeexercise_site_structure.txt"
IMAGES_SRC = DOMAIN / "iprescribeexercise_images"
IMAGES_DEST = SITE / "images"
MANIFEST_PATH = SITE / ".build_manifest.json"

CATEGORY_LABELS = {
    "joint-specific-pain": "Joint Specific Pain",
    "reading-the-warning-signs": "Reading the Warning Signs",
    "recovery-and-rehab": "Recovery and Rehab",
    "smarter-training-approach": "Smarter Training Approach",
}
CATEGORY_ORDER = list(CATEGORY_LABELS)


def slugify(value: str) -> str:
    value = html.unescape(value).lower().replace("\u2019", "'")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_date(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%d/%m/%Y")


def is_due(status: str, date_str: str, as_of: datetime) -> bool:
    """Shared by build() (when as_of is passed) and publish.py's own due-checks,
    so there is exactly one definition of "due" for this site."""
    if (status or "").strip().lower() == "published":
        return True
    if date_str and date_str.strip():
        return parse_date(date_str) <= as_of
    return False


def display_date(value: str) -> str:
    d = parse_date(value)
    return d.strftime("%#d %B %Y") if hasattr(d, "strftime") else str(value)


def parse_categories(text: str) -> dict[str, str]:
    """Read the Categories tree out of iprescribeexercise_site_structure.txt so the
    post->category mapping stays live (not hand-duplicated) if the sitemap is ever
    regenerated with the same taxonomy shape."""
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip().startswith("iprescribeexercise.com/"))
    end = next(i for i, l in enumerate(lines) if l.strip().startswith("Category key"))
    block = lines[start + 1 : end]
    category_of: dict[str, str] = {}
    current_category = None
    in_blog = False
    for raw in block:
        if not raw.strip():
            continue
        m = re.match(r"^([\s\u2502]*)(\u251c\u2500\u2500|\u2514\u2500\u2500)\s*(.+?)/?\s*$", raw)
        if not m:
            continue
        indent, _, content = m.groups()
        depth = len(indent)
        if content == "blog":
            in_blog = True
            continue
        if not in_blog:
            continue
        if depth <= 4:
            current_category = content
        else:
            category_of[content] = current_category
    return category_of


HREF_RE = re.compile(r'href="([^"]+)"')


def normalize_hrefs(body: str) -> str:
    def repl(m: re.Match) -> str:
        href = m.group(1)
        if href.startswith(("http://", "https://", "mailto:", "#", "/")):
            return m.group(0)
        clean = href.rstrip("/")
        return f'href="/{clean}"'

    return HREF_RE.sub(repl, body)


IMG_RE = re.compile(r'src="iprescribeexercise_images/([^"]+)"')


def normalize_images(body: str) -> str:
    return IMG_RE.sub(lambda m: f'src="/images/{m.group(1)}"', body)


H1_RE = re.compile(r"^\s*<h1>(.*?)</h1>\s*", re.IGNORECASE | re.DOTALL)


def strip_leading_h1(body: str) -> str:
    return H1_RE.sub("", body, count=1)


def excerpt(body: str, length: int = 155) -> str:
    text = re.sub(r"<[^>]+>", " ", body)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:length].rsplit(" ", 1)[0] + "\u2026" if len(text) > length else text


HEAD = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Fira+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          brand: {
            teal: '#0492BF',
            'teal-dark': '#037A9E',
            red: '#D33939',
            'red-dark': '#B62E2E',
            ink: '#444444',
            mauve: '#C19393',
          }
        },
        fontFamily: {
          display: ['Poppins', 'sans-serif'],
          body: ['"Fira Sans"', 'sans-serif'],
        },
      }
    }
  }
</script>
<style>
  html { scroll-behavior: smooth; }
  body { font-family: 'Fira Sans', sans-serif; color: #444444; }
  h1, h2, h3, .font-display { font-family: 'Poppins', sans-serif; }
  .btn-red { transition: transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.15s ease; }
  .btn-red:hover { background-color: #B62E2E; transform: translateY(-1px); }
  .btn-red:active { transform: translateY(0); }
  .btn-red:focus-visible { outline: 2px solid #0492BF; outline-offset: 2px; }
  .nav-panel { transition: max-height 0.25s ease, opacity 0.2s ease; }
  .card-cta { transition: transform 0.15s ease, box-shadow 0.15s ease; }
  .card-cta:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -8px rgba(4,146,191,0.35); }
  .pill { transition: background-color 0.15s ease, color 0.15s ease; }
  .pill:hover { background-color: #0492BF; color: #fff; }
  .icon-btn:focus-visible, a:focus-visible, button:focus-visible, input:focus-visible {
    outline: 2px solid #0492BF; outline-offset: 2px;
  }
  .post-body a { color: #0492BF; }
  .post-body a:hover { color: #037A9E; }
  .post-body h2 { font-family: Poppins, sans-serif; font-weight: 700; font-size: 1.5rem; color: #444444; margin-top: 2.5rem; margin-bottom: 0.75rem; }
  .post-body h3 { font-family: Poppins, sans-serif; font-weight: 700; font-size: 1.25rem; color: #444444; margin-top: 2rem; margin-bottom: 0.5rem; }
  .post-body p { margin-bottom: 1.25rem; }
  .post-body ul { list-style: disc; padding-left: 1.25rem; margin-bottom: 1.25rem; }
  .post-body ol { list-style: decimal; padding-left: 1.25rem; margin-bottom: 1.25rem; }
  .post-body li + li { margin-top: 0.5rem; }
  .post-body img { width: 100%; border-radius: 2px; margin: 1.75rem 0; }
  .post-body table { width: 100%; border-collapse: collapse; margin: 1.75rem 0; font-size: 0.95rem; }
  .post-body th, .post-body td { border: 1px solid #e5e5e5; padding: 0.6rem 0.75rem; text-align: left; vertical-align: top; }
  .post-body th { background: #f7f7f7; font-family: Poppins, sans-serif; font-weight: 600; color: #444444; }
  .post-body dl { margin-bottom: 1.25rem; }
  .post-body dt { font-weight: 700; color: #444444; margin-top: 1rem; }
  .post-body dd { margin-left: 0; margin-bottom: 0.5rem; }
  .post-body blockquote { border-left: 3px solid #0492BF; padding-left: 1rem; margin: 1.5rem 0; font-style: italic; color: #555; }
  @media (prefers-reduced-motion: reduce) {
    * { transition-duration: 0.001ms !important; }
  }
</style>"""

HEADER = """<header class="bg-white relative z-30">
    <div class="max-w-6xl mx-auto px-5 py-5 flex items-center justify-between">
      <a href="/" class="block">
        <div class="font-display font-bold text-2xl sm:text-3xl leading-none tracking-tight">
          <span class="text-brand-ink">I PRESCRIBE</span><span class="text-brand-teal">EXERCISE</span>
        </div>
        <p class="text-[11px] sm:text-xs font-semibold tracking-[0.15em] text-gray-500 mt-1">
          TRAIN SMART &bull; PREVENT INJURY &bull; RECOVER STRONGER
        </p>
      </a>
      <div class="flex items-center gap-4">
        <button id="searchToggle" aria-label="Open search" aria-expanded="false" class="icon-btn text-brand-ink hover:text-brand-teal transition-colors rounded p-1">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </button>
        <button id="menuToggle" aria-label="Open menu" aria-expanded="false" class="icon-btn text-brand-teal hover:text-brand-teal-dark transition-colors rounded p-1">
          <svg id="menuIcon" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          <svg id="closeIcon" class="hidden" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>
        </button>
      </div>
    </div>

    <nav id="navPanel" class="nav-panel max-h-0 opacity-0 overflow-hidden bg-brand-teal">
      <ul class="max-w-6xl mx-auto px-5 py-6 flex flex-col gap-4 text-white font-display font-semibold uppercase tracking-wide text-sm">
        <li><a href="/#about" class="hover:text-white/70">About</a></li>
        <li><a href="/blog" class="hover:text-white/70">Blog</a></li>
        <li><a href="/#guides" class="hover:text-white/70">Guides</a></li>
        <li><a href="/#newsletter" class="hover:text-white/70">Join the List</a></li>
      </ul>
    </nav>

    <div id="searchOverlay" class="hidden fixed inset-0 bg-brand-teal z-40 flex items-start justify-center">
      <div class="w-full max-w-xl mt-32 sm:mt-48 px-6">
        <div class="relative border-b border-white/50 pb-3">
          <input type="text" placeholder="Search..." class="w-full bg-transparent text-white placeholder-white/70 text-2xl font-body outline-none" />
          <button id="searchClose" aria-label="Close search" class="absolute right-0 top-0 text-white/80 hover:text-white">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>
          </button>
        </div>
      </div>
    </div>
  </header>"""

SCRIPT = """<script>
    const menuToggle = document.getElementById('menuToggle');
    const navPanel = document.getElementById('navPanel');
    const menuIcon = document.getElementById('menuIcon');
    const closeIcon = document.getElementById('closeIcon');
    let menuOpen = false;
    menuToggle.addEventListener('click', () => {
      menuOpen = !menuOpen;
      menuToggle.setAttribute('aria-expanded', String(menuOpen));
      if (menuOpen) {
        navPanel.style.maxHeight = navPanel.scrollHeight + 'px';
        navPanel.style.opacity = '1';
        menuIcon.classList.add('hidden');
        closeIcon.classList.remove('hidden');
      } else {
        navPanel.style.maxHeight = '0px';
        navPanel.style.opacity = '0';
        menuIcon.classList.remove('hidden');
        closeIcon.classList.add('hidden');
      }
    });

    const searchToggle = document.getElementById('searchToggle');
    const searchOverlay = document.getElementById('searchOverlay');
    const searchClose = document.getElementById('searchClose');
    searchToggle.addEventListener('click', () => {
      searchOverlay.classList.remove('hidden');
      searchToggle.setAttribute('aria-expanded', 'true');
      searchOverlay.querySelector('input').focus();
    });
    searchClose.addEventListener('click', () => {
      searchOverlay.classList.add('hidden');
      searchToggle.setAttribute('aria-expanded', 'false');
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        searchOverlay.classList.add('hidden');
        searchToggle.setAttribute('aria-expanded', 'false');
      }
    });
  </script>"""


def footer(featured_pages: list[dict], categories: list[str]) -> str:
    guide_items = "".join(
        f'<li><a href="/{slugify(p["page_title"])}" class="hover:text-white">{html.escape(p["page_title"])}</a></li>'
        for p in featured_pages
    )
    topic_items = "".join(
        f'<li><a href="/blog/{c}" class="hover:text-white">{html.escape(CATEGORY_LABELS[c])}</a></li>'
        for c in categories
    )
    return f"""<footer class="bg-brand-teal text-white">
    <div class="max-w-6xl mx-auto px-5 py-14 grid sm:grid-cols-3 gap-10">
      <div>
        <p class="font-display font-bold text-sm tracking-wide mb-4">PAGES</p>
        <ul class="space-y-3 text-white/90">
          <li><a href="/#about" class="hover:text-white">About</a></li>
          <li><a href="/blog" class="hover:text-white">Blog</a></li>
          <li><a href="/#guides" class="hover:text-white">Guides</a></li>
          <li><a href="/#newsletter" class="hover:text-white">Join the List</a></li>
        </ul>
      </div>
      <div>
        <p class="font-display font-bold text-sm tracking-wide mb-4">GUIDES</p>
        <ul class="space-y-3 text-white/90">{guide_items}</ul>
      </div>
      <div>
        <p class="font-display font-bold text-sm tracking-wide mb-4">TOPICS</p>
        <ul class="space-y-3 text-white/90">{topic_items}</ul>
      </div>
    </div>
    <div class="border-t border-white/25">
      <div class="max-w-6xl mx-auto px-5 py-8 flex flex-col items-center gap-4 text-center">
        <div class="flex items-center gap-4">
          <a href="#" aria-label="Instagram" class="icon-btn w-9 h-9 rounded-full border border-white/60 flex items-center justify-center hover:bg-white/10">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1"/></svg>
          </a>
          <a href="#" aria-label="YouTube" class="icon-btn w-9 h-9 rounded-full border border-white/60 flex items-center justify-center hover:bg-white/10">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="3"/><polygon points="10,9 15,12 10,15" fill="white" stroke="none"/></svg>
          </a>
          <a href="#" aria-label="Twitter" class="icon-btn w-9 h-9 rounded-full border border-white/60 flex items-center justify-center hover:bg-white/10">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="white" stroke="none"><path d="M22 5.9c-.7.3-1.5.5-2.3.6.8-.5 1.5-1.3 1.8-2.3-.8.5-1.7.8-2.6 1a4.1 4.1 0 0 0-7 3.7A11.6 11.6 0 0 1 3.4 4.6a4 4 0 0 0 1.3 5.4c-.6 0-1.3-.2-1.8-.5v.1c0 2 1.4 3.6 3.3 4a4.1 4.1 0 0 1-1.8.1 4.1 4.1 0 0 0 3.8 2.8A8.2 8.2 0 0 1 2 18.4a11.6 11.6 0 0 0 6.3 1.8c7.5 0 11.7-6.3 11.7-11.7v-.5c.8-.6 1.5-1.3 2-2.1z"/></svg>
          </a>
        </div>
        <p class="text-xs text-white/80 uppercase tracking-wide">I Prescribe Exercise is reader supported</p>
        <p class="text-xs text-white/80 uppercase tracking-wide">Copyright &copy; 2026 iprescribeexercise.com</p>
      </div>
    </div>
  </footer>"""


def chrome(title: str, main: str, description: str, footer_html: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
{HEAD}
</head>
<body class="bg-white">
  {HEADER}
{main}
  {footer_html}
  {SCRIPT}
</body>
</html>"""


def render_article(
    title: str,
    raw_body: str,
    date_str: str,
    breadcrumb_href: str,
    breadcrumb_label: str,
    related: list[tuple[str, str]],
    pill: str | None,
) -> str:
    body = strip_leading_h1(raw_body)
    body = normalize_hrefs(body)
    body = normalize_images(body)
    related_html = "".join(
        f'<li><a href="{href}" class="hover:text-brand-teal-dark">{html.escape(label)}</a></li>'
        for href, label in related
    )
    pill_html = f'<a href="#" class="pill bg-gray-100 text-brand-ink text-sm font-medium px-4 py-2 rounded-full">{html.escape(pill)}</a>' if pill else ""
    main = f"""
  <div class="max-w-3xl mx-auto px-5 pt-6">
    <nav class="text-sm text-brand-ink" aria-label="Breadcrumb">
      <a href="/" class="hover:text-brand-teal">Home</a>
      <span class="mx-1 text-gray-400">&raquo;</span>
      <a href="{breadcrumb_href}" class="hover:text-brand-teal">{html.escape(breadcrumb_label)}</a>
      <span class="mx-1 text-gray-400">&raquo;</span>
      <span class="text-gray-500">{html.escape(title)}</span>
    </nav>
  </div>
  <header class="max-w-3xl mx-auto px-5 pt-4">
    <h1 class="font-display font-bold text-[32px] leading-[1.15] sm:text-[42px] sm:leading-[1.15] text-brand-ink">
      {html.escape(title)}
    </h1>
    <p class="text-sm mt-4">
      <span class="text-gray-500 uppercase">Posted {display_date(date_str)} by</span>
      <span class="font-semibold text-brand-teal">I Prescribe Exercise</span>
    </p>
  </header>
  <article class="post-body max-w-3xl mx-auto px-5 py-10 text-base sm:text-lg leading-relaxed">
    {body}
  </article>
  <div class="max-w-3xl mx-auto px-5 pb-10">
    <div class="border-t border-gray-200 pt-8">
      <p class="text-xs font-display font-semibold tracking-wide text-gray-500 mb-3">RELATED</p>
      <ul class="flex flex-wrap gap-x-6 gap-y-2 text-brand-teal font-display font-semibold text-sm">{related_html}</ul>
    </div>
    <div class="flex items-center justify-between flex-wrap gap-4 mt-6">
      {pill_html}
    </div>
  </div>
  <section class="relative">
    <div class="absolute inset-0 bg-gradient-to-br from-brand-ink to-black"></div>
    <div class="relative max-w-6xl mx-auto px-5 py-16 sm:py-20">
      <div class="max-w-xl">
        <p class="text-white text-2xl sm:text-3xl font-display font-semibold leading-snug mb-4">
          Not sure where to start? Get matched to the right guide.
        </p>
        <p class="text-white/85 text-base leading-relaxed mb-8">
          Tell me what hurts and how it started, and I'll point you to the exact guide that
          fits &mdash; no account needed, no upsell.
        </p>
        <a href="/#newsletter" class="btn-red inline-block bg-brand-red text-white font-display font-bold uppercase tracking-wide text-sm px-8 py-4 rounded-sm">
          Find Your Starting Point &rarr;
        </a>
      </div>
    </div>
  </section>"""
    return main, excerpt(body)


def build(output_dir: Path = SITE, manifest_path: Path | None = None, as_of: datetime | None = None) -> None:
    """as_of=None (default, used by `python build_site.py`) renders every post/page
    regardless of date -- the complete review site. Passing as_of filters to only
    posts/pages due by that moment (see is_due), for publish.py's pruned _deploy/
    build -- same rendering code path either way, so a due post's page is byte-for-
    byte identical whether it's reached via the complete build or the deploy one."""
    manifest_path = manifest_path or (output_dir / ".build_manifest.json")
    images_dest = output_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    posts = read_rows(POSTS_CSV)
    pages = read_rows(PAGES_CSV)
    if as_of is not None:
        posts = [r for r in posts if is_due(r.get("post_status", ""), r.get("post_date", ""), as_of)]
        pages = [r for r in pages if is_due(r.get("page_status", ""), r.get("page_date", ""), as_of)]
    category_of = parse_categories(SITE_STRUCTURE_TXT.read_text(encoding="utf-8"))

    for r in posts:
        r["_slug"] = slugify(r["post_title"])
        r["_category"] = category_of[r["_slug"]]
        r["_href"] = f"/blog/{r['_category']}/{r['_slug']}"
    for r in pages:
        r["_slug"] = slugify(r["page_title"])
        r["_href"] = f"/{r['_slug']}"

    posts_by_category: dict[str, list[dict]] = {c: [] for c in CATEGORY_ORDER}
    for r in posts:
        posts_by_category[r["_category"]].append(r)
    for c in posts_by_category:
        posts_by_category[c].sort(key=lambda r: parse_date(r["post_date"]))

    # ---- manifest cleanup: remove files generated by a prior run before writing new ones ----
    previous_manifest: list[str] = []
    if manifest_path.exists():
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for rel in previous_manifest:
        p = output_dir / rel
        if p.exists() and p.is_file():
            p.unlink()
    # remove now-empty category directories from a prior run
    blog_dir = output_dir / "blog"
    if blog_dir.is_dir():
        for sub in blog_dir.iterdir():
            if sub.is_dir() and not any(sub.iterdir()):
                sub.rmdir()

    generated: list[str] = []

    def write(rel_path: str, content: str) -> None:
        p = output_dir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        generated.append(rel_path)

    # ---- copy images ----
    images_dest.mkdir(exist_ok=True)
    all_content = "".join(r["post_content"] for r in posts) + "".join(r["page_content"] for r in pages)
    referenced = set(re.findall(r"iprescribeexercise_images/([^\"]+)", all_content))
    copied = 0
    for name in referenced:
        src = IMAGES_SRC / name
        dest = images_dest / name
        if src.exists():
            shutil.copyfile(src, dest)
            copied += 1

    featured_page_slugs = [
        "is-it-soreness-or-is-it-an-injury",
        "warming-up-before-you-lift-what-actually-works",
        "deload-weeks-when-and-how-to-back-off-on-purpose",
        "should-you-train-today-a-decision-guide-for-rough-mornings",
    ]
    featured_pages = [p for slug in featured_page_slugs for p in pages if p["_slug"] == slug]
    footer_html = footer(featured_pages, CATEGORY_ORDER)

    # ---- posts ----
    for r in posts:
        siblings = [s for s in posts_by_category[r["_category"]] if s["_slug"] != r["_slug"]][:3]
        related = [(s["_href"], s["post_title"]) for s in siblings]
        main, desc = render_article(
            r["post_title"], r["post_content"], r["post_date"],
            f"/blog/{r['_category']}", CATEGORY_LABELS[r["_category"]],
            related, CATEGORY_LABELS[r["_category"]],
        )
        write(f"blog/{r['_category']}/{r['_slug']}.html", chrome(f"{r['post_title']} \u2014 I Prescribe Exercise", main, desc, footer_html))

    # ---- pages ----
    for r in pages:
        siblings = [s for s in pages if s["_slug"] != r["_slug"]][:3]
        related = [(s["_href"], s["page_title"]) for s in siblings]
        main, desc = render_article(
            r["page_title"], r["page_content"], r["page_date"],
            "/blog", "Guides",
            related, None,
        )
        write(f"{r['_slug']}.html", chrome(f"{r['page_title']} \u2014 I Prescribe Exercise", main, desc, footer_html))

    # ---- category listing pages ----
    for cat in CATEGORY_ORDER:
        rows = sorted(posts_by_category[cat], key=lambda r: parse_date(r["post_date"]), reverse=True)
        items = "".join(
            f'''<li class="py-6 border-b border-gray-200">
        <a href="{r['_href']}" class="font-display font-semibold text-lg text-brand-ink hover:text-brand-teal">{html.escape(r['post_title'])}</a>
        <p class="text-sm text-gray-500 mt-1">{display_date(r['post_date'])}</p>
        <p class="text-base text-gray-600 mt-2">{html.escape(excerpt(strip_leading_h1(r['post_content']), 180))}</p>
      </li>'''
            for r in rows
        )
        main = f"""
  <div class="max-w-3xl mx-auto px-5 pt-10 pb-4">
    <p class="text-xs font-display font-semibold tracking-wide text-brand-teal mb-2">TOPIC</p>
    <h1 class="font-display font-bold text-[32px] sm:text-[42px] text-brand-ink">{html.escape(CATEGORY_LABELS[cat])}</h1>
  </div>
  <div class="max-w-3xl mx-auto px-5 pb-16">
    <ul>{items}</ul>
    <a href="/blog" class="inline-block text-brand-teal font-semibold text-sm mt-8 hover:text-brand-teal-dark">&larr; ALL POSTS</a>
  </div>"""
        write(f"blog/{cat}.html", chrome(f"{CATEGORY_LABELS[cat]} \u2014 I Prescribe Exercise", main, f"Posts on {CATEGORY_LABELS[cat].lower()}.", footer_html))

    # ---- blog index ----
    ordered_all = sorted(posts, key=lambda r: parse_date(r["post_date"]), reverse=True)
    pills = "".join(
        f'<a href="/blog/{c}" class="pill bg-gray-100 text-brand-ink text-sm font-medium px-4 py-2 rounded-full">{html.escape(CATEGORY_LABELS[c])}</a>'
        for c in CATEGORY_ORDER
    )
    items = "".join(
        f'''<li class="py-6 border-b border-gray-200">
        <a href="{r['_href']}" class="font-display font-semibold text-lg text-brand-ink hover:text-brand-teal">{html.escape(r['post_title'])}</a>
        <p class="text-sm text-gray-500 mt-1">{display_date(r['post_date'])} &bull; {html.escape(CATEGORY_LABELS[r['_category']])}</p>
        <p class="text-base text-gray-600 mt-2">{html.escape(excerpt(strip_leading_h1(r['post_content']), 180))}</p>
      </li>'''
        for r in ordered_all
    )
    blog_main = f"""
  <div class="max-w-3xl mx-auto px-5 pt-10 pb-4">
    <h1 class="font-display font-bold text-[32px] sm:text-[42px] text-brand-ink">All Posts</h1>
    <div class="flex flex-wrap gap-2 mt-6 mb-2">{pills}</div>
  </div>
  <div class="max-w-3xl mx-auto px-5 pb-16">
    <ul>{items}</ul>
  </div>"""
    write("blog.html", chrome("Blog \u2014 I Prescribe Exercise", blog_main, "Every injury recovery and prevention guide on I Prescribe Exercise.", footer_html))

    # ---- homepage ----
    latest3 = ordered_all[:3]
    latest_items = "".join(
        f'''<li class="py-4 flex items-start gap-3">
          <span class="text-brand-teal mt-1">&#9656;</span>
          <div>
            <a href="{r['_href']}" class="font-display font-semibold text-brand-ink hover:text-brand-teal">{html.escape(r['post_title'])}</a>
            <p class="text-sm text-gray-500 mt-1">{display_date(r['post_date'])}</p>
          </div>
        </li>'''
        for r in latest3
    )
    _hero_match = re.search(r'iprescribeexercise_images/([^"]+)', posts[0]["post_content"]) if posts else None
    hero_img = f"/images/{_hero_match.group(1)}" if _hero_match else ""
    card_colors = ["brand-mauve", "brand-teal", "gray-700", "brand-red"]
    card_images = ["shoulder_discipline_1_7289370.jpeg", "warmup_first_set_1_6295709.jpeg", "tendon_pain_1_421160.jpeg", "return_after_layoff_1_11161583.jpeg"]
    cards = ""
    for i, p in enumerate(featured_pages):
        cards += f"""
    <div class="card-cta">
      <div class="bg-{card_colors[i % 4]} rounded-sm overflow-hidden">
        <img src="/images/{card_images[i % 4]}" alt="{html.escape(p['page_title'])}" class="w-full h-auto object-cover" style="max-height:280px" />
      </div>
      <h3 class="font-display font-semibold text-lg text-brand-ink mt-5">{html.escape(p['page_title'])}</h3>
      <p class="text-base leading-relaxed mt-2 max-w-2xl">{html.escape(excerpt(strip_leading_h1(p['page_content']), 160))}</p>
      <a href="{p['_href']}" class="btn-red inline-block bg-brand-red text-white font-display font-bold uppercase text-xs tracking-wide px-6 py-3 rounded-sm mt-4">
        Read The Guide
      </a>
    </div>"""
    topic_pills = "".join(
        f'<a href="/blog/{c}" class="pill bg-gray-100 text-brand-ink text-sm font-medium px-4 py-2 rounded-full">{html.escape(CATEGORY_LABELS[c])}</a>'
        for c in CATEGORY_ORDER
    )

    home_main = f"""
  <section class="max-w-6xl mx-auto px-5 pt-6 pb-10">
    <h1 class="font-display font-bold text-[32px] leading-[1.15] sm:text-[42px] sm:leading-[1.2] text-brand-ink max-w-2xl">
      Tired of getting hurt every time you push hard?
    </h1>
    <div class="w-16 h-[3px] bg-brand-red mt-5 mb-8"></div>
    <div class="relative rounded-sm overflow-hidden">
      <img src="{hero_img}" alt="Training around an old injury" class="w-full h-auto object-cover" style="max-height:500px" />
      <div class="absolute top-4 left-4 bg-black/80 text-white text-xs sm:text-sm rounded-sm overflow-hidden flex items-center shadow-lg">
        <span class="w-9 h-9 sm:w-10 sm:h-10 bg-brand-teal flex items-center justify-center shrink-0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="white"><circle cx="12" cy="12" r="4"/></svg>
        </span>
        <span class="px-3 py-2 font-semibold">Welcome to I Prescribe Exercise</span>
      </div>
    </div>
  </section>

  <section id="about" class="max-w-6xl mx-auto px-5 pb-14">
    <div class="max-w-2xl">
      <p class="text-base sm:text-lg leading-relaxed mb-6">
        I spent years training through pain instead of training around it, and it cost me
        more time on the sidelines than any single hard workout ever earned me. I'm not
        credentialed. I learned anatomy, rehab protocols, and program design the hard way,
        working through my own overuse injuries with physical therapists. Every week I send
        one honest lesson on avoiding the mistake I already made, so you don't have to.
      </p>
    </div>
    <form class="max-w-2xl grid gap-3" onsubmit="return false;" id="newsletter">
      <input type="text" placeholder="First Name" class="w-full border border-gray-300 rounded-sm px-4 py-3 text-base focus:outline-none focus:border-brand-teal" />
      <input type="email" placeholder="Email" class="w-full border border-gray-300 rounded-sm px-4 py-3 text-base focus:outline-none focus:border-brand-teal" />
      <button class="btn-red w-full bg-brand-red text-white font-display font-bold uppercase tracking-wide text-sm py-4 rounded-sm">
        Count Me In!
      </button>
    </form>
  </section>

  <section class="bg-brand-teal">
    <div class="max-w-6xl mx-auto px-5 py-8">
      <div class="relative border-b border-white/40 pb-3 max-w-2xl">
        <input type="text" placeholder="Search..." class="w-full bg-transparent text-white placeholder-white/70 text-lg font-body outline-none" />
      </div>
      <p class="text-white font-display font-semibold mt-4 text-base sm:text-lg">
        Trying to train around an injury? Search the archive.
      </p>
    </div>
  </section>

  <section class="max-w-6xl mx-auto px-5 py-14">
    <div class="flex items-center gap-3 mb-10">
      <h2 class="font-display text-2xl sm:text-3xl text-brand-ink">What Readers Are <span class="font-bold">Saying</span></h2>
      <div class="hidden sm:block flex-1 h-px bg-gray-300"></div>
    </div>
    <div class="grid sm:grid-cols-2 gap-10">
      <div>
        <p class="italic text-lg leading-relaxed mb-4">
          "I'd been babying my shoulder for two years because I didn't know which pains
          were 'fine' and which ones weren't. Your breakdown was the first thing that
          actually made that distinction clear."
        </p>
        <div class="flex items-center gap-3">
          <span class="w-12 h-12 rounded-full bg-brand-mauve text-white font-display font-bold flex items-center justify-center">D</span>
          <span class="font-semibold text-brand-ink">Dana</span>
        </div>
      </div>
      <div>
        <p class="italic text-lg leading-relaxed mb-4">
          "Followed the return-to-lifting protocol after a low back flare up. Zero
          re-injuries, and I'm stronger now than before it happened. Wish I'd found this
          years earlier."
        </p>
        <div class="flex items-center gap-3">
          <span class="w-12 h-12 rounded-full bg-brand-teal text-white font-display font-bold flex items-center justify-center">M</span>
          <span class="font-semibold text-brand-ink">Marcus</span>
        </div>
      </div>
    </div>
  </section>

  <section id="guides" class="max-w-6xl mx-auto px-5 pb-6">
    <div class="flex items-center gap-3 mb-4">
      <h2 class="font-display text-2xl sm:text-3xl text-brand-ink">Injury <span class="font-bold">Guides</span></h2>
      <div class="hidden sm:block flex-1 h-px bg-gray-300"></div>
    </div>
    <p class="text-base sm:text-lg leading-relaxed max-w-2xl mb-2">
      Written from the recovery side, not the theory side &mdash; what actually caused each
      injury, and the exact way back to training without repeating it.
    </p>
    <a href="/blog" class="inline-block text-brand-teal font-semibold text-sm mt-2 hover:text-brand-teal-dark">
      CHECK OUT ALL THE GUIDES &rarr;
    </a>
  </section>

  <section class="max-w-6xl mx-auto px-5 py-8 space-y-14">
    {cards}
  </section>

  <section class="bg-gray-50 mt-10">
    <div class="max-w-6xl mx-auto px-5 py-14">
      <p class="font-display font-bold text-sm tracking-wide text-brand-ink mb-6">LATEST FROM THE BLOG:</p>
      <ul class="divide-y divide-gray-300 max-w-2xl">{latest_items}</ul>
      <a href="/blog" class="inline-block text-brand-teal font-semibold text-sm mt-6 hover:text-brand-teal-dark">ALL POSTS &rarr;</a>
    </div>
  </section>

  <section class="max-w-6xl mx-auto px-5 py-14">
    <div class="flex items-center gap-3 mb-6">
      <h2 class="font-display text-2xl sm:text-3xl text-brand-ink">Explore More <span class="font-bold">Injury Topics</span></h2>
      <div class="hidden sm:block flex-1 h-px bg-gray-300"></div>
    </div>
    <p class="text-xs font-display font-semibold tracking-wide text-gray-500 mb-3">TOPICS</p>
    <div class="flex flex-wrap gap-2 mb-8">{topic_pills}</div>
    <p class="text-xs font-display font-semibold tracking-wide text-gray-500 mb-3">SEARCH</p>
    <div class="relative border-b border-gray-300 pb-3 max-w-md">
      <input type="text" placeholder="Search..." class="w-full bg-transparent text-brand-ink placeholder-gray-400 text-base outline-none" />
    </div>
  </section>

  <section class="relative">
    <div class="absolute inset-0 bg-gradient-to-br from-brand-ink to-black"></div>
    <div class="relative max-w-6xl mx-auto px-5 py-16 sm:py-20">
      <div class="max-w-xl">
        <p class="text-white text-2xl sm:text-3xl font-display font-semibold leading-snug mb-4">
          Not sure where to start? Get matched to the right guide.
        </p>
        <p class="text-white/85 text-base leading-relaxed mb-8">
          Tell me what hurts and how it started, and I'll point you to the exact guide that
          fits &mdash; no account needed, no upsell.
        </p>
        <a href="/#newsletter" class="btn-red inline-block bg-brand-red text-white font-display font-bold uppercase tracking-wide text-sm px-8 py-4 rounded-sm">
          Find Your Starting Point &rarr;
        </a>
      </div>
    </div>
  </section>"""
    write("index.html", chrome("I Prescribe Exercise \u2014 Train Smart, Prevent Injury, Recover Stronger", home_main, "Injury recovery and prevention guidance from a reformed over trainer.", footer_html))

    # ---- sitemap.xml ----
    base = "https://iprescribeexercise.com"
    urls = [f"{base}/", f"{base}/blog"] + [f"{base}{p['_href']}" for p in pages] + [f"{base}/blog/{c}" for c in CATEGORY_ORDER] + [f"{base}{r['_href']}" for r in posts]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n"
    write("sitemap.xml", sitemap)

    # ---- .htaccess ----
    htaccess = """RewriteEngine On

# Redirect any request still carrying .html to the clean extensionless URL.
RewriteCond %{THE_REQUEST} \\s/+([^.\\s?]+)\\.html[\\s?] [NC]
RewriteRule ^ /%1 [R=301,L]

# Serve real files/directories directly.
RewriteCond %{REQUEST_FILENAME} -f [OR]
RewriteCond %{REQUEST_FILENAME} -d
RewriteRule ^ - [L]

# Serve the matching .html file for a clean URL request without exposing the extension.
RewriteCond %{DOCUMENT_ROOT}/$1.html -f
RewriteRule ^(.+?)/?$ $1.html [L]
"""
    write(".htaccess", htaccess)

    manifest_path.write_text(json.dumps(sorted(generated), indent=2), encoding="utf-8")

    print(
        f"Built {len(posts)} posts, {len(pages)} pages, {len(CATEGORY_ORDER)} category listings, "
        f"blog index, homepage, sitemap.xml, .htaccess. Copied {copied} images (of {len(referenced)} referenced)."
    )


if __name__ == "__main__":
    build()
