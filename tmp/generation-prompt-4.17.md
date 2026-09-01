Generate updated OpenShift 4.17 installation documentation by following the skill file instructions.

## Skill File

Read and follow: skills/generate-install-docs/SKILL.md

## Inputs

- Previous version docs (4.16 baseline): docs-corpus/ocp/4.16/installing/
- Enhanced code diff: diffs/installing/4.16-to-4.17/enhanced-combined-diff-4.16-to-4.17.md
- Target distro: ocp
- Output directory: eval/dataset/cases/installing/case-4.17/output/
- Source repos for runtime lookup:
  - installer/ (non-bare, use: git -C installer show origin/release-4.17:<path>)
  - api.git/ (bare, use: git --git-dir api.git show release-4.17:<path>)
  - baremetal-operator.git/ (bare, use: git --git-dir baremetal-operator.git show release-4.17:<path>)
  - machine-config-operator/ (non-bare, use: git -C machine-config-operator show origin/release-4.17:<path>)
  - machine-api-operator/ (non-bare, use: git -C machine-api-operator show origin/release-4.17:<path>)

## What to Do

1. Read the skill file completely first
2. Read the enhanced code diff completely — it contains full Go type files with all field definitions, full validation.go and permissions.go files, and CRD schema changes
3. Copy docs-corpus/ocp/4.16/installing/ as your baseline into the output directory
4. Identify ALL changes from the diff that require documentation updates, including:
   - New struct fields (new json:"..." tags)
   - Changed Go comments on EXISTING fields (description rewrites, scope widening)
   - Deprecated fields (Go comments saying "deprecated")
   - Removed network plugins or platforms
   - New validation rules and permission requirements
   - New CLI commands and automatic behaviors
   - Feature gates moving to GA (default-on)
   - Version-specific strings that need bumping
5. For EVERY new/changed parameter, add a proper table row with: field name, description (from Go comment), type, and constraints
6. For new CLI commands (image-based), create complete documentation (not stubs)
7. For deprecated fields, mark them deprecated and document replacements
8. For GA feature gates, remove ALL Tech Preview snippets and add required config (e.g., credentialsMode)
9. For removed CNI/platforms, sweep ALL modules that reference them
10. Do a version-string sweep: RHCOS URLs, kubelet versions, capability sets
11. Look up source repos when you need additional context (validation logic, defaults, permissions)
12. Write all output to: eval/dataset/cases/case-4.17/output/

## Rules

- Do NOT read docs-corpus/ocp/4.17/ — that is ground truth, reading it is cheating
- Do NOT leave TODO stubs — either write complete content or flag for human review
- Every new parameter needs its own table row with: field name, description (from Go comment), type, and constraints
- When a field is deprecated in Go (comment says "deprecated"), mark it deprecated in docs and document the replacement
- When a field's Go comment CHANGES (not just new fields), update the doc description to match
- Use {product-title}, {op-system}, {product-version} attributes — never hardcode product names
- Check pkg/asset/installconfig/<platform>/validation.go and permissions.go — not just pkg/types/
