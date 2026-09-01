# Evaluation Prompt: Full 3-Way LLM Evaluation for Updating Docs 4.20

You are evaluating AI-generated "Updating clusters" documentation for OpenShift 4.20. Perform a comprehensive 3-way comparison.

**CRITICAL: Do NOT use subagents or parallel tasks.** Evaluate everything yourself in a single pass. Subagents produce contradictory assessments because they lack shared context.

## Three-Way Inputs

1. **Baseline (4.19):** `docs-corpus/ocp/4.19/updating/`
2. **Generated (4.20):** `generated/updating/4.20/`
3. **Ground Truth (4.20):** `docs-corpus/ocp/4.20/updating/`

## Also Read

- **Code diff:** `diffs/updating/4.19-to-4.20/combined-diff-4.19-to-4.20.md`
- **Source repos (for grounded verification):**
  - CVO: `cluster-version-operator.git` (bare, branch: release-4.20)
  - oc: `oc.git` (bare, branch: release-4.20)
  - MCO: `machine-config-operator` (non-bare, branch: origin/release-4.20)
  - API: `api.git` (bare, branch: release-4.20)
  - CNO: `cluster-network-operator.git` (bare, branch: release-4.20)

## Evaluation Dimensions

### 1. Semantic Accuracy (per file)

For EVERY .adoc file that exists in both generated and ground truth:
- Compare the content semantically (not string-matching)
- Classify as: UNCHANGED_CORRECT (same as 4.19 and GT), CORRECT, MINOR_ISSUES, or MAJOR_ISSUES
- If generated = baseline = ground truth, classify as UNCHANGED_CORRECT (no penalty)
- MINOR: slightly imprecise wording, cosmetic formatting issues
- MAJOR: wrong version numbers, incorrect CLI syntax, fabricated behavior, missing critical info

### 2. Completeness (against code diff)

Read the code diff and identify user-facing changes **relevant to the updating section specifically**. Do NOT count changes that belong to other sections (networking, security, compute, storage). For each:
- Classify as COVERED or MISSED

### 3. Structure Compliance

Check for AsciiDoc convention compliance. Separate inherited vs agent-introduced issues.

### 4. Parameter/Command Accuracy (Grounded)

Verify CLI commands/flags against source code. Check feature gate requirements (Rule 23).

## Output Format

Write your full evaluation to `eval/dataset/cases/updating/case-4.20/llm-eval-results.md`

Structure:
```
# LLM Evaluation: Updating Docs 4.20

## Overall Score: X%

## Metric Summary
| Metric | Score | Details |
...

## Semantic Accuracy Detail
## Completeness Detail
## Structure Detail
## Command Accuracy Detail
## Key Findings
```
