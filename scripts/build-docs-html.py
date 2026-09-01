#!/usr/bin/env python3
"""Build HTML docs from AsciiDoc source for visual comparison.

Usage:
    python3 build-docs-html.py <version> [port]

Example:
    python3 build-docs-html.py 4.17

Builds and serves 3 doc sites:
  - Existing 4.16 (previous)
  - Existing 4.17 (actual)
  - Generated 4.17

Each rendered with OpenShift-like styling and navigation.
"""

import os
import sys
import re
import html
import json
import http.server
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote

BASE_DIR = Path(__file__).resolve().parent.parent

# Attributes that would be resolved in real builds
ATTRIBUTES = {
    'product-title': 'OpenShift Container Platform',
    'product-version': '4.17',
    'op-system': 'RHCOS',
    'op-system-first': 'Red Hat Enterprise Linux CoreOS (RHCOS)',
    'op-system-base': 'RHEL',
    'op-system-base-full': 'Red Hat Enterprise Linux (RHEL)',
    'op-system-lowercase': 'rhcos',
    'ocp-data-dir': '/var/lib/etcd',
    'ibm-z-title': 'IBM Z',
    'ibm-z-name': 'IBM Z',
    'ibm-linuxone-title': 'IBM LinuxONE',
    'ibm-power-title': 'IBM Power',
    'ibm-cloud-title': 'IBM Cloud',
    'azure-short': 'Azure',
    'gcp-short': 'GCP',
    'aws-short': 'AWS',
    'vmw-short': 'vSphere',
    'rh-openstack-first': 'Red Hat OpenStack Platform (RHOSP)',
    'rh-openstack': 'RHOSP',
    'sno': 'single-node OpenShift',
    'VirtProductName': 'OpenShift Virtualization',
}


def resolve_attributes(text):
    """Replace {attribute} references with values."""
    def replace_attr(m):
        name = m.group(1)
        return ATTRIBUTES.get(name, f'{{{name}}}')
    return re.sub(r'\{([a-zA-Z0-9_-]+)\}', replace_attr, text)


def adoc_to_html(text, base_path=""):
    """Convert AsciiDoc text to styled HTML."""
    text = resolve_attributes(text)
    lines = text.split('\n')
    html_parts = []
    in_code = False
    in_list = False
    code_lang = ""
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Code blocks
        if line.strip() == '----':
            if in_code:
                html_parts.append('</code></pre>')
                in_code = False
            else:
                in_code = True
                html_parts.append(f'<pre class="code-block"><code>')
            i += 1
            continue
        
        if in_code:
            html_parts.append(html.escape(line) + '\n')
            i += 1
            continue
        
        # Source language hint
        if re.match(r'^\[source', line):
            lang_match = re.search(r'source,(\w+)', line)
            code_lang = lang_match.group(1) if lang_match else ""
            i += 1
            continue
        
        # Skip metadata lines
        if re.match(r'^:_mod-docs-content-type:', line) or re.match(r'^:context:', line):
            i += 1
            continue
        
        if re.match(r'^\[id=', line):
            i += 1
            continue
            
        # Headers
        if line.startswith('= ') and not line.startswith('== '):
            title = html.escape(line[2:].strip())
            html_parts.append(f'<h1 class="doc-title">{title}</h1>')
            i += 1
            continue
        elif line.startswith('== '):
            html_parts.append(f'<h2>{html.escape(line[3:].strip())}</h2>')
            i += 1
            continue
        elif line.startswith('=== '):
            html_parts.append(f'<h3>{html.escape(line[4:].strip())}</h3>')
            i += 1
            continue
        elif line.startswith('==== '):
            html_parts.append(f'<h4>{html.escape(line[5:].strip())}</h4>')
            i += 1
            continue
        
        # Admonitions
        if line.strip() in ('[NOTE]', '[IMPORTANT]', '[WARNING]', '[TIP]', '[CAUTION]'):
            adm_type = line.strip()[1:-1].lower()
            # Collect content until ====
            i += 1
            if i < len(lines) and lines[i].strip() == '====':
                i += 1
                adm_content = []
                while i < len(lines) and lines[i].strip() != '====':
                    adm_content.append(lines[i])
                    i += 1
                i += 1  # skip closing ====
                html_parts.append(f'<div class="admonition adm-{adm_type}"><strong>{adm_type.upper()}:</strong> {html.escape(" ".join(adm_content))}</div>')
            continue
        
        # Include directives (render as links)
        if line.startswith('include::'):
            match = re.match(r'include::(.+?)\[', line)
            if match:
                inc_path = match.group(1)
                display = inc_path.replace('modules/', '').replace('.adoc', '')
                html_parts.append(f'<div class="include-ref">&#x25B6; {html.escape(display)}</div>')
            i += 1
            continue
        
        # Conditionals (hide them)
        if re.match(r'^(ifdef|ifndef|endif)::', line):
            i += 1
            continue
        
        # Comments
        if line.startswith('//'):
            i += 1
            continue
        
        # Table start
        if line.strip() == '|===':
            html_parts.append('<table class="doc-table"><tbody>')
            i += 1
            while i < len(lines) and lines[i].strip() != '|===':
                row = lines[i]
                if row.startswith('|'):
                    cells = [c.strip() for c in row.split('|')[1:] if c.strip()]
                    html_parts.append('<tr>' + ''.join(f'<td>{html.escape(c)}</td>' for c in cells) + '</tr>')
                i += 1
            html_parts.append('</tbody></table>')
            i += 1
            continue
        
        # Unordered list
        if line.startswith('* '):
            if not in_list:
                html_parts.append('<ul>')
                in_list = True
            html_parts.append(f'<li>{html.escape(line[2:])}</li>')
            i += 1
            continue
        elif in_list and not line.startswith('* ') and not line.startswith('+'):
            html_parts.append('</ul>')
            in_list = False
        
        # Ordered list
        if re.match(r'^\. \S', line):
            content = html.escape(line[2:])
            html_parts.append(f'<ol><li>{content}</li></ol>')
            i += 1
            continue
        
        # Bold/italic
        escaped = html.escape(line)
        escaped = re.sub(r'\*(.+?)\*', r'<strong>\1</strong>', escaped)
        escaped = re.sub(r'_(.+?)_', r'<em>\1</em>', escaped)
        escaped = re.sub(r'`(.+?)`', r'<code class="inline">\1</code>', escaped)
        
        # Links
        escaped = re.sub(r'link:(\S+)\[([^\]]*)\]', r'<a href="\1">\2</a>', escaped)
        
        if line.strip() == '':
            html_parts.append('<br>')
        elif line.strip().startswith('toc::'):
            pass  # skip toc macro
        else:
            html_parts.append(f'<p>{escaped}</p>')
        
        i += 1
    
    if in_list:
        html_parts.append('</ul>')
    if in_code:
        html_parts.append('</code></pre>')
    
    return '\n'.join(html_parts)


def build_nav(files_dict, base_url):
    """Build navigation tree from file paths."""
    tree = {}
    for filepath in sorted(files_dict.keys()):
        parts = filepath.split('/')
        current = tree
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = filepath
    
    def render_tree(node, depth=0):
        items = []
        # Directories first
        dirs = {k: v for k, v in sorted(node.items()) if isinstance(v, dict)}
        files = {k: v for k, v in sorted(node.items()) if isinstance(v, str)}
        
        for name, subtree in dirs.items():
            display = name.replace('installing_', '').replace('_', ' ').title()
            items.append(f'<details class="nav-dir"><summary>{html.escape(display)}</summary>')
            items.append(render_tree(subtree, depth + 1))
            items.append('</details>')
        
        for name, path in files:
            display = name.replace('.adoc', '').replace('-', ' ').replace('_', ' ').title()
            items.append(f'<a class="nav-link" href="{base_url}?file={quote(path)}">{html.escape(display[:40])}</a>')
        
        return '\n'.join(items)
    
    return render_tree(tree)


def get_prev_version(version):
    parts = version.split(".")
    return f"{parts[0]}.{int(parts[1]) - 1}"


class DocsHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        if path == '/':
            self.send_html(self.build_index_page())
        elif path in ('/existing-prev', '/existing-target', '/generated'):
            file_path = params.get('file', [''])[0]
            self.send_html(self.build_doc_page(path[1:], file_path))
        elif path == '/api/render':
            source = params.get('source', [''])[0]
            file_path = params.get('file', [''])[0]
            self.send_json(self.render_file(source, file_path))
        else:
            self.send_response(404)
            self.end_headers()
    
    def send_html(self, content):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def get_dir_for_source(self, source):
        if source == 'existing-prev':
            return self.server.prev_dir
        elif source == 'existing-target':
            return self.server.exist_dir
        elif source == 'generated':
            return self.server.gen_dir
        return None
    
    def render_file(self, source, file_path):
        d = self.get_dir_for_source(source)
        if not d or not file_path:
            return {'html': '<p class="empty">Select a file</p>', 'title': ''}
        
        full_path = d / file_path
        if not full_path.exists():
            return {'html': '<p class="empty">File not found in this version</p>', 'title': file_path}
        
        text = full_path.read_text(errors='replace')
        rendered = adoc_to_html(text)
        
        # Extract title
        title_match = re.search(r'^= (.+)$', text, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path
        title = resolve_attributes(title)
        
        return {'html': rendered, 'title': title}
    
    def build_index_page(self):
        v = self.server.version
        pv = self.server.prev_version
        
        # Collect all file paths and classify them
        all_files = set()
        prev_set = set()
        exist_set = set()
        gen_set = set()
        
        for d, s in [(self.server.prev_dir, prev_set), (self.server.exist_dir, exist_set), (self.server.gen_dir, gen_set)]:
            if d.exists():
                for f in d.rglob("*.adoc"):
                    rel = str(f.relative_to(d))
                    if not rel.startswith('_attributes'):
                        all_files.add(rel)
                        s.add(rel)
        
        # Classify files
        # "interesting" = exists in both generated AND existing 4.17, AND at least one differs from 4.16
        interesting_files = []
        unchanged_files = []
        other_files = []
        
        for f in sorted(all_files):
            in_prev = f in prev_set
            in_exist = f in exist_set
            in_gen = f in gen_set
            
            if in_exist and in_gen:
                # Check if either differs from 4.16
                prev_content = ""
                exist_content = ""
                gen_content = ""
                
                if in_prev:
                    pp = self.server.prev_dir / f
                    if pp.exists():
                        prev_content = pp.read_text(errors='replace')
                
                ep = self.server.exist_dir / f
                if ep.exists():
                    exist_content = ep.read_text(errors='replace')
                
                gp = self.server.gen_dir / f
                if gp.exists():
                    gen_content = gp.read_text(errors='replace')
                
                exist_changed = (exist_content != prev_content)
                gen_changed = (gen_content != prev_content)
                
                if exist_changed or gen_changed or not in_prev:
                    interesting_files.append({'path': f, 'exist_changed': exist_changed, 'gen_changed': gen_changed, 'is_new': not in_prev})
                else:
                    unchanged_files.append(f)
            else:
                other_files.append({'path': f, 'in_prev': in_prev, 'in_exist': in_exist, 'in_gen': in_gen})
        
        nav_json_parts = []
        for f in interesting_files:
            label = ""
            if f['is_new']:
                label = "NEW"
            elif f['exist_changed'] and f['gen_changed']:
                label = "BOTH CHANGED"
            elif f['exist_changed']:
                label = "EXIST CHANGED"
            elif f['gen_changed']:
                label = "GEN CHANGED"
            nav_json_parts.append(f'{{"path":"{f["path"]}","category":"interesting","label":"{label}"}}')
        
        for f in unchanged_files:
            nav_json_parts.append(f'{{"path":"{f}","category":"unchanged","label":""}}')
        
        for f in other_files:
            label = ""
            if f['in_exist'] and not f['in_gen']:
                label = "MISSING FROM GEN"
            elif f['in_gen'] and not f['in_exist']:
                label = "EXTRA IN GEN"
            else:
                label = "ONLY IN PREV"
            nav_json_parts.append(f'{{"path":"{f["path"]}","category":"other","label":"{label}"}}')
        
        nav_json = '[' + ','.join(nav_json_parts) + ']'
        
        return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Installation Docs Comparison - {v}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Red Hat Display','Red Hat Text',-apple-system,sans-serif; height:100vh; display:flex; flex-direction:column; }}
.topbar {{ background:#151515; color:#fff; padding:10px 20px; display:flex; align-items:center; gap:20px; }}
.topbar h1 {{ font-size:15px; font-weight:500; }}
.topbar .tabs {{ display:flex; gap:2px; margin-left:auto; }}
.topbar .tab {{ padding:6px 14px; background:#333; color:#ccc; cursor:pointer; border-radius:4px 4px 0 0; font-size:12px; }}
.topbar .tab.active {{ background:#fff; color:#151515; }}
.main {{ display:flex; flex:1; overflow:hidden; }}
.sidebar {{ width:260px; background:#f0f0f0; border-right:1px solid #ddd; overflow-y:auto; padding:8px; }}
.sidebar input {{ width:100%; padding:6px; margin-bottom:6px; border:1px solid #ccc; border-radius:3px; font-size:12px; }}
.sidebar .file {{ padding:4px 6px; font-size:11px; cursor:pointer; border-radius:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.sidebar .file:hover {{ background:#ddd; }}
.sidebar .file.active {{ background:#0066cc; color:#fff; }}
.sidebar .file.cat-interesting {{ border-left:3px solid #e65100; font-weight:500; }}
.sidebar .file.cat-unchanged {{ border-left:3px solid transparent; color:#888; }}
.sidebar .file.cat-other {{ border-left:3px solid #999; color:#999; font-style:italic; }}
.sidebar .badge {{ font-size:9px; padding:1px 4px; border-radius:2px; margin-left:4px; }}
.sidebar .badge-both {{ background:#fff3e0; color:#e65100; }}
.sidebar .badge-exist {{ background:#e8f5e9; color:#2e7d32; }}
.sidebar .badge-gen {{ background:#fce4ec; color:#c62828; }}
.sidebar .badge-new {{ background:#e3f2fd; color:#1565c0; }}
.sidebar .badge-missing {{ background:#f8d7da; color:#721c24; }}
.sidebar .badge-extra {{ background:#fff3cd; color:#856404; }}
.sidebar .section-header {{ font-size:10px; text-transform:uppercase; letter-spacing:1px; color:#555; padding:8px 6px 4px; font-weight:600; border-top:1px solid #ddd; margin-top:6px; }}
.sidebar .count {{ color:#999; font-weight:normal; }}
.content {{ flex:1; display:flex; overflow:hidden; }}
.panel {{ flex:1; overflow-y:auto; padding:20px 30px; border-right:1px solid #eee; max-width:33.33%; }}
.panel:last-child {{ border:none; }}
.panel-label {{ font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#666; margin-bottom:4px; padding:4px 8px; border-radius:3px; display:inline-block; }}
.pl-prev {{ background:#e3f2fd; color:#1565c0; }}
.pl-exist {{ background:#e8f5e9; color:#2e7d32; }}
.pl-gen {{ background:#fff3e0; color:#e65100; }}
.doc-body {{ font-family:'Red Hat Text',sans-serif; font-size:14px; line-height:1.7; color:#333; }}
.doc-body h1 {{ font-size:24px; margin:20px 0 12px; color:#151515; border-bottom:2px solid #e0e0e0; padding-bottom:8px; }}
.doc-body h2 {{ font-size:20px; margin:18px 0 10px; color:#252525; }}
.doc-body h3 {{ font-size:16px; margin:14px 0 8px; color:#353535; }}
.doc-body h4 {{ font-size:14px; margin:10px 0 6px; color:#454545; }}
.doc-body p {{ margin:6px 0; }}
.doc-body .code-block {{ background:#f4f4f4; border:1px solid #ddd; border-radius:4px; padding:12px; font-family:'JetBrains Mono',monospace; font-size:12px; overflow-x:auto; margin:8px 0; }}
.doc-body .inline {{ background:#f0f0f0; padding:1px 4px; border-radius:2px; font-size:13px; }}
.doc-body .include-ref {{ color:#6a1b9a; padding:4px 0; border-left:3px solid #ce93d8; padding-left:10px; margin:4px 0; font-size:13px; }}
.doc-body .admonition {{ border-left:4px solid; padding:8px 12px; margin:8px 0; border-radius:0 4px 4px 0; font-size:13px; }}
.doc-body .adm-note {{ border-color:#1976d2; background:#e3f2fd; }}
.doc-body .adm-important {{ border-color:#d32f2f; background:#ffebee; }}
.doc-body .adm-warning {{ border-color:#f57c00; background:#fff3e0; }}
.doc-body .adm-tip {{ border-color:#388e3c; background:#e8f5e9; }}
.doc-body .doc-table {{ border-collapse:collapse; width:100%; margin:8px 0; font-size:13px; }}
.doc-body .doc-table td,.doc-body .doc-table th {{ border:1px solid #ddd; padding:6px 8px; }}
.doc-body .doc-table tr:nth-child(even) {{ background:#f9f9f9; }}
.doc-body ul,.doc-body ol {{ margin:6px 0 6px 20px; }}
.doc-body li {{ margin:3px 0; }}
.empty {{ color:#999; font-style:italic; text-align:center; padding:40px; }}
.doc-title {{ font-size:24px !important; }}
</style>
</head><body>
<div class="topbar">
    <h1>Installation Docs</h1>
    <span style="color:#888;font-size:12px">Comparing: Existing {pv} | Existing {v} | Generated {v}</span>
</div>
<div class="main">
    <div class="sidebar">
        <input type="text" id="search" placeholder="Filter assemblies..." oninput="filterNav()">
        <div id="navList"></div>
    </div>
    <div class="content" id="content">
        <div class="panel">
            <div class="panel-label pl-prev">Existing {pv}</div>
            <div class="doc-body" id="body-prev"><p class="empty">Select a file</p></div>
        </div>
        <div class="panel">
            <div class="panel-label pl-exist">Existing {v}</div>
            <div class="doc-body" id="body-exist"><p class="empty">Select a file</p></div>
        </div>
        <div class="panel">
            <div class="panel-label pl-gen">Generated {v}</div>
            <div class="doc-body" id="body-gen"><p class="empty">Select a file</p></div>
        </div>
    </div>
</div>
<script>
const NAV_FILES = {nav_json};
let currentFile = null;
let showUnchanged = false;

function getDisplayName(path) {{
    const parts = path.split('/');
    const name = parts[parts.length-1].replace('.adoc','').replace(/-/g,' ').replace(/_/g,' ');
    const dir = parts.length > 1 ? parts[0].replace('installing_','').replace(/_/g,' ') + ' > ' : '';
    return dir + name;
}}

function getBadgeHtml(label) {{
    if (!label) return '';
    const cls = label.includes('BOTH') ? 'badge-both' : 
                label.includes('EXIST') ? 'badge-exist' :
                label.includes('GEN CHANGED') ? 'badge-gen' :
                label.includes('NEW') ? 'badge-new' :
                label.includes('MISSING') ? 'badge-missing' :
                label.includes('EXTRA') ? 'badge-extra' : '';
    return `<span class="badge ${{cls}}">${{label}}</span>`;
}}

function renderNav(filter) {{
    const list = document.getElementById('navList');
    const q = (filter || '').toLowerCase();
    
    const interesting = NAV_FILES.filter(f => f.category === 'interesting' && (f.path.toLowerCase().includes(q)));
    const unchanged = NAV_FILES.filter(f => f.category === 'unchanged' && (f.path.toLowerCase().includes(q)));
    const other = NAV_FILES.filter(f => f.category === 'other' && (f.path.toLowerCase().includes(q)));
    
    let html = `<div class="section-header">Changed Files <span class="count">(${{interesting.length}})</span></div>`;
    html += interesting.map(f => 
        `<div class="file cat-interesting ${{f.path===currentFile?'active':''}}" onclick="loadFile('${{f.path}}')" title="${{f.path}}">${{getDisplayName(f.path)}}${{getBadgeHtml(f.label)}}</div>`
    ).join('');
    
    html += `<div class="section-header" style="cursor:pointer" onclick="toggleUnchanged()">Unchanged <span class="count">(${{unchanged.length}}) ▸</span></div>`;
    if (showUnchanged) {{
        html += unchanged.map(f => 
            `<div class="file cat-unchanged ${{f.path===currentFile?'active':''}}" onclick="loadFile('${{f.path}}')" title="${{f.path}}">${{getDisplayName(f.path)}}</div>`
        ).join('');
    }}
    
    html += `<div class="section-header">Other <span class="count">(${{other.length}})</span></div>`;
    html += other.map(f => 
        `<div class="file cat-other ${{f.path===currentFile?'active':''}}" onclick="loadFile('${{f.path}}')" title="${{f.path}}">${{getDisplayName(f.path)}}${{getBadgeHtml(f.label)}}</div>`
    ).join('');
    
    list.innerHTML = html;
}}

function toggleUnchanged() {{ showUnchanged = !showUnchanged; renderNav(document.getElementById('search').value); }}
function filterNav() {{ renderNav(document.getElementById('search').value); }}

async function loadFile(path) {{
    currentFile = path;
    renderNav(document.getElementById('search').value);
    
    const [prev, exist, gen] = await Promise.all([
        fetch('/api/render?source=existing-prev&file=' + encodeURIComponent(path)).then(r=>r.json()),
        fetch('/api/render?source=existing-target&file=' + encodeURIComponent(path)).then(r=>r.json()),
        fetch('/api/render?source=generated&file=' + encodeURIComponent(path)).then(r=>r.json()),
    ]);
    
    document.getElementById('body-prev').innerHTML = prev.html;
    document.getElementById('body-exist').innerHTML = exist.html;
    document.getElementById('body-gen').innerHTML = gen.html;
}}

renderNav('');
</script>
</body></html>"""
    
    def build_doc_page(self, source, file_path):
        return ""  # Not used in this version


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 build-docs-html.py <version> [port]")
        sys.exit(1)
    
    version = sys.argv[1]
    prev_version = get_prev_version(version)
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9091
    section = sys.argv[3] if len(sys.argv) > 3 else "installing"
    
    prev_dir = BASE_DIR / "docs-corpus" / "ocp" / prev_version / section
    exist_dir = BASE_DIR / "docs-corpus" / "ocp" / version / section
    gen_dir = BASE_DIR / "generated" / section / version
    
    print(f"=== {section.capitalize()} Docs HTML Viewer ===")
    print(f"  Section: {section}")
    print(f"  Existing {prev_version}: {prev_dir}")
    print(f"  Existing {version}: {exist_dir}")
    print(f"  Generated {version}: {gen_dir}")
    print()
    
    server = http.server.HTTPServer(("", port), DocsHandler)
    server.version = version
    server.prev_version = prev_version
    server.prev_dir = prev_dir
    server.exist_dir = exist_dir
    server.gen_dir = gen_dir
    
    import webbrowser
    url = f"http://localhost:{port}/"
    print(f"  Open: {url}")
    print(f"  Press Ctrl+C to stop")
    webbrowser.open(url)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
