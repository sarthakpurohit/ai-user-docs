I need you to do a FULL LLM-based evaluation of AI-generated OpenShift 4.17 installation docs.
Evaluate EVERY file, not a sample. DO NOT generate or modify any docs — only evaluate.

## What You're Evaluating

An AI skill generated 4.17 docs by taking 4.16 docs + code diff. You need to judge quality
using a 3-way comparison:

- Baseline 4.16 (what the skill started from): docs-corpus/ocp/4.16/installing/
- Generated 4.17 (what the skill produced): eval/dataset/cases/installing/case-4.17/output/
- Ground truth 4.17 (what humans wrote): eval/dataset/cases/installing/case-4.17/reference/installing/
- Code diff that was applied: diffs/installing/4.16-to-4.17/enhanced-combined-diff-4.16-to-4.17.md

NOTE: reference/ has an installing/ subfolder, output/ does not.
Compare: reference/installing/<path> vs output/<path>
Baseline: docs-corpus/ocp/4.16/installing/<path>

## Evaluation Tasks

### Task 1: Full Semantic Accuracy (ALL common files)

For EVERY .adoc file that exists in BOTH output/ and reference/installing/:
1. Read the generated version and the ground-truth version
2. For files that DIFFER, also read the 4.16 baseline to understand what changed
3. Classify each file into one of:
   - CORRECT: Generated content is semantically equivalent to ground truth (minor wording OK)
   - MINOR_ISSUES: Small inaccuracies (wrong optional/required, slightly imprecise, minor omissions)
   - MAJOR_ISSUES: Significant errors (wrong types, wrong defaults, missing critical content, fabricated info)
   - UNCHANGED_CORRECT: File is identical/near-identical in all three versions (baseline=generated=reference)

Key rule: If something is "wrong" in generated but was ALSO "wrong" in baseline 4.16,
that is NOT the agent's fault — mark UNCHANGED_CORRECT.

Write to: eval/dataset/cases/case-4.17/semantic-accuracy-full.md

### Task 2: Full Completeness Check (diff coverage)

Read: diffs/installing/4.16-to-4.17/enhanced-combined-diff-4.16-to-4.17.md

For EVERY significant change in the diff:
1. Identify what documentation change it should produce
2. Check if that change exists in the generated output
3. Mark as COVERED or MISSED

Compare what changed baseline→ground truth vs what changed baseline→generated.
The generated should capture the SAME delta.

Write to: eval/dataset/cases/case-4.17/completeness-full.md

### Task 3: Full Structure Validation (ALL generated files)

Check EVERY file in output/ for AsciiDoc convention compliance:
- Correct :_mod-docs-content-type: header (ASSEMBLY/PROCEDURE/CONCEPT/REFERENCE)
- Correct [id="..._{context}"] format
- Procedures have .Prerequisites, .Procedure, .Verification sections
- Uses {product-title} not hardcoded "OpenShift Container Platform"
- Uses {op-system} not "RHCOS"
- Code blocks properly formatted
- include:: directives point to existing files in the output tree

Mark inherited-from-4.16 issues separately from agent-introduced issues.

Write to: eval/dataset/cases/case-4.17/structure-full.md

### Task 4: Full Parameter Verification (against source code)

Find ALL parameter reference files in output/ (files containing parameter tables).
For EVERY documented parameter that is NEW or CHANGED vs 4.16, verify against Go source:

```bash
git -C installer show origin/release-4.17:pkg/types/<platform>/platform.go
git -C installer show origin/release-4.17:pkg/types/<platform>/machinepool.go
git -C installer show origin/release-4.17:pkg/types/imagebased/imagebased_config_types.go
```

Check:
- Parameter name matches json:"..." tag
- Description matches Go comment above the field
- Type is correct
- Optional/Required matches // +optional annotation
- Deprecated fields are marked deprecated with correct replacement noted

Write to: eval/dataset/cases/case-4.17/parameter-verification-full.md

### Task 5: Final Summary

Write combined results to: eval/dataset/cases/case-4.17/llm-eval-results.md

Format:
```markdown
# Full LLM Evaluation: case-4.17

| Metric | Score | Details |
|--------|-------|---------|
| Semantic Accuracy | X% (Y/Z files correct) | ... |
| Completeness | X% (Y/Z changes covered) | ... |
| Structure Compliance | X% strict / X% agent-attributable | ... |
| Parameter Accuracy | X% (Y/Z params correct) | ... |
| **Overall** | **X%** | ... |

## Top Issues to Fix in SKILL.md
1. ...
2. ...
3. ...
```

## IMPORTANT RULES

- Evaluate ALL files, not a sample
- Be strict — do not inflate scores
- 3-way comparison matters:
  - If wrong in generated BUT also wrong in 4.16 baseline → NOT agent's fault (UNCHANGED_CORRECT)
  - If correct in baseline AND ground truth but agent CHANGED it → agent fault
  - If changed between baseline→ground truth but agent DIDN'T update → miss
- Use source repos to verify parameters (git commands above)
- Structure issues inherited from 4.16 baseline should be noted but scored separately
