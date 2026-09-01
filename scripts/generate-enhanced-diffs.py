#!/usr/bin/env python3
"""Generate enhanced structured diff summaries with full file context for key types.

This is an improved version of generate-multi-repo-diffs.py that provides:
1. Full file contents for key type definition files (platform.go, machinepool.go, etc.)
2. Wider diff context (-U5 instead of -U2) for better understanding
3. Relaxed filtering — keeps more lines around struct definitions
4. Full content of new doc files (docs/user/) added in the target version
5. CRD schema sections for changed fields (not the full 5000-line YAML)

The goal: give the LLM enough context to understand WHAT changed and
HOW the field is defined (types, descriptions, constraints) without
drowning it in irrelevant implementation details.
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
        "full_file_patterns": [
            r"pkg/types/[^/]+/platform\.go$",
            r"pkg/types/[^/]+/machinepool\.go$",
            r"pkg/types/[^/]+/.*_types\.go$",
            r"pkg/types/defaults/.*\.go$",
            r"pkg/asset/installconfig/[^/]+/permissions\.go$",
            r"pkg/asset/installconfig/[^/]+/validation\.go$",
            r"docs/user/.*\.md$",
        ],
        "crd_file": "data/data/install.openshift.io_installconfigs.yaml",
    },
    "api": {
        "path": BASE_DIR / "api.git",
        "bare": True,
        "doc_paths": [
            "install/", "config/", "features/",
            "machine/", "operator/", "network/",
        ],
        "full_file_patterns": [
            r"config/v1/types_.*\.go$",
            r"install/v1/types\.go$",
            r"install/v1alpha1/types.*\.go$",
            r"machine/v1/types.*\.go$",
            r"machine/v1beta1/types.*\.go$",
            r"features/.*\.go$",
            r"network/v1/types.*\.go$",
        ],
        "crd_file": None,
    },
    "baremetal-operator": {
        "path": BASE_DIR / "baremetal-operator.git",
        "bare": True,
        "doc_paths": [
            "apis/", "pkg/", "docs/", "config/", "controllers/",
        ],
        "full_file_patterns": [
            r"apis/metal3\.io/.*types.*\.go$",
            r"docs/.*\.md$",
        ],
        "crd_file": None,
    },
    "assisted-installer": {
        "path": BASE_DIR / "assisted-installer.git",
        "bare": True,
        "doc_paths": [
            "src/", "cmd/", "docs/", "config/",
        ],
        "full_file_patterns": [
            r"docs/.*\.md$",
        ],
        "crd_file": None,
    },
    "cluster-network-operator": {
        "path": BASE_DIR / "cluster-network-operator.git",
        "bare": True,
        "doc_paths": [
            "pkg/", "manifests/", "bindata/", "docs/",
        ],
        "full_file_patterns": [
            r"docs/.*\.md$",
        ],
        "crd_file": None,
    },
    "machine-config-operator": {
        "path": BASE_DIR / "machine-config-operator",
        "bare": False,
        "doc_paths": [
            "pkg/", "cmd/", "docs/", "manifests/", "templates/",
        ],
        "full_file_patterns": [
            r"docs/.*\.md$",
            r"pkg/apis/.*types.*\.go$",
        ],
        "crd_file": None,
    },
    "machine-api-operator": {
        "path": BASE_DIR / "machine-api-operator",
        "bare": False,
        "doc_paths": [
            "pkg/", "cmd/", "docs/", "config/",
        ],
        "full_file_patterns": [
            r"docs/.*\.md$",
            r"pkg/apis/.*types.*\.go$",
        ],
        "crd_file": None,
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
        _, _, rc = run_git(["rev-parse", "--verify", branch], repo_path, bare)
        return rc == 0
    else:
        _, _, rc = run_git(["rev-parse", "--verify", f"origin/{branch}"], repo_path, bare)
        if rc == 0:
            return True
        _, _, rc = run_git(["rev-parse", "--verify", branch], repo_path, bare)
        return rc == 0


def get_branch_ref(branch, bare):
    """Return the correct ref for a branch depending on bare/non-bare."""
    if bare:
        return branch
    return f"origin/{branch}"


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


def get_file_content(repo_path, branch_ref, filepath, bare=False):
    """Get the full content of a file at a specific branch."""
    args = ["show", f"{branch_ref}:{filepath}"]
    stdout, _, rc = run_git(args, repo_path, bare)
    if rc == 0:
        return stdout
    return None


def get_full_diff_for_file(repo_path, from_b, to_b, filepath, bare=False):
    """Get the complete diff for a single file with full context."""
    args = ["diff", "-U5", f"{from_b}..{to_b}", "--", filepath]
    stdout, _, _ = run_git(args, repo_path, bare)
    return stdout


def should_include_full_file(filepath, patterns):
    """Check if a file matches the full-file inclusion patterns."""
    for pattern in patterns:
        if re.search(pattern, filepath):
            return True
    return False


def extract_crd_changed_sections(repo_path, from_b, to_b, crd_file, bare=False):
    """Extract only the changed sections of the CRD schema with surrounding context.
    
    Instead of including the full 5000-line CRD, we include the diff hunks
    with extra context lines to show the field hierarchy.
    """
    args = ["diff", "-U10", f"{from_b}..{to_b}", "--", crd_file]
    stdout, _, rc = run_git(args, repo_path, bare)
    if rc != 0 or not stdout.strip():
        return None

    lines = stdout.split("\n")
    sections = []
    current_section = []
    in_hunk = False

    for line in lines:
        if line.startswith("@@"):
            if current_section:
                sections.append("\n".join(current_section))
            current_section = [line]
            in_hunk = True
        elif in_hunk:
            current_section.append(line)
            if len(current_section) > 80:
                current_section.append("... [truncated, hunk too large] ...")
                sections.append("\n".join(current_section))
                current_section = []
                in_hunk = False

    if current_section:
        sections.append("\n".join(current_section))

    return "\n\n".join(sections[:50])


def get_key_changes_enhanced(repo_path, from_b, to_b, paths, bare=False, full_file_patterns=None):
    """Get diff content with enhanced filtering.
    
    Improvements over the original:
    - Uses -U5 for more context around changes
    - Keeps ALL lines within struct definitions (not just filtered patterns)
    - Keeps Go comments that precede struct fields (field documentation)
    - Keeps validation/constraint lines
    """
    args = ["diff", "-U5", f"{from_b}..{to_b}", "--"] + paths
    stdout, _, _ = run_git(args, repo_path, bare)

    changes = []
    current_file = None
    current_hunks = []
    in_struct_block = False

    for line in stdout.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_hunks:
                changes.append((current_file, current_hunks[:60]))
            match = re.search(r"b/(.*)", line)
            current_file = match.group(1) if match else "unknown"
            current_hunks = []
            in_struct_block = False
        elif line.startswith("@@"):
            current_hunks.append(line)
            in_struct_block = False
        elif line.startswith("+") and not line.startswith("+++"):
            stripped = line[1:].strip()
            # Keep line if:
            # 1. It's a type/struct/interface/func definition
            # 2. It's a Go comment (field documentation)
            # 3. It has json/yaml tags (parameter names)
            # 4. It's part of a struct body (field definitions)
            # 5. It has validation annotations
            # 6. It references spec/status/description
            # 7. It's inside a struct block we're tracking
            if (re.search(r'(type |struct\s*\{|interface\s*\{|func )', line, re.IGNORECASE) or
                stripped.startswith("//") or
                re.search(r'(json:"|yaml:"|description|spec\.|status\.)', line, re.IGNORECASE) or
                re.search(r'(`json:"[^"]*"`|`yaml:"[^"]*"`)', line) or
                re.search(r'(//\s*\+optional|//\s*\+required|//\s*\+kubebuilder)', line) or
                re.search(r'(Enum=|Maximum=|Minimum=|MaxItems=|MinItems=)', line) or
                re.search(r'(string|int|bool|float|map\[|^\s*\w+\s+\w)', stripped) and
                    re.search(r'`(json|yaml):', line)):
                current_hunks.append(line)
                if "struct" in line and "{" in line:
                    in_struct_block = True
            elif in_struct_block and stripped and not stripped.startswith("}"):
                current_hunks.append(line)
            elif in_struct_block and stripped.startswith("}"):
                current_hunks.append(line)
                in_struct_block = False
        elif line.startswith("-") and not line.startswith("---"):
            stripped = line[1:].strip()
            if (re.search(r'(type |struct\s*\{|interface\s*\{|func )', line, re.IGNORECASE) or
                stripped.startswith("//") or
                re.search(r'(json:"|yaml:"|description|spec\.|status\.)', line, re.IGNORECASE) or
                re.search(r'(`json:"[^"]*"`|`yaml:"[^"]*"`)', line) or
                re.search(r'(//\s*\+optional|//\s*\+required|//\s*\+kubebuilder)', line) or
                re.search(r'(Enum=|Maximum=|Minimum=|MaxItems=|MinItems=)', line)):
                current_hunks.append(line)

    if current_file and current_hunks:
        changes.append((current_file, current_hunks[:60]))

    return changes[:50]


def get_commit_messages(repo_path, from_b, to_b, paths, bare=False):
    args = ["log", "--oneline", "--no-merges", f"{from_b}..{to_b}", "--"] + paths
    stdout, _, _ = run_git(args, repo_path, bare)
    lines = [l for l in stdout.strip().split("\n") if l]
    return lines[:60]


def generate_repo_diff(repo_name, config, from_ver, to_ver):
    """Generate enhanced diff summary for a single repo."""
    repo_path = config["path"]
    bare = config["bare"]
    paths = config["doc_paths"]
    full_file_patterns = config.get("full_file_patterns", [])
    crd_file = config.get("crd_file")

    from_branch = f"release-{from_ver}"
    to_branch = f"release-{to_ver}"
    from_b = get_branch_ref(from_branch, bare)
    to_b = get_branch_ref(to_branch, bare)

    if not repo_path.exists():
        return None, f"Repo not found: {repo_path}"

    if not has_branch(repo_path, from_branch if bare else from_branch, bare):
        return None, f"Branch release-{from_ver} not found"
    if not has_branch(repo_path, to_branch if bare else to_branch, bare):
        return None, f"Branch release-{to_ver} not found"

    new_files = get_new_files(repo_path, from_b, to_b, paths, bare)
    deleted_files = get_deleted_files(repo_path, from_b, to_b, paths, bare)
    modified_files = get_modified_files(repo_path, from_b, to_b, paths, bare)
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

    # SECTION: Full file contents for key type definitions (NEW)
    full_file_section = []
    files_to_show_full = []

    # Include full content of MODIFIED files that match full_file_patterns
    for f in modified_files:
        if should_include_full_file(f, full_file_patterns):
            files_to_show_full.append(("modified", f))

    # Include full content of NEW files that match full_file_patterns
    for f in new_files:
        if should_include_full_file(f, full_file_patterns):
            files_to_show_full.append(("new", f))

    if files_to_show_full:
        md.append("## Full File Contents (Target Version)")
        md.append("")
        md.append("These are the complete contents of key type definition and documentation files")
        md.append("in the TARGET version. Use these to understand the full field definitions,")
        md.append("types, comments (which become doc descriptions), and constraints.")
        md.append("")

        for status, filepath in files_to_show_full[:25]:
            content = get_file_content(repo_path, to_b, filepath, bare)
            if content and len(content) < 8000:
                md.append(f"### `{filepath}` ({status})")
                md.append("")
                md.append("```go")
                md.append(content.rstrip())
                md.append("```")
                md.append("")
            elif content:
                md.append(f"### `{filepath}` ({status}) [truncated to 8KB]")
                md.append("")
                md.append("```go")
                md.append(content[:8000].rstrip())
                md.append("\n// ... file continues (truncated) ...")
                md.append("```")
                md.append("")

    # SECTION: CRD schema changes (enhanced)
    if crd_file:
        crd_sections = extract_crd_changed_sections(repo_path, from_b, to_b, crd_file, bare)
        if crd_sections:
            md.append("## CRD Schema Changes (install.openshift.io_installconfigs.yaml)")
            md.append("")
            md.append("Changed sections of the CRD with surrounding context.")
            md.append("Field hierarchy shown via indentation. New/modified descriptions")
            md.append("should be reflected in documentation parameter tables.")
            md.append("")
            md.append("```yaml")
            # Limit CRD output to avoid overwhelming the diff
            if len(crd_sections) > 15000:
                md.append(crd_sections[:15000])
                md.append("\n# ... [additional CRD changes truncated] ...")
            else:
                md.append(crd_sections)
            md.append("```")
            md.append("")

    # SECTION: Key code changes (enhanced filtering)
    key_changes = get_key_changes_enhanced(
        repo_path, from_b, to_b, paths, bare, full_file_patterns
    )

    if key_changes:
        md.append("## Key Code Changes (Enhanced Diff)")
        md.append("")
        md.append("Filtered diff showing type definitions, struct fields, comments,")
        md.append("json/yaml tags, validation annotations, and API changes.")
        md.append("")
        for filepath, hunks in key_changes:
            # Skip files we already showed in full
            if any(filepath == f for _, f in files_to_show_full):
                continue
            md.append(f"### `{filepath}`")
            md.append("")
            md.append("```diff")
            for h in hunks:
                md.append(h)
            md.append("```")
            md.append("")

    if new_files:
        md.append("## New Files")
        md.append("")
        for f in sorted(new_files)[:60]:
            md.append(f"- `{f}`")
        md.append("")

    if deleted_files:
        md.append("## Deleted Files")
        md.append("")
        for f in sorted(deleted_files)[:40]:
            md.append(f"- `{f}`")
        md.append("")

    if commits:
        md.append("## Key Commits")
        md.append("")
        for c in commits[:50]:
            md.append(f"- {c}")
        md.append("")

    if stat:
        md.append("## Diffstat")
        md.append("")
        md.append("```")
        md.append(stat[:5000])
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

    print(f"Generating ENHANCED multi-repo diff summaries: {from_ver} → {to_ver}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    combined_parts = []
    combined_parts.append(f"# Enhanced Combined Multi-Repo Diff: release-{from_ver} → release-{to_ver}")
    combined_parts.append("")
    combined_parts.append("This document combines ENHANCED code diffs from all repos relevant to")
    combined_parts.append("installation documentation. It includes:")
    combined_parts.append("- Full file contents for key type definition files (platform.go, types.go)")
    combined_parts.append("- CRD schema change sections with field hierarchy context")
    combined_parts.append("- Enhanced diff filtering with struct body tracking")
    combined_parts.append("- Full content of new documentation files")
    combined_parts.append("")
    combined_parts.append("Use the 'Full File Contents' sections to understand exact field names,")
    combined_parts.append("types, Go comments (which become parameter descriptions), json tags")
    combined_parts.append("(which become parameter names), and validation annotations (which")
    combined_parts.append("become constraints in the docs).")
    combined_parts.append("")

    for repo_name, config in REPOS.items():
        print(f"  Processing {repo_name}...")
        summary, error = generate_repo_diff(repo_name, config, from_ver, to_ver)

        if error:
            print(f"    SKIP: {error}")
            continue

        # Write individual file
        outfile = OUTPUT_DIR / f"{repo_name}-enhanced-diff-{from_ver}-to-{to_ver}.md"
        outfile.write_text(summary)
        lines = summary.count("\n")
        size_kb = len(summary) // 1024
        print(f"    Written: {outfile.name} ({lines} lines, {size_kb} KB)")

        combined_parts.append(f"\n---\n")
        combined_parts.append(summary)

    # Write combined file
    combined_content = "\n".join(combined_parts)
    combined_file = OUTPUT_DIR / f"enhanced-combined-diff-{from_ver}-to-{to_ver}.md"
    combined_file.write_text(combined_content)
    size_kb = len(combined_content) // 1024
    print(f"\n  Combined: {combined_file.name} ({size_kb} KB)")
    print(f"\n  (Original combined diff was typically ~100-200 KB)")
    print(f"  (Enhanced version provides full type files + CRD sections)")
    print("\nDone.")


if __name__ == "__main__":
    main()
