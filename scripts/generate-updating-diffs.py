#!/usr/bin/env python3
"""Generate structured code diff summaries for the updating section.

Source repositories:
- cluster-version-operator.git (bare) — CVO behavior, preconditions, upgrade logic
- oc.git (bare) — CLI commands (oc adm upgrade subcommands)
- machine-config-operator/ (non-bare) — MCO node update behavior
- api.git (bare) — ClusterVersion API types, Kubernetes version (go.mod)
- cluster-network-operator.git (bare) — CNI/SDN migration gates, network update blockers

Output: diffs/updating/<from>-to-<to>/combined-diff-<from>-to-<to>.md
"""

import subprocess
import os
from pathlib import Path

WORKSPACE = Path("/home/sapurohi/Desktop/Agentic OKD docs")
DIFFS_ROOT = WORKSPACE / "diffs" / "updating"

REPOS = {
    "cluster-version-operator": {
        "path": WORKSPACE / "cluster-version-operator.git",
        "bare": True,
        "doc_paths": ["pkg/cvo/", "pkg/payload/", "pkg/autoupdate/", "cmd/", "docs/"],
        "description": "Cluster Version Operator — orchestrates cluster updates"
    },
    "oc": {
        "path": WORKSPACE / "oc.git",
        "bare": True,
        "doc_paths": ["pkg/cli/admin/upgrade/"],
        "description": "oc CLI — oc adm upgrade subcommands (recommend, status, channel, accept, rollback)"
    },
    "machine-config-operator": {
        "path": WORKSPACE / "machine-config-operator",
        "bare": False,
        "doc_paths": ["pkg/daemon/", "pkg/controller/node/", "pkg/controller/drain/", "docs/", "pkg/apis/"],
        "description": "Machine Config Operator — node update orchestration (drain, reboot, MCP coordination)"
    },
    "api": {
        "path": WORKSPACE / "api.git",
        "bare": True,
        "doc_paths": ["config/v1/", "config/v1alpha1/", "operator/v1/"],
        "description": "OpenShift API — ClusterVersion types, condition types, operator API changes affecting updates"
    },
    "cluster-network-operator": {
        "path": WORKSPACE / "cluster-network-operator.git",
        "bare": True,
        "doc_paths": ["pkg/network/", "pkg/controller/", "bindata/", "docs/", "manifests/"],
        "description": "Cluster Network Operator — SDN/OVN migration gates, CNI changes that block or affect updates"
    },
}

# Key file patterns for full content extraction
KEY_FILES_PATTERNS = [
    # CVO
    "pkg/cvo/upgradeable.go",
    "pkg/cvo/status.go",
    "pkg/cvo/status_history.go",
    "pkg/payload/precondition/clusterversion/upgradeable.go",
    "pkg/autoupdate/autoupdate.go",
    # oc CLI
    "pkg/cli/admin/upgrade/upgrade.go",
    "pkg/cli/admin/upgrade/recommend/recommend.go",
    "pkg/cli/admin/upgrade/status/status.go",
    "pkg/cli/admin/upgrade/status/controlplane.go",
    "pkg/cli/admin/upgrade/status/workerpool.go",
    "pkg/cli/admin/upgrade/channel/channel.go",
    # MCO
    "pkg/daemon/update.go",
    "pkg/controller/node/node_controller.go",
    # API — ClusterVersion types (tells us conditions, spec fields, Kubernetes version)
    "config/v1/types_cluster_version.go",
    "config/v1/types_cluster_operator.go",
    # API — go.mod (Kubernetes version shipped)
    "go.mod",
    # CNO — SDN/OVN migration and network gates
    "pkg/network/render.go",
    "manifests/0000_70_cluster-network-operator_01_crd.yaml",
]


def run(cmd, cwd=None):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.stdout.strip()


def has_branch(repo_path, branch, bare):
    if bare:
        out = run(["git", "--git-dir", str(repo_path), "branch", "--list", branch])
    else:
        out = run(["git", "-C", str(repo_path), "branch", "-r", "--list", f"origin/{branch}"])
    return bool(out.strip())


def get_diff(repo_path, from_branch, to_branch, paths, bare, context=5):
    if bare:
        cmd = ["git", "--git-dir", str(repo_path), "diff", f"-U{context}",
               from_branch, to_branch, "--"] + paths
    else:
        cmd = ["git", "-C", str(repo_path), "diff", f"-U{context}",
               f"origin/{from_branch}", f"origin/{to_branch}", "--"] + paths
    return run(cmd)


def get_commits(repo_path, from_branch, to_branch, paths, bare, max_commits=40):
    if bare:
        cmd = ["git", "--git-dir", str(repo_path), "log", "--oneline",
               f"{from_branch}..{to_branch}", "--"] + paths
    else:
        cmd = ["git", "-C", str(repo_path), "log", "--oneline",
               f"origin/{from_branch}..origin/{to_branch}", "--"] + paths
    out = run(cmd)
    lines = out.split("\n") if out else []
    return lines[:max_commits]


def get_file_content(repo_path, branch, filepath, bare):
    if bare:
        cmd = ["git", "--git-dir", str(repo_path), "show", f"{branch}:{filepath}"]
    else:
        cmd = ["git", "-C", str(repo_path), "show", f"origin/{branch}:{filepath}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        content = result.stdout
        # For go.mod, extract only the Kubernetes version lines
        if filepath == "go.mod" and len(content) > 2000:
            lines = content.split("\n")
            filtered = [l for l in lines if "k8s.io/" in l or "module " in l]
            return f"// Filtered go.mod — Kubernetes dependency versions:\n" + "\n".join(filtered[:30])
        return content
    return None


def get_diffstat(repo_path, from_branch, to_branch, paths, bare):
    if bare:
        cmd = ["git", "--git-dir", str(repo_path), "diff", "--stat",
               from_branch, to_branch, "--"] + paths
    else:
        cmd = ["git", "-C", str(repo_path), "diff", "--stat",
               f"origin/{from_branch}", f"origin/{to_branch}", "--"] + paths
    return run(cmd)


def filter_key_changes(diff_text, max_hunks=50):
    """Extract doc-relevant hunks from the diff."""
    lines = diff_text.split("\n")
    output = []
    in_hunk = False
    hunk_count = 0
    current_file = ""

    for line in lines:
        if line.startswith("diff --git"):
            current_file = line.split(" b/")[-1] if " b/" in line else ""
            output.append(line)
            in_hunk = False
        elif line.startswith("@@"):
            hunk_count += 1
            if hunk_count > max_hunks:
                output.append(f"... ({hunk_count}+ hunks, truncated)")
                break
            output.append(line)
            in_hunk = True
        elif in_hunk and (line.startswith("+") or line.startswith("-") or line.startswith(" ")):
            # Keep all context in update-related code
            output.append(line)

    return "\n".join(output)


def generate_repo_diff(repo_name, config, from_ver, to_ver):
    repo_path = config["path"]
    bare = config["bare"]
    paths = config["doc_paths"]

    from_branch = f"release-{from_ver}"
    to_branch = f"release-{to_ver}"

    if not has_branch(repo_path, from_branch, bare):
        return None
    if not has_branch(repo_path, to_branch, bare):
        return None

    sections = []
    sections.append(f"# {repo_name}")
    sections.append(f"**{config['description']}**\n")

    # Diffstat
    diffstat = get_diffstat(repo_path, from_branch, to_branch, paths, bare)
    if diffstat:
        sections.append("## Diffstat")
        sections.append(f"```\n{diffstat}\n```\n")

    # Full file contents for key files
    full_files = []
    for pattern in KEY_FILES_PATTERNS:
        content = get_file_content(repo_path, to_branch, pattern, bare)
        if content and len(content) < 15000:
            full_files.append(f"### {pattern}\n```go\n{content}\n```")
    
    if full_files:
        sections.append("## Full File Contents (Target Version)")
        sections.append("These files show the complete state in the target version:\n")
        sections.extend(full_files)
        sections.append("")

    # Key code changes
    diff_text = get_diff(repo_path, from_branch, to_branch, paths, bare)
    if diff_text:
        filtered = filter_key_changes(diff_text)
        if filtered:
            sections.append("## Key Code Changes")
            sections.append(f"```diff\n{filtered}\n```\n")

    # Commits
    commits = get_commits(repo_path, from_branch, to_branch, paths, bare)
    if commits:
        sections.append("## Commits")
        sections.append("```")
        sections.extend(commits)
        sections.append("```\n")

    return "\n".join(sections)


def main():
    version_pairs = [
        ("4.16", "4.17"),
        ("4.17", "4.18"),
        ("4.18", "4.19"),
        ("4.19", "4.20"),
        ("4.20", "4.21"),
        ("4.21", "4.22"),
    ]

    for from_ver, to_ver in version_pairs:
        output_dir = DIFFS_ROOT / f"{from_ver}-to-{to_ver}"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"Generating updating diff: {from_ver} → {to_ver}")
        print(f"{'='*60}")

        combined_sections = []
        combined_sections.append(f"# Updating Section Code Diff: {from_ver} → {to_ver}")
        combined_sections.append(f"\nThis document summarizes code changes relevant to the 'Updating clusters' documentation section between OpenShift {from_ver} and {to_ver}.\n")
        combined_sections.append("---\n")

        for repo_name, config in REPOS.items():
            print(f"  Processing {repo_name}...")
            content = generate_repo_diff(repo_name, config, from_ver, to_ver)
            if content:
                combined_sections.append(content)
                combined_sections.append("\n---\n")
                # Also save individual repo diff
                repo_file = output_dir / f"{repo_name}-diff-{from_ver}-to-{to_ver}.md"
                repo_file.write_text(content)
            else:
                print(f"    Skipped (branches not found)")

        # Write combined diff
        combined_file = output_dir / f"combined-diff-{from_ver}-to-{to_ver}.md"
        combined_file.write_text("\n".join(combined_sections))
        print(f"  Output: {combined_file}")


if __name__ == "__main__":
    main()
