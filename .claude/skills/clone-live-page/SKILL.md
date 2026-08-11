---
name: clone-live-page
description: Capture a design reference by pulling it live from a real URL (via Chrome browser automation) instead of from a screenshot the user provided. Use whenever the user wants to clone/copy a page (homepage, blog listing, blog post, pricing page, etc.) from a live website and no reference image already exists in sites/<name>/reference/ — e.g. "clone the blog page from X.com", "copy the design of Y's homepage", "grab a reference from this live site", "go pull the post template from <url>". Not needed if a static reference image/screenshot has already been supplied — that's the normal CLAUDE.md reference-image workflow, not this one.
---

# Clone Live Page

Turns a live URL into the same kind of reference asset this repo normally works
from (a screenshot in `sites/<name>/reference/`), so the standard CLAUDE.md
build-and-compare loop can take over. This is the "no reference image exists yet"
precursor step — it does not replace the match/compare/placeholder rules in
`CLAUDE.md`, it just produces what those rules need to work from.

## Step 0: Confirm this is actually needed

Check `sites/<name>/reference/` first. If a usable screenshot or reference image
is already there, skip this skill entirely and go straight to the normal
CLAUDE.md workflow. This skill is only for when the source is a live page and
nothing has been captured from it yet.

Figure out the target folder: an existing `sites/<name>/` if cloning another
page for a site already in this repo, or a new `sites/<name>/` if this is the
first page from that site.

## Step 1: Load browser tools and capture the page

Load the Chrome tools in one batch (see the `claude-in-chrome` MCP instructions
for the exact `ToolSearch` call), then navigate to the target URL.

Capture the full page top to bottom with `browser_batch`, alternating
scroll + screenshot so you get section-by-section coverage — don't just grab
the first viewport. Batch several scroll/screenshot pairs per call rather than
one at a time.

Gotchas specific to this environment:
- The Chrome extension side panel eats a large chunk of window width, so
  `resize_window` to a "desktop" size will not actually get you a wide desktop
  viewport — `window.innerWidth` tends to cap around 750–900px CSS pixels
  regardless of how wide you resize the window. Treat what you capture as a
  mobile/tablet-width reference and use ordinary Tailwind responsive judgment
  (`sm:`/`lg:` breakpoints) for how the layout should widen on desktop, rather
  than fighting the tool for a wider capture.
- Cookie banners, ad slots, and "update privacy preferences" widgets will show
  up in screenshots. These are not part of the site's design — ignore them
  when transcribing colors/layout, and don't reproduce them.

**Save the screenshots into `sites/<name>/reference/`, not just the
conversation.** Number them in reading order (e.g.
`blog-post-01-header-title-meta.jpg`, `...-02-...`) so a future session can
open the folder and understand the page without re-crawling the live site.
Viewing screenshots inline during the session and then not persisting them is
a wasted crawl — the whole point is that the next clone (or the next session
of this one) doesn't have to repeat Step 1.

## Step 2: Extract exact colors, type, and spacing via computed styles

Screenshots alone lose exact hex values, font stacks, and pixel sizes. Use
`javascript_tool` to read `getComputedStyle()` on the key elements (headings,
body copy, buttons, cards, dividers, nav) rather than eyeballing them from
pixels. A helper like this, run per element of interest, keeps it fast:

```js
function cs(el, props) {
  if (!el) return null;
  const s = getComputedStyle(el);
  const out = {};
  props.forEach(p => out[p] = s[p]);
  const r = el.getBoundingClientRect();
  out.rect = { w: Math.round(r.width), h: Math.round(r.height) };
  return out;
}
```

Pull font-family/size/weight/line-height/color for each heading level and body
text, background/text/border color for buttons and cards, and border-radius /
padding / gap for anything structural. Cross-check colors against any
`tailwind.config` already defined in a sibling page in the same site folder —
if the hex values match exactly (they usually will, since it's the same
brand), that confirms the existing color/font tokens and components can be
reused as-is rather than re-derived.

Gotcha: don't dump full `outerHTML` or raw `style` attributes containing image
URLs through the JS tool — query strings in URLs can trip a content filter
(`[BLOCKED: Cookie/query string data]`). Pull specific computed-style
properties instead of serializing whole elements.

**Save the findings as a text file in `sites/<name>/reference/`**, organized
under headings like `COLORS`, `TYPOGRAPHY`, `LAYOUT`, and
`RECURRING CONTENT BLOCKS` (see `sites/ecolibriumsolar/reference/devtools-computed-styles.txt`
for the format this repo already uses). This is the artifact that lets a
future build match the live site without re-opening a browser.

## Step 3: Hand off to the normal build workflow

Once `sites/<name>/reference/` has screenshots + a computed-styles note, stop
— this skill's job is done. From here, follow `CLAUDE.md` as usual:
`frontend-design` skill, reuse any header/footer/components already
established by sibling pages in the same site folder, build against
`localhost` via `serve.mjs`, and run at least 2 screenshot-compare rounds via
`screenshot.mjs` before calling it done.

If the new page needs real content or images sourced from another project in
this repo (not just this live-site reference), copy those assets into this
site's own folder — sites stay self-contained and never reference each other's
files directly.
