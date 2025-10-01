#!/usr/bin/env python3
import argparse, pathlib, re, html, json, shutil
from datetime import datetime, timezone

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s or 'index'

def split_num_label(name: str):
    m = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)$', name.strip())
    if m:
        return m.group(1), m.group(2)
    return '', name.strip()

def _is_abs_url(u: str) -> bool:
    return bool(re.match(r'^(?:[a-z]+:)?//', u)) or u.startswith('data:') or u.startswith('/')

def inline_html(s: str, rel_dir: pathlib.Path, src_root: pathlib.Path, asset_base: str, media_root: pathlib.Path) -> str:
    s = html.escape(s)
    # Protect math spans from other substitutions
    math_tokens = []
    def protect(pattern, text):
        def _rep(m):
            math_tokens.append(m.group(0))
            return f"@@MATH{len(math_tokens)-1}@@"
        return re.sub(pattern, _rep, text, flags=re.S)
    s = protect(r"\$\$(.+?)\$\$", s)
    s = protect(r"\$(.+?)\$", s)
    s = protect(r"\\\[(.+?)\\\]", s)
    s = protect(r"\\\((.+?)\\\)", s)
    # images
    def _img_sub(m):
        alt = m.group(1); src = m.group(2)
        if _is_abs_url(src):
            new_src = src
        else:
            src_path = (src_root / rel_dir / src).resolve()
            dest_path = (media_root / rel_dir / src).resolve()
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                if src_path.exists():
                    dest_path.write_bytes(src_path.read_bytes())
            except Exception:
                pass
            new_src = f"{asset_base}/assets/media/{rel_dir.as_posix()}/{src}"
        return f'<img src="{new_src}" alt="{alt}">'
    s = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', _img_sub, s)
    s = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', s)
    # Restore math tokens
    for i, tok in enumerate(math_tokens):
        s = s.replace(f"@@MATH{i}@@", tok)
    return s

def md_to_html(md: str, rel_dir: pathlib.Path, src_root: pathlib.Path, asset_base: str, media_root: pathlib.Path) -> str:
    lines = md.splitlines()
    out, para = [], []
    list_stack = []
    bullet_re = re.compile(r'^([ \t]*)([-\*])\s+(.*)$')
    def flush_para():
        nonlocal para
        if para:
            out.append('<p>' + inline_html(' '.join(para).strip(), rel_dir, src_root, asset_base, media_root) + '</p>')
            para = []
    def set_list_depth(depth: int):
        while len(list_stack) < depth:
            out.append('<ul>'); list_stack.append('ul')
        while len(list_stack) > depth:
            out.append('</ul>'); list_stack.pop()
    for raw in lines:
        line = raw.rstrip('\n')
        if line.lstrip().startswith('<'):
            flush_para(); set_list_depth(0); out.append(line); continue
        if not line.strip():
            flush_para(); set_list_depth(0); continue
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m:
            flush_para(); set_list_depth(0)
            level = len(m.group(1)); text = inline_html(m.group(2), rel_dir, src_root, asset_base, media_root)
            out.append(f'<h{level}>' + text + f'</h{level}>'); continue
        if re.match(r'^-{3,}\s*$', line):
            flush_para(); set_list_depth(0); out.append('<hr>'); continue
        bm = bullet_re.match(line)
        if bm:
            flush_para()
            indent = bm.group(1).replace('\t', '    ')
            depth = min(6, len(indent)//2)
            set_list_depth(depth+1)
            out.append('<li>' + inline_html(bm.group(3), rel_dir, src_root, asset_base, media_root) + '</li>'); continue
        para.append(line)
    flush_para(); set_list_depth(0)
    return '\n'.join(out)

def render_page(template_path: pathlib.Path, asset_base: str, title: str, content_html: str) -> str:
    tpl = template_path.read_text(encoding='utf-8')
    return tpl.replace('{{asset_base}}', asset_base).replace('{{title}}', title).replace('{{content}}', content_html)

def build(book: pathlib.Path, out_dir: pathlib.Path, assets_dir: pathlib.Path, template_path: pathlib.Path, asset_base: str):
    if not book.exists():
        raise SystemExit(f'Book directory not found: {book}')
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    media_root = assets_dir / 'media'
    partials_dir = assets_dir / 'partials'
    partials_dir.mkdir(parents=True, exist_ok=True)

    # Build sections including empty top-level dirs
    sections = {}
    for entry in sorted(book.iterdir()):
        if entry.is_dir() and not entry.name.startswith('.'):
            sections.setdefault(entry.name, [])
    for md_path in book.rglob('*.md'):
        rel = md_path.relative_to(book)
        parts = list(rel.parts)
        if not parts:
            continue
        sections.setdefault(parts[0], []).append(md_path)
    for k in list(sections.keys()):
        sections[k] = sorted(sections[k])

    manifest = []
    sidebar_data = []
    pages_by_dir = {}

    for sect_label, files in sections.items():
        sect_slug = slugify(sect_label)
        entry = { 'label': sect_label, 'slug': sect_slug, 'pages': [] }
        for md_path in files:
            rel = md_path.relative_to(book)
            out_dirs = [slugify(p) for p in rel.parts[:-1]]
            name_slug = slugify(md_path.stem)
            out_html = out_dir.joinpath(*(out_dirs + [name_slug + '.html']))
            out_html.parent.mkdir(parents=True, exist_ok=True)
            md = md_path.read_text(encoding='utf-8')
            num, label = split_num_label(md_path.stem)
            title = (num + ' ' if num else '') + label
            md_lines = md.splitlines()
            if md_lines and re.match(r'^#\s+.+', md_lines[0]):
                first = re.sub(r'^#\s+', '', md_lines[0]).strip()
                if first.lower() == title.lower() or first.lower() == label.lower():
                    md_lines = md_lines[1:]
                md = '\n'.join(md_lines)
            rel_dir = rel.parent
            content = md_to_html(md, rel_dir, book, asset_base, media_root)
            html_page = render_page(template_path, asset_base, title, content)
            out_html.write_text(html_page, encoding='utf-8')
            url_path = f"/pages/{'/'.join(out_dirs + [name_slug + '.html'])}"
            entry['pages'].append({ 'title': title, 'path': url_path })
            pages_by_dir.setdefault(rel_dir, []).append({ 'title': title, 'path': url_path })
            print(f'Rendered {md_path} -> {out_html}')
        manifest.append(entry)

        # Sidebar data for this section
        src_section_dir = book / sect_label
        root_rel = src_section_dir.relative_to(book)
        root_pages = pages_by_dir.get(root_rel, [])
        try:
            child_dirs = [d for d in sorted(src_section_dir.iterdir()) if d.is_dir() and not d.name.startswith('.')]
        except Exception:
            child_dirs = []
        children = []
        for c in child_dirs:
            child_rel = c.relative_to(book)
            child_slug = slugify(c.name)
            children.append({ 'label': c.name, 'slug': child_slug, 'pages': pages_by_dir.get(child_rel, []) })
        sidebar_data.append({ 'label': sect_label, 'slug': sect_slug, 'root_pages': root_pages, 'children': children })

        # Generate index for all directories under this section
        all_dirs = [src_section_dir]
        for d in src_section_dir.rglob('*'):
            if d.is_dir() and not d.name.startswith('.'):
                all_dirs.append(d)
        for d in all_dirs:
            rel_dir = d.relative_to(book)
            out_section_dir = out_dir.joinpath(*[slugify(p) for p in rel_dir.parts])
            out_section_dir.mkdir(parents=True, exist_ok=True)
            try:
                child_dirs2 = [c for c in sorted(d.iterdir()) if c.is_dir() and not c.name.startswith('.')]
            except Exception:
                child_dirs2 = []
            sub_links = ''
            if child_dirs2:
                items = []
                for c in child_dirs2:
                    child_rel2 = c.relative_to(book)
                    child_out = '/'.join([slugify(p) for p in child_rel2.parts])
                    items.append(f'<li><a href="{asset_base}/pages/{child_out}/index.html">{html.escape(c.name)}</a></li>')
                sub_links = '<h2>Subsections</h2>\n<ul>\n' + '\n'.join(items) + '\n</ul>'
            dir_pages = pages_by_dir.get(rel_dir, [])
            page_links = ''
            if dir_pages:
                items = [f'<li><a href="{asset_base}{p["path"]}">{html.escape(p["title"])}</a></li>' for p in dir_pages]
                page_links = '<h2>Pages</h2>\n<ul>\n' + '\n'.join(items) + '\n</ul>'
            body_parts = [part for part in [sub_links, page_links] if part]
            sec_body = '\n<hr>\n'.join(body_parts) if body_parts else '<p>Coming soon.</p>'
            title2 = rel_dir.name if rel_dir.parts else sect_label
            (out_section_dir / 'index.html').write_text(render_page(template_path, asset_base, title2, sec_body), encoding='utf-8')

    # Write manifest + sidebar + index
    (assets_dir / 'site.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    build_info = {
        'builder': 'build-pages',
        'version': 'v0.1.2',
        'built_at': datetime.now(timezone.utc).isoformat(),
        'source': str(book),
        'output': str(out_dir),
        'asset_base': asset_base,
        'counts': {'sections': len(manifest), 'pages': sum(len(s['pages']) for s in manifest)},
    }
    (assets_dir / 'build-info.json').write_text(json.dumps(build_info, indent=2), encoding='utf-8')

    sidebar = ['<div class="card">', '  <nav>', f'    <a href="{asset_base}/index.html" data-match="/index.html">Home</a>', '    <hr style="border:none;border-top:1px solid var(--border);margin:8px 0;">', '    <strong style="display:block;padding:4px 10px;color:var(--muted)">Sections</strong>']
    for sect in sidebar_data:
      first = f"/pages/{sect['slug']}/index.html"
      sidebar.append(f'    <a href="{asset_base}{first}" data-match="/pages/{sect["slug"]}/'>{html.escape(sect["label"])}</a>')
      if sect.get('root_pages'):
        sidebar.append('    <ul style="margin:6px 0 10px 16px; padding:0; list-style: none;">')
        for p in sect['root_pages']:
          sidebar.append(f'      <li><a href="{asset_base}{p["path"]}">{html.escape(p["title"])}</a></li>')
        sidebar.append('    </ul>')
      if sect.get('children'):
        sidebar.append('    <ul style="margin:6px 0 10px 16px; padding:0; list-style: none;">')
        for child in sect['children']:
          child_href = f"/pages/{sect['slug']}/{child['slug']}/index.html"
          sidebar.append(f'      <li><a href="{asset_base}{child_href}">{html.escape(child["label"])}</a>')
          if child.get('pages'):
            sidebar.append('        <ul style="margin:4px 0 6px 14px; padding:0; list-style: none;">')
            for p in child['pages']:
              sidebar.append(f'          <li><a href="{asset_base}{p["path"]}">{html.escape(p["title"])}</a></li>')
            sidebar.append('        </ul>')
          sidebar.append('      </li>')
        sidebar.append('    </ul>')
    sidebar += ['  </nav>', '</div>']
    (partials_dir / 'sidebar.html').write_text('\n'.join(sidebar), encoding='utf-8')

    cards = []
    for sect in manifest:
        link = f'{asset_base}/pages/{sect["slug"]}/index.html'
        title = html.escape(sect['label'])
        cards.append(f'''    <div class="card">
      <h3>{title}</h3>
      <div class="buttons">
        <a href="{link}" class="button">Open Section</a>
      </div>
    </div>''')
    index_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <script>
    (function(){
      try { var m = localStorage.getItem('theme'); if (m === 'light' || m === 'dark') document.documentElement.setAttribute('data-theme', m); } catch (e) {}
    })();
  </script>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mathematical Economics</title>
  <link rel="stylesheet" href="{asset_base}/assets/css/style.css" />
  <script defer src="{asset_base}/assets/js/site-nav.js"></script>
</head>
<body>
  <button id="navToggle" class="hamburger" aria-label="Toggle navigation" aria-expanded="false">≡</button>
  <button id="themeToggle" class="theme-toggle" aria-label="Toggle theme" title="Toggle light/dark">◎</button>
  <div class="font-slider" aria-label="Font size">
    <input id="fontSize" type="range" min="90" max="220" step="5" />
  </div>
  <div id="backdrop" class="backdrop" hidden></div>
  <div class="layout">
    <aside id="sidebar" class="sidebar"></aside>
    <main class="content">
  <div class="container">
    <h1>Mathematical Economics</h1>
    <p class="tagline">Sections generated from the book.</p>

{chr(10).join(cards)}

  </div>
    </main>
  </div>
</body>
</html>
'''
    (assets_dir.parent / 'index.html').write_text(index_html, encoding='utf-8')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Render an Obsidian folder to GitHub Pages site.')
    ap.add_argument('--book', required=True, help='Path to the Obsidian folder (source).')
    ap.add_argument('--asset-base', default='/', help='Base path where the site is hosted, e.g., /repo-name')
    ap.add_argument('--out', default='pages', help='Output folder (default: pages)')
    ap.add_argument('--assets', default='assets', help='Assets folder (default: assets)')
    ap.add_argument('--template', default=str(pathlib.Path(__file__).parent / 'templates' / 'section.html'), help='HTML template for pages')
    args = ap.parse_args()

    ROOT = pathlib.Path('.').resolve()
    build(
        book=pathlib.Path(args.book).resolve(),
        out_dir=(ROOT / args.out).resolve(),
        assets_dir=(ROOT / args.assets).resolve(),
        template_path=pathlib.Path(args.template).resolve(),
        asset_base=args.asset_base.rstrip('/'))
