# OKD Documentation Automation -- Agent Instructions

This repository contains the automation infrastructure for AI-driven OKD
documentation maintenance. All documentation lives in the
[openshift/openshift-docs](https://github.com/openshift/openshift-docs)
repository and is built using AsciiDoc + AsciiBinder.

## Repository Purpose

OKD is the upstream, community distribution of Red Hat OpenShift. Its
documentation is produced from the same source as OpenShift Container Platform
(OCP) docs, differentiated via AsciiDoc conditionals and topic-map filters.

This repo provides:

- **GitHub Agentic Workflows** that watch OKD-relevant code repos and
  auto-generate documentation PRs against `openshift/openshift-docs`
- **The OKD Difference Catalog** (`config/okd-difference-catalog.yaml`) --
  the single source of truth for all OKD-vs-OCP doc differences
- **Scripts** for auditing drift, correlating features across repos, and
  building the difference catalog
- **Agent skills and instructions** that encode OKD doc-writing conventions

## Critical Rules for All Agents

### Never auto-merge

Every generated PR must be a **draft**. Humans review and merge.

### Use AsciiDoc attributes, not hardcoded names

- Use `{product-title}` instead of "OKD" or "OpenShift Container Platform"
- Use `{op-system}` instead of "SCOS" or "RHCOS"
- Use `{op-system-first}` for the first mention with the expanded form
- Use `{op-system-base}` instead of "CentOS Stream" or "RHEL"
- See `_attributes/common-attributes.adoc` for all available attributes

### Use ifdef/endif for OKD-specific content

```asciidoc
ifdef::openshift-origin[]
This content appears only in OKD documentation.
endif::openshift-origin[]

ifndef::openshift-origin[]
This content appears in all distributions except OKD.
endif::openshift-origin[]
```

### Do not use ifdef to conditionalize entire files

If an entire file is specific to one distribution, set the `Distros` field
in `_topic_maps/_topic_map.yml` instead.

### Follow the openshift-docs module/assembly structure

- **Assemblies** live in top-level topic directories (e.g., `installing/`)
- **Modules** live in `modules/` with the naming convention:
  - `con-*.adoc` for concept modules
  - `proc-*.adoc` for procedure modules
  - `ref-*.adoc` for reference modules
- Assemblies include modules via `include::modules/filename.adoc[leveloffset=+1]`

### OKD OS is CentOS Stream CoreOS (SCOS), not Fedora CoreOS

As of OKD 4.16, the node operating system is CentOS Stream CoreOS (SCOS).
All new docs must reference SCOS. The old FCOS references in
`common-attributes.adoc` are stale and pending a fix.

### OKD uses community-operators, not redhat-operators

When referencing operator catalog sources, OKD uses `community-operators`
from OperatorHub.io, not `redhat-operators`.

## Files Not to Modify

- `AGENTS.md` (this file)
- `package.json` / `package-lock.json` (if present)
- `.github/workflows/*.lock.yml` (generated, do not hand-edit)
- Any file in `_upstream/` (read-only reference clones)

## Key Reference Files

- `config/okd-difference-catalog.yaml` -- All OKD-vs-OCP differences
- `config/monitored-repos.yaml` -- Repos to watch for changes
- `config/topic-map-rules.yaml` -- Topic map conventions
- `skills/okd-doc-writer.md` -- Detailed doc-writing skill for agents
- `scripts/build-diff-catalog.sh` -- Regenerate the difference catalog
- `scripts/correlate-features.py` -- Group PRs by Jira ID for release sweeps
- `scripts/audit-okd-docs.sh` -- Detect drift in rendered OKD docs
