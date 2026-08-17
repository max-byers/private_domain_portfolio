# Boddhitree site

This is the coded static site for `boddhitree.com`. Content remains sourced live
from the portfolio CSVs in `private_domain_portfolio/boddhitree.com/`.

## Rebuilding content pages

Run `python build_site.py` from this folder. It regenerates the homepage, blog
listing, 20 post pages, standalone reference page, and complete sitemap using the
Boddhitree design system. Internal links are extensionless; on-disk files retain
their `.html` suffix and `.htaccess` supplies the clean URL rewrites.

## Scheduled publishing

`publish.py` prevents future posts from being uploaded early. It reads post and
page dates directly from the content CSVs on every run.

- `python publish.py` reports what is due without writing anything.
- `python publish.py --build` regenerates `_deploy/` with only due content and
  removes future-post cards from the homepage and blog index.
- `python publish.py --as-of 2027-01-01 --build` creates a historical/test build.
- `python publish.py --upload` rebuilds and uploads `_deploy/` by FTP.
- `python publish.py --commit` changes due `future` post rows to `published`.

The homepage latest-article grid has three slots when three or more posts are due;
future slots disappear until their dates arrive. Never upload the site folder
itself. Upload `_deploy/` only.
