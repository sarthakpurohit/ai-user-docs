#!/usr/bin/env python3
"""Generate structured code diff summaries between installer release branches.

For each version pair (4.16->4.17, ..., 4.21->4.22), extracts the code diff
from doc-relevant paths and produces a structured Markdown summary suitable
for LLM consumption during doc generation.
"""

import subprocess
import re
import os
import sys

from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
INSTALLER_REPO = str(_BASE_DIR / "installer")
DIFFS_ROOT = str(_BASE_DIR / "diffs" / "installing")

DOC_RELEVANT_PATHS = [
    "pkg/types/",
    "docs/user/",
    "cmd/openshift-install/",
    "data/data/install.openshift.io_installconfigs.yaml",
    "upi/",
    "pkg/asset/installconfig/",
    "pkg/asset/machines/",
    "pkg/asset/manifests/",
]

VERSION_PAIRS = [
    ("4.16", "4.17"),
    ("4.17", "4.18"),
    ("4.18", "4.19"),
    ("4.19", "4.20"),
    ("4.20", "4.21"),
    ("4.21", "4.22"),
]


def run_git(args, cwd=INSTALLER_REPO):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout, result.stderr, result.returncode


def get_diff_stat(from_branch, to_branch, paths):
    args = ["diff", "--stat", f"origin/release-{from_branch}..origin/release-{to_branch}", "--"] + paths
    stdout, _, _ = run_git(args)
    return stdout


def get_diff_summary(from_branch, to_branch, paths):
    args = ["diff", "--stat", "--summary", f"origin/release-{from_branch}..origin/release-{to_branch}", "--"] + paths
    stdout, _, _ = run_git(args)
    return stdout


def get_new_files(from_branch, to_branch, paths):
    args = ["diff", "--diff-filter=A", "--name-only", f"origin/release-{from_branch}..origin/release-{to_branch}", "--"] + paths
    stdout, _, _ = run_git(args)
    return [f for f in stdout.strip().split("\n") if f]


def get_deleted_files(from_branch, to_branch, paths):
    args = ["diff", "--diff-filter=D", "--name-only", f"origin/release-{from_branch}..origin/release-{to_branch}", "--"] + paths
    stdout, _, _ = run_git(args)
    return [f for f in stdout.strip().split("\n") if f]


def get_modified_files(from_branch, to_branch, paths):
    args = ["diff", "--diff-filter=M", "--name-only", f"origin/release-{from_branch}..origin/release-{to_branch}", "--"] + paths
    stdout, _, _ = run_git(args)
    return [f for f in stdout.strip().split("\n") if f]


def get_struct_changes(from_branch, to_branch):
    """Extract changes to install-config Go structs in pkg/types/."""
    args = ["diff", "-U3", f"origin/release-{from_branch}..origin/release-{to_branch}", "--", "pkg/types/"]
    stdout, _, _ = run_git(args)
    
    changes = []
    current_file = None
    current_hunks = []
    
    for line in stdout.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_hunks:
                changes.append((current_file, current_hunks))
            match = re.search(r"b/(.*)", line)
            current_file = match.group(1) if match else "unknown"
            current_hunks = []
        elif line.startswith("@@"):
            current_hunks.append(line)
        elif line.startswith("+") and not line.startswith("+++"):
            if re.search(r'^\+\s*(//|type |.*struct|.*`json)', line):
                current_hunks.append(line)
        elif line.startswith("-") and not line.startswith("---"):
            if re.search(r'^\-\s*(//|type |.*struct|.*`json)', line):
                current_hunks.append(line)
    
    if current_file and current_hunks:
        changes.append((current_file, current_hunks))
    
    return changes


def get_cli_changes(from_branch, to_branch):
    """Extract changes to CLI commands."""
    args = ["diff", "-U2", f"origin/release-{from_branch}..origin/release-{to_branch}", "--", "cmd/openshift-install/"]
    stdout, _, _ = run_git(args)
    return stdout[:5000] if stdout else ""


def get_platform_changes(from_branch, to_branch):
    """Detect new/removed platform directories in pkg/types/."""
    args = ["diff", "--diff-filter=A", "--name-only", f"origin/release-{from_branch}..origin/release-{to_branch}", "--", "pkg/types/"]
    stdout, _, _ = run_git(args)
    
    new_platforms = set()
    for f in stdout.strip().split("\n"):
        if f:
            parts = f.replace("pkg/types/", "").split("/")
            if len(parts) > 1 and parts[0] not in ("", "defaults", "validation"):
                new_platforms.add(parts[0])
    
    args = ["diff", "--diff-filter=D", "--name-only", f"origin/release-{from_branch}..origin/release-{to_branch}", "--", "pkg/types/"]
    stdout, _, _ = run_git(args)
    
    removed_platforms = set()
    for f in stdout.strip().split("\n"):
        if f:
            parts = f.replace("pkg/types/", "").split("/")
            if len(parts) > 1 and parts[0] not in ("", "defaults", "validation"):
                removed_platforms.add(parts[0])
    
    return new_platforms, removed_platforms


def get_commit_messages(from_branch, to_branch, paths):
    """Get key commit messages for context."""
    args = ["log", "--oneline", "--no-merges", f"origin/release-{from_branch}..origin/release-{to_branch}", "--"] + paths
    stdout, _, _ = run_git(args)
    lines = [l for l in stdout.strip().split("\n") if l]
    return lines[:50]


def generate_diff_summary(from_ver, to_ver):
    """Generate a complete structured diff summary for one version pair."""
    
    print(f"  Generating diff summary: {from_ver} -> {to_ver}")
    
    stat = get_diff_stat(from_ver, to_ver, DOC_RELEVANT_PATHS)
    new_files = get_new_files(from_ver, to_ver, DOC_RELEVANT_PATHS)
    deleted_files = get_deleted_files(from_ver, to_ver, DOC_RELEVANT_PATHS)
    modified_files = get_modified_files(from_ver, to_ver, DOC_RELEVANT_PATHS)
    struct_changes = get_struct_changes(from_ver, to_ver)
    cli_changes = get_cli_changes(from_ver, to_ver)
    new_platforms, removed_platforms = get_platform_changes(from_ver, to_ver)
    commits = get_commit_messages(from_ver, to_ver, DOC_RELEVANT_PATHS)
    
    md = []
    md.append(f"# Installer Code Diff: release-{from_ver} → release-{to_ver}")
    md.append("")
    md.append(f"This document summarizes documentation-relevant changes in the `openshift/installer`")
    md.append(f"repository between release branches `release-{from_ver}` and `release-{to_ver}`.")
    md.append("")
    
    md.append("## Overview")
    md.append("")
    md.append(f"- **New files**: {len(new_files)}")
    md.append(f"- **Deleted files**: {len(deleted_files)}")
    md.append(f"- **Modified files**: {len(modified_files)}")
    md.append("")
    
    if new_platforms:
        md.append("## New Platforms Added")
        md.append("")
        for p in sorted(new_platforms):
            md.append(f"- `{p}`")
        md.append("")
    
    if removed_platforms:
        md.append("## Platforms Removed/Deprecated")
        md.append("")
        for p in sorted(removed_platforms):
            md.append(f"- `{p}`")
        md.append("")
    
    if struct_changes:
        md.append("## Install-Config Struct Changes (pkg/types/)")
        md.append("")
        md.append("These changes affect the user-facing `install-config.yaml` schema:")
        md.append("")
        for filepath, hunks in struct_changes[:20]:
            md.append(f"### `{filepath}`")
            md.append("")
            md.append("```go")
            for h in hunks[:30]:
                md.append(h)
            md.append("```")
            md.append("")
    
    if cli_changes:
        md.append("## CLI Changes (cmd/openshift-install/)")
        md.append("")
        md.append("```diff")
        md.append(cli_changes[:3000])
        md.append("```")
        md.append("")
    
    if new_files:
        md.append("## New Files")
        md.append("")
        for f in sorted(new_files)[:50]:
            md.append(f"- `{f}`")
        md.append("")
    
    if deleted_files:
        md.append("## Deleted Files")
        md.append("")
        for f in sorted(deleted_files)[:50]:
            md.append(f"- `{f}`")
        md.append("")
    
    if commits:
        md.append("## Key Commits")
        md.append("")
        for c in commits[:30]:
            md.append(f"- {c}")
        md.append("")
    
    md.append("## Stat Summary")
    md.append("")
    md.append("```")
    md.append(stat[:3000] if stat else "(no changes)")
    md.append("```")
    
    return "\n".join(md)


def main():
    print("Generating installer code diff summaries...")
    print(f"Repo: {INSTALLER_REPO}")
    print(f"Output root: {DIFFS_ROOT}")
    print()
    
    for from_ver, to_ver in VERSION_PAIRS:
        summary = generate_diff_summary(from_ver, to_ver)
        
        output_dir = os.path.join(DIFFS_ROOT, f"{from_ver}-to-{to_ver}")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"installer-diff-{from_ver}-to-{to_ver}.md")
        with open(output_file, "w") as f:
            f.write(summary)
        
        lines = summary.count("\n")
        print(f"  Written: {output_file} ({lines} lines)")
        print()
    
    print("=== All diff summaries generated ===")


if __name__ == "__main__":
    main()
