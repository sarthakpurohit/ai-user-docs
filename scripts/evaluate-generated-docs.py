#!/usr/bin/env python3
"""Evaluate generated installation docs against actual docs for a given version.

Compares the generated documentation output against the ground-truth docs
extracted from openshift-docs, producing quantitative metrics and a detailed
report of differences.

Usage:
    python3 evaluate-generated-docs.py <generated-dir> <actual-dir> [--output=<report-path>]
"""

import os
import sys
import re
import difflib
from pathlib import Path
from collections import defaultdict


def normalize_text(text):
    """Normalize AsciiDoc text for comparison (strip comments, normalize whitespace)."""
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("//") and not stripped.startswith("// Module"):
            continue
        lines.append(line)
    return "\n".join(lines)


def extract_sections(text):
    """Extract section headers and their content from AsciiDoc."""
    sections = {}
    current_section = "preamble"
    current_content = []
    
    for line in text.split("\n"):
        if re.match(r'^=+\s+', line):
            if current_content:
                sections[current_section] = "\n".join(current_content)
            current_section = re.sub(r'^=+\s+', '', line).strip()
            current_content = []
        else:
            current_content.append(line)
    
    if current_content:
        sections[current_section] = "\n".join(current_content)
    
    return sections


def extract_parameters(text):
    """Extract parameter names from AsciiDoc parameter tables."""
    params = set()
    for match in re.finditer(r'`([a-zA-Z][a-zA-Z0-9_.]*)`', text):
        candidate = match.group(1)
        if '.' in candidate or candidate[0].islower():
            params.add(candidate)
    return params


def extract_includes(text):
    """Extract include directives."""
    includes = set()
    for match in re.finditer(r'include::(modules/[^\[]+)\[', text):
        includes.add(match.group(1))
    return includes


def extract_code_blocks(text):
    """Extract code block contents."""
    blocks = []
    in_block = False
    current_block = []
    
    for line in text.split("\n"):
        if line.strip() == "----":
            if in_block:
                blocks.append("\n".join(current_block))
                current_block = []
                in_block = False
            else:
                in_block = True
        elif in_block:
            current_block.append(line)
    
    return blocks


def compute_text_similarity(text1, text2):
    """Compute similarity ratio between two texts."""
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    
    seq = difflib.SequenceMatcher(None, text1.split("\n"), text2.split("\n"))
    return seq.ratio()


def find_matching_file(gen_file, actual_files):
    """Find the best matching file in actual docs for a generated file."""
    gen_name = os.path.basename(gen_file)
    
    for af in actual_files:
        if os.path.basename(af) == gen_name:
            return af
    
    gen_stem = Path(gen_file).stem
    for af in actual_files:
        if Path(af).stem == gen_stem:
            return af
    
    return None


def evaluate_file_pair(gen_path, actual_path):
    """Compare a generated file against its actual counterpart."""
    with open(gen_path, 'r', errors='replace') as f:
        gen_text = f.read()
    with open(actual_path, 'r', errors='replace') as f:
        actual_text = f.read()
    
    gen_norm = normalize_text(gen_text)
    actual_norm = normalize_text(actual_text)
    
    metrics = {}
    
    # Overall text similarity
    metrics['text_similarity'] = compute_text_similarity(gen_norm, actual_norm)
    
    # Section coverage
    gen_sections = extract_sections(gen_norm)
    actual_sections = extract_sections(actual_norm)
    
    if actual_sections:
        matched_sections = set(gen_sections.keys()) & set(actual_sections.keys())
        metrics['section_coverage'] = len(matched_sections) / len(actual_sections)
        metrics['extra_sections'] = list(set(gen_sections.keys()) - set(actual_sections.keys()))
        metrics['missing_sections'] = list(set(actual_sections.keys()) - set(gen_sections.keys()))
    else:
        metrics['section_coverage'] = 1.0 if not gen_sections else 0.0
        metrics['extra_sections'] = []
        metrics['missing_sections'] = []
    
    # Parameter coverage
    gen_params = extract_parameters(gen_norm)
    actual_params = extract_parameters(actual_norm)
    
    if actual_params:
        matched_params = gen_params & actual_params
        metrics['param_coverage'] = len(matched_params) / len(actual_params)
        metrics['missing_params'] = list(actual_params - gen_params)
        metrics['extra_params'] = list(gen_params - actual_params)
    else:
        metrics['param_coverage'] = 1.0
        metrics['missing_params'] = []
        metrics['extra_params'] = []
    
    # Include directive coverage
    gen_includes = extract_includes(gen_norm)
    actual_includes = extract_includes(actual_norm)
    
    if actual_includes:
        matched_includes = gen_includes & actual_includes
        metrics['include_coverage'] = len(matched_includes) / len(actual_includes)
        metrics['missing_includes'] = list(actual_includes - gen_includes)
    else:
        metrics['include_coverage'] = 1.0
        metrics['missing_includes'] = []
    
    # Code block count comparison
    gen_blocks = extract_code_blocks(gen_norm)
    actual_blocks = extract_code_blocks(actual_norm)
    metrics['code_block_count_gen'] = len(gen_blocks)
    metrics['code_block_count_actual'] = len(actual_blocks)
    
    # Line count comparison
    metrics['line_count_gen'] = len(gen_norm.split("\n"))
    metrics['line_count_actual'] = len(actual_norm.split("\n"))
    
    return metrics


def evaluate_directory(generated_dir, actual_dir):
    """Full evaluation of generated docs against actual docs."""
    
    gen_files = []
    for root, dirs, files in os.walk(generated_dir):
        for f in files:
            if f.endswith('.adoc'):
                gen_files.append(os.path.join(root, f))
    
    actual_files = []
    for root, dirs, files in os.walk(actual_dir):
        for f in files:
            if f.endswith('.adoc'):
                actual_files.append(os.path.join(root, f))
    
    # File-level metrics
    gen_basenames = {os.path.basename(f) for f in gen_files}
    actual_basenames = {os.path.basename(f) for f in actual_files}
    
    results = {
        'file_metrics': {
            'generated_count': len(gen_files),
            'actual_count': len(actual_files),
            'matched_files': len(gen_basenames & actual_basenames),
            'missing_files': sorted(actual_basenames - gen_basenames),
            'extra_files': sorted(gen_basenames - actual_basenames),
        },
        'per_file': {},
        'aggregate': {},
    }
    
    # Per-file comparison
    similarities = []
    section_coverages = []
    param_coverages = []
    include_coverages = []
    
    for gen_path in gen_files:
        match = find_matching_file(gen_path, actual_files)
        if match:
            rel_path = os.path.relpath(gen_path, generated_dir)
            file_metrics = evaluate_file_pair(gen_path, match)
            results['per_file'][rel_path] = file_metrics
            similarities.append(file_metrics['text_similarity'])
            section_coverages.append(file_metrics['section_coverage'])
            param_coverages.append(file_metrics['param_coverage'])
            include_coverages.append(file_metrics['include_coverage'])
    
    # Score missing files as 0% (files in actual but not generated)
    missing_count = len(results['file_metrics']['missing_files'])
    for _ in range(missing_count):
        similarities.append(0.0)
        section_coverages.append(0.0)
        param_coverages.append(0.0)
        include_coverages.append(0.0)
    
    # Aggregate metrics
    n = len(similarities) if similarities else 1
    results['aggregate'] = {
        'avg_text_similarity': sum(similarities) / n if similarities else 0,
        'avg_section_coverage': sum(section_coverages) / n if section_coverages else 0,
        'avg_param_coverage': sum(param_coverages) / n if param_coverages else 0,
        'avg_include_coverage': sum(include_coverages) / n if include_coverages else 0,
        'file_coverage': results['file_metrics']['matched_files'] / max(results['file_metrics']['actual_count'], 1),
    }
    
    return results


def format_report(results, generated_dir, actual_dir):
    """Format evaluation results as a Markdown report."""
    
    agg = results['aggregate']
    fm = results['file_metrics']
    
    report = []
    report.append("# Documentation Evaluation Report (Fair)")
    report.append("")
    report.append(f"**Generated docs:** `{generated_dir}`")
    report.append(f"**Actual docs:** `{actual_dir}`")
    report.append("")
    report.append("> **Fair evaluation**: New files (in actual but not generated) are scored as 0%.")
    report.append("> No content was copied from actual docs during generation.")
    report.append("")
    
    report.append("## Aggregate Metrics")
    report.append("")
    report.append("| Metric | Score |")
    report.append("|--------|-------|")
    report.append(f"| File Coverage | {agg['file_coverage']:.1%} ({fm['matched_files']}/{fm['actual_count']}) |")
    report.append(f"| Avg Text Similarity | {agg['avg_text_similarity']:.1%} |")
    report.append(f"| Avg Section Coverage | {agg['avg_section_coverage']:.1%} |")
    report.append(f"| Avg Parameter Coverage | {agg['avg_param_coverage']:.1%} |")
    report.append(f"| Avg Include Coverage | {agg['avg_include_coverage']:.1%} |")
    report.append("")
    
    report.append("## File Inventory")
    report.append("")
    report.append(f"- Generated files: {fm['generated_count']}")
    report.append(f"- Actual files: {fm['actual_count']}")
    report.append(f"- Matched: {fm['matched_files']}")
    report.append(f"- Missing from generated: {len(fm['missing_files'])}")
    report.append(f"- Extra in generated: {len(fm['extra_files'])}")
    report.append("")
    
    if fm['missing_files']:
        report.append("### Missing Files (in actual but not generated)")
        report.append("")
        for f in fm['missing_files'][:30]:
            report.append(f"- `{f}`")
        if len(fm['missing_files']) > 30:
            report.append(f"- ... and {len(fm['missing_files']) - 30} more")
        report.append("")
    
    if fm['extra_files']:
        report.append("### Extra Files (in generated but not actual)")
        report.append("")
        for f in fm['extra_files'][:30]:
            report.append(f"- `{f}`")
        report.append("")
    
    # Per-file details (top issues)
    report.append("## Per-File Results (sorted by similarity)")
    report.append("")
    report.append("| File | Similarity | Sections | Params | Includes |")
    report.append("|------|-----------|----------|--------|----------|")
    
    sorted_files = sorted(results['per_file'].items(), key=lambda x: x[1]['text_similarity'])
    for filepath, metrics in sorted_files[:30]:
        report.append(
            f"| `{filepath}` | {metrics['text_similarity']:.1%} | "
            f"{metrics['section_coverage']:.1%} | {metrics['param_coverage']:.1%} | "
            f"{metrics['include_coverage']:.1%} |"
        )
    report.append("")
    
    # Missing sections aggregate
    all_missing_sections = defaultdict(int)
    for filepath, metrics in results['per_file'].items():
        for s in metrics.get('missing_sections', []):
            all_missing_sections[s] += 1
    
    if all_missing_sections:
        report.append("## Most Commonly Missing Sections")
        report.append("")
        for section, count in sorted(all_missing_sections.items(), key=lambda x: -x[1])[:20]:
            report.append(f"- `{section}` (missing in {count} files)")
        report.append("")
    
    # Recommendations
    report.append("## Recommendations for Skill Refinement")
    report.append("")
    
    if agg['avg_text_similarity'] < 0.5:
        report.append("- **LOW TEXT SIMILARITY**: The generated content diverges significantly from actual. Consider using more of the baseline content verbatim and only modifying sections affected by the diff.")
    if agg['avg_section_coverage'] < 0.7:
        report.append("- **MISSING SECTIONS**: Many sections from actual docs are not present in generated output. The skill should preserve all existing sections unless explicitly deprecated by the diff.")
    if agg['avg_param_coverage'] < 0.8:
        report.append("- **PARAMETER GAPS**: Configuration parameters are missing. The skill should cross-reference the full install-config struct, not just the diff delta.")
    if agg['file_coverage'] < 0.8:
        report.append("- **FILE COVERAGE**: Many actual doc files are missing from generated output. The skill should copy all baseline files and only modify those affected by changes.")
    if agg['avg_include_coverage'] < 0.8:
        report.append("- **INCLUDE DIRECTIVES**: Module includes are inconsistent with actual docs. Preserve the include hierarchy from the baseline.")
    
    if agg['avg_text_similarity'] >= 0.8 and agg['file_coverage'] >= 0.9:
        report.append("- **GOOD BASELINE**: Generation quality is high. Focus refinements on the specific files with lowest similarity scores above.")
    
    report.append("")
    
    return "\n".join(report)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 evaluate-generated-docs.py <generated-dir> <actual-dir> [--output=<report-path>]")
        sys.exit(1)
    
    generated_dir = sys.argv[1]
    actual_dir = sys.argv[2]
    
    output_path = None
    for arg in sys.argv[3:]:
        if arg.startswith("--output="):
            output_path = arg.split("=", 1)[1]
    
    if not os.path.isdir(generated_dir):
        print(f"ERROR: Generated directory not found: {generated_dir}")
        sys.exit(1)
    if not os.path.isdir(actual_dir):
        print(f"ERROR: Actual directory not found: {actual_dir}")
        sys.exit(1)
    
    print(f"Evaluating generated docs...")
    print(f"  Generated: {generated_dir}")
    print(f"  Actual: {actual_dir}")
    print()
    
    results = evaluate_directory(generated_dir, actual_dir)
    report = format_report(results, generated_dir, actual_dir)
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"Report written to: {output_path}")
    else:
        print(report)
    
    # Print quick summary
    agg = results['aggregate']
    print(f"\n--- Quick Summary ---")
    print(f"  File Coverage: {agg['file_coverage']:.1%}")
    print(f"  Avg Similarity: {agg['avg_text_similarity']:.1%}")
    print(f"  Avg Section Coverage: {agg['avg_section_coverage']:.1%}")
    print(f"  Avg Param Coverage: {agg['avg_param_coverage']:.1%}")


if __name__ == "__main__":
    main()
