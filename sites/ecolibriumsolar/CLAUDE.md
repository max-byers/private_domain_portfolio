# ecolibriumsolar — Site-Specific Notes

## Content source
This site's copy is not written here — it's a one-time export from the
content pipeline in `projects/private_domain_portfolio/ecolibriumsolar.com/`.
That project remains the source of truth for content generation (topics,
scraping, drafting, style). This folder only holds the finished output,
shaped for dropping into HTML.

- `content/pages/<slug>.html` — evergreen page bodies, extracted from
  `ecolibriumsolar_pages_content.csv` (`page_content` column).
- `content/posts/<slug>.html` — blog post bodies, extracted from
  `ecolibriumsolar_posts.csv` (`post_content` column).
- `content/manifest.csv` — type/title/slug/status/date index for everything
  above, so you don't have to re-parse the source CSVs to know what exists.
- `content/images/` — copy of `ecolibriumsolar_images/`, including
  `ecolibriumsolar_image_placement.txt` (which image goes where, and why,
  per post) and `ecolibriumsolar_images_credits.csv` (attribution).

## Re-syncing content
If the portfolio project produces new/edited pages or posts, re-run the
same extraction (read the updated CSVs, write per-slug `.html` files into
`content/pages/` or `content/posts/`, refresh `manifest.csv`). This is a
one-directional sync: portfolio → site. Never write back into
`private_domain_portfolio/`, and never duplicate `serve.mjs` /
`screenshot.mjs` / `package.json` into the portfolio project — those stay
at the `website_building/` repo root per the parent `CLAUDE.md`.

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
