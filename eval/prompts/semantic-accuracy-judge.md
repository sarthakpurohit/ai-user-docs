# Semantic Accuracy Judge

You are evaluating AI-generated OpenShift installation documentation for **semantic accuracy**.

## Your Task

Compare the GENERATED documentation against the REFERENCE (human-written) documentation.
Focus on whether the **meaning and facts** are correct, not just whether the exact words match.

## What to Evaluate

For a sample of files (up to 10), compare:

1. **Parameter values and types** — Are field types (string, integer, object, array) correct?
2. **Default values** — Are defaults documented correctly?
3. **Constraints** — Are limits (max items, allowed values, required vs optional) accurate?
4. **Feature descriptions** — Do explanations match what the feature actually does?
5. **Version-specific content** — Are version numbers, capability sets, feature gates correct for this version?
6. **Platform correctness** — Is platform-specific content (AWS, GCP, Azure, etc.) attributed to the right platform?

## What NOT to penalize

- Minor wording differences that preserve meaning ("You can" vs "It is possible to")
- Different ordering of bullet points or table rows
- Slightly different formatting (bold vs not bold)
- Missing content that requires information NOT available in the code diff

## Scoring Rubric

| Score | Meaning |
|-------|---------|
| 5 | All facts correct. No inaccuracies found. Semantically equivalent to reference. |
| 4 | 1-2 minor inaccuracies (wrong optional/required status, slightly imprecise wording). |
| 3 | Some factual issues (wrong defaults, missing constraints, incorrect type). |
| 2 | Multiple significant inaccuracies that would mislead users. |
| 1 | Pervasive errors. Documentation would cause installation failures if followed. |

## Input

Generated docs: {{ outputs.generated_sample }}
Reference docs: {{ outputs.reference_sample }}

## Output

Provide your score and a detailed rationale explaining what was correct and what was inaccurate.
