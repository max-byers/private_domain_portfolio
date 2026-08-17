#!/usr/bin/env python3
"""Build and optionally upload the date-aware Boddhitree static site."""

from __future__ import annotations

import argparse
import csv
import ftplib
import importlib.util
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


SITE = Path(__file__).resolve().parent
DEPLOY = SITE / "_deploy"
PORTFOLIO = Path(r"C:\Users\Max\Max OS\projects\private_domain_portfolio")
DOMAIN = PORTFOLIO / "boddhitree.com"
POSTS_CSV = DOMAIN / "boddhitree_posts.csv"
PAGES_CSV = DOMAIN / "boddhitree_pages_content.csv"


def load_builder():
    spec = importlib.util.spec_from_file_location("boddhitree_build", SITE / "build_site.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_date(value: str) -> datetime:
    value = value.strip()
    return datetime.strptime(value, "%d/%m/%Y %H:%M" if ":" in value else "%d/%m/%Y")


def is_due(row: dict[str, str], as_of: datetime, kind: str) -> bool:
    status = row[f"{kind}_status"].strip().lower()
    return status == "published" or parse_date(row[f"{kind}_date"]) <= as_of


def remove_undue_blocks(source: str, slugs: set[str]) -> str:
    for slug in slugs:
        source = re.sub(rf'<article\b[^>]*data-content-slug="{re.escape(slug)}"[^>]*>.*?</article>', "", source, flags=re.S)
    return source


def latest_cards(due_posts: list[dict[str, str]], builder) -> str:
    selected = sorted(due_posts, key=lambda row: parse_date(row["post_date"]), reverse=True)[:3]
    return "".join(
        f'''<article class="card" data-content-slug="{builder.slugify(row['post_title'])}"><div class="eyebrow">Latest field note</div><h3>{__import__('html').escape(row['post_title'])}</h3><p>Read the latest practical note from the Boddhitree journal.</p><a href="{builder.slugify(row['post_title'])}">Read the article →</a></article>'''
        for row in selected
    )


def build(as_of: datetime) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    builder = load_builder()
    builder.build()
    post_rows = rows(POSTS_CSV)
    page_rows = rows(PAGES_CSV)
    due_posts = [r for r in post_rows if is_due(r, as_of, "post")]
    due_pages = [r for r in page_rows if is_due(r, as_of, "page")]
    undue_slugs = {builder.slugify(r["post_title"]) for r in post_rows if r not in due_posts}

    if DEPLOY.exists():
        shutil.rmtree(DEPLOY)
    DEPLOY.mkdir()
    for name in ["index.html", "blog.html", ".htaccess"]:
        text = (SITE / name).read_text(encoding="utf-8")
        if name.endswith(".html"):
            text = remove_undue_blocks(text, undue_slugs)
        if name == "index.html":
            text = re.sub(r'<!-- LATEST_POSTS_START -->.*?<!-- LATEST_POSTS_END -->', f'<!-- LATEST_POSTS_START -->{latest_cards(due_posts, builder)}<!-- LATEST_POSTS_END -->', text, flags=re.S)
        (DEPLOY / name).write_text(text, encoding="utf-8")
    for row in due_posts:
        name = f"{builder.slugify(row['post_title'])}.html"
        shutil.copy2(SITE / name, DEPLOY / name)
    for row in due_pages:
        name = f"{builder.slugify(row['page_title'])}.html"
        shutil.copy2(SITE / name, DEPLOY / name)

    # Copy only the local image assets referenced by pages in this deploy.
    # A valid <img> tag is not enough: the static upload must contain the file.
    image_sources: set[str] = set()
    for html_path in DEPLOY.glob("*.html"):
        image_sources.update(re.findall(r'<img\s+[^>]*src="([^"]+)"', html_path.read_text(encoding="utf-8")))
    for source in sorted(image_sources):
        if source.startswith(("http://", "https://", "//", "data:")):
            continue
        source_path = SITE / source
        if not source_path.is_file():
            raise FileNotFoundError(f"Referenced image is missing from the source site: {source}")
        destination = DEPLOY / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)

    urls = ["https://boddhitree.com/", "https://boddhitree.com/blog"]
    urls += [f"https://boddhitree.com/{builder.slugify(r['page_title'])}" for r in due_pages]
    urls += [f"https://boddhitree.com/{builder.slugify(r['post_title'])}" for r in due_posts]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{url}</loc></url>\n" for url in urls) + "</urlset>\n"
    (DEPLOY / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    return due_posts, due_pages


def credentials() -> tuple[str, str, str, str]:
    host = os.getenv("BODDHITREE_FTP_HOST", "")
    user = os.getenv("BODDHITREE_FTP_USER", "")
    password = os.getenv("BODDHITREE_FTP_PASSWORD", "")
    remote = os.getenv("BODDHITREE_FTP_REMOTE", "/public_html")
    accounts = PORTFOLIO / "hosting_accounts.csv"
    if accounts.exists():
        for row in rows(accounts):
            if row.get("Domain", "").strip().lower() == "boddhitree.com":
                host = host or row.get("FTP Hostname", "")
                user = user or row.get("Username", "")
                password = password or row.get("Password", "")
                remote = row.get("Remote Path", "") or remote
                break
    if not all([host, user, password]):
        raise SystemExit("FTP credentials are not recorded in hosting_accounts.csv. Add the Boddhitree row or set BODDHITREE_FTP_HOST, BODDHITREE_FTP_USER, and BODDHITREE_FTP_PASSWORD.")
    return host, user, password, remote


def upload() -> None:
    host, user, password, remote = credentials()
    with ftplib.FTP(host, user, password) as ftp:
        ftp.cwd(remote)
        for path in DEPLOY.rglob("*"):
            if path.is_file():
                with path.open("rb") as handle:
                    ftp.storbinary(f"STOR {path.relative_to(DEPLOY).as_posix()}", handle)


def commit_status(as_of: datetime) -> None:
    source = rows(POSTS_CSV)
    changed = False
    for row in source:
        if row["post_status"].strip().lower() == "future" and parse_date(row["post_date"]) <= as_of:
            row["post_status"] = "published"
            changed = True
    if changed:
        with POSTS_CSV.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=source[0].keys(), quoting=csv.QUOTE_ALL, lineterminator="\n")
            writer.writeheader(); writer.writerows(source)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--as-of", help="Local date/time in YYYY-MM-DD or YYYY-MM-DDTHH:MM format")
    args = parser.parse_args()
    as_of = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now()
    post_rows, page_rows = rows(POSTS_CSV), rows(PAGES_CSV)
    due_posts = [r for r in post_rows if is_due(r, as_of, "post")]
    due_pages = [r for r in page_rows if is_due(r, as_of, "page")]
    print(f"As of {as_of:%Y-%m-%d %H:%M}: {len(due_posts)}/{len(post_rows)} posts and {len(due_pages)}/{len(page_rows)} pages are due.")
    if args.build or args.upload:
        build(as_of)
        print(f"Deploy build ready: {DEPLOY}")
    if args.upload:
        upload(); print("Upload complete.")
    if args.commit:
        commit_status(as_of); print("Due post statuses committed to the source CSV.")


if __name__ == "__main__":
    main()
