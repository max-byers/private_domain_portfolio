"""
Release script for ecolibriumsolar.com.

Static site, FTP-hosted, no server logic -- so "scheduling" a post means:
don't put its file on the live host, and don't link to it from anywhere,
until its post_date arrives. This script reads post/page status and dates
live from the private_domain_portfolio project (the source of truth, per
that project's CLAUDE.md), decides what's due as of a given moment, strips
not-yet-due posts out of the site's nav/card/sidebar/sitemap chrome, and
writes a "_deploy" folder containing only what should currently be public.

Usage:
    python publish.py                         # report only, no writes
    python publish.py --build                  # write _deploy/ locally
    python publish.py --build --upload          # also FTP _deploy/ to the live host
    python publish.py --build --upload --commit # also flip post_status future -> published
    python publish.py --as-of 2026-10-01        # pretend "now" is this date (testing)

--upload and --commit touch the live site / source CSV and are not run automatically.
"""

import argparse
import csv
import ftplib
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent
PORTFOLIO_DIR = SITE_DIR.parents[2] / "private_domain_portfolio" / "ecolibriumsolar.com"
POSTS_CSV = PORTFOLIO_DIR / "ecolibriumsolar_posts.csv"
PAGES_CSV = PORTFOLIO_DIR / "ecolibriumsolar_pages_content.csv"
HOSTING_CSV = PORTFOLIO_DIR.parent / "hosting_accounts.csv"
DEPLOY_DIR = SITE_DIR / "_deploy"
DOMAIN = "ecolibriumsolar.com"

DATE_FORMATS = ("%d/%m/%Y %H:%M", "%d/%m/%Y")

# Files/dirs at the site root that are source material, not deployable output.
NON_DEPLOY_NAMES = {"reference", "temporary screenshots", "CLAUDE.md", "publish.py", "_deploy", "content"}


def parse_date(value):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value!r}")


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def load_items(csv_path, title_col, status_col, date_col):
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    items = []
    for row in rows:
        title = row[title_col]
        items.append({
            "title": title,
            "slug": slugify(title),
            "status": row[status_col],
            "date": parse_date(row[date_col]),
            "row": row,
        })
    return items


def is_due(item, as_of):
    if item["status"] == "published":
        return True
    if item["date"] is not None and item["date"] <= as_of:
        return True
    return False


# ---- HTML chrome patterns shared across every page in the site ----
# These match the site-wide nav dropdown, card grid, and footer "Recent
# Posts" sidebar blocks that reference a post by its slug. They're read
# from the live template files each run, not hardcoded here, so hand
# edits to blog.html/index.html/etc. keep working as long as the
# href="<slug>.html" convention holds.

def nav_item_pattern(slug):
    return re.compile(
        r'[ \t]*<a href="' + re.escape(slug) + r'\.html" class="block py-2 pl-4[^"]*">[^<]*</a>\s*\n'
    )


RECENT_POSTS_RE = re.compile(
    r'(<h3 class="font-sans font-bold text-white text-lg mb-5">Recent Posts</h3>\s*'
    r'<ul class="space-y-4 text-white/80 leading-snug">)([\s\S]*?)(</ul>)'
)

FEATURED_LINK_RE = re.compile(
    r'(<a href=")[a-z0-9-]+(\.html" class="link-underline link-underline-static '
    r'font-semibold text-brand-green hover:text-white transition-colors">'
    r'Read the full story &rarr;</a>)'
)


def render_recent_posts_items(due_posts_by_recency, limit=3):
    lines = []
    for p in due_posts_by_recency[:limit]:
        title = p["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(
            f'            <li><a href="{p["slug"]}.html" '
            f'class="link-underline hover:text-brand-green transition-colors">{title}</a></li>'
        )
    return "\n".join(lines)


def replace_recent_posts(html_text, due_posts_by_recency):
    # Regenerated fresh each run from whichever posts are actually due, ranked
    # by post_date descending -- not a fixed, hand picked list of slugs.
    items_html = render_recent_posts_items(due_posts_by_recency)
    inner = ("\n" + items_html + "\n          ") if items_html else "\n          "
    return RECENT_POSTS_RE.sub(lambda m: m.group(1) + inner + m.group(3), html_text)


def replace_featured_link(html_text, due_posts_by_recency):
    # index.html's homepage pull-quote always points at the most recently
    # due post; falls back to the blog index if nothing is due yet.
    target = due_posts_by_recency[0]["slug"] if due_posts_by_recency else "blog"
    return FEATURED_LINK_RE.sub(lambda m: m.group(1) + target + m.group(2), html_text)


def card_block_pattern(slug):
    return re.compile(
        r'[ \t]*<a href="' + re.escape(slug) + r'\.html" class="card-lift[\s\S]*?</a>\s*\n'
    )


def sitemap_url_pattern(slug):
    return re.compile(
        r'[ \t]*<url><loc>https://www\.ecolibriumsolar\.com/' + re.escape(slug) + r'\.html</loc></url>\s*\n'
    )


def apply_post_chrome(html_text, posts, as_of):
    due_by_recency = sorted(
        (p for p in posts if is_due(p, as_of)),
        key=lambda p: p["date"] or datetime.min,
        reverse=True,
    )
    not_due_slugs = {p["slug"] for p in posts if not is_due(p, as_of)}

    for slug in not_due_slugs:
        html_text = nav_item_pattern(slug).sub("", html_text)
        html_text = card_block_pattern(slug).sub("", html_text)
        html_text = sitemap_url_pattern(slug).sub("", html_text)

    html_text = replace_recent_posts(html_text, due_by_recency)
    html_text = replace_featured_link(html_text, due_by_recency)
    return html_text


def build_deploy(posts, pages, as_of, verbose=True):
    due_posts = {p["slug"] for p in posts if is_due(p, as_of)}
    not_due_posts = {p["slug"] for p in posts if not is_due(p, as_of)}
    due_pages = {p["slug"] for p in pages if is_due(p, as_of)}

    if DEPLOY_DIR.exists():
        shutil.rmtree(DEPLOY_DIR)
    DEPLOY_DIR.mkdir()

    post_slugs = {p["slug"] for p in posts}
    page_slugs = {p["slug"] for p in pages}

    for entry in sorted(SITE_DIR.iterdir()):
        name = entry.name
        if name in NON_DEPLOY_NAMES or name.startswith("."):
            continue

        if entry.is_dir():
            shutil.copytree(entry, DEPLOY_DIR / name)
            continue

        stem = entry.stem
        if stem in post_slugs and stem not in due_posts:
            if verbose:
                print(f"  SKIP  {name}  (not due yet)")
            continue
        if stem in page_slugs and stem not in due_pages:
            if verbose:
                print(f"  SKIP  {name}  (page not published)")
            continue

        if entry.suffix == ".html" or name == "sitemap.xml":
            text = entry.read_text(encoding="utf-8")
            text = apply_post_chrome(text, posts, as_of)
            (DEPLOY_DIR / name).write_text(text, encoding="utf-8")
        else:
            shutil.copy2(entry, DEPLOY_DIR / name)

    if verbose:
        print(f"\n_deploy/ built with {len(due_posts)}/{len(posts)} posts due, {len(due_pages)}/{len(pages)} pages due.")
    return due_posts, not_due_posts


def load_hosting_row():
    with open(HOSTING_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Domain"] == DOMAIN:
                return row
    raise SystemExit(f"No hosting_accounts.csv row found for {DOMAIN}")


def upload(remote_dir="/"):
    host_row = load_hosting_row()
    ftp = ftplib.FTP(host_row["FTP Hostname"])
    ftp.login(host_row["Username"], host_row["Password"])
    if remote_dir != "/":
        ftp.cwd(remote_dir)

    def upload_dir(local_dir, remote_path):
        for entry in sorted(local_dir.iterdir()):
            target = f"{remote_path}/{entry.name}" if remote_path else entry.name
            if entry.is_dir():
                try:
                    ftp.mkd(target)
                except ftplib.error_perm:
                    pass  # already exists
                upload_dir(entry, target)
            else:
                with open(entry, "rb") as f:
                    ftp.storbinary(f"STOR {target}", f)
                print(f"  UPLOADED  {target}")

    upload_dir(DEPLOY_DIR, "")
    ftp.quit()


def commit_status(newly_due_posts):
    if not newly_due_posts:
        return
    with open(POSTS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    changed = 0
    for row in rows:
        slug = slugify(row["post_title"])
        if slug in newly_due_posts and row["post_status"] != "published":
            row["post_status"] = "published"
            changed += 1
    with open(POSTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Marked {changed} post(s) as published in {POSTS_CSV.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--as-of", help="Pretend 'now' is this date (YYYY-MM-DD), for testing.")
    parser.add_argument("--build", action="store_true", help="Write the _deploy/ folder locally.")
    parser.add_argument("--upload", action="store_true", help="FTP _deploy/ contents to the live host.")
    parser.add_argument("--remote-dir", default="/", help="Remote FTP directory to upload into (default: FTP root).")
    parser.add_argument("--commit", action="store_true", help="Flip post_status future->published for posts released this run.")
    args = parser.parse_args()

    as_of = datetime.strptime(args.as_of, "%Y-%m-%d") if args.as_of else datetime.now()

    posts = load_items(POSTS_CSV, "post_title", "post_status", "post_date")
    pages = load_items(PAGES_CSV, "page_title", "page_status", "page_date")

    print(f"As of {as_of:%Y-%m-%d %H:%M}:")
    for p in sorted(posts, key=lambda p: p["date"] or datetime.min):
        state = "DUE" if is_due(p, as_of) else "not due"
        date_str = p["date"].strftime("%d/%m/%Y %H:%M") if p["date"] else "(none)"
        print(f"  [{state:8}] {p['title']}  ({p['status']}, {date_str})")

    if not args.build and not args.upload:
        print("\n(report only -- pass --build to write _deploy/, --upload to push it live)")
        return

    due_posts, not_due_posts = build_deploy(posts, pages, as_of)

    newly_due = set()
    if args.upload:
        # Posts that are due now but still marked "future" in the CSV are the
        # ones this release is actually making live for the first time.
        newly_due = {p["slug"] for p in posts if p["status"] != "published" and p["slug"] in due_posts}
        print(f"\nUploading _deploy/ to {DOMAIN} ...")
        upload(remote_dir=args.remote_dir)
        print("Upload complete.")

    if args.commit:
        if not args.upload:
            print("\n--commit without --upload: updating post_status without anything actually being live. Skipping.", file=sys.stderr)
        else:
            commit_status(newly_due)


if __name__ == "__main__":
    main()
