Reusable GitHub Pages Builder
============================

Use these scripts to render any Obsidian folder into a static site.

Quick start
- Example (this repo):
  python3 build.py --book /home/somebody/mathematical-economics/mathematical-economics/mathematical-economics-book \
    --asset-base /mathematical-economics --out pages --assets assets
- For another repo, copy this build-pages folder there (or reference it), ensure `assets/css/style.css` and `assets/js/site-nav.js` exist (provided here), then run:
  python3 build.py --book /path/to/obsidian/folder --asset-base /that-repo-name

Flags
- --book: source notes folder (Obsidian dir)
- --asset-base: URL base path for the site (e.g., /repo-name)
- --out: output HTML folder (default: pages)
- --assets: assets folder (default: assets)
- --template: HTML template to use (default: templates/section.html)

What it generates
- pages/: rendered HTML with slugified URLs
- assets/partials/sidebar.html and assets/site.json
- index.html landing page with links into sections

