# Evaluation Prompt: Full 3-Way LLM Evaluation for Updating Docs 4.21

You are evaluating AI-generated "Updating clusters" documentation for OpenShift 4.21. Perform a comprehensive 3-way comparison.

**CRITICAL: Do NOT use subagents or parallel tasks.** Evaluate everything yourself in a single pass. Subagents produce contradictory assessments because they lack shared context.

## Three-Way Inputs

1. **Baseline (4.20):** `docs-corpus/ocp/4.20/updating/`
2. **Generated (4.21):** `generated/updating/4.21/`
3. **Ground Truth (4.21):** `docs-corpus/ocp/4.21/updating/`

## Also Read

- **Code diff:** `diffs/updating/4.20-to-4.21/combined-diff-4.20-to-4.21.md`
- **Source repos (for grounded verification):**
  - CVO: `cluster-version-operator.git` (bare, branch: release-4.21)
  - oc: `oc.git` (bare, branch: release-4.21)
  - MCO: `machine-config-operator` (non-bare, branch: origin/release-4.21)
  - API: `api.git` (bare, branch: release-4.21)
  - CNO: `cluster-network-operator.git` (bare, branch: release-4.21)

## Evaluation Dimensions

### 1. Semantic Accuracy (per file)

For EVERY .adoc file that exists in both generated and ground truth:
- Compare the content semantically (not string-matching)
- Classify as: UNCHANGED_CORRECT, CORRECT, MINOR_ISSUES, or MAJOR_ISSUES

### 2. Completeness (against code diff)

Identify user-facing changes **relevant to the updating section specifically**. Do NOT count changes belonging to other sections.

### 3. Structure Compliance

Check AsciiDoc conventions. Separate inherited vs agent-introduced issues.

### 4. Parameter/Command Accuracy (Grounded)

Verify CLI commands/flags against source code. Check feature gate requirements.

## Output Format

Write your full evaluation to `eval/dataset/cases/updating/case-4.21/llm-eval-results.md`

Structure:
```
# LLM Evaluation: Updating Docs 4.21

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
