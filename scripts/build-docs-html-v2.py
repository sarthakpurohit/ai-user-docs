#!/usr/bin/env python3
"""Build HTML docs viewer v2 with GitHub-style line diffs and resizable sidebar.

Usage:
    python3 build-docs-html-v2.py <version> [port]

Example:
    python3 build-docs-html-v2.py 4.17 9092
"""

import os
import sys
import re
import html
import json
import difflib
import http.server
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote

BASE_DIR = Path(__file__).resolve().parent.parent

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
    def replace_attr(m):
        name = m.group(1)
        return ATTRIBUTES.get(name, f'{{{name}}}')
    return re.sub(r'\{([a-zA-Z0-9_-]+)\}', replace_attr, text)


def adoc_to_html(text, base_path=""):
    text = resolve_attributes(text)
    lines = text.split('\n')
    html_parts = []
    in_code = False
    in_list = False

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.strip() == '----':
            if in_code:
                html_parts.append('</code></pre>')
                in_code = False
            else:
                in_code = True
                html_parts.append('<pre class="code-block"><code>')
            i += 1
            continue

        if in_code:
            html_parts.append(html.escape(line) + '\n')
            i += 1
            continue

        if re.match(r'^\[source', line):
            i += 1
            continue

        if re.match(r'^:_mod-docs-content-type:', line) or re.match(r'^:context:', line):
            i += 1
            continue

        if re.match(r'^\[id=', line):
            i += 1
            continue

        if line.startswith('= ') and not line.startswith('== '):
            html_parts.append(f'<h1 class="doc-title">{html.escape(line[2:].strip())}</h1>')
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

        if line.strip() in ('[NOTE]', '[IMPORTANT]', '[WARNING]', '[TIP]', '[CAUTION]'):
            adm_type = line.strip()[1:-1].lower()
            i += 1
            if i < len(lines) and lines[i].strip() == '====':
                i += 1
                adm_content = []
                while i < len(lines) and lines[i].strip() != '====':
                    adm_content.append(lines[i])
                    i += 1
                i += 1
                html_parts.append(f'<div class="admonition adm-{adm_type}"><strong>{adm_type.upper()}:</strong> {html.escape(" ".join(adm_content))}</div>')
            continue

        if line.startswith('include::'):
            match = re.match(r'include::(.+?)\[', line)
            if match:
                inc_path = match.group(1)
                display = inc_path.replace('modules/', '').replace('.adoc', '')
                html_parts.append(f'<div class="include-ref">&#x25B6; {html.escape(display)}</div>')
            i += 1
            continue

        if re.match(r'^(ifdef|ifndef|endif)::', line):
            i += 1
            continue

        if line.startswith('//'):
            i += 1
            continue

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

        if re.match(r'^\. \S', line):
            html_parts.append(f'<ol><li>{html.escape(line[2:])}</li></ol>')
            i += 1
            continue

        escaped = html.escape(line)
        escaped = re.sub(r'\*(.+?)\*', r'<strong>\1</strong>', escaped)
        escaped = re.sub(r'_(.+?)_', r'<em>\1</em>', escaped)
        escaped = re.sub(r'`(.+?)`', r'<code class="inline">\1</code>', escaped)
        escaped = re.sub(r'link:(\S+)\[([^\]]*)\]', r'<a href="\1">\2</a>', escaped)

        if line.strip() == '':
            html_parts.append('<br>')
        elif line.strip().startswith('toc::'):
            pass
        else:
            html_parts.append(f'<p>{escaped}</p>')

        i += 1

    if in_list:
        html_parts.append('</ul>')
    if in_code:
        html_parts.append('</code></pre>')

    return '\n'.join(html_parts)


def compute_annotated_html(base_lines, target_lines):
    """Produce annotated HTML for a target file showing changes from base.
    
    Returns rows where added/changed lines are green, removed lines are red (inline).
    """
    sm = difflib.SequenceMatcher(None, base_lines, target_lines)
    opcodes = sm.get_opcodes()
    rows = []
    additions = 0
    deletions = 0

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            for idx in range(j2 - j1):
                ln = j1 + idx + 1
                content = html.escape(target_lines[j1 + idx])
                rows.append(f'<tr class="diff-equal"><td class="ln">{ln}</td><td class="code">{content}</td></tr>')
        elif tag == 'replace':
            for idx in range(i2 - i1):
                content = html.escape(base_lines[i1 + idx])
                rows.append(f'<tr class="diff-removed"><td class="ln del-ln"></td><td class="code">{content}</td></tr>')
                deletions += 1
            for idx in range(j2 - j1):
                ln = j1 + idx + 1
                content = html.escape(target_lines[j1 + idx])
                rows.append(f'<tr class="diff-added"><td class="ln">{ln}</td><td class="code">{content}</td></tr>')
                additions += 1
        elif tag == 'delete':
            for idx in range(i2 - i1):
                content = html.escape(base_lines[i1 + idx])
                rows.append(f'<tr class="diff-removed"><td class="ln del-ln"></td><td class="code">{content}</td></tr>')
                deletions += 1
        elif tag == 'insert':
            for idx in range(j2 - j1):
                ln = j1 + idx + 1
                content = html.escape(target_lines[j1 + idx])
                rows.append(f'<tr class="diff-added"><td class="ln">{ln}</td><td class="code">{content}</td></tr>')
                additions += 1

    return {
        'html': '\n'.join(rows),
        'stats': {'additions': additions, 'deletions': deletions}
    }


def compute_plain_html(lines):
    """Render plain lines with line numbers (no highlighting)."""
    rows = []
    for i, line in enumerate(lines, 1):
        content = html.escape(line)
        rows.append(f'<tr class="diff-equal"><td class="ln">{i}</td><td class="code">{content}</td></tr>')
    return '\n'.join(rows)


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
        elif path == '/api/render':
            source = params.get('source', [''])[0]
            file_path = params.get('file', [''])[0]
            self.send_json(self.render_file(source, file_path))
        elif path == '/api/diff':
            file_path = params.get('file', [''])[0]
            mode = params.get('mode', ['exist-vs-gen'])[0]
            self.send_json(self.compute_file_diff(file_path, mode))
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
        self.send_header('Access-Control-Allow-Origin', '*')
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
        title_match = re.search(r'^= (.+)$', text, re.MULTILINE)
        title = title_match.group(1) if title_match else file_path
        title = resolve_attributes(title)
        return {'html': rendered, 'title': title}

    def compute_file_diff(self, file_path, mode):
        """Compute 3-panel annotated diff: baseline plain, existing highlighted, generated highlighted."""
        if not file_path:
            return {'prev_html': '', 'exist_html': '', 'gen_html': '',
                    'exist_stats': {'additions': 0, 'deletions': 0},
                    'gen_stats': {'additions': 0, 'deletions': 0}}

        prev_lines = []
        exist_lines = []
        gen_lines = []

        prev_path = self.server.prev_dir / file_path
        exist_path = self.server.exist_dir / file_path
        gen_path = self.server.gen_dir / file_path

        if prev_path.exists():
            prev_lines = prev_path.read_text(errors='replace').splitlines()
        if exist_path.exists():
            exist_lines = exist_path.read_text(errors='replace').splitlines()
        if gen_path.exists():
            gen_lines = gen_path.read_text(errors='replace').splitlines()

        prev_html = compute_plain_html(prev_lines) if prev_lines else '<tr><td colspan="2" class="empty">File not found in this version</td></tr>'

        if exist_lines:
            exist_result = compute_annotated_html(prev_lines, exist_lines)
            exist_html = exist_result['html']
            exist_stats = exist_result['stats']
        else:
            exist_html = '<tr><td colspan="2" class="empty">File not found in this version</td></tr>'
            exist_stats = {'additions': 0, 'deletions': 0}

        if gen_lines:
            gen_result = compute_annotated_html(prev_lines, gen_lines)
            gen_html = gen_result['html']
            gen_stats = gen_result['stats']
        else:
            gen_html = '<tr><td colspan="2" class="empty">File not found in this version</td></tr>'
            gen_stats = {'additions': 0, 'deletions': 0}

        return {
            'prev_html': prev_html,
            'exist_html': exist_html,
            'gen_html': gen_html,
            'exist_stats': exist_stats,
            'gen_stats': gen_stats,
        }

    def build_index_page(self):
        v = self.server.version
        pv = self.server.prev_version

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

        interesting_files = []
        unchanged_files = []
        other_files = []

        for f in sorted(all_files):
            in_prev = f in prev_set
            in_exist = f in exist_set
            in_gen = f in gen_set

            if in_exist and in_gen:
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
<title>Installation Docs Comparison v2 - {v}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; height:100vh; display:flex; flex-direction:column; background:#fff; }}

/* Top bar */
.topbar {{ background:#24292f; color:#fff; padding:10px 20px; display:flex; align-items:center; gap:20px; flex-shrink:0; }}
.topbar h1 {{ font-size:15px; font-weight:500; }}
.topbar .info {{ color:#8b949e; font-size:12px; }}
.topbar .tabs {{ display:flex; gap:2px; margin-left:auto; }}
.topbar .tab {{ padding:7px 16px; background:#32383f; color:#c9d1d9; cursor:pointer; border-radius:6px 6px 0 0; font-size:12px; font-weight:500; border:1px solid #444c56; border-bottom:none; }}
.topbar .tab:hover {{ background:#3d444d; color:#fff; }}
.topbar .tab.active {{ background:#fff; color:#24292f; border-color:#d0d7de; }}

/* Main layout */
.main {{ display:flex; flex:1; overflow:hidden; }}

/* Sidebar - resizable */
.sidebar {{
    width:280px;
    min-width:180px;
    max-width:600px;
    background:#f6f8fa;
    border-right:1px solid #d0d7de;
    overflow-y:auto;
    padding:8px;
    position:relative;
    flex-shrink:0;
}}
.sidebar input {{ width:100%; padding:7px 10px; margin-bottom:8px; border:1px solid #d0d7de; border-radius:6px; font-size:12px; background:#fff; }}
.sidebar input:focus {{ outline:none; border-color:#0969da; box-shadow:0 0 0 3px rgba(9,105,218,0.15); }}
.sidebar .file {{
    padding:5px 8px;
    font-size:12px;
    cursor:pointer;
    border-radius:4px;
    overflow:hidden;
    text-overflow:ellipsis;
    white-space:nowrap;
    display:flex;
    align-items:center;
    gap:4px;
}}
.sidebar .file:hover {{ background:#e8e8e8; }}
.sidebar .file.active {{ background:#0969da; color:#fff; }}
.sidebar .file.active .badge {{ background:rgba(255,255,255,0.25); color:#fff; }}
.sidebar .file.cat-interesting {{ font-weight:500; }}
.sidebar .file.cat-unchanged {{ color:#656d76; }}
.sidebar .file.cat-other {{ color:#656d76; font-style:italic; }}
.sidebar .file-name {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; }}
.sidebar .badge {{ font-size:9px; padding:1px 5px; border-radius:10px; font-weight:500; flex-shrink:0; }}
.sidebar .badge-both {{ background:#fff3e0; color:#bc4c00; }}
.sidebar .badge-exist {{ background:#dafbe1; color:#116329; }}
.sidebar .badge-gen {{ background:#ffebe9; color:#82071e; }}
.sidebar .badge-new {{ background:#ddf4ff; color:#0550ae; }}
.sidebar .badge-missing {{ background:#ffebe9; color:#82071e; }}
.sidebar .badge-extra {{ background:#fff8c5; color:#4d2d00; }}
.sidebar .section-header {{ font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#57606a; padding:10px 8px 4px; font-weight:600; border-top:1px solid #d8dee4; margin-top:8px; }}
.sidebar .section-header:first-child {{ border-top:none; margin-top:0; }}
.sidebar .count {{ color:#8b949e; font-weight:normal; }}

/* Resize handle */
.resize-handle {{
    position:absolute;
    top:0;
    right:0;
    width:4px;
    height:100%;
    cursor:col-resize;
    background:transparent;
    z-index:10;
}}
.resize-handle:hover, .resize-handle.dragging {{ background:#0969da; }}

/* Content area */
.content {{ flex:1; display:flex; flex-direction:column; overflow:hidden; }}

/* Rendered panels view */
.panels {{ display:flex; flex:1; overflow:hidden; }}
.panel {{ flex:1; overflow-y:auto; padding:20px 24px; border-right:1px solid #d8dee4; }}
.panel:last-child {{ border:none; }}
.panel-label {{ font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#57606a; margin-bottom:8px; padding:3px 8px; border-radius:4px; display:inline-block; font-weight:600; }}
.pl-prev {{ background:#ddf4ff; color:#0550ae; }}
.pl-exist {{ background:#dafbe1; color:#116329; }}
.pl-gen {{ background:#fff3e0; color:#bc4c00; }}

/* Doc body styles */
.doc-body {{ font-family:-apple-system,sans-serif; font-size:14px; line-height:1.7; color:#1f2328; }}
.doc-body h1 {{ font-size:24px; margin:16px 0 12px; color:#1f2328; border-bottom:1px solid #d8dee4; padding-bottom:8px; }}
.doc-body h2 {{ font-size:20px; margin:20px 0 10px; color:#1f2328; }}
.doc-body h3 {{ font-size:16px; margin:14px 0 8px; color:#1f2328; }}
.doc-body h4 {{ font-size:14px; margin:10px 0 6px; color:#1f2328; font-weight:600; }}
.doc-body p {{ margin:6px 0; }}
.doc-body .code-block {{ background:#f6f8fa; border:1px solid #d0d7de; border-radius:6px; padding:12px 16px; font-family:'JetBrains Mono','Fira Code',monospace; font-size:12px; overflow-x:auto; margin:8px 0; }}
.doc-body .inline {{ background:#eff1f3; padding:1px 5px; border-radius:4px; font-size:13px; font-family:monospace; }}
.doc-body .include-ref {{ color:#8250df; padding:4px 0; border-left:3px solid #c297ff; padding-left:10px; margin:4px 0; font-size:13px; }}
.doc-body .admonition {{ border-left:4px solid; padding:8px 14px; margin:8px 0; border-radius:0 6px 6px 0; font-size:13px; }}
.doc-body .adm-note {{ border-color:#0969da; background:#ddf4ff; }}
.doc-body .adm-important {{ border-color:#cf222e; background:#ffebe9; }}
.doc-body .adm-warning {{ border-color:#bf8700; background:#fff8c5; }}
.doc-body .adm-tip {{ border-color:#1a7f37; background:#dafbe1; }}
.doc-body .doc-table {{ border-collapse:collapse; width:100%; margin:8px 0; font-size:13px; }}
.doc-body .doc-table td,.doc-body .doc-table th {{ border:1px solid #d0d7de; padding:6px 10px; }}
.doc-body .doc-table tr:nth-child(even) {{ background:#f6f8fa; }}
.doc-body ul,.doc-body ol {{ margin:6px 0 6px 20px; }}
.doc-body li {{ margin:3px 0; }}
.empty {{ color:#656d76; font-style:italic; text-align:center; padding:40px; }}

/* ====== DIFF VIEW ====== */
.diff-container {{ flex:1; display:flex; overflow:hidden; }}
.diff-pane {{
    flex:1;
    overflow:auto;
    border-right:1px solid #d0d7de;
}}
.diff-pane:last-child {{ border-right:none; }}
.diff-pane-header {{
    position:sticky;
    top:0;
    background:#f6f8fa;
    border-bottom:1px solid #d0d7de;
    padding:8px 16px;
    font-size:12px;
    font-weight:600;
    color:#1f2328;
    z-index:5;
    display:flex;
    align-items:center;
    gap:8px;
}}
.diff-pane-header .stats {{
    font-weight:normal;
    color:#57606a;
    margin-left:auto;
    font-family:monospace;
    font-size:11px;
}}
.diff-pane-header .stat-add {{ color:#1a7f37; font-weight:600; }}
.diff-pane-header .stat-del {{ color:#cf222e; font-weight:600; }}

.diff-pane table {{ width:100%; border-collapse:collapse; font-family:'JetBrains Mono','Fira Code','SF Mono',monospace; font-size:12px; line-height:20px; }}
.diff-pane td {{ padding:0 12px; white-space:pre-wrap; word-break:break-all; vertical-align:top; }}
.diff-pane td.ln {{ width:50px; min-width:50px; text-align:right; color:#8b949e; padding-right:10px; user-select:none; background:#f6f8fa; border-right:1px solid #d0d7de; }}
.diff-pane td.ln.del-ln {{ background:#ffd7d5; }}
.diff-pane td.code {{ padding-left:12px; }}

.diff-pane tr.diff-equal td {{ background:#fff; }}
.diff-pane tr.diff-added td {{ background:#e6ffec; }}
.diff-pane tr.diff-added td.ln {{ background:#ccffd8; color:#116329; }}
.diff-pane tr.diff-added td.code {{ color:#116329; }}
.diff-pane tr.diff-removed td {{ background:#ffebe9; }}
.diff-pane tr.diff-removed td.ln {{ background:#ffd7d5; color:#82071e; }}
.diff-pane tr.diff-removed td.code {{ color:#82071e; text-decoration:line-through; opacity:0.7; }}
.diff-pane tr.diff-pad td {{ background:#f6f8fa; }}

/* Diff mode selector */
.diff-toolbar {{
    background:#f6f8fa;
    border-bottom:1px solid #d0d7de;
    padding:6px 16px;
    display:flex;
    align-items:center;
    gap:12px;
    font-size:12px;
    flex-shrink:0;
}}
.diff-toolbar label {{ color:#57606a; font-weight:500; }}
.diff-toolbar .info {{ color:#57606a; font-style:italic; }}

/* Sync scroll indicator */
.sync-scroll {{ display:flex; align-items:center; gap:4px; color:#57606a; margin-left:auto; }}
.sync-scroll input {{ cursor:pointer; }}

/* Hider for views */
.hidden {{ display:none !important; }}
</style>
</head><body>
<div class="topbar">
    <h1>Installation Docs Comparison</h1>
    <span class="info">{pv} → {v}</span>
    <div class="tabs">
        <div class="tab active" id="tab-render" onclick="switchView('render')">Rendered</div>
        <div class="tab" id="tab-diff" onclick="switchView('diff')">Diff</div>
    </div>
</div>
<div class="main">
    <div class="sidebar" id="sidebar">
        <input type="text" id="search" placeholder="Filter files..." oninput="filterNav()">
        <div id="navList"></div>
        <div class="resize-handle" id="resizeHandle"></div>
    </div>
    <div class="content">
        <!-- Rendered panels view -->
        <div class="panels" id="view-render">
            <div class="panel">
                <div class="panel-label pl-prev">Existing {pv}</div>
                <div class="doc-body" id="body-prev"><p class="empty">Select a file from the left panel</p></div>
            </div>
            <div class="panel">
                <div class="panel-label pl-exist">Existing {v}</div>
                <div class="doc-body" id="body-exist"><p class="empty">Select a file from the left panel</p></div>
            </div>
            <div class="panel">
                <div class="panel-label pl-gen">Generated {v}</div>
                <div class="doc-body" id="body-gen"><p class="empty">Select a file from the left panel</p></div>
            </div>
        </div>
        <!-- Diff view -->
        <div id="view-diff" class="hidden" style="display:flex;flex-direction:column;flex:1;overflow:hidden;">
            <div class="diff-toolbar">
                <label>Showing changes from {pv} baseline:</label>
                <span class="info">Green = added vs {pv}, Red = removed vs {pv}</span>
                <div class="sync-scroll">
                    <input type="checkbox" id="syncScroll" checked>
                    <label for="syncScroll">Sync scroll</label>
                </div>
            </div>
            <div class="diff-container" id="diffContainer">
                <div class="diff-pane" id="diffPrev">
                    <div class="diff-pane-header">Existing {pv} <span class="stats">(baseline)</span></div>
                    <table><tbody id="diffPrevBody"></tbody></table>
                </div>
                <div class="diff-pane" id="diffExist">
                    <div class="diff-pane-header">Existing {v} <span class="stats" id="existStats"></span></div>
                    <table><tbody id="diffExistBody"></tbody></table>
                </div>
                <div class="diff-pane" id="diffGen">
                    <div class="diff-pane-header">Generated {v} <span class="stats" id="genStats"></span></div>
                    <table><tbody id="diffGenBody"></tbody></table>
                </div>
            </div>
        </div>
    </div>
</div>
<script>
const NAV_FILES = {nav_json};
let currentFile = null;
let currentView = 'render';
let showUnchanged = false;

// ===== Resizable sidebar =====
(function() {{
    const sidebar = document.getElementById('sidebar');
    const handle = document.getElementById('resizeHandle');
    let isResizing = false;
    let startX, startWidth;

    handle.addEventListener('mousedown', function(e) {{
        isResizing = true;
        startX = e.clientX;
        startWidth = sidebar.offsetWidth;
        handle.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    }});

    document.addEventListener('mousemove', function(e) {{
        if (!isResizing) return;
        const dx = e.clientX - startX;
        const newWidth = Math.max(180, Math.min(600, startWidth + dx));
        sidebar.style.width = newWidth + 'px';
    }});

    document.addEventListener('mouseup', function() {{
        if (isResizing) {{
            isResizing = false;
            handle.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }}
    }});
}})();

// ===== Sync scroll for diff panes =====
(function() {{
    const panes = [
        document.getElementById('diffPrev'),
        document.getElementById('diffExist'),
        document.getElementById('diffGen')
    ];
    let syncing = false;

    function syncFrom(source) {{
        if (syncing || !document.getElementById('syncScroll').checked) return;
        syncing = true;
        const pct = source.scrollTop / (source.scrollHeight - source.clientHeight || 1);
        panes.forEach(p => {{
            if (p !== source) {{
                p.scrollTop = pct * (p.scrollHeight - p.clientHeight || 1);
            }}
        }});
        syncing = false;
    }}

    panes.forEach(p => p.addEventListener('scroll', () => syncFrom(p)));
}})();

// ===== View switching =====
function switchView(view) {{
    currentView = view;
    document.getElementById('tab-render').classList.toggle('active', view === 'render');
    document.getElementById('tab-diff').classList.toggle('active', view === 'diff');
    document.getElementById('view-render').classList.toggle('hidden', view !== 'render');
    const diffView = document.getElementById('view-diff');
    if (view === 'diff') {{
        diffView.classList.remove('hidden');
        diffView.style.display = 'flex';
    }} else {{
        diffView.classList.add('hidden');
        diffView.style.display = 'none';
    }}
    if (currentFile) loadCurrentView();
}}

// ===== Navigation =====
function getDisplayName(path) {{
    const parts = path.split('/');
    const name = parts[parts.length-1].replace('.adoc','').replace(/-/g,' ');
    const dir = parts.length > 1 ? parts.slice(0, -1).join('/').replace(/installing_/g,'').replace(/_/g,' ') + ' / ' : '';
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

    const interesting = NAV_FILES.filter(f => f.category === 'interesting' && f.path.toLowerCase().includes(q));
    const unchanged = NAV_FILES.filter(f => f.category === 'unchanged' && f.path.toLowerCase().includes(q));
    const other = NAV_FILES.filter(f => f.category === 'other' && f.path.toLowerCase().includes(q));

    let h = `<div class="section-header">Changed Files <span class="count">(${{interesting.length}})</span></div>`;
    h += interesting.map(f =>
        `<div class="file cat-interesting ${{f.path===currentFile?'active':''}}" onclick="loadFile('${{f.path}}')" title="${{f.path}}"><span class="file-name">${{getDisplayName(f.path)}}</span>${{getBadgeHtml(f.label)}}</div>`
    ).join('');

    h += `<div class="section-header" style="cursor:pointer" onclick="toggleUnchanged()">Unchanged <span class="count">(${{unchanged.length}}) ${{showUnchanged?'▾':'▸'}}</span></div>`;
    if (showUnchanged) {{
        h += unchanged.map(f =>
            `<div class="file cat-unchanged ${{f.path===currentFile?'active':''}}" onclick="loadFile('${{f.path}}')" title="${{f.path}}"><span class="file-name">${{getDisplayName(f.path)}}</span></div>`
        ).join('');
    }}

    h += `<div class="section-header">Other <span class="count">(${{other.length}})</span></div>`;
    h += other.map(f =>
        `<div class="file cat-other ${{f.path===currentFile?'active':''}}" onclick="loadFile('${{f.path}}')" title="${{f.path}}"><span class="file-name">${{getDisplayName(f.path)}}</span>${{getBadgeHtml(f.label)}}</div>`
    ).join('');

    list.innerHTML = h;
}}

function toggleUnchanged() {{ showUnchanged = !showUnchanged; renderNav(document.getElementById('search').value); }}
function filterNav() {{ renderNav(document.getElementById('search').value); }}

// ===== File loading =====
async function loadFile(path) {{
    currentFile = path;
    renderNav(document.getElementById('search').value);
    await loadCurrentView();
}}

async function loadCurrentView() {{
    if (!currentFile) return;
    if (currentView === 'render') {{
        const [prev, exist, gen] = await Promise.all([
            fetch('/api/render?source=existing-prev&file=' + encodeURIComponent(currentFile)).then(r=>r.json()),
            fetch('/api/render?source=existing-target&file=' + encodeURIComponent(currentFile)).then(r=>r.json()),
            fetch('/api/render?source=generated&file=' + encodeURIComponent(currentFile)).then(r=>r.json()),
        ]);
        document.getElementById('body-prev').innerHTML = prev.html;
        document.getElementById('body-exist').innerHTML = exist.html;
        document.getElementById('body-gen').innerHTML = gen.html;
    }} else {{
        await loadDiff();
    }}
}}

async function loadDiff() {{
    if (!currentFile) return;
    const resp = await fetch('/api/diff?file=' + encodeURIComponent(currentFile));
    const data = await resp.json();

    document.getElementById('diffPrevBody').innerHTML = data.prev_html;
    document.getElementById('diffExistBody').innerHTML = data.exist_html;
    document.getElementById('diffGenBody').innerHTML = data.gen_html;

    const es = data.exist_stats;
    const gs = data.gen_stats;
    document.getElementById('existStats').innerHTML = (es.additions || es.deletions)
        ? `<span class="stat-add">+${{es.additions}}</span> <span class="stat-del">-${{es.deletions}}</span>`
        : '(unchanged)';
    document.getElementById('genStats').innerHTML = (gs.additions || gs.deletions)
        ? `<span class="stat-add">+${{gs.additions}}</span> <span class="stat-del">-${{gs.deletions}}</span>`
        : '(unchanged)';

    // Reset scroll
    document.getElementById('diffPrev').scrollTop = 0;
    document.getElementById('diffExist').scrollTop = 0;
    document.getElementById('diffGen').scrollTop = 0;
}}

renderNav('');
</script>
</body></html>"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 build-docs-html-v2.py <version> [port] [section]")
        print("  section defaults to 'installing'")
        sys.exit(1)

    version = sys.argv[1]
    prev_version = get_prev_version(version)
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9092
    section = sys.argv[3] if len(sys.argv) > 3 else "installing"

    prev_dir = BASE_DIR / "docs-corpus" / "ocp" / prev_version / section
    exist_dir = BASE_DIR / "docs-corpus" / "ocp" / version / section
    gen_dir = BASE_DIR / "generated" / section / version

    print(f"=== {section.capitalize()} Docs HTML Viewer v2 ===")
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

    url = f"http://localhost:{port}/"
    print(f"  Open: {url}")
    print(f"  Press Ctrl+C to stop")

    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
