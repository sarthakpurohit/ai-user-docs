# Generation Prompt: Updating Docs 4.21

You are generating updated "Updating clusters" documentation for OpenShift 4.21 based on the 4.20 docs and code diffs.

## Your Task

Follow the skill file at `skills/generate-updating-docs/SKILL.md` exactly.

## Inputs

- **Previous version docs (4.20 baseline):** `docs-corpus/ocp/4.20/updating/`
- **Code diff summary:** `diffs/updating/4.20-to-4.21/combined-diff-4.20-to-4.21.md`
- **Target distro:** `ocp`
- **Output directory:** `generated/updating/4.21/`
- **Source repos (for runtime lookup):**
  - `cluster-version-operator.git/` (bare) at `cluster-version-operator.git`
  - `oc.git/` (bare) at `oc.git`
  - `machine-config-operator/` (non-bare) at `machine-config-operator`
  - `api.git/` (bare) at `api.git`
  - `cluster-network-operator.git/` (bare) at `cluster-network-operator.git`

## Instructions

1. Read the SKILL.md file completely first.
2. Read the full code diff summary.
3. Read the 4.20 baseline docs (all assemblies and their included modules).
4. Following Phase 1 of the skill, analyze and map changes to documentation impact.
5. Following Phase 2, generate the complete updated docs for 4.21.

## Output Requirements

- Write ALL output files to `generated/updating/4.21/`
- Maintain the exact directory structure from the 4.20 baseline
- Files from the 4.20 baseline should appear in the output UNLESS they clearly belong to a different documentation section (Rule 21) or are deprecated content (Rule 26)
- New modules/assemblies may be added if the diff warrants them
- At the end, provide a summary of what changed and why

## Key Reminders

- **CRITICAL: Do NOT use subagents or parallel tasks.** Process everything sequentially in a single context. You need full awareness of ALL rules and ALL changes to make consistent decisions across files. Spawning subagents causes contradictory edits and rule violations.
- You are NOT writing from scratch. Copy the 4.20 baseline and modify only what the diff demands.
- Version strings: `stable-4.20` → `stable-4.21`, version numbers in examples updated
- Kubelet: check `api.git` go.mod for Kubernetes version → derive kubelet version
- Admin-ack: OCP 4.20 = Kubernetes 1.33 which removes APIs. Check if 4.21's Kubernetes version has removals too (Rule 25 — always verify from CVO precondition code, don't trust hardcoded list alone)
- GA promotions: if a feature gate is REMOVED, the command becomes primary (Rule 27)
- New CLI commands: check if they're behind feature gates / env vars (Rule 23)
- Example outputs: use test fixtures from source repos, don't fabricate (Rule 24)
- User-configurable TP features ARE user-facing (Rule 28)
- Use `{product-title}` not "OpenShift Container Platform"
- Use `ifdef::openshift-origin[]` for OKD-specific content
