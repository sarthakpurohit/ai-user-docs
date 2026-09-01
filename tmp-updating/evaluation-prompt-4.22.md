# Evaluation Prompt: Full 3-Way LLM Evaluation for Updating Docs 4.22

You are evaluating AI-generated "Updating clusters" documentation for OpenShift 4.22. Perform a comprehensive 3-way comparison.

**CRITICAL: Do NOT use subagents or parallel tasks.** Evaluate everything yourself in a single pass. Subagents produce contradictory assessments because they lack shared context.

## Three-Way Inputs

1. **Baseline (4.21):** `docs-corpus/ocp/4.21/updating/`
2. **Generated (4.22):** `generated/updating/4.22/`
3. **Ground Truth (4.22):** `docs-corpus/ocp/4.22/updating/`

## Also Read

- **Code diff:** `diffs/updating/4.21-to-4.22/combined-diff-4.21-to-4.22.md`
- **Source repos (for grounded verification):**
  - CVO: `cluster-version-operator.git` (bare, branch: release-4.22)
  - oc: `oc.git` (bare, branch: release-4.22)
  - MCO: `machine-config-operator` (non-bare, branch: origin/release-4.22)
  - API: `api.git` (bare, branch: release-4.22)
  - CNO: `cluster-network-operator.git` (bare, branch: release-4.22)

## Evaluation Dimensions

### 1. Semantic Accuracy (per file)
For EVERY .adoc file in both generated and ground truth:
- Classify as: UNCHANGED_CORRECT, CORRECT, MINOR_ISSUES, or MAJOR_ISSUES

### 2. Completeness (against code diff)
Identify user-facing changes **relevant to the updating section specifically**.

### 3. Structure Compliance
Check AsciiDoc conventions. Separate inherited vs agent-introduced issues.

### 4. Parameter/Command Accuracy (Grounded)
Verify CLI commands/flags against source code.

## Output Format

Write your full evaluation to `eval/dataset/cases/updating/case-4.22/llm-eval-results.md`

Structure:
```
# LLM Evaluation: Updating Docs 4.22

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
