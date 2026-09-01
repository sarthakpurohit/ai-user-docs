# Generation Prompt: Updating Docs 4.18

You are generating updated "Updating clusters" documentation for OpenShift 4.18 based on the 4.17 docs and code diffs.

## Your Task

Follow the skill file at `skills/generate-updating-docs/SKILL.md` exactly.

## Inputs

- **Previous version docs (4.17 baseline):** `docs-corpus/ocp/4.17/updating/`
- **Code diff summary:** `diffs/updating/4.17-to-4.18/combined-diff-4.17-to-4.18.md`
- **Target distro:** `ocp`
- **Output directory:** `generated/updating/4.18/`
- **Source repos (for runtime lookup):**
  - `cluster-version-operator.git/` (bare) at `cluster-version-operator.git`
  - `oc.git/` (bare) at `oc.git`
  - `machine-config-operator/` (non-bare) at `machine-config-operator`
  - `api.git/` (bare) at `api.git`
  - `cluster-network-operator.git/` (bare) at `cluster-network-operator.git`

## Instructions

1. Read the SKILL.md file completely first.
2. Read the full code diff summary.
3. Read the 4.17 baseline docs (all assemblies and their included modules).
4. Following Phase 1 of the skill, analyze and map changes to documentation impact.
5. Following Phase 2, generate the complete updated docs for 4.18.

## Output Requirements

- Write ALL output files to `generated/updating/4.18/`
- Maintain the exact directory structure from the 4.17 baseline
- Files from the 4.17 baseline should appear in the output UNLESS they clearly belong to a different documentation section (Rule 21)
- New modules/assemblies may be added if the diff warrants them
- At the end, provide a summary of what changed and why

## Key Reminders

- **CRITICAL: Do NOT use subagents or parallel tasks.** Process everything sequentially in a single context. You need full awareness of ALL rules and ALL changes to make consistent decisions across files. Spawning subagents causes contradictory edits and rule violations.
- You are NOT writing from scratch. Copy the 4.17 baseline and modify only what the diff demands.
- Version strings: `stable-4.17` → `stable-4.18`, version numbers in examples updated
- Kubelet: check `api.git` go.mod for Kubernetes version → derive kubelet version
- Check for new `oc adm upgrade` subcommands or changed output formats
- Check for new CVO preconditions or upgrade gates
- Check for MCO drain/reboot behavior changes
- Check CNO diff for any SDN/OVN migration changes that block updates
- Admin-ack: only add if there's evidence of new Kubernetes API removals (Rule 13)
- Use `{product-title}` not "OpenShift Container Platform"
- Use `ifdef::openshift-origin[]` for OKD-specific content
