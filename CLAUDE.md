# CLAUDE.md — Frontend Website Rules

## Always Do First
- **Invoke the `frontend-design` skill** before writing any frontend code, every session, no exceptions.

## Reference Images
- If a reference image is provided: match layout, spacing, typography, and color exactly. Swap in placeholder content (images via `https://placehold.co/`, generic copy). Do not improve or add to the design.
- If no reference image: design from scratch with high craft (see guardrails below).
- Screenshot your output, compare against reference, fix mismatches, re-screenshot. Do at least 2 comparison rounds. Stop only when no visible differences remain or user says so.

## Multi-Site Structure
- This repo holds multiple independent site clones under `sites/<site-name>/`.
- Each site folder is fully self-contained (its own `index.html`, inline styles/JS, own `reference/` and `temporary screenshots/`). Sites never import or reference each other's files.
- Only dev-time tooling (`serve.mjs`, `screenshot.mjs`, `package.json`) is shared at the repo root — none of it ships with any site.
- Reference material for a clone (source screenshots, DevTools notes) goes in `sites/<site-name>/reference/`.

## Finding an Existing Site (before concluding one doesn't exist)
- Never trust a bare repo-root glob (`*`, `**/*`) to survey what exists — `node_modules/` at the repo root holds thousands of files and will bury or crowd out a real site's results.
- `sites/*` alone returns nothing even when a site exists — glob only matches files, not directory names. Match a file inside the site instead, e.g. `sites/*/index.html` or `sites/*/CLAUDE.md`.
- If that comes up empty, search by a distinctive fragment of the domain name (e.g. `**/*<fragment>*`, scoped to this repo, excluding `node_modules`) before concluding no site exists for that domain — folder naming may not exactly match the domain string.

## Local Server
- **Always serve on localhost** — never screenshot a `file:///` URL.
- Start the dev server: `node serve.mjs sites/<site-name>` (e.g. `node serve.mjs sites/ecolibriumsolar`) — serves that site at `http://localhost:3000`
- `serve.mjs` lives in the repo root. Start it in the background before taking any screenshots.
- If the server is already running, do not start a second instance.

## Screenshot Workflow
- Puppeteer is installed at `C:/Users/nateh/AppData/Local/Temp/puppeteer-test/`. Chrome cache is at `C:/Users/nateh/.cache/puppeteer/`.
- **Always screenshot from localhost:** `node screenshot.mjs sites/<site-name> http://localhost:3000`
- Screenshots are saved automatically to `sites/<site-name>/temporary screenshots/screenshot-N.png` (auto-incremented, never overwritten).
- Optional label suffix: `node screenshot.mjs sites/<site-name> http://localhost:3000 label` → saves as `screenshot-N-label.png`
- `screenshot.mjs` lives in the repo root. Use it as-is.
- After screenshotting, read the PNG from `sites/<site-name>/temporary screenshots/` with the Read tool — Claude can see and analyze the image directly.
- When comparing, be specific: "heading is 32px but reference shows ~24px", "card gap is 16px but should be 24px"
- Check: spacing/padding, font size/weight/line-height, colors (exact hex), alignment, border-radius, shadows, image sizing

## Output Defaults
- Single `index.html` file, all styles inline, unless user says otherwise
- Tailwind CSS via CDN: `<script src="https://cdn.tailwindcss.com"></script>`
- Placeholder images: `https://placehold.co/WIDTHxHEIGHT`
- Mobile-first responsive

## Brand Assets
- Always check the `brand_assets/` folder before designing. It may contain logos, color guides, style guides, or images.
- If assets exist there, use them. Do not use placeholders where real assets are available.
- If a logo is present, use it. If a color palette is defined, use those exact values — do not invent brand colors.

## Anti-Generic Guardrails
- **Colors:** Never use default Tailwind palette (indigo-500, blue-600, etc.). Pick a custom brand color and derive from it.
- **Shadows:** Never use flat `shadow-md`. Use layered, color-tinted shadows with low opacity.
- **Typography:** Never use the same font for headings and body. Pair a display/serif with a clean sans. Apply tight tracking (`-0.03em`) on large headings, generous line-height (`1.7`) on body.
- **Gradients:** Layer multiple radial gradients. Add grain/texture via SVG noise filter for depth.
- **Animations:** Only animate `transform` and `opacity`. Never `transition-all`. Use spring-style easing.
- **Interactive states:** Every clickable element needs hover, focus-visible, and active states. No exceptions.
- **Images:** Add a gradient overlay (`bg-gradient-to-t from-black/60`) and a color treatment layer with `mix-blend-multiply`.
- **Spacing:** Use intentional, consistent spacing tokens — not random Tailwind steps.
- **Depth:** Surfaces should have a layering system (base → elevated → floating), not all sit at the same z-plane.

## Hard Rules
- Do not add sections, features, or content not in the reference
- Do not "improve" a reference design — match it
- Do not stop after one screenshot pass
- Do not use `transition-all`
- Do not use default Tailwind blue/indigo as primary color
