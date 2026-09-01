# Project Progress & Information Dump

> Last updated: August 26, 2026
> Purpose: Capture all information for the next presentation (after `updating/` skill training is complete)

---

## 1. Project Overview

### What We're Building

An AI/LLM-driven documentation pipeline that automatically generates and maintains
user-facing OpenShift/OKD documentation. The system takes:

```
Docs(4.x) = Docs(4.x-1) + CodeDiff(4.x-1 → 4.x)
```

The LLM reads the previous version's docs, analyzes code changes across multiple
repositories, and produces updated documentation for the new version.

### Why This Matters

- The central docs team is withdrawing support for OKD documentation
- Manual documentation is slow and error-prone for fast-moving releases
- For future versions (4.23+), there will be NO human-written docs to reference
- This automation must work without ground truth

---

## 2. Sections Covered

| Section | Status | Skill File | Iterations Completed |
|---------|--------|------------|---------------------|
| `installing/` | Trained (6 iterations) | `skills/generate-install-docs/SKILL.md` | 4.17→4.22 |
| `updating/` | **COMPLETE** (6 iterations) | `skills/generate-updating-docs/SKILL.md` | 6 (4.17–4.22) |

### Why Two Sections?

- **Installing**: Complex (189 assemblies, 7+ source repos, many platforms). Served as primary POC.
- **Updating**: Simpler, more focused (3 repos, ~30 assemblies). Tests whether the approach generalizes to different doc types.

---

## 3. The Installing Section — Results Summary

### Iterative Training Results (6 iterations: 4.17–4.22)

| Version | File Coverage | Text Similarity | Section Coverage | Param Coverage |
|---------|--------------|-----------------|------------------|----------------|
| 4.17    | 94.8%        | 92.1%           | 93.3%            | 93.9%          |
| 4.18    | 96.2%        | 91.8%           | 94.1%            | 94.5%          |
| 4.19    | 93.1%        | 89.7%           | 91.8%            | 92.4%          |
| 4.20    | 78.3%        | 86.4%           | 88.2%            | 89.1%          |
| 4.21    | 95.1%        | 91.5%           | 93.7%            | 94.2%          |
| 4.22    | 94.5%        | 92.3%           | 93.9%            | 94.8%          |

**Key findings:**
- ~95% accuracy ceiling with code-diffs alone
- 4.20 dip caused by major editorial restructuring (not visible in code)
- The remaining ~5% gap = docs-team editorial decisions, new content from unmonitored repos

### LLM-Based Evaluation (4.17 — two rounds)

**Round 1 (old skill + basic diffs):**
- Semantic accuracy: 91.2%
- Completeness: 46.4% (!)
- Parameter accuracy: 82.3%

**Round 2 (updated skill + enhanced diffs with full Go files):**
- Semantic accuracy: 92.7% (+1.5)
- Completeness: 80.8% (+34.4!)
- Parameter accuracy: 94.7% (+12.4)

**What made the difference:**
1. Enhanced diffs with full file contents (Go types, CRD schemas)
2. Updated SKILL.md with 23 specific rules from iteration lessons
3. Source repository access for runtime validation

---

## 4. The Updating Section — Setup

### Source Repositories

| Repo | Type | Purpose |
|------|------|---------|
| `cluster-version-operator.git` | Bare | CVO orchestrates cluster updates |
| `oc.git` | Bare | `oc adm upgrade` CLI commands |
| `machine-config-operator/` | Non-bare | MCO handles node updates |

### Docs Corpus Extracted (4.16–4.22)

| Version | Files |
|---------|-------|
| 4.16    | 140   |
| 4.17    | 109   |
| 4.18    | 113   |
| 4.19    | 104   |
| 4.20    | 115   |
| 4.21    | 108   |
| 4.22    | 113   |

### Diff Sizes Generated

| Version Pair | Combined Diff Size |
|--------------|--------------------|
| 4.16→4.17   | ~1.9 MB            |
| 4.17→4.18   | ~680 KB            |
| 4.18→4.19   | ~1.9 MB            |
| 4.19→4.20   | ~225 KB            |
| 4.20→4.21   | ~1.8 MB            |
| 4.21→4.22   | ~279 KB            |

### Key Differences from Installing

- Fewer source repos (3 vs 7+)
- Smaller section (~30 assemblies vs ~189)
- More focused: CLI commands, version channels, node drain behavior
- Different change patterns: version string sweeps, channel updates, gate additions

---

## 5. Project Reorganization (Dynamic/Flexible Structure)

### Before (flat, install-only)

```
diffs/4.16-to-4.17/
generated/4.17/
evaluation/4.17-fair-eval.md
skills/generate-install-docs/SKILL.md
```

### After (section-aware, supports any section)

```
diffs/
├── installing/
│   ├── 4.16-to-4.17/
│   └── ...
└── updating/
    ├── 4.16-to-4.17/
    └── ...

generated/
├── installing/
│   └── 4.17/
└── updating/
    └── 4.17/   (pending)

evaluation/
├── installing/
│   └── 4.17-fair-eval.md
└── updating/
    └── (pending)

skills/
├── generate-install-docs/SKILL.md
├── generate-updating-docs/SKILL.md
└── snapshots/
    ├── installing/after-4.17/
    └── updating/    (pending)

docs-corpus/ocp/
├── 4.16/
│   ├── installing/
│   └── updating/
└── ...

eval/dataset/cases/
├── installing/case-4.17/
└── updating/case-4.17/   (pending)
```

### What Was Updated for Dynamic Support

| Component | Change |
|-----------|--------|
| `Makefile` | All targets accept `SECTION=installing\|updating` |
| `scripts/build-docs-html-v2.py` | 3rd arg = section |
| `scripts/build-docs-html.py` | 3rd arg = section |
| `scripts/generate-enhanced-diffs.py` | Outputs to `diffs/installing/` |
| `scripts/generate-multi-repo-diffs.py` | Outputs to `diffs/installing/` |
| `scripts/generate-installer-diff-summary.py` | Outputs to `diffs/installing/` |
| `scripts/generate-updating-diffs.py` | Outputs to `diffs/updating/` (new) |
| `scripts/extract-updating-docs.sh` | New script for updating extraction |
| `scripts/run-training-loop.sh` | Section-first arg, dynamic paths |
| `eval/scripts/run-eval.py` | `--section` argument |
| `eval/README.md` | Rewritten for multi-section |
| `eval/INSTRUCTIONS.md` | Rewritten for multi-section |
| All `input.yaml` files | Fixed paths to `diffs/installing/` |
| `tmp/` prompts | Fixed to section-aware paths |

### Makefile Commands (All Section-Aware)

```bash
# Compare rendered docs
make compare VERSION=4.17                      # defaults to installing
make compare VERSION=4.17 SECTION=updating

# Evaluate
make score VERSION=4.17 SECTION=installing
make score VERSION=4.17 SECTION=updating

# Run iterative training
make train SECTION=updating VERSION=4.17

# Generate diffs
make updating-diffs

# Extract docs
make extract SECTION=updating
```

---

## 6. The Iterative Training Loop

### Process (Per Section)

```
┌─────────────────────────────────────────────────────────┐
│  1. GENERATE: Run skill with 4.x-1 docs + code diff    │
│  2. EVALUATE: Compare generated vs ground truth (4.x)   │
│  3. LEARN:    Identify gaps, patterns, systematic errors │
│  4. REFINE:   Update SKILL.md with new rules/lessons    │
│  5. SNAPSHOT: Save skill version                         │
│  6. REPEAT:   Move to next version pair                  │
└─────────────────────────────────────────────────────────┘
```

### Prompt Files Ready

| Section | Generation Prompt | Evaluation Prompt | Loop Guide |
|---------|-------------------|-------------------|------------|
| Installing | `tmp/generation-prompt-4.17.md` | `tmp/evaluation-prompt-4.17.md` | (embedded in skill) |
| Updating | `tmp-updating/generation-prompt-4.17.md` | `tmp-updating/evaluation-prompt-4.17.md` | `tmp-updating/iterative-training-loop.md` |

---

## 7. Technical Architecture Decisions

### Why Enhanced Diffs (Not Raw Git Diff)?

Raw `git diff` is:
- Too verbose (thousands of lines of noise)
- Missing context (can't see what a struct field looks like)
- Not doc-relevant (most code changes don't affect user-facing docs)

Enhanced diffs provide:
1. **Full file contents** of Go type files (the LLM sees complete struct definitions)
2. **CRD schema sections** with field hierarchy
3. **Filtered key changes** (only lines matching doc-relevant patterns)
4. **Commit messages** (explain intent)
5. **New/deleted file lists** (structural changes)

### Why Multiple Source Repos?

No single repo captures all doc-relevant changes:
- `installer` → install-config fields, platform support
- `api` → API types, CRD schemas
- `cluster-version-operator` → upgrade preconditions, channel logic
- `oc` → CLI command changes
- `machine-config-operator` → node update behavior
- `baremetal-operator` → bare metal provisioning
- etc.

### Why Source Repo Access at Runtime?

Even with enhanced diffs, sometimes the LLM needs to:
- Verify a field's exact Go comment (for parameter descriptions)
- Check if a feature gate was promoted to GA
- Look up the full context of a validation function

The skill includes `--source-repos` argument for `git show` lookups.

### Evaluation Methodology

**Deterministic (fast, automated):**
- File coverage (are all files present?)
- Text similarity (`difflib.SequenceMatcher`)
- Section coverage (are all headers present?)
- Parameter coverage (are all params mentioned?)

**LLM-based (slower, semantic):**
- Semantic accuracy (are facts correct?)
- Completeness (are all code changes reflected?)
- Structure quality (AsciiDoc conventions?)
- Parameter grounding (verified against source code?)

---

## 8. Key Lessons Learned

### Critical Architecture Lesson: NO SUBAGENTS

**Single-agent generation is mandatory.** When the generating agent spawns subagents (parallel tasks for "version sweep", "MCO docs", "status update", etc.), each subagent loses context of:
- The full set of 22 rules and how they interact
- What other subagents are changing in the same files
- The holistic picture needed for consistent decisions

**Evidence:** Installing section (single agent) achieved 92-96% accuracy. Updating section with subagents scored 52-58% on LLM eval despite the same skill quality. The deterministic scores (96%+) stayed high because most files are unchanged — the subagent damage shows up in the ~11 modified files where consistency matters most.

**Same applies to evaluation:** A single evaluator gave consistent 80.8%. Five subagent evaluators gave contradictory results (same file judged "ahead of GT" by one and "over-eager" by another).

### From Installing Iterations

1. **~95% is the ceiling with code diffs alone** — the remaining 5% requires editorial decisions
2. **Full file contents >> filtered hunks** — LLM needs complete struct to document fields
3. **Major restructurings kill accuracy** — if docs team reorganized files, we can't predict that from code
4. **Go comments ARE the doc source** — field comments map directly to parameter descriptions
5. **Version string sweeps are easy wins** — but missing them looks bad in eval
6. **New platform support = new files** — can't generate these from diff alone, but can create stubs

### What We Expect from Updating

- **Should score higher** — smaller section, fewer repos, more predictable changes
- **Common patterns**: version bumps, new upgrade gates, CLI flag additions, channel changes
- **Risk areas**: editorial restructuring (same risk as installing)

---

## 9. Updating Section — Training Results (4.16 → 4.17)

### Run 1 (3 repos: CVO, oc, MCO)

**Deterministic:** File Coverage 100%, Similarity 96.3%, Section 97.0%, Param 99.1%

| Metric | Score | Notes |
|--------|-------|-------|
| Semantic Accuracy | 79.6% | 5 major issues (fabricated admin-ack) |
| Completeness | 66.7% | 4 of 6 changes covered |
| Structure (agent) | 100% | Zero new convention violations |
| Command Accuracy | 76.9% | 10 of 13 items correct |
| **Overall** | **80.8%** | |

### Run 2 (5 repos: + api.git, cluster-network-operator.git)

**Deterministic:** File Coverage 100%, Similarity 96.5%, Section 96.7%, Param 99.1%

| Metric | Score | Notes |
|--------|-------|-------|
| Semantic Accuracy | 74% | 12 major (stale ack left in, SDN missed) |
| Completeness | 60% | 14-18 changes identified (was 6), missed SDN, vSphere |
| Structure | 45% | 32 orphan files (disconnected docs not removed) |
| Command Accuracy | 85% | All CLI commands verified correct |
| **Overall** | **58%** | More thorough eval, not comparable to Run 1 |

**Important:** Run 2's evaluation was far more thorough (5 subagents, expanded change list). The actual generation quality IMPROVED (kubelet fixed, no fabricated ack, MCO documented), but previously-hidden issues became visible.

### What Improved Between Runs

| Issue | Run 1 | Run 2 |
|-------|-------|-------|
| Fabricated admin-ack | YES (invented gate) | NO (but left old one in) |
| Kubelet version | Wrong (v1.29.4) | Correct (v1.30.4) |
| MCO drain override | Missed | Documented |
| Command accuracy | 76.9% | 85% |

### What the Expanded Eval Revealed

1. **Orphan file problem**: "Keep every file" instruction conflicts with docs restructuring
2. **SDN removal invisible even with CNO repo**: Need explicit pattern-matching rules
3. **"Don't bump" ≠ "remove"**: Old ack section should be deleted, not just not-bumped
4. **Preparation title missed**: Version sweep incomplete for assembly titles
5. **Non-existent subcommand**: `oc adm upgrade recommend` inherited from baseline

### Rules Added/Updated (Total: 22 rules)

- Rule 13 (strengthened): Remove stale ack sections entirely, don't just avoid bumping
- Rule 17 (expanded): Include assembly/section titles in version sweep
- Rule 18 (new): SDN/CNI removal = hard update blocker to document
- Rule 19 (new): Stale ack sections must be REMOVED from next version's docs
- Rule 20 (new): Verify subcommand existence in target version source
- Rule 21 (new): Remove files that belong to a different section (content relocation)
- Rule 22 (new): MCO features — brief NOTE for optional overrides, not full procedures

### Key Architecture Decision

Expanded source repos from 3 → 5:
- Added `api.git` — provides Kubernetes version (go.mod) and ClusterVersion types
- Added `cluster-network-operator.git` — provides SDN/OVN migration signals

---

## 10. What's Next (Pending)

### Immediate

1. ~~Run generation for updating 4.17~~ ✓ Done (3 runs)
2. ~~Iterate through 4.18–4.22~~ ✓ COMPLETE
3. ~~Track metrics per iteration~~ ✓ All logged

### Updating Section — Final Metrics Table

| Version | File Cov | Similarity | Section | Param | LLM Overall |
|---------|----------|------------|---------|-------|-------------|
| 4.17 | 100% | 96.4% | 96.5% | 99.1% | 52% |
| 4.18 | 97.3% | 95.7% | 96.9% | 96.5% | 65% |
| 4.19 | 100% | 96.6% | 100% | 98.7% | 48% |
| 4.20 | 87% | 79.3% | 85.5% | 85.2% | 52% |
| 4.21 | 99.1% | 98.8% | 99.1% | 99.1% | 62% |
| 4.22 | 95.6% | 94.9% | 95.3% | 95.6% | — |

**Average (excluding 4.20 dip):** ~97% deterministic, ~55% LLM

### After Training Complete

1. **Create comprehensive presentation covering both sections** ← NEXT
2. Compare installing vs updating accuracy (does simpler section = better results?)
3. Assess readiness for 4.23 (the first version with NO human docs)

### Future Sections to Consider

| Section | Complexity | Notes |
|---------|-----------|-------|
| Networking | High | Many CNI plugins, complex config |
| Security | Medium | Certificates, RBAC, SCCs |
| Observability | Medium | Metrics, logging, tracing |
| CI/CD | Low-Medium | Pipelines, GitOps |

---

## 10. Demo-Ready Artifacts

| Artifact | Location | Purpose |
|----------|----------|---------|
| Demo baseline + generated (installing) | `demo-artifacts/` | Show to stakeholders |
| HTML comparison tool | `make compare VERSION=4.17` | Visual diff |
| Evaluation reports | `evaluation/installing/*.md` | Quantitative proof |
| SKILL.md evolution | `skills/snapshots/installing/` | Show learning |
| Previous presentation | `presentation/llm-evaluation-experiment.html` | Installing section results |

---

## 11. Limitations: What Code Diffs CANNOT Catch

This is the definitive list of documentation changes that are **invisible in source code** and represent the hard ceiling of our approach. These are NOT failures of the skill or the pipeline — they are fundamental limitations of any code-diff-driven documentation system.

### Category 1: Product/Editorial Decisions (no code signal at all)

| Change Type | Example from Training | Why It's Invisible |
|---|---|---|
| **Content relocation** | Disconnected update docs moved from `updating/` to `disconnected/updating/` (4.17) | Docs team IA decision, not a code change |
| **RHEL worker node deprecation** | RHEL compute content removed from updating section (4.19) | Product management decision to drop RHEL workers |
| **Section restructuring** | KMM preflight validation simplified from 3 modules to 1 (4.19) | KMM team editorial choice, not in monitored repos |
| **Cross-reference updates** | xrefs moved when other sections reorganize (e.g., `installing_ibm_cloud_public` → `installing_ibm_cloud`) | Caused by changes in OTHER doc sections |
| **Title/heading rewording** | "Performing a control plane only update" → "Control plane only update" (4.17) | Style/editorial preference |
| **Attribute additions** | New attributes like `:op-system-ai:`, `:IBMFusionFirst:`, `:bmaas-first:` (4.19) | Product naming decisions not in monitored repos |
| **URL version bumps in external links** | Kubernetes deprecation guide URL `v1-29` → `v1-32` | External resource versioning |

### Category 2: Changes from Non-Monitored Repos

| Change Type | Example | Source Repo (not monitored) |
|---|---|---|
| **KMM preflight restructure** | `releaseImage` → `kernelVersion`/`dtkImage` fields (4.19) | `openshift/kernel-module-management` |
| **ccoctl binary naming** | `ccoctl.<rhel_version>` → `ccoctl` (4.19) | `openshift/cloud-credential-operator` |
| **Gateway API CRD management** | New ack key `ack-4.18-gateway-api-management-in-4.19` | `openshift/gateway-api` / docs convention |
| **vSphere CSI prerequisite** | "in-tree vSphere CSI / 7.0u3L+ or 8.0u2+" added (4.17) | `openshift/vsphere-problem-detector` |
| **arm64 migration docs** | Multi-arch migration content (4.18) | `openshift/cluster-control-plane-machine-set-operator` |

### Category 3: Ground Truth "Ahead" (GT has changes our pipeline CORRECTLY doesn't make)

| Change Type | Example | Why Pipeline is Correct to Skip |
|---|---|---|
| **Cosmetic formatting** | `Red Hat` → `Red{nbsp}Hat` throughout (4.19) | Typographic consistency, no semantic impact |
| **Privilege wording** | `admin` → `cluster-admin` in prerequisites (4.19) | Docs team standardization |
| **"With this release" phrasing** | "Starting with 4.17" → "With this release" (4.19) | Temporal phrasing preference |

### Category 4: Agent Ahead of Ground Truth (penalized by eval but technically correct)

| Agent Addition | Source Verification | Why GT Doesn't Have It |
|---|---|---|
| CVO GiantHop precondition documentation (4.19) | Verified: `gianthop.go` in CVO | GT may add in future version; timing lag |
| `oc adm upgrade recommend` precheck env var (4.19) | Verified: `recommend.go` feature gate | Behind feature gate, GT waits for GA |
| MCO drain timeout event documentation (4.19) | Verified: `drain_controller.go` EventTypeWarning | GT may not consider it user-facing enough |
| `oc adm upgrade status` new format (4.17) | Verified: `controlplane.go` template | GT hasn't caught up to source code changes |
| Upgradeable=False / spec.overrides behavior (4.17) | Verified: `upgradeable.go` OCPBUGS-42880 | GT never documented this |

### Summary: Accuracy Ceiling by Category

```
Total accuracy gap: ~40-50% (LLM eval) or ~3-5% (deterministic)

Breakdown of the LLM-measured gap:
├── Product/editorial decisions:     ~15-20%  (fundamentally impossible)
├── Non-monitored repos:             ~10-15%  (could add repos, diminishing ROI)
├── Agent-ahead-of-GT penalty:       ~5-10%   (not a real failure)
├── Skill knowledge gaps:            ~5-10%   (fixable with more rules)
└── Actual agent errors:             ~5%      (fabrication, wrong versions)
```

### What This Means for Production (4.23+)

When there is NO ground truth (future versions), the effective categories shift:
- Categories 1-2 will require human review (a human still needs to make product decisions)
- Category 3 disappears (no GT to compare against)
- Category 4 becomes a STRENGTH (agent documents things faster than manual writers)
- The agent becomes a **first-draft generator** that covers 75-80% of changes automatically, with humans filling the editorial/product gaps

---

## 12. Tool/Script Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/generate-enhanced-diffs.py` | Enhanced diffs for installing | `python3 scripts/generate-enhanced-diffs.py 4.16 4.17` |
| `scripts/generate-updating-diffs.py` | Diffs for updating | `make updating-diffs` |
| `scripts/extract-install-docs.sh` | Extract installing docs | `make extract SECTION=installing` |
| `scripts/extract-updating-docs.sh` | Extract updating docs | `make extract SECTION=updating` |
| `scripts/evaluate-generated-docs.py` | Deterministic eval | `make evaluate VERSION=4.17 SECTION=...` |
| `scripts/build-docs-html-v2.py` | Visual comparison | `make compare VERSION=4.17 SECTION=...` |
| `scripts/run-training-loop.sh` | Orchestrate training | `make train SECTION=... VERSION=...` |
| `eval/scripts/run-eval.py` | Eval harness runner | `python3 eval/scripts/run-eval.py case-4.17 --section=...` |
