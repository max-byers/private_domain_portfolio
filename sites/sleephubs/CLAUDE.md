# Sleep Hubs site

The source root is the complete approved site. `publish.py` reads the live content CSVs and creates `_deploy/`, containing only posts and pages due on the selected date. Future article files and their references are removed from blog, category, homepage, and sitemap surfaces.

Use `python publish.py --build` for today's deploy preview. Test dates with `--as-of YYYY-MM-DD`. Production is `python publish.py --build --upload --commit`; upload sends only `_deploy/`, and commit marks newly released posts as published after a successful upload.
