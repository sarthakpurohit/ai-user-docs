# OKD Documentation — Evaluation Suite

This directory contains a comprehensive evaluation framework for the
doc generation skills. It evaluates whether AI-generated OpenShift
documentation is accurate, complete, and well-structured.

Supports multiple sections: `installing`, `updating`, and any future additions.

## Quick Start

### Run deterministic evaluation

```bash
# Evaluate installing section (default)
python3 eval/scripts/run-eval.py case-4.17 --section=installing

# Evaluate updating section
python3 eval/scripts/run-eval.py case-4.17 --section=updating

# Evaluate all cases for a section
python3 eval/scripts/run-eval.py all --section=installing

# Or use the Makefile
make score VERSION=4.17
make score VERSION=4.17 SECTION=updating
```

### Using the comparison viewer

```bash
make compare VERSION=4.17
make compare VERSION=4.17 SECTION=updating
```

## Directory Structure

```
eval/
├── eval.yaml                  # Main evaluation config
├── README.md                  # This file
├── dataset/
│   └── cases/
│       ├── installing/        # Installing section cases
│       │   ├── case-4.17/
│       │   │   ├── input.yaml
│       │   │   ├── reference/
│       │   │   └── output/
│       │   ├── case-4.18/
│       │   └── ...
│       └── updating/          # Updating section cases
│           ├── case-4.17/
│           └── ...
├── prompts/
│   ├── semantic-accuracy-judge.md
│   ├── completeness-judge.md
│   ├── structure-quality-judge.md
│   └── parameter-grounded-judge.md
└── scripts/
    └── run-eval.py            # Standalone evaluation script
```

## What Gets Evaluated

### Deterministic Metrics

| Metric | What It Checks | Pass Threshold |
|--------|---------------|----------------|
| `file_coverage` | % of reference files present in output | ≥90% |
| `text_similarity` | Line-by-line content similarity (difflib) | ≥85% |
| `section_coverage` | % of AsciiDoc section headers present | ≥90% |
| `parameter_coverage` | % of parameter names from reference found in output | ≥90% |

### LLM Judges (Semantic — run separately)

| Judge | What It Evaluates |
|-------|------------------|
| `semantic_accuracy` | Are facts, types, defaults, constraints correct? |
| `completeness` | Are all code diff changes reflected in docs? |
| `structure_quality` | Does output follow OpenShift doc conventions? |
| `parameter_accuracy` | Do parameter descriptions match source code? |

## How to Run Evaluation for a Section

### Step 1: Generate the docs

Open a fresh agent window. Use the prompt from `tmp-<section>/generation-prompt-4.XX.md`.

### Step 2: Run deterministic evaluation

```bash
# Using Makefile
make evaluate VERSION=4.17 SECTION=updating

# Or directly
python3 scripts/evaluate-generated-docs.py \
  generated/updating/4.17 \
  docs-corpus/ocp/4.17/updating \
  --output=evaluation/updating/4.17-fair-eval.md
```

### Step 3: Run LLM evaluation (optional)

Open another fresh agent window. Use the prompt from `tmp-<section>/evaluation-prompt-4.XX.md`.

### Step 4: Review and refine

Based on evaluation results, update the skill:
- `skills/generate-installing-docs/SKILL.md`
- `skills/generate-updating-docs/SKILL.md`

## Fair Evaluation Rules

1. **No copying from ground truth.** The skill must generate from prev-version + diff ONLY.
2. **Missing files score 0%.** If a file exists in reference but not in output, it gets 0% on all metrics.
3. **Source repos are available.** The skill MAY read specific source files for context.
4. **The ~5% accuracy ceiling** is primarily caused by editorial decisions not visible in code diffs.
