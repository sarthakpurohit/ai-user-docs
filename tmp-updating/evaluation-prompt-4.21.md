# Evaluation Prompt: Full 3-Way LLM Evaluation for Updating Docs 4.21

You are evaluating AI-generated "Updating clusters" documentation for OpenShift 4.21. Perform a comprehensive 3-way comparison.

**CRITICAL: Do NOT use subagents or parallel tasks.** Evaluate everything yourself in a single pass. Subagents produce contradictory assessments because they lack shared context.

## Three-Way Inputs

1. **Baseline (4.20):** `/home/sapurohi/Desktop/Agentic OKD docs/docs-corpus/ocp/4.20/updating/`
2. **Generated (4.21):** `/home/sapurohi/Desktop/Agentic OKD docs/generated/updating/4.21/`
3. **Ground Truth (4.21):** `/home/sapurohi/Desktop/Agentic OKD docs/docs-corpus/ocp/4.21/updating/`

## Also Read

- **Code diff:** `/home/sapurohi/Desktop/Agentic OKD docs/diffs/updating/4.20-to-4.21/combined-diff-4.20-to-4.21.md`
- **Source repos (for grounded verification):**
  - CVO: `/home/sapurohi/Desktop/Agentic OKD docs/cluster-version-operator.git` (bare, branch: release-4.21)
  - oc: `/home/sapurohi/Desktop/Agentic OKD docs/oc.git` (bare, branch: release-4.21)
  - MCO: `/home/sapurohi/Desktop/Agentic OKD docs/machine-config-operator` (non-bare, branch: origin/release-4.21)
  - API: `/home/sapurohi/Desktop/Agentic OKD docs/api.git` (bare, branch: release-4.21)
  - CNO: `/home/sapurohi/Desktop/Agentic OKD docs/cluster-network-operator.git` (bare, branch: release-4.21)

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

Write your full evaluation to `/home/sapurohi/Desktop/Agentic OKD docs/eval/dataset/cases/updating/case-4.21/llm-eval-results.md`

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
