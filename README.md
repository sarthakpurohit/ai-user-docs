# ai-user-docs

AI-driven generation of user-facing documentation for [OKD](https://www.okd.io/) and [OpenShift Container Platform](https://www.redhat.com/en/technologies/cloud-computing/openshift/container-platform), using LLM skills trained on source code diffs.

OKD/OpenShift documentation is built from [openshift/openshift-docs](https://github.com/openshift/openshift-docs) using AsciiDoc and covers ~20 sections (Installing, Updating, Networking, Security, etc.) that must be refreshed every release. This project automates that refresh.

## What This Does

Generates updated OpenShift documentation for each release by applying a simple formula:

```
Docs(version) = SKILL.md + Docs(previous_version) + CodeDiff(previous → current)
```

An LLM reads the previous version's OpenShift documentation, analyzes what changed in the source code across multiple repositories (e.g., `openshift/installer`, `openshift/api`, `openshift/cluster-version-operator`), and produces an updated AsciiDoc documentation set. A trained **SKILL.md** file encodes OpenShift doc conventions, AsciiDoc patterns, and lessons learned from prior iterations.

## How It Works

1. **Extract** baseline docs for a known version
2. **Generate** structured code diffs between two release branches across multiple repos
3. **Feed** the SKILL.md + baseline docs + code diff to an LLM
4. **Score** the generated output against ground truth (deterministic metrics)
5. **Evaluate** with an LLM judge for semantic accuracy
6. **Refine** the SKILL.md based on what the LLM got wrong
7. **Repeat** for the next version — each pass adds battle-tested rules

## Trained Sections

| Section | Skill File | Rules | Source Repos | Avg Similarity |
|---------|-----------|-------|-------------|----------------|
| Installing | `skills/generate-install-docs/SKILL.md` | 23 | 7 | 94.8% |
| Updating | `skills/generate-updating-docs/SKILL.md` | 28 | 5 | 96.5% |

Each section was trained over 6 iterations (versions 4.17 through 4.22), with the skill growing from ~12 generic rules to 23-28 specific rules.

## Project Structure

```
├── skills/                      # SKILL.md files per section
│   ├── generate-install-docs/   # Installing section skill
│   ├── generate-updating-docs/  # Updating section skill
│   └── snapshots/               # Historical skill versions per iteration
├── scripts/                     # Diff generation, evaluation, HTML viewer
├── diffs/                       # Structured code diff summaries per version
├── generated/                   # AI-generated documentation output
├── evaluation/                  # Deterministic scoring reports
├── eval/                        # LLM evaluation harness config
├── presentation/                # Project overview (open in browser)
├── tmp/                         # Generation & evaluation prompts (installing)
├── tmp-updating/                # Generation & evaluation prompts (updating)
├── demo-artifacts/              # Preserved demo data
├── comparison/                  # Static HTML comparison pages
└── Makefile                     # Convenience commands
```

## Quick Start

### Prerequisites

- Python 3.9+
- Git (for cloning source repos)
- An LLM-capable editor (e.g., Cursor) for running generation/evaluation prompts

### 1. Clone source repositories

The diff generation scripts expect bare clones of the relevant OpenShift source repos:

```bash
# For the installing section
git clone --bare https://github.com/openshift/installer.git
git clone --bare https://github.com/openshift/api.git
git clone --bare https://github.com/openshift/baremetal-operator.git
git clone --bare https://github.com/openshift/assisted-installer.git
git clone --bare https://github.com/openshift/cluster-network-operator.git
git clone https://github.com/openshift/machine-config-operator
git clone https://github.com/openshift/machine-api-operator

# For the updating section
git clone --bare https://github.com/openshift/cluster-version-operator.git
git clone --bare https://github.com/openshift/oc.git
# machine-config-operator is shared with installing
```

### 2. Extract docs corpus

```bash
make extract SECTION=installing
make extract SECTION=updating
```

### 3. Generate diffs

```bash
# Installing section
make diffs FROM=4.16 TO=4.17

# Updating section
make updating-diffs FROM=4.16 TO=4.17
```

### 4. Run the comparison viewer

```bash
make compare VERSION=4.17 SECTION=installing
# Opens http://localhost:9092 with 3-panel comparison
```

### 5. Run deterministic scoring

```bash
make score VERSION=4.17 SECTION=installing
```

## Evaluation Metrics

### Deterministic (automated, fast)
- **File Coverage** — are all expected files present?
- **Text Similarity** — line-by-line content similarity (difflib)
- **Section Coverage** — are all section headings present?
- **Parameter Coverage** — are all parameter names mentioned?

### LLM-Based (semantic, thorough)
- **Semantic Accuracy** — are the facts correct?
- **Completeness** — are all code changes reflected?
- **Structure Compliance** — are AsciiDoc/OpenShift doc conventions followed?
- **Command Accuracy** — are CLI commands verified against source?

## Key Findings

- **94-97% deterministic accuracy** on stable releases (code-derivable changes)
- **~20-25% of doc changes** come from product/editorial decisions invisible in code — the hard ceiling for code-diff-only approaches
- **Enhanced diffs** (full Go type files, CRD schemas) improve LLM completeness by +34%
- **Single-agent generation is mandatory** — subagents lose context and produce contradictory edits
- **Iterative skill training works** — each pass adds 2-5 rules from real failures

## Presentation

Open `presentation/project-overview-final.html` in a browser for the full project overview with interactive results, diagrams, and methodology explanation.

## License

Apache 2.0
