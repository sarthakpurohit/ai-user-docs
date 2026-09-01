#!/usr/bin/env python3
"""Generate a comparison webpage for installation docs.

Usage:
    python3 compare-docs.py <version> [port]
    
Example:
    python3 compare-docs.py 4.17
    python3 compare-docs.py 4.17 8891

Opens a browser with 3-panel comparison:
  - Existing docs for previous version (e.g., 4.16)
  - Existing docs for target version (e.g., 4.17)
  - Generated docs for target version (generated/4.17)

Differences are highlighted:
  - Green: lines added
  - Red: lines removed
  - Yellow: modified files in the sidebar
"""

import os
import sys
import json
import difflib
import html
import http.server
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE_DIR = Path(__file__).resolve().parent.parent


def get_prev_version(version):
    parts = version.split(".")
    major, minor = int(parts[0]), int(parts[1])
    return f"{major}.{minor - 1}"


def collect_file_list(directory):
    """Collect all .adoc file paths relative to directory."""
    files = []
    if not directory.exists():
        return files
    for f in sorted(directory.rglob("*.adoc")):
        files.append(str(f.relative_to(directory)))
    return files


def read_file(directory, rel_path):
    """Read a single file, return content or empty string."""
    fpath = directory / rel_path
    if fpath.exists():
        try:
            return fpath.read_text(errors='replace')
        except Exception:
            return ""
    return ""


def compute_diff_lines(text1, text2, label1, label2):
    """Compute unified diff and return as list of annotated line dicts."""
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()
    
    diff = list(difflib.unified_diff(lines1, lines2, fromfile=label1, tofile=label2, n=3))
    
    result = []
    for line in diff:
        if line.startswith('+++') or line.startswith('---'):
            result.append({'type': 'header', 'text': line})
        elif line.startswith('@@'):
            result.append({'type': 'hunk', 'text': line})
        elif line.startswith('+'):
            result.append({'type': 'added', 'text': line[1:]})
        elif line.startswith('-'):
            result.append({'type': 'removed', 'text': line[1:]})
        else:
            result.append({'type': 'context', 'text': line[1:] if line.startswith(' ') else line})
    
    return result


class CompareHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that serves the comparison UI and file content on demand."""
    
    def log_message(self, format, *args):
        pass  # Suppress access logs
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(self.server.index_html.encode())
        
        elif path == '/api/files':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.server.file_index).encode())
        
        elif path == '/api/file':
            filename = params.get('name', [''])[0]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            prev_content = read_file(self.server.prev_dir, filename)
            exist_content = read_file(self.server.exist_dir, filename)
            gen_content = read_file(self.server.gen_dir, filename)
            
            # Compute diffs
            pv = self.server.prev_version
            v = self.server.version
            
            diff_pe = compute_diff_lines(prev_content, exist_content, f"existing-{pv}", f"existing-{v}")
            diff_eg = compute_diff_lines(exist_content, gen_content, f"existing-{v}", f"generated-{v}")
            diff_pg = compute_diff_lines(prev_content, gen_content, f"existing-{pv}", f"generated-{v}")
            
            result = {
                'prev': prev_content,
                'existing': exist_content,
                'generated': gen_content,
                'diff_prev_exist': diff_pe,
                'diff_exist_gen': diff_eg,
                'diff_prev_gen': diff_pg,
            }
            self.wfile.write(json.dumps(result).encode())
        
        else:
            self.send_response(404)
            self.end_headers()


def build_file_index(prev_dir, exist_dir, gen_dir):
    """Build categorized file index."""
    prev_files = set(collect_file_list(prev_dir))
    exist_files = set(collect_file_list(exist_dir))
    gen_files = set(collect_file_list(gen_dir))
    all_files = sorted(prev_files | exist_files | gen_files)
    
    index = []
    for f in all_files:
        status = "normal"
        if f in exist_files and f not in prev_files:
            status = "new"
        elif f in exist_files and f not in gen_files:
            status = "missing"
        elif f in gen_files and f not in exist_files:
            status = "extra"
        
        index.append({
            'path': f,
            'name': f.split('/')[-1],
            'status': status,
            'in_prev': f in prev_files,
            'in_exist': f in exist_files,
            'in_gen': f in gen_files,
        })
    
    return index


def generate_index_html(version, prev_version):
    """Generate the main comparison page HTML."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Docs Comparison: {version} (prev: {prev_version})</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; height: 100vh; display: flex; flex-direction: column; }}

.header {{
    background: #1a1a2e; color: white; padding: 10px 20px;
    display: flex; justify-content: space-between; align-items: center;
}}
.header h1 {{ font-size: 16px; font-weight: 500; }}
.header .stats {{ font-size: 12px; color: #aaa; }}

.toolbar {{
    background: #f5f5f5; border-bottom: 1px solid #ddd; padding: 6px 20px;
    display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
}}
.toolbar label {{ font-size: 13px; }}
.toolbar select {{ padding: 3px 8px; font-size: 13px; }}
.legend {{ display: flex; gap: 12px; font-size: 11px; margin-left: auto; }}
.legend-item {{ display: flex; align-items: center; gap: 4px; }}
.legend-dot {{ width: 10px; height: 10px; border-radius: 2px; }}
.dot-green {{ background: #d4edda; border: 1px solid #28a745; }}
.dot-red {{ background: #f8d7da; border: 1px solid #dc3545; }}
.dot-yellow {{ background: #fff3cd; border: 1px solid #ffc107; }}

.main {{ display: flex; flex: 1; overflow: hidden; }}

.sidebar {{
    width: 260px; min-width: 200px; border-right: 1px solid #ddd;
    overflow-y: auto; background: #fafafa; display: flex; flex-direction: column;
}}
.sidebar .search {{
    width: calc(100% - 12px); margin: 6px; padding: 5px 8px;
    border: 1px solid #ddd; border-radius: 4px; font-size: 12px;
}}
.file-list {{ flex: 1; overflow-y: auto; padding: 0 4px; }}
.file-item {{
    padding: 3px 6px; font-size: 11px; cursor: pointer; border-radius: 3px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    border-left: 3px solid transparent;
}}
.file-item:hover {{ background: #e8e8e8; }}
.file-item.active {{ background: #0066cc; color: white; }}
.file-item.s-new {{ border-left-color: #28a745; }}
.file-item.s-missing {{ border-left-color: #dc3545; }}
.file-item.s-extra {{ border-left-color: #ffc107; }}

.content {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}
.panels {{ flex: 1; display: flex; overflow: hidden; }}
.panel {{
    flex: 1; overflow-y: auto; border-right: 1px solid #eee;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 12px; line-height: 1.6;
}}
.panel:last-child {{ border-right: none; }}
.panel-header {{
    font-family: -apple-system, sans-serif; font-weight: 600; font-size: 12px;
    padding: 5px 10px; position: sticky; top: 0; z-index: 10;
}}
.ph-prev {{ background: #e3f2fd; color: #1565c0; }}
.ph-exist {{ background: #e8f5e9; color: #2e7d32; }}
.ph-gen {{ background: #fff3e0; color: #e65100; }}
.ph-diff {{ background: #f3e5f5; color: #6a1b9a; }}

.panel-body {{ padding: 8px; white-space: pre-wrap; word-break: break-word; }}

.line-added {{ background: #d4edda; color: #155724; display: block; padding: 0 4px; }}
.line-removed {{ background: #f8d7da; color: #721c24; display: block; padding: 0 4px; }}
.line-hunk {{ color: #6f42c1; font-weight: bold; display: block; margin-top: 8px; }}
.line-header {{ color: #666; font-weight: bold; display: block; }}
.line-context {{ color: #555; display: block; padding: 0 4px; }}

.empty {{ color: #999; font-style: italic; padding: 30px; text-align: center; }}
.loading {{ color: #666; padding: 20px; text-align: center; }}
</style>
</head>
<body>

<div class="header">
    <h1>Installation Docs Comparison &mdash; {version}</h1>
    <div class="stats" id="stats">Loading...</div>
</div>

<div class="toolbar">
    <label>View:</label>
    <select id="viewMode" onchange="renderFile()">
        <option value="three">3-Panel: Prev {prev_version} | Existing {version} | Generated {version}</option>
        <option value="diff-pe">Diff: Existing {prev_version} → Existing {version}</option>
        <option value="diff-eg">Diff: Existing {version} vs Generated {version}</option>
        <option value="diff-pg">Diff: Existing {prev_version} vs Generated {version}</option>
    </select>
    <div class="legend">
        <div class="legend-item"><div class="legend-dot dot-green"></div>Added</div>
        <div class="legend-item"><div class="legend-dot dot-red"></div>Removed</div>
        <div class="legend-item"><div class="legend-dot dot-yellow"></div>Extra/Modified</div>
    </div>
</div>

<div class="main">
    <div class="sidebar">
        <input type="text" class="search" id="searchBox" placeholder="Filter files..." oninput="filterFiles()">
        <div class="file-list" id="fileList"></div>
    </div>
    <div class="content">
        <div class="panels" id="panels">
            <div class="panel"><div class="empty">Select a file from the sidebar to compare</div></div>
        </div>
    </div>
</div>

<script>
let fileIndex = [];
let currentFile = null;
let currentData = null;

async function init() {{
    const resp = await fetch('/api/files');
    fileIndex = await resp.json();
    renderFileList();
    
    const total = fileIndex.length;
    const newCount = fileIndex.filter(f => f.status === 'new').length;
    const missingCount = fileIndex.filter(f => f.status === 'missing').length;
    const extraCount = fileIndex.filter(f => f.status === 'extra').length;
    document.getElementById('stats').textContent = 
        `Total: ${{total}} | New in {version}: ${{newCount}} | Missing from gen: ${{missingCount}} | Extra in gen: ${{extraCount}}`;
}}

function renderFileList() {{
    const query = document.getElementById('searchBox').value.toLowerCase();
    const container = document.getElementById('fileList');
    container.innerHTML = fileIndex
        .filter(f => f.path.toLowerCase().includes(query))
        .map(f => `<div class="file-item s-${{f.status}}" data-path="${{f.path}}" 
            onclick="selectFile('${{f.path.replace(/'/g, "\\\\'")}}')" 
            title="${{f.path}}">${{f.name}}</div>`)
        .join('');
}}

function filterFiles() {{ renderFileList(); }}

async function selectFile(path) {{
    currentFile = path;
    document.querySelectorAll('.file-item').forEach(el => {{
        el.classList.toggle('active', el.dataset.path === path);
    }});
    
    document.getElementById('panels').innerHTML = '<div class="panel"><div class="loading">Loading...</div></div>';
    
    const resp = await fetch(`/api/file?name=${{encodeURIComponent(path)}}`);
    currentData = await resp.json();
    renderFile();
}}

function escapeHtml(text) {{
    return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function renderRaw(text) {{
    if (!text) return '<div class="empty">File does not exist</div>';
    return '<div class="panel-body">' + escapeHtml(text) + '</div>';
}}

function renderDiff(diffLines) {{
    if (!diffLines || diffLines.length === 0) return '<div class="panel-body"><div class="empty" style="color:#28a745">No differences</div></div>';
    let html = '<div class="panel-body">';
    for (const line of diffLines) {{
        const escaped = escapeHtml(line.text);
        switch(line.type) {{
            case 'added': html += `<span class="line-added">+ ${{escaped}}</span>`; break;
            case 'removed': html += `<span class="line-removed">- ${{escaped}}</span>`; break;
            case 'hunk': html += `<span class="line-hunk">${{escaped}}</span>`; break;
            case 'header': html += `<span class="line-header">${{escaped}}</span>`; break;
            default: html += `<span class="line-context">  ${{escaped}}</span>`;
        }}
    }}
    html += '</div>';
    return html;
}}

function renderFile() {{
    if (!currentData) return;
    const mode = document.getElementById('viewMode').value;
    const panels = document.getElementById('panels');
    
    if (mode === 'three') {{
        panels.innerHTML = `
            <div class="panel"><div class="panel-header ph-prev">Existing {prev_version}</div>${{renderRaw(currentData.prev)}}</div>
            <div class="panel"><div class="panel-header ph-exist">Existing {version}</div>${{renderRaw(currentData.existing)}}</div>
            <div class="panel"><div class="panel-header ph-gen">Generated {version}</div>${{renderRaw(currentData.generated)}}</div>
        `;
    }} else if (mode === 'diff-pe') {{
        panels.innerHTML = `<div class="panel"><div class="panel-header ph-diff">Diff: Existing {prev_version} → Existing {version}</div>${{renderDiff(currentData.diff_prev_exist)}}</div>`;
    }} else if (mode === 'diff-eg') {{
        panels.innerHTML = `<div class="panel"><div class="panel-header ph-diff">Diff: Existing {version} vs Generated {version}</div>${{renderDiff(currentData.diff_exist_gen)}}</div>`;
    }} else if (mode === 'diff-pg') {{
        panels.innerHTML = `<div class="panel"><div class="panel-header ph-diff">Diff: Existing {prev_version} vs Generated {version}</div>${{renderDiff(currentData.diff_prev_gen)}}</div>`;
    }}
}}

init();
</script>
</body>
</html>"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 compare-docs.py <version> [port]")
        print("Example: python3 compare-docs.py 4.17")
        sys.exit(1)
    
    version = sys.argv[1]
    prev_version = get_prev_version(version)
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8890
    
    prev_dir = BASE_DIR / "docs-corpus" / "ocp" / prev_version / "installing"
    exist_dir = BASE_DIR / "docs-corpus" / "ocp" / version / "installing"
    gen_dir = BASE_DIR / "generated" / version
    
    print(f"=== Docs Comparison Server ===")
    print(f"  Version: {version} (previous: {prev_version})")
    print(f"  Existing {prev_version}: {prev_dir}")
    print(f"  Existing {version}: {exist_dir}")
    print(f"  Generated {version}: {gen_dir}")
    print()
    
    # Build file index
    file_index = build_file_index(prev_dir, exist_dir, gen_dir)
    print(f"  Total files indexed: {len(file_index)}")
    
    # Create server
    index_html = generate_index_html(version, prev_version)
    
    server = http.server.HTTPServer(("", port), CompareHandler)
    server.prev_dir = prev_dir
    server.exist_dir = exist_dir
    server.gen_dir = gen_dir
    server.version = version
    server.prev_version = prev_version
    server.file_index = file_index
    server.index_html = index_html
    
    url = f"http://localhost:{port}/"
    print(f"\n  Serving at: {url}")
    print(f"  Press Ctrl+C to stop\n")
    
    webbrowser.open(url)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
