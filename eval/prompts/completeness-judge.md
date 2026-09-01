# Completeness Judge

You are evaluating AI-generated OpenShift installation documentation for **completeness of change coverage**.

## Your Task

Given a code diff summary and the generated documentation, evaluate whether ALL significant code changes are properly reflected in the documentation.

## What to Evaluate

1. **New parameters documented** — Every new struct field with a `json:"..."` tag in the diff should have a corresponding entry in a parameter reference module.
2. **New platforms/features** — If the diff shows a new platform directory or major new feature, there should be new documentation modules for it.
3. **Removed/deprecated features** — If fields or platforms were removed, docs should reflect deprecation or removal.
4. **Validation constraint changes** — If limits changed (MaxItems, Enum values, new required fields), docs should be updated.
5. **New CLI commands** — If new subcommands were added to `openshift-install`, they should be documented.
6. **Capability set updates** — If new cluster capabilities were added, the capability documentation should be updated.

## What NOT to penalize

- Changes to test files, CI, or internal implementation details
- Changes that don't affect user-facing behavior
- Minor refactoring of existing content

## Scoring Rubric

| Score | Meaning |
|-------|---------|
| 5 | Every code change is reflected in docs. No gaps. Complete coverage. |
| 4 | 1-2 minor changes not documented (cosmetic field renames, minor constraint tweaks). |
| 3 | Some meaningful changes missed (new optional parameters, updated constraints). |
| 2 | Major features or platforms undocumented despite being in the diff. |
| 1 | Most code changes are not reflected. Documentation appears unchanged from previous version. |

## Input

Code diff summary: {{ inputs.diff_content }}
Generated docs (sample of changed files): {{ outputs.changed_files_sample }}

## Output

Provide your score and list specific changes from the diff that are/aren't covered.
