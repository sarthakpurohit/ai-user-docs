# Generation Prompt: Updating Docs 4.22

You are generating updated "Updating clusters" documentation for OpenShift 4.22 based on the 4.21 docs and code diffs.

## Your Task

Follow the skill file at `skills/generate-updating-docs/SKILL.md` exactly.

## Inputs

- **Previous version docs (4.21 baseline):** `docs-corpus/ocp/4.21/updating/`
- **Code diff summary:** `diffs/updating/4.21-to-4.22/combined-diff-4.21-to-4.22.md`
- **Target distro:** `ocp`
- **Output directory:** `generated/updating/4.22/`
- **Source repos (for runtime lookup):**
  - `cluster-version-operator.git/` (bare) at `cluster-version-operator.git`
  - `oc.git/` (bare) at `oc.git`
  - `machine-config-operator/` (non-bare) at `machine-config-operator`
  - `api.git/` (bare) at `api.git`
  - `cluster-network-operator.git/` (bare) at `cluster-network-operator.git`

## Instructions

1. Read the SKILL.md file completely first.
2. Read the full code diff summary.
3. Read the 4.21 baseline docs (all assemblies and their included modules).
4. Following Phase 1 of the skill, analyze and map changes to documentation impact.
5. Following Phase 2, generate the complete updated docs for 4.22.

## Output Requirements

- Write ALL output files to `generated/updating/4.22/`
- Maintain the exact directory structure from the 4.21 baseline
- Files from the 4.21 baseline should appear in the output UNLESS they clearly belong to a different documentation section (Rule 21) or are deprecated content (Rule 26)
- New modules/assemblies may be added if the diff warrants them
- At the end, provide a summary of what changed and why

## Key Reminders

- **CRITICAL: Do NOT use subagents or parallel tasks.** Process everything sequentially in a single context. You need full awareness of ALL rules and ALL changes to make consistent decisions across files. Spawning subagents causes contradictory edits and rule violations.
- You are NOT writing from scratch. Copy the 4.21 baseline and modify only what the diff demands.
- Version strings: `stable-4.21` → `stable-4.22`, version numbers in examples updated
- Kubelet: check `api.git` go.mod for Kubernetes version → derive kubelet version (use .0 patch if exact patch unknown)
- Admin-ack: Always verify from CVO `pkg/payload/precondition/` code — don't trust hardcoded mapping alone (Rule 25)
- GA promotions: if a feature gate is REMOVED, the command becomes primary (Rule 27)
- User-configurable TP features ARE user-facing (Rule 28)
- Example outputs: use test fixtures from source repos, don't fabricate (Rule 24)
- Use `{product-title}` not "OpenShift Container Platform"
- Use `ifdef::openshift-origin[]` for OKD-specific content
