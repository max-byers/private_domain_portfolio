"""Build and optionally upload the date-aware Sleep Hubs static release."""
import argparse, csv, ftplib, re, shutil, sys
from datetime import datetime
from html import escape
from pathlib import Path

SITE = Path(__file__).resolve().parent
DOMAIN_DIR = SITE.parents[2] / "private_domain_portfolio" / "sleephubs.com"
POSTS = DOMAIN_DIR / "sleephubs_posts.csv"
PAGES = DOMAIN_DIR / "sleephubs_pages_content.csv"
HOSTS = DOMAIN_DIR.parent / "hosting_accounts.csv"
DEPLOY = SITE / "_deploy"
DOMAIN = "sleephubs.com"
SKIP = {"reference", "temporary screenshots", "_deploy", "publish.py", "build_site.py", ".generated-manifest.json", "CLAUDE.md"}

def date(value):
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try: return datetime.strptime((value or "").strip(), fmt)
        except ValueError: pass
    return None

def slug(title): return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

def load(path, prefix):
    with path.open(newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
    return [{"title": r[f"{prefix}_title"], "slug": slug(r[f"{prefix}_title"]),
             "status": r[f"{prefix}_status"], "date": date(r[f"{prefix}_date"]), "row": r} for r in rows]

def due(item, now): return item["status"] == "published" or bool(item["date"] and item["date"] <= now)

def remove_future_refs(text, future):
    for s in future:
        path = "/blog/" + s
        text = re.sub(r'<article class="row">(?:(?!</article>).)*href="' + re.escape(path) + r'"(?:(?!</article>).)*</article>', "", text, flags=re.S)
        text = re.sub(r'<article class="card">(?:(?!</article>).)*href="' + re.escape(path) + r'"(?:(?!</article>).)*</article>', "", text, flags=re.S)
        text = re.sub(r'\s*<url><loc>https://(?:www\.)?sleephubs\.com' + re.escape(path) + r'</loc></url>', "", text)
    return text

def refresh_home(text, current):
    if not current: return re.sub(r'<a class="button" href="/blog/[^"]+">.*?</a>', '<a class="button" href="/blog">Browse the journal</a>', text)
    p = current[0]
    target = "/blog/" + p["slug"]
    text = re.sub(r'<a class="button" href="/blog/[^"]+">.*?</a>', f'<a class="button" href="{target}">Start with the latest field note</a>', text)
    # Future cards are removed first; this guarantees the hero CTA is never stale.
    return text

def build(posts, pages, now):
    current = sorted((p for p in posts if due(p, now)), key=lambda p: p["date"] or datetime.min, reverse=True)
    future = {p["slug"] for p in posts if not due(p, now)}
    page_due = {p["slug"] for p in pages if due(p, now)}
    post_slugs = {p["slug"] for p in posts}
    page_slugs = {p["slug"] for p in pages}
    if DEPLOY.exists(): shutil.rmtree(DEPLOY)
    DEPLOY.mkdir()
    for src in SITE.rglob("*"):
        rel = src.relative_to(SITE)
        if any(part in SKIP for part in rel.parts) or src.is_dir(): continue
        if rel.parts[0] == "blog" and src.stem in post_slugs and src.stem in future: continue
        if len(rel.parts) == 1 and src.stem in page_slugs and src.stem not in page_due: continue
        dst = DEPLOY / rel; dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in {".html", ".xml"}:
            text = remove_future_refs(src.read_text(encoding="utf-8"), future)
            if rel.as_posix() == "index.html": text = refresh_home(text, current)
            dst.write_text(text, encoding="utf-8")
        else: shutil.copy2(src, dst)
    print(f"Built _deploy: {len(current)}/{len(posts)} posts and {len(page_due)}/{len(pages)} pages due")
    return {p["slug"] for p in current}

def host_row():
    with HOSTS.open(newline="", encoding="utf-8") as f:
        return next(r for r in csv.DictReader(f) if r["Domain"] == DOMAIN)

def upload(remote="public_html"):
    h = host_row(); ftp = ftplib.FTP(h["FTP Hostname"], timeout=30); ftp.login(h["Username"], h["Password"]); ftp.cwd(remote)
    def put(local, prefix=""):
        for item in sorted(local.iterdir()):
            target = f"{prefix}/{item.name}" if prefix else item.name
            if item.is_dir():
                try: ftp.mkd(target)
                except ftplib.error_perm: pass
                put(item, target)
            else:
                with item.open("rb") as f: ftp.storbinary("STOR " + target, f)
                print("UPLOADED", target)
    put(DEPLOY); ftp.quit()

def commit(due_slugs):
    with POSTS.open(newline="", encoding="utf-8") as f: reader=csv.DictReader(f); fields=reader.fieldnames; rows=list(reader)
    changed=0
    for r in rows:
        if slug(r["post_title"]) in due_slugs and r["post_status"] != "published": r["post_status"]="published"; changed += 1
    with POSTS.open("w", newline="", encoding="utf-8") as f: w=csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL); w.writeheader(); w.writerows(rows)
    print(f"Marked {changed} newly released post(s) published")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--as-of"); ap.add_argument("--build", action="store_true"); ap.add_argument("--upload", action="store_true"); ap.add_argument("--commit", action="store_true"); ap.add_argument("--remote-dir", default="public_html"); a=ap.parse_args()
    now=datetime.strptime(a.as_of, "%Y-%m-%d") if a.as_of else datetime.now()
    posts, pages=load(POSTS,"post"), load(PAGES,"page")
    print(f"As of {now:%Y-%m-%d}: {sum(due(p,now) for p in posts)}/{len(posts)} posts due; {sum(due(p,now) for p in pages)}/{len(pages)} pages due")
    if not (a.build or a.upload): return
    released=build(posts,pages,now)
    newly={p["slug"] for p in posts if p["status"] != "published" and p["slug"] in released}
    if a.upload: upload(a.remote_dir)
    if a.commit:
        if not a.upload: print("Refusing --commit without --upload", file=sys.stderr); raise SystemExit(2)
        commit(newly)
if __name__ == "__main__": main()
