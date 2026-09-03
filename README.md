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

---

## View the Results (No LLM Needed)

Want to see how AI-generated docs compare to human-written ones? The repo includes all generated output for both sections. You just need to extract the ground-truth docs, generate the code diffs, and launch the viewer.

### Prerequisites

- Python 3.9+
- Git

### Step 1: Clone source repositories

This pulls the upstream OpenShift code repos used for diff generation (~5 min first time):

```bash
make init
```

### Step 2: Extract the ground-truth docs

This pulls the official docs from `openshift/openshift-docs` (auto-clones the repo on first run, ~2 min):

```bash
make extract                        # both sections
make extract SECTION=installing     # or just one section
```

This creates `docs-corpus/ocp/4.16/installing/`, `docs-corpus/ocp/4.17/installing/`, etc.

### Step 3: Launch the comparison viewer

Pick any version from 4.17 to 4.22:

```bash
make compare VERSION=4.17 SECTION=installing
```

This opens a browser at `http://localhost:9092` with a 3-panel view:

| Panel | Shows |
|-------|-------|
| **Existing 4.16** | The previous version's docs (baseline) |
| **Existing 4.17** | The human-written docs for this version |
| **Generated 4.17** | What the AI produced from 4.16 + code diffs |

Switch to the **Diff** tab to see GitHub-style line-by-line highlighting of what changed from the baseline in both the human and AI versions.

### Step 4: Try other versions or sections

```bash
make compare VERSION=4.20 SECTION=installing
make compare VERSION=4.18 SECTION=updating
```

> **Tip:** The sidebar categorizes files as "Changed", "Unchanged", and "Other". Start with **Changed Files** tagged **BOTH CHANGED** — those show where both the human and AI made edits, so you can directly compare their approaches.

---

## Full Setup (For Generating New Docs)

If you want to run the full pipeline yourself (generate docs, run diffs, evaluate), follow these steps.

### 1. Clone source repositories

```bash
make init                        # all repos for both sections
make init SECTION=installing     # only repos for installing
make init SECTION=updating       # only repos for updating
```

### 2. Extract docs corpus

```bash
make extract                        # both sections
make extract SECTION=installing     # or just one
make extract SECTION=updating
```

### 3. Generate code diffs

```bash
make diffs                          # both sections, all versions (4.16→4.22)
make diffs SECTION=installing       # installing only
make diffs SECTION=updating         # updating only
```

Or generate a single version pair:

```bash
make diffs SECTION=installing FROM=4.16 TO=4.17
```

### 4. Run deterministic scoring

```bash
make score VERSION=4.17 SECTION=installing
make score VERSION=4.17 SECTION=updating
```

### 5. Run the training loop

```bash
make train SECTION=installing VERSION=4.17
```

For LLM-based generation and evaluation, use the prompt files in `tmp/` (installing) or `tmp-updating/` (updating) in an LLM-capable editor.

---

## Project Structure

```
├── skills/                      # SKILL.md files per section
│   ├── generate-install-docs/   # Installing section skill (23 rules)
│   ├── generate-updating-docs/  # Updating section skill (28 rules)
│   └── snapshots/               # Historical skill versions per iteration
├── scripts/                     # Diff generation, evaluation, HTML viewer
├── generated/                   # AI-generated documentation output
│   ├── installing/              # Versions 4.17-4.22
│   └── updating/                # Versions 4.17-4.22
├── evaluation/                  # Deterministic scoring reports
├── eval/                        # LLM evaluation harness config
├── presentation/                # Project overview (open in browser)
├── tmp/                         # Generation & evaluation prompts (installing)
├── tmp-updating/                # Generation & evaluation prompts (updating)
└── Makefile                     # All commands (run `make help`)
```

> **Note:** `diffs/` and `docs-corpus/` are gitignored (regenerable artifacts). Run `make diffs` and `make extract` to create them locally.

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

**[View the Project Overview](https://sarthakpurohit.github.io/ai-user-docs/)** — live GitHub Pages link with interactive results, diagrams, and methodology explanation.

Or open `presentation/project-overview-final.html` locally in a browser.

## License

Apache 2.0
