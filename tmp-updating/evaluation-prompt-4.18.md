# Evaluation Prompt: Full 3-Way LLM Evaluation for Updating Docs 4.18

You are evaluating AI-generated "Updating clusters" documentation for OpenShift 4.18. Perform a comprehensive 3-way comparison.

**CRITICAL: Do NOT use subagents or parallel tasks.** Evaluate everything yourself in a single pass. Subagents produce contradictory assessments because they lack shared context.

## Three-Way Inputs

1. **Baseline (4.17):** `/home/sapurohi/Desktop/Agentic OKD docs/docs-corpus/ocp/4.17/updating/`
2. **Generated (4.18):** `/home/sapurohi/Desktop/Agentic OKD docs/generated/updating/4.18/`
3. **Ground Truth (4.18):** `/home/sapurohi/Desktop/Agentic OKD docs/docs-corpus/ocp/4.18/updating/`

## Also Read

- **Code diff:** `/home/sapurohi/Desktop/Agentic OKD docs/diffs/updating/4.17-to-4.18/combined-diff-4.17-to-4.18.md`
- **Source repos (for grounded verification):**
  - CVO: `/home/sapurohi/Desktop/Agentic OKD docs/cluster-version-operator.git` (bare, branch: release-4.18)
  - oc: `/home/sapurohi/Desktop/Agentic OKD docs/oc.git` (bare, branch: release-4.18)
  - MCO: `/home/sapurohi/Desktop/Agentic OKD docs/machine-config-operator` (non-bare, branch: origin/release-4.18)
  - API: `/home/sapurohi/Desktop/Agentic OKD docs/api.git` (bare, branch: release-4.18)
  - CNO: `/home/sapurohi/Desktop/Agentic OKD docs/cluster-network-operator.git` (bare, branch: release-4.18)

## Evaluation Dimensions

### 1. Semantic Accuracy (per file)

For EVERY .adoc file that exists in both generated and ground truth:
- Compare the content semantically (not string-matching)
- Classify as: UNCHANGED_CORRECT (same as 4.17 and GT), CORRECT, MINOR_ISSUES, or MAJOR_ISSUES
- If generated = baseline = ground truth, classify as UNCHANGED_CORRECT (no penalty)
- MINOR: slightly imprecise wording, cosmetic formatting issues
- MAJOR: wrong version numbers, incorrect CLI syntax, fabricated behavior, missing critical info

Report: total files, unchanged_correct count, correct count, minor count, major count, and percentage.

### 2. Completeness (against code diff)

Read the code diff and identify ALL user-facing changes. For each:
- Determine if it's documented in the generated output
- Classify as COVERED or MISSED
- User-facing changes include: new CLI subcommands/flags, changed CLI output, new preconditions/upgrade gates, changed channel behavior, MCO behavior changes affecting user experience, version string updates, SDN/CNI migration requirements

Report: total changes identified, covered count, missed count, and details of misses.

### 3. Structure Compliance

Check generated docs for AsciiDoc convention compliance:
- Module headers (`:_mod-docs-content-type:`)
- ID format (`[id="name_{context}"]`)
- Proper include syntax
- Attribute usage (`{product-title}`, `{oc-first}`)
- Procedure format (`.Prerequisites`, `.Procedure`, `.Verification`)
- No orphan files (every file should be included by an assembly or be an assembly itself)

Separate inherited-from-baseline issues from agent-introduced issues.

### 4. Parameter/Command Accuracy (Grounded)

For any new or changed CLI commands/flags/output in the generated docs:
- Verify against the actual source code (oc.git, CVO)
- Check: command name correct, flag names correct, output format matches test fixtures, behavior description matches code comments

Report: total verifiable items, correct count, incorrect count, with details.

## Output Format

Write your full evaluation to `/home/sapurohi/Desktop/Agentic OKD docs/eval/dataset/cases/updating/case-4.18/llm-eval-results.md`

Structure:
```
# LLM Evaluation: Updating Docs 4.18

## Overall Score: X%

## Metric Summary
| Metric | Score | Details |
...

## Semantic Accuracy Detail
(per-file breakdown for non-UNCHANGED_CORRECT files)

## Completeness Detail
(each code-diff change and whether COVERED or MISSED)

## Structure Detail
(issues found, separated by inherited vs agent-introduced)

## Command Accuracy Detail
(each verified command/flag with CORRECT or INCORRECT)

## Key Findings
- What the agent did well
- What needs improvement
- Lessons for SKILL.md refinement
```
