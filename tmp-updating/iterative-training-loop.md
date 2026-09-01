# Iterative Training Loop: Updating Section

This document describes the iterative process for refining the `generate-updating-docs` skill.

## The Formula

```
Docs(4.x) = Docs(4.x-1) + CodeDiff(4.x-1 → 4.x)
```

Applied by the SKILL.md to produce generated docs, then evaluated against ground truth.

## Process for Each Iteration

### Step 1: Generate

Use the generation prompt (`generation-prompt-4.{X}.md`) in a fresh agent window.

The agent will:
1. Read `skills/generate-updating-docs/SKILL.md`
2. Read `docs-corpus/ocp/4.{X-1}/updating/` (baseline)
3. Read `diffs/updating/4.{X-1}-to-4.{X}/combined-diff-*.md` (code changes)
4. Output to `generated/updating/4.{X}/`

### Step 2: Evaluate

Use the evaluation prompt (`evaluation-prompt-4.{X}.md`) in another fresh agent window.

The agent will:
1. Read all three versions (baseline, generated, ground truth)
2. Read the code diff
3. Verify against source repos
4. Produce a scored evaluation report

### Step 3: Refine SKILL.md

Based on the evaluation results:
1. Identify failure patterns (what the agent consistently gets wrong)
2. Add specific rules to SKILL.md to address those patterns
3. Update the Appendix with iteration findings

### Step 4: Save Snapshot

After updating SKILL.md:
```bash
cp skills/generate-updating-docs/SKILL.md skills/snapshots/updating/after-4.{X}/SKILL.md
```

### Step 5: Repeat

Move to the next version pair and repeat. Each iteration refines the skill further.

---

## Version Schedule

| Iteration | Base | Target | Diff File | Status |
|---|---|---|---|---|
| 1 | 4.16 | 4.17 | `diffs/updating/4.16-to-4.17/combined-diff-4.16-to-4.17.md` | Ready |
| 2 | 4.17 | 4.18 | `diffs/updating/4.17-to-4.18/combined-diff-4.17-to-4.18.md` | Ready |
| 3 | 4.18 | 4.19 | `diffs/updating/4.18-to-4.19/combined-diff-4.18-to-4.19.md` | Ready |
| 4 | 4.19 | 4.20 | `diffs/updating/4.19-to-4.20/combined-diff-4.19-to-4.20.md` | Ready |
| 5 | 4.20 | 4.21 | `diffs/updating/4.20-to-4.21/combined-diff-4.20-to-4.21.md` | Ready |
| 6 | 4.21 | 4.22 | `diffs/updating/4.21-to-4.22/combined-diff-4.21-to-4.22.md` | Ready |

---

## Key Differences from Installing Section

| Aspect | Installing | Updating |
|---|---|---|
| Assembly count | ~189 | ~17 |
| Module count | ~800+ | ~90 |
| Primary repos | installer, api, BMO, assisted-installer, CNO | CVO, oc CLI, MCO |
| Change type | New fields, platforms, parameters | Behavior changes, CLI output, preconditions |
| Version sensitivity | install-config fields | CLI output, channel names, version strings |
| Platform-specific | Heavy (per-cloud) | Light (mostly platform-agnostic) |
| Expected accuracy | ~91% | Potentially higher (simpler, fewer editorial moves) |

---

## Quick Commands

```bash
# Generate diffs for all versions
python3 scripts/generate-updating-diffs.py

# Run deterministic evaluation (after generation)
python3 eval/scripts/run-eval.py --section updating --version 4.17

# Compare in browser
make compare VERSION=4.17 SECTION=updating
```
