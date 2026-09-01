#!/usr/bin/env python3
"""Generate structured diff summaries from multiple repos between release branches.

Handles both regular and bare git repos. Focuses on doc-relevant paths per repo.
"""

import subprocess
import re
import os
from pathlib import Path

BASE_DIR = Path("/home/sapurohi/Desktop/Agentic OKD docs")
DIFFS_ROOT = BASE_DIR / "diffs" / "installing"

REPOS = {
    "installer": {
        "path": BASE_DIR / "installer",
        "bare": False,
        "doc_paths": [
            "pkg/types/", "docs/user/", "cmd/openshift-install/",
            "data/data/install.openshift.io_installconfigs.yaml",
            "upi/", "pkg/asset/installconfig/", "pkg/asset/machines/",
            "pkg/asset/manifests/",
        ],
    },
    "api": {
        "path": BASE_DIR / "api.git",
        "bare": True,
        "doc_paths": [
            "install/", "config/", "features/",
            "machine/", "operator/", "network/",
        ],
    },
    "baremetal-operator": {
        "path": BASE_DIR / "baremetal-operator.git",
        "bare": True,
        "doc_paths": [
            "apis/", "pkg/", "docs/", "config/", "controllers/",
        ],
    },
    "assisted-installer": {
        "path": BASE_DIR / "assisted-installer.git",
        "bare": True,
        "doc_paths": [
            "src/", "cmd/", "docs/", "config/",
        ],
    },
    "cluster-network-operator": {
        "path": BASE_DIR / "cluster-network-operator.git",
        "bare": True,
        "doc_paths": [
            "pkg/", "manifests/", "bindata/", "docs/",
        ],
    },
    "machine-config-operator": {
        "path": BASE_DIR / "machine-config-operator",
        "bare": False,
        "doc_paths": [
            "pkg/", "cmd/", "docs/", "manifests/", "templates/",
        ],
    },
    "machine-api-operator": {
        "path": BASE_DIR / "machine-api-operator",
        "bare": False,
        "doc_paths": [
            "pkg/", "cmd/", "docs/", "config/",
        ],
    },
}


def run_git(args, repo_path, bare=False):
    cmd = ["git"]
    if bare:
        cmd += ["--git-dir", str(repo_path)]
    result = subprocess.run(
        cmd + args,
        cwd=str(repo_path) if not bare else None,
        capture_output=True, text=True, timeout=120,
    )
    return result.stdout, result.stderr, result.returncode


def has_branch(repo_path, branch, bare=False):
    if bare:
        stdout, _, rc = run_git(["rev-parse", "--verify", branch], repo_path, bare)
        return rc == 0
    else:
        # Non-bare repos: check remote branches with origin/ prefix
        stdout, _, rc = run_git(["rev-parse", "--verify", f"origin/{branch}"], repo_path, bare)
        if rc == 0:
            return True
        # Also try without prefix
        stdout, _, rc = run_git(["rev-parse", "--verify", branch], repo_path, bare)
        return rc == 0


def get_diff_stat(repo_path, from_b, to_b, paths, bare=False):
    args = ["diff", "--stat", f"{from_b}..{to_b}", "--"] + paths
    stdout, _, _ = run_git(args, repo_path, bare)
    return stdout


def get_new_files(repo_path, from_b, to_b, paths, bare=False):
    args = ["diff", "--diff-filter=A", "--name-only", f"{from_b}..{to_b}", "--"] + paths
    stdout, _, _ = run_git(args, repo_path, bare)
    return [f for f in stdout.strip().split("\n") if f]


def get_deleted_files(repo_path, from_b, to_b, paths, bare=False):
    args = ["diff", "--diff-filter=D", "--name-only", f"{from_b}..{to_b}", "--"] + paths
    stdout, _, _ = run_git(args, repo_path, bare)
    return [f for f in stdout.strip().split("\n") if f]


def get_modified_files(repo_path, from_b, to_b, paths, bare=False):
    args = ["diff", "--diff-filter=M", "--name-only", f"{from_b}..{to_b}", "--"] + paths
    stdout, _, _ = run_git(args, repo_path, bare)
    return [f for f in stdout.strip().split("\n") if f]


def get_key_changes(repo_path, from_b, to_b, paths, bare=False):
    """Get the actual diff content, truncated for LLM consumption."""
    args = ["diff", "-U2", f"{from_b}..{to_b}", "--"] + paths
    stdout, _, _ = run_git(args, repo_path, bare)
    
    # Extract struct/type definitions and significant changes
    changes = []
    current_file = None
    current_hunks = []
    
    for line in stdout.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_hunks:
                changes.append((current_file, current_hunks[:40]))
            match = re.search(r"b/(.*)", line)
            current_file = match.group(1) if match else "unknown"
            current_hunks = []
        elif line.startswith("@@"):
            current_hunks.append(line)
        elif line.startswith("+") and not line.startswith("+++"):
            # Keep significant additions
            if re.search(r'(type |struct|interface|func |//|json:|yaml:|description|spec\.|status\.)', line, re.IGNORECASE):
                current_hunks.append(line)
        elif line.startswith("-") and not line.startswith("---"):
            if re.search(r'(type |struct|interface|func |//|json:|yaml:|description|spec\.|status\.)', line, re.IGNORECASE):
                current_hunks.append(line)
    
    if current_file and current_hunks:
        changes.append((current_file, current_hunks[:40]))
    
    return changes[:30]  # Limit to 30 files


def get_commit_messages(repo_path, from_b, to_b, paths, bare=False):
    args = ["log", "--oneline", "--no-merges", f"{from_b}..{to_b}", "--"] + paths
    stdout, _, _ = run_git(args, repo_path, bare)
    lines = [l for l in stdout.strip().split("\n") if l]
    return lines[:40]


def generate_repo_diff(repo_name, config, from_ver, to_ver):
    """Generate diff summary for a single repo."""
    repo_path = config["path"]
    bare = config["bare"]
    paths = config["doc_paths"]
    
    from_b = f"release-{from_ver}"
    to_b = f"release-{to_ver}"
    
    # Non-bare repos use origin/ prefix
    if not bare:
        from_b = f"origin/release-{from_ver}"
        to_b = f"origin/release-{to_ver}"
    
    if not repo_path.exists():
        return None, f"Repo not found: {repo_path}"
    
    if not has_branch(repo_path, from_b if bare else f"release-{from_ver}", bare):
        return None, f"Branch release-{from_ver} not found"
    if not has_branch(repo_path, to_b if bare else f"release-{to_ver}", bare):
        return None, f"Branch release-{to_ver} not found"
    
    new_files = get_new_files(repo_path, from_b, to_b, paths, bare)
    deleted_files = get_deleted_files(repo_path, from_b, to_b, paths, bare)
    modified_files = get_modified_files(repo_path, from_b, to_b, paths, bare)
    key_changes = get_key_changes(repo_path, from_b, to_b, paths, bare)
    commits = get_commit_messages(repo_path, from_b, to_b, paths, bare)
    stat = get_diff_stat(repo_path, from_b, to_b, paths, bare)
    
    md = []
    md.append(f"# {repo_name}: release-{from_ver} → release-{to_ver}")
    md.append("")
    md.append(f"Repo: `openshift/{repo_name}`")
    md.append("")
    
    md.append("## Overview")
    md.append("")
    md.append(f"- New files: {len(new_files)}")
    md.append(f"- Deleted files: {len(deleted_files)}")
    md.append(f"- Modified files: {len(modified_files)}")
    md.append(f"- Total commits: {len(commits)}")
    md.append("")
    
    if key_changes:
        md.append("## Key Code Changes")
        md.append("")
        for filepath, hunks in key_changes:
            md.append(f"### `{filepath}`")
            md.append("")
            md.append("```")
            for h in hunks:
                md.append(h)
            md.append("```")
            md.append("")
    
    if new_files:
        md.append("## New Files")
        md.append("")
        for f in sorted(new_files)[:40]:
            md.append(f"- `{f}`")
        md.append("")
    
    if deleted_files:
        md.append("## Deleted Files")
        md.append("")
        for f in sorted(deleted_files)[:30]:
            md.append(f"- `{f}`")
        md.append("")
    
    if commits:
        md.append("## Key Commits")
        md.append("")
        for c in commits[:30]:
            md.append(f"- {c}")
        md.append("")
    
    if stat:
        md.append("## Stat")
        md.append("")
        md.append("```")
        md.append(stat[:4000])
        md.append("```")
    
    return "\n".join(md), None


def main():
    from_ver = "4.16"
    to_ver = "4.17"
    
    if len(os.sys.argv) > 2:
        from_ver = os.sys.argv[1]
        to_ver = os.sys.argv[2]
    
    OUTPUT_DIR = DIFFS_ROOT / f"{from_ver}-to-{to_ver}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating multi-repo diff summaries: {from_ver} → {to_ver}")
    print(f"Output: {OUTPUT_DIR}")
    print()
    
    combined_parts = []
    combined_parts.append(f"# Combined Multi-Repo Diff: release-{from_ver} → release-{to_ver}")
    combined_parts.append("")
    combined_parts.append("This document combines code diffs from all repos relevant to installation documentation.")
    combined_parts.append("")
    
    for repo_name, config in REPOS.items():
        print(f"  Processing {repo_name}...")
        summary, error = generate_repo_diff(repo_name, config, from_ver, to_ver)
        
        if error:
            print(f"    SKIP: {error}")
            continue
        
        # Write individual file
        outfile = OUTPUT_DIR / f"{repo_name}-diff-{from_ver}-to-{to_ver}.md"
        outfile.write_text(summary)
        lines = summary.count("\n")
        print(f"    Written: {outfile.name} ({lines} lines)")
        
        combined_parts.append(f"\n---\n")
        combined_parts.append(summary)
    
    # Write combined file
    combined_file = OUTPUT_DIR / f"combined-diff-{from_ver}-to-{to_ver}.md"
    combined_file.write_text("\n".join(combined_parts))
    print(f"\n  Combined: {combined_file.name} ({combined_file.stat().st_size // 1024} KB)")
    print("\nDone.")


if __name__ == "__main__":
    main()
