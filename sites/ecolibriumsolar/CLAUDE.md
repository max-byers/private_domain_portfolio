# ecolibriumsolar — Site-Specific Notes

## Content source
This site's copy is not written here, and is not cached here either — read
it live, at overlay time, straight from the content pipeline in
`projects/private_domain_portfolio/ecolibriumsolar.com/`. That project is
the single source of truth for both content generation (topics, scraping,
drafting, style) and the finished content itself. Do not copy, export, or
snapshot it into this folder:

- Pages — `ecolibriumsolar_pages_content.csv` (`page_title`, `page_content`,
  `page_status`, `page_date` columns).
- Posts — `ecolibriumsolar_posts.csv` (`post_title`, `post_content`,
  `post_status`, `post_date` columns).
- Images — `ecolibriumsolar_images/`, including
  `ecolibriumsolar_image_placement.txt` (which image goes where, and why,
  per post) and `ecolibriumsolar_images_credits.csv` (attribution).

Because there's no local copy, there's nothing to fall out of sync — a new
post, an edited `post_date`, or a status flip in the portfolio project is
picked up automatically the next time content is pulled in here. This is
still one-directional (portfolio → site): never write back into
`private_domain_portfolio/`, and never duplicate `serve.mjs` /
`screenshot.mjs` / `package.json` into the portfolio project — those stay
at the `website_building/` repo root per the parent `CLAUDE.md`.

**Stale artifacts:** `content/manifest.csv` and the per-slug files under
`content/pages/` and `content/posts/` were an earlier synced-copy approach
and are no longer kept up to date — treat the CSVs above as authoritative
if the two ever disagree. They have not been deleted yet; ask the user
before removing them.

## Scheduled publishing

This is a static, FTP-hosted site (no server logic), so a post's
`post_status`/`post_date` in `ecolibriumsolar_posts.csv` can't gate access
to a file that's already live on the host — the file simply can't exist
there yet. `publish.py` (this folder) handles that: it reads `post_status`/
`post_date` and `page_status`/`page_date` live from the portfolio CSVs,
decides what's due as of "now" (or `--as-of DATE` for testing), strips
nav/card/sidebar/sitemap references to not-yet-due posts out of every
top-level `.html` file plus `sitemap.xml`, and writes the result to
`_deploy/` (git/deploy-ignored, rebuilt fresh each run) — a snapshot of
only what should currently be public. `--upload` FTPs `_deploy/` to the
live host (credentials from `hosting_accounts.csv`); `--commit` flips
`post_status` from `future` to `published` in the source CSV for posts
just released. Run `python publish.py` with no flags for a status report
before doing either. See the script's own docstring for full usage.

The footer "Recent Posts" sidebar (every page) and the index.html
pull-quote's "Read the full story" link are both fully dynamic: each run,
they're regenerated from whichever posts are actually due, ranked by
`post_date` descending — top 3 for the sidebar, single most recent for the
featured link. Falls back to `blog.html` for the featured link, and an
empty list for the sidebar, if nothing is due yet.

## Design reference
Cloning the **blog post page** template from homesteadingfamily.com (not the
homepage — this site's content is posts/pages, not a landing page), captured
2026-08-08 via live browser inspection of
https://homesteadingfamily.com/how-to-handle-farm-fresh-eggs/:

- `reference/blog-post-01..06-*.jpg` — full page walked top to bottom
  (header/title/meta, body+image+subscribe box, body+callout+videos divider,
  H2 section, end-of-article CTA + popular posts, footer)
- `reference/devtools-computed-styles.txt` — colors, fonts, sizes, spacing,
  and a rundown of every recurring content block on the page

Build the post template against these before touching the page template —
ecolibriumsolar's finished content in `content/pages/` and `content/posts/`
is entirely long-form article copy, so the blog-post layout is the one that
matters most.
