#!/usr/bin/env python3
"""Render the complete Sleep Hubs review site from the portfolio CSVs."""
from __future__ import annotations
import csv, html, json, re, shutil
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent
DOMAIN = Path(r"C:\Users\Max\Max OS\projects\private_domain_portfolio\sleephubs.com")
POSTS = DOMAIN / "sleephubs_posts.csv"
PAGES = DOMAIN / "sleephubs_pages_content.csv"
IMAGE_DIR = DOMAIN / "sleephubs_images"
MANIFEST = SITE / ".generated-manifest.json"

NAVY, ORANGE, MIST = "#16324A", "#F4772C", "#F7F8F9"
CSS = f"""
:root{{--navy:{NAVY};--orange:{ORANGE};--mist:{MIST};--ink:#243746;--line:#dfe6eb}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;color:var(--ink);font-family:Montserrat,Arial,sans-serif;line-height:1.7}}a{{color:inherit}}a:hover{{color:var(--orange)}}a:focus-visible,button:focus-visible{{outline:3px solid var(--orange);outline-offset:3px}}.wrap{{width:min(1180px,calc(100% - 40px));margin:auto}}.top{{background:var(--navy);color:#fff;text-align:center;padding:8px;font-size:12px;font-weight:700}}header{{background:#fff;border-bottom:1px solid var(--line)}}.head{{min-height:78px;display:flex;align-items:center;justify-content:space-between;gap:24px}}.brand{{display:flex;align-items:center;gap:10px;text-decoration:none;font-size:22px;font-weight:800}}.mark{{width:38px;height:38px;border-radius:10px;background:var(--navy);color:#fff;display:grid;place-items:center;font-weight:800}}nav{{display:flex;gap:24px;align-items:center;font-size:14px;font-weight:700}}nav a{{text-decoration:none}}.hero{{background:linear-gradient(120deg,#eef4f7 0%,#fff 65%);padding:82px 0}}.eyebrow{{color:var(--orange);font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}}h1,h2,h3{{color:var(--navy);letter-spacing:-.04em;line-height:1.1}}.hero h1,.title{{font-size:clamp(40px,6vw,72px);max-width:900px;margin:14px 0 20px}}.hero p{{font-size:19px;max-width:700px}}.button{{display:inline-block;background:var(--orange);color:#fff!important;border-radius:5px;padding:12px 18px;margin-top:14px;text-decoration:none;font-weight:800}}.section{{padding:66px 0}}.alt{{background:var(--mist)}}.section h2{{font-size:42px;margin:0 0 12px}}.intro{{max-width:700px;color:#526675}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:28px}}.card{{border:1px solid var(--line);border-radius:10px;background:#fff;padding:24px;box-shadow:0 5px 18px #16324a12}}.card h3{{font-size:25px;margin:8px 0 12px}}.card p{{font-size:14px;color:#526675}}.card a{{font-weight:800;text-decoration-thickness:1px;text-underline-offset:4px}}.article-head{{background:var(--mist);padding:54px 0 44px}}.meta{{font-size:13px;color:#647785}}.article{{width:min(760px,calc(100% - 40px));margin:auto;padding:52px 0 80px;font-size:18px}}.article h2{{font-size:35px;margin:45px 0 15px}}.article h3{{font-size:26px;margin:32px 0 12px}}.article p{{margin:0 0 22px}}.article ul,.article ol{{padding-left:26px;margin-bottom:26px}}.article li{{margin:7px 0}}.article table{{width:100%;border-collapse:collapse;margin:28px 0;font-size:15px;display:block;overflow-x:auto}}.article th,.article td{{border:1px solid var(--line);padding:10px;text-align:left;vertical-align:top}}.article th{{background:#eef4f7;color:var(--navy)}}.article img{{max-width:100%;height:auto;border-radius:8px;margin:24px 0;display:block}}.article a{{color:#b64d16;font-weight:700;text-underline-offset:3px}}.listing{{padding:56px 0 80px}}.row{{display:grid;grid-template-columns:150px 1fr;gap:24px;padding:25px 0;border-bottom:1px solid var(--line)}}.row time{{color:#647785;font-size:13px}}.row h2{{font-size:29px;margin:0 0 8px}}.row h2 a{{text-decoration:none}}.row p{{color:#526675;margin:0}}.footer{{background:var(--navy);color:#dce7ee;padding:34px 0;margin-top:20px}}.foot{{display:flex;justify-content:space-between;gap:20px;align-items:center;font-size:13px}}.foot nav{{font-size:13px}}@media(max-width:760px){{.head{{align-items:flex-start;padding:16px 0;flex-wrap:wrap}}nav{{gap:12px;flex-wrap:wrap}}.hero{{padding:58px 0}}.grid{{grid-template-columns:1fr}}.row{{grid-template-columns:1fr;gap:4px}}.foot{{display:block}}.foot nav{{margin-top:15px}}.article{{font-size:17px}}}}
"""

def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))
def slug(v):
    v = html.unescape(v).lower().replace("’", "'")
    return re.sub(r"[^a-z0-9]+", "-", v).strip("-")
def date(v): return datetime.strptime(v.strip(), "%d/%m/%Y %H:%M" if ":" in v else "%d/%m/%Y")
def date_text(v):
    d=date(v); return f"{d.day} {d.strftime('%B %Y')}"
def plain(v): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", v)).strip()

def link_body(body, post_slugs, page_slugs):
    body = body.replace('""', '"')
    body = re.sub(r'(?i)(src|href)=["\'](?:[^"\']*\\)?sleephubs_images/', r'\1="images/', body)
    def fix(m):
        attr, val = m.group(1), m.group(2)
        if val.startswith(("http:", "https:", "#", "mailto:")): return m.group(0)
        if val == "blog" or val.startswith("blog/"):
            val = "/" + val.lstrip("/")
        elif val.rstrip("/") in post_slugs:
            val = "/blog/" + val.strip("/")
        elif val.rstrip("/") in page_slugs:
            val = "/" + val.strip("/")
        val = val.replace(".html", "")
        return f'{attr}="{val}"'
    body = re.sub(r'(href)=["\']([^"\']+)["\']', fix, body)
    return body

def shell(title, main, desc="Sleep Hubs: practical, evidence-aware ways to understand sleep and build steadier routines."):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} — Sleep Hubs</title><meta name="description" content="{html.escape(desc[:155])}"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap" rel="stylesheet"><style>{CSS}</style></head><body><div class="top">Practical sleep knowledge for ordinary life</div><header><div class="wrap head"><a class="brand" href="/"><span class="mark">S</span><span><span style="color:var(--orange)">Sleep</span>Hubs</span></a><nav aria-label="Main navigation"><a href="/">Home</a><a href="/blog">Articles</a><a href="/sleep-and-lifestyle-audit-checklist">Resources</a></nav></div></header>{main}<footer class="footer"><div class="wrap foot"><span>© 2026 Sleep Hubs</span><nav aria-label="Footer navigation"><a href="/">Home</a><a href="/blog">Articles</a><a href="/sleep-and-lifestyle-audit-checklist">Sleep checklist</a></nav></div></footer></body></html>'''

def article(row, kind, body):
    title = row['post_title'] if kind=='post' else row['page_title']; dt=row['post_date'] if kind=='post' else row['page_date']
    label='Field note' if kind=='post' else 'Sleep resource'
    main=f'<main><header class="article-head"><div class="wrap"><div class="eyebrow">{label}</div><h1 class="title">{html.escape(title)}</h1><div class="meta">Sleep Hubs · {date_text(dt)}</div></div></header><article class="article">{body}</article></main>'
    return shell(title, main, plain(body))

def build():
    posts, pages = rows(POSTS), rows(PAGES)
    post_map={slug(r['post_title']):r for r in posts}; page_map={slug(r['page_title']):r for r in pages}
    generated=[]
    for r in posts:
        p=SITE/'blog'/f"{slug(r['post_title'])}.html"; p.parent.mkdir(exist_ok=True)
        p.write_text(article(r,'post',link_body(r['post_content'],post_map,page_map)), encoding='utf-8'); generated.append(str(p.relative_to(SITE)))
    for r in pages:
        p=SITE/f"{slug(r['page_title'])}.html"; p.write_text(article(r,'page',link_body(r['page_content'],post_map,page_map)), encoding='utf-8'); generated.append(str(p.relative_to(SITE)))
    ordered=sorted(posts,key=lambda r:date(r['post_date']),reverse=True)
    cards=''.join(f'<article class="card"><div class="eyebrow">Field note</div><h3>{html.escape(r["post_title"])}</h3><p>{html.escape(plain(r["post_content"])[:180])}…</p><a href="/blog/{slug(r["post_title"])}">Read the article →</a></article>' for r in ordered[:3])
    guide=pages[0]
    home=f'<main><section class="hero"><div class="wrap"><div class="eyebrow">Lifestyle &amp; sleep</div><h1>Sleep better by noticing what your day is already telling you.</h1><p>Sleep Hubs brings together practical experiments, clear explanations, and simple tools for making sense of restless nights and steadier routines.</p><a class="button" href="/blog/{slug(ordered[0]["post_title"])}">Start with the latest field note</a></div></section><section class="section"><div class="wrap"><h2>Where to begin</h2><p class="intro">Choose one useful starting point. Read, test a small change, and pay attention to your own pattern.</p><div class="grid"><article class="card"><div class="eyebrow">Latest</div><h3>{html.escape(ordered[0]["post_title"])}</h3><p>{html.escape(plain(ordered[0]["post_content"])[:170])}…</p><a href="/blog/{slug(ordered[0]["post_title"])}">Read the field note →</a></article><article class="card"><div class="eyebrow">Resource</div><h3>{html.escape(guide["page_title"])}</h3><p>Use a short checklist to spot patterns across schedule, light, food, movement, and evening habits.</p><a href="/{slug(guide["page_title"])}">Open the checklist →</a></article><article class="card"><div class="eyebrow">Browse</div><h3>Sleep topics, without the noise</h3><p>Explore the full journal across caffeine, screens, schedules, stress, food, and family life.</p><a href="/blog">Browse all articles →</a></article></div></div></section><section class="section alt"><div class="wrap"><h2>Latest from Sleep Hubs</h2><p class="intro">Personal experiments and practical sleep knowledge for days that do not run to plan.</p><div class="grid">{cards}</div></div></section></main>'
    (SITE/'index.html').write_text(shell('Practical Sleep Knowledge',home),encoding='utf-8'); generated.append('index.html')
    listing=''.join(f'<article class="row"><time>{date_text(r["post_date"])}</time><div><h2><a href="/blog/{slug(r["post_title"])}">{html.escape(r["post_title"])}</a></h2><p>{html.escape(plain(r["post_content"])[:240])}…</p></div></article>' for r in ordered)
    (SITE/'blog.html').write_text(shell('Articles',f'<main><header class="article-head"><div class="wrap"><div class="eyebrow">The Sleep Hubs journal</div><h1 class="title">Practical notes for steadier nights</h1><p class="intro">Experiments, explanations, and small changes across the habits that shape sleep.</p></div></header><section class="listing"><div class="wrap">{listing}</div></section></main>'),encoding='utf-8'); generated.append('blog.html')
    cats={
      'sleep-disruptors-and-substances':['Caffeine','Alcohol','Sugar'], 'screens-light-and-evening-input':['Phone','Blue Light'],
      'exercise-and-body-routines':['Workout','Cold Shower'], 'work-travel-and-schedule-disruption':['Shift','Commute','Remote','Jet Lag'],
      'food-hydration-and-meal-timing':['Snacking','Hydration','Meal Timing','Fasting'], 'sleep-timing-stress-and-family-life':['Stress','Weekend','Napping','Parenting']}
    for cat, terms in cats.items():
        rs=[r for r in posts if any(t.lower() in (r['post_title']+r['source_topic']).lower() for t in terms)]
        body=''.join(f'<article class="row"><time>{date_text(r["post_date"])}</time><div><h2><a href="/blog/{slug(r["post_title"])}">{html.escape(r["post_title"])}</a></h2><p>{html.escape(plain(r["post_content"])[:220])}…</p></div></article>' for r in rs)
        p=SITE/'category'/f'{cat}.html'; p.parent.mkdir(exist_ok=True); p.write_text(shell(cat.replace('-',' ').title(),f'<main><header class="article-head"><div class="wrap"><div class="eyebrow">Category</div><h1 class="title">{html.escape(cat.replace("-"," ").title())}</h1></div></header><section class="listing"><div class="wrap">{body}</div></section></main>'),encoding='utf-8'); generated.append(str(p.relative_to(SITE)))
    (SITE/'images').mkdir(exist_ok=True)
    for image in IMAGE_DIR.glob('*'):
        if image.is_file(): shutil.copy2(image,SITE/'images'/image.name)
    urls=['https://sleephubs.com/','https://sleephubs.com/blog']+[f'https://sleephubs.com/{slug(r["page_title"])}' for r in pages]+[f'https://sleephubs.com/blog/{slug(r["post_title"])}' for r in posts]
    urls += [f'https://sleephubs.com/category/{c}' for c in cats]
    (SITE/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{u}</loc></url>\n' for u in urls)+'</urlset>\n',encoding='utf-8'); generated.append('sitemap.xml')
    ht=SITE/'.htaccess'
    if not ht.exists():
        ht.write_text('RewriteEngine On\nRewriteRule ^blog/?$ blog.html [L]\nRewriteCond %{REQUEST_FILENAME} !-f\nRewriteCond %{REQUEST_FILENAME} !-d\nRewriteCond %{DOCUMENT_ROOT}/$1.html -f\nRewriteRule ^(.+?)/?$ $1.html [L]\nRewriteCond %{THE_REQUEST} \\s/+(.+?)\\.html[\\s?] [NC]\nRewriteRule ^ /%1 [R=301,L,NE]\n',encoding='utf-8')
    generated.append('.htaccess')
    MANIFEST.write_text(json.dumps(sorted(set(generated)),indent=2),encoding='utf-8')
    print(f'Built homepage, blog, {len(posts)} posts, {len(pages)} pages, 6 categories, local images, sitemap, and clean URL rewrites.')
if __name__=='__main__': build()
