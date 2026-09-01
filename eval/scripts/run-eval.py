#!/usr/bin/env python3
"""Standalone evaluation script for generated docs.

Run against a specific eval case to produce a comprehensive report
with both deterministic and (optionally) LLM-based scoring.

Usage:
    python3 eval/scripts/run-eval.py case-4.17
    python3 eval/scripts/run-eval.py case-4.17 --llm-judge  # Requires ANTHROPIC_API_KEY
"""

import os
import re
import sys
import difflib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVAL_DIR = BASE_DIR / "eval"


def normalize_text(content):
    """Strip AsciiDoc comments and normalize whitespace."""
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("//") and not stripped.startswith("// Module included"):
            continue
        lines.append(line)
    return "\n".join(lines)


def get_adoc_files(directory):
    """Get all .adoc files recursively."""
    files = {}
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            if f.endswith(".adoc"):
                rel = os.path.relpath(os.path.join(root, f), directory)
                files[rel] = os.path.join(root, f)
    return files


def extract_sections(content):
    """Extract AsciiDoc section headers."""
    return set(re.findall(r'^(=+ .+)$', content, re.MULTILINE))


def extract_parameters(content):
    """Extract backtick-quoted parameter names."""
    return set(re.findall(r'`([a-zA-Z][a-zA-Z0-9_.]+)`', content))


def extract_includes(content):
    """Extract include directives."""
    return set(re.findall(r'include::(modules/[^\[]+)\[', content))


def evaluate_case(case_name, cases_base_dir=None):
    """Run full evaluation for a case."""
    if cases_base_dir is None:
        cases_base_dir = EVAL_DIR / "dataset" / "cases"
    case_dir = cases_base_dir / case_name
    ref_dir = case_dir / "reference"
    out_dir = case_dir / "output"

    if not ref_dir.exists():
        print(f"ERROR: Reference directory not found: {ref_dir}")
        sys.exit(1)
    if not out_dir.exists():
        print(f"ERROR: Output directory not found: {out_dir}")
        print(f"  Run the skill first to generate output into: {out_dir}")
        sys.exit(1)

    # Handle nested directory structures — if reference has a single
    # subdirectory like "installing/", descend into it for comparison
    ref_subdirs = [d for d in ref_dir.iterdir() if d.is_dir()]
    if len(ref_subdirs) == 1 and ref_subdirs[0].name == "installing":
        ref_dir = ref_subdirs[0]

    # Same for output — check if it has a single "installing/" wrapper
    out_subdirs = [d for d in out_dir.iterdir() if d.is_dir()]
    if len(out_subdirs) == 1 and out_subdirs[0].name == "installing":
        out_dir = out_subdirs[0]

    ref_files = get_adoc_files(ref_dir)
    gen_files = get_adoc_files(out_dir)

    print(f"{'='*70}")
    print(f"  EVALUATION: {case_name}")
    print(f"{'='*70}")
    print(f"  Reference files: {len(ref_files)}")
    print(f"  Generated files: {len(gen_files)}")
    print()

    # ── File Coverage ──
    present = set(ref_files.keys()) & set(gen_files.keys())
    missing = set(ref_files.keys()) - set(gen_files.keys())
    extra = set(gen_files.keys()) - set(ref_files.keys())
    file_coverage = len(present) / len(ref_files) if ref_files else 0

    # ── Per-file Metrics ──
    text_similarities = []
    section_coverages = []
    param_coverages = []
    include_coverages = []
    low_scoring = []

    for rel_path in sorted(present):
        ref_content = Path(ref_files[rel_path]).read_text(errors="replace")
        gen_content = Path(gen_files[rel_path]).read_text(errors="replace")

        # Text similarity
        ref_norm = normalize_text(ref_content)
        gen_norm = normalize_text(gen_content)
        ref_lines = ref_norm.split("\n")
        gen_lines = gen_norm.split("\n")
        sim = difflib.SequenceMatcher(None, gen_lines, ref_lines).ratio()
        text_similarities.append(sim)

        # Section coverage
        ref_sections = extract_sections(ref_content)
        gen_sections = extract_sections(gen_content)
        if ref_sections:
            sec_cov = len(ref_sections & gen_sections) / len(ref_sections)
        else:
            sec_cov = 1.0
        section_coverages.append(sec_cov)

        # Parameter coverage
        ref_params = extract_parameters(ref_content)
        gen_params = extract_parameters(gen_content)
        if ref_params:
            param_cov = len(ref_params & gen_params) / len(ref_params)
        else:
            param_cov = 1.0
        param_coverages.append(param_cov)

        # Include coverage
        ref_includes = extract_includes(ref_content)
        gen_includes = extract_includes(gen_content)
        if ref_includes:
            inc_cov = len(ref_includes & gen_includes) / len(ref_includes)
        else:
            inc_cov = 1.0
        include_coverages.append(inc_cov)

        if sim < 0.80:
            low_scoring.append((rel_path, sim, sec_cov, param_cov))

    # Score missing files as 0%
    for _ in missing:
        text_similarities.append(0.0)
        section_coverages.append(0.0)
        param_coverages.append(0.0)
        include_coverages.append(0.0)

    # ── Aggregates ──
    avg_text_sim = sum(text_similarities) / len(text_similarities) if text_similarities else 0
    avg_section = sum(section_coverages) / len(section_coverages) if section_coverages else 0
    avg_param = sum(param_coverages) / len(param_coverages) if param_coverages else 0
    avg_include = sum(include_coverages) / len(include_coverages) if include_coverages else 0

    # ── Hardcoded Names Check ──
    violations = []
    patterns = [
        (r'OpenShift Container Platform', "{product-title}"),
        (r'\bRHCOS\b', "{op-system}"),
        (r'\bRHEL\b', "{op-system-base}"),
    ]
    for rel_path in sorted(present)[:50]:
        gen_content = Path(gen_files[rel_path]).read_text(errors="replace")
        in_code = False
        for i, line in enumerate(gen_content.split("\n"), 1):
            if line.strip() == "----":
                in_code = not in_code
            if in_code:
                continue
            for pat, fix in patterns:
                if re.search(pat, line):
                    violations.append(f"{rel_path}:{i}")

    # ── Include Validity ──
    broken_includes = []
    for rel_path in sorted(present):
        gen_content = Path(gen_files[rel_path]).read_text(errors="replace")
        for match in re.finditer(r'include::(modules/[^\[]+)\[', gen_content):
            target = out_dir / match.group(1)
            if not target.exists():
                broken_includes.append(f"{rel_path} -> {match.group(1)}")

    # ── Report ──
    report = []
    report.append(f"# Evaluation Report: {case_name}")
    report.append("")
    report.append("## Summary Metrics")
    report.append("")
    report.append(f"| Metric | Score | Status |")
    report.append(f"|--------|-------|--------|")
    report.append(f"| File Coverage | {file_coverage:.1%} | {'PASS' if file_coverage >= 0.90 else 'FAIL'} |")
    report.append(f"| Text Similarity (avg) | {avg_text_sim:.1%} | {'PASS' if avg_text_sim >= 0.85 else 'WARN'} |")
    report.append(f"| Section Coverage (avg) | {avg_section:.1%} | {'PASS' if avg_section >= 0.90 else 'FAIL'} |")
    report.append(f"| Parameter Coverage (avg) | {avg_param:.1%} | {'PASS' if avg_param >= 0.90 else 'FAIL'} |")
    report.append(f"| Include Coverage (avg) | {avg_include:.1%} | {'PASS' if avg_include >= 0.90 else 'FAIL'} |")
    report.append(f"| Hardcoded Names | {len(violations)} violations | {'PASS' if len(violations) <= 5 else 'FAIL'} |")
    report.append(f"| Broken Includes | {len(broken_includes)} broken | {'PASS' if not broken_includes else 'FAIL'} |")
    report.append("")

    report.append("## File Statistics")
    report.append("")
    report.append(f"- Reference files: {len(ref_files)}")
    report.append(f"- Generated files: {len(gen_files)}")
    report.append(f"- Present in both: {len(present)}")
    report.append(f"- Missing from generated: {len(missing)}")
    report.append(f"- Extra in generated: {len(extra)}")
    report.append("")

    if missing:
        report.append("## Missing Files (scored as 0%)")
        report.append("")
        for f in sorted(missing)[:30]:
            report.append(f"- `{f}`")
        if len(missing) > 30:
            report.append(f"- ... and {len(missing) - 30} more")
        report.append("")

    if extra:
        report.append("## Extra Files (in generated, not in reference)")
        report.append("")
        for f in sorted(extra)[:20]:
            report.append(f"- `{f}`")
        report.append("")

    if low_scoring:
        report.append("## Low-Scoring Files (text similarity < 80%)")
        report.append("")
        report.append("| File | Text Sim | Section Cov | Param Cov |")
        report.append("|------|----------|-------------|-----------|")
        for path, sim, sec, param in sorted(low_scoring, key=lambda x: x[1]):
            report.append(f"| `{path}` | {sim:.1%} | {sec:.1%} | {param:.1%} |")
        report.append("")

    if broken_includes:
        report.append("## Broken Include Directives")
        report.append("")
        for bi in broken_includes[:20]:
            report.append(f"- `{bi}`")
        report.append("")

    report_text = "\n".join(report)

    # Write report
    results_file = case_dir / "results.md"
    results_file.write_text(report_text)
    print(report_text)
    print(f"\n  Report written to: {results_file}")

    # Write machine-readable metrics
    import json
    metrics = {
        "file_coverage": round(file_coverage, 4),
        "text_similarity": round(avg_text_sim, 4),
        "section_coverage": round(avg_section, 4),
        "parameter_coverage": round(avg_param, 4),
        "include_coverage": round(avg_include, 4),
        "hardcoded_violations": len(violations),
        "broken_includes": len(broken_includes),
        "missing_files": len(missing),
        "extra_files": len(extra),
    }
    metrics_file = case_dir / "metrics.json"
    metrics_file.write_text(json.dumps(metrics, indent=2))
    print(f"  Metrics written to: {metrics_file}")

    return metrics


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 eval/scripts/run-eval.py <case-name> [--section=installing|updating]")
        print("       python3 eval/scripts/run-eval.py case-4.17")
        print("       python3 eval/scripts/run-eval.py case-4.17 --section=updating")
        print("       python3 eval/scripts/run-eval.py all --section=installing")
        sys.exit(1)

    case_arg = sys.argv[1]
    
    # Parse --section argument
    section = "installing"
    for arg in sys.argv[2:]:
        if arg.startswith("--section="):
            section = arg.split("=", 1)[1]
    
    # Override the cases path with section
    CASES_DIR = EVAL_DIR / "dataset" / "cases" / section

    if case_arg == "all":
        all_metrics = {}
        if not CASES_DIR.exists():
            print(f"ERROR: Cases directory not found: {CASES_DIR}")
            sys.exit(1)
        for case_dir in sorted(CASES_DIR.iterdir()):
            if case_dir.is_dir() and case_dir.name.startswith("case-"):
                if (case_dir / "output").exists():
                    m = evaluate_case(case_dir.name, CASES_DIR)
                    all_metrics[case_dir.name] = m
                    print()
                else:
                    print(f"  SKIP: {case_dir.name} (no output/ directory)")

        if all_metrics:
            print(f"\n{'='*70}")
            print("  SUMMARY ACROSS ALL CASES")
            print(f"{'='*70}")
            print(f"{'Case':<12} {'FileCov':>8} {'TextSim':>8} {'SecCov':>8} {'ParamCov':>9}")
            for name, m in sorted(all_metrics.items()):
                print(f"{name:<12} {m['file_coverage']:>7.1%} {m['text_similarity']:>7.1%} "
                      f"{m['section_coverage']:>7.1%} {m['parameter_coverage']:>8.1%}")
    else:
        evaluate_case(case_arg, CASES_DIR)
