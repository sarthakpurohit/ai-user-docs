# How to Run the Full Evaluation

This document provides step-by-step instructions for running the
doc generation skill evaluation.

## Supported Sections

| Section | Skill | Diff Script | Source Repos |
|---------|-------|-------------|--------------|
| `installing` | `skills/generate-install-docs/SKILL.md` | `scripts/generate-enhanced-diffs.py` | installer, api.git, baremetal-operator.git, MCO, MAO |
| `updating` | `skills/generate-updating-docs/SKILL.md` | `scripts/generate-updating-diffs.py` | cluster-version-operator.git, oc.git, MCO |

## Prerequisites

Ensure these exist in the workspace root:
- `docs-corpus/ocp/4.16/` through `4.22/` with section subdirs
- `diffs/<section>/4.16-to-4.17/` (and all pairs) — generated diffs
- Source repos cloned (see table above)

## Running Evaluation for Installing

### Step 1: Generate Docs

Open a fresh agent window. Use the prompt from `tmp/generation-prompt-4.17.md`.

**Key paths:**
- Skill: `skills/generate-install-docs/SKILL.md`
- Baseline: `docs-corpus/ocp/4.16/installing/`
- Diff: `diffs/installing/4.16-to-4.17/enhanced-combined-diff-4.16-to-4.17.md`
- Output: `eval/dataset/cases/installing/case-4.17/output/`

### Step 2: Run Deterministic Evaluation

```bash
python3 eval/scripts/run-eval.py case-4.17 --section=installing
# Or:
make score VERSION=4.17 SECTION=installing
```

### Step 3: Run LLM Evaluation (Optional)

Open another fresh agent window. Use the prompt from `tmp/evaluation-prompt-4.17.md`.

## Running Evaluation for Updating

### Step 1: Generate Docs

Open a fresh agent window. Use the prompt from `tmp-updating/generation-prompt-4.17.md`.

**Key paths:**
- Skill: `skills/generate-updating-docs/SKILL.md`
- Baseline: `docs-corpus/ocp/4.16/updating/`
- Diff: `diffs/updating/4.16-to-4.17/combined-diff-4.16-to-4.17.md`
- Output: `generated/updating/4.17/`

### Step 2: Run Deterministic Evaluation

```bash
make score VERSION=4.17 SECTION=updating
```

### Step 3: Run LLM Evaluation (Optional)

Open another fresh agent window. Use the prompt from `tmp-updating/evaluation-prompt-4.17.md`.

## Running All Cases

```bash
# All installing cases
python3 eval/scripts/run-eval.py all --section=installing

# All updating cases
python3 eval/scripts/run-eval.py all --section=updating
```

## Iterative Training Loop

```bash
# Prepare baseline + evaluate for a section
make train SECTION=updating VERSION=4.17

# Or for all versions
make train SECTION=updating
```

After evaluation, update the relevant skill file and save a snapshot:
```bash
cp skills/generate-updating-docs/SKILL.md skills/snapshots/updating/after-4.17/SKILL.md
```
