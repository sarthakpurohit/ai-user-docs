.PHONY: compare score enhanced-diffs updating-diffs diffs extract help init

PORT ?= 9092
SECTION ?= installing

# Clone all required source repositories.
#
# Usage:
#   make init                         # clone all repos for both sections
#   make init SECTION=installing      # clone only repos needed for installing
#   make init SECTION=updating        # clone only repos needed for updating
#
# Source repos are cloned into the project root (bare repos as *.git,
# non-bare repos as directories). openshift-docs is cloned by `make extract`.
init:
	@echo "=== Cloning source repositories ==="
ifeq ($(SECTION),updating)
	@[ -d cluster-version-operator.git ] || git clone --bare https://github.com/openshift/cluster-version-operator.git
	@[ -d oc.git ]                       || git clone --bare https://github.com/openshift/oc.git
	@[ -d machine-config-operator ]      || git clone https://github.com/openshift/machine-config-operator
	@[ -d api.git ]                      || git clone --bare https://github.com/openshift/api.git
	@[ -d cluster-network-operator.git ] || git clone --bare https://github.com/openshift/cluster-network-operator.git
else ifeq ($(SECTION),installing)
	@[ -d installer ]                    || git clone https://github.com/openshift/installer
	@[ -d api.git ]                      || git clone --bare https://github.com/openshift/api.git
	@[ -d baremetal-operator.git ]       || git clone --bare https://github.com/openshift/baremetal-operator.git
	@[ -d assisted-installer.git ]       || git clone --bare https://github.com/openshift/assisted-installer.git
	@[ -d cluster-network-operator.git ] || git clone --bare https://github.com/openshift/cluster-network-operator.git
	@[ -d machine-config-operator ]      || git clone https://github.com/openshift/machine-config-operator
	@[ -d machine-api-operator ]         || git clone https://github.com/openshift/machine-api-operator
else
	@echo "Cloning all repos..."
	@[ -d installer ]                    || git clone https://github.com/openshift/installer
	@[ -d api.git ]                      || git clone --bare https://github.com/openshift/api.git
	@[ -d baremetal-operator.git ]       || git clone --bare https://github.com/openshift/baremetal-operator.git
	@[ -d assisted-installer.git ]       || git clone --bare https://github.com/openshift/assisted-installer.git
	@[ -d cluster-network-operator.git ] || git clone --bare https://github.com/openshift/cluster-network-operator.git
	@[ -d machine-config-operator ]      || git clone https://github.com/openshift/machine-config-operator
	@[ -d machine-api-operator ]         || git clone https://github.com/openshift/machine-api-operator
	@[ -d cluster-version-operator.git ] || git clone --bare https://github.com/openshift/cluster-version-operator.git
	@[ -d oc.git ]                       || git clone --bare https://github.com/openshift/oc.git
endif
	@echo "Done. Source repos ready."

# Launch the docs comparison viewer.
#
# Usage:
#   make compare VERSION=4.17                    # installing (default section)
#   make compare VERSION=4.17 SECTION=updating   # updating section
#   make compare VERSION=4.19 PORT=9093          # different port
#
# Opens a browser with 3-panel view (Existing prev, Existing target, Generated target)
# plus a Diff tab with line-by-line highlighting of changes from the previous version.
compare:
ifndef VERSION
	@read -p "Enter version to compare (e.g. 4.17): " ver && \
	fuser -k $(PORT)/tcp 2>/dev/null || true; \
	sleep 1; \
	python3 scripts/build-docs-html-v2.py $$ver $(PORT) $(SECTION)
else
	@fuser -k $(PORT)/tcp 2>/dev/null || true
	@sleep 1
	@python3 scripts/build-docs-html-v2.py $(VERSION) $(PORT) $(SECTION)
endif

# Run DETERMINISTIC scoring on generated docs.
# (This is the fast, automated check — NOT the LLM-based evaluation.)
#
# Uses: difflib text similarity, file coverage, section/param coverage.
#
# Usage:
#   make score VERSION=4.17                    # installing section (default)
#   make score VERSION=4.17 SECTION=updating   # updating section
#
# For LLM-based semantic evaluation, use the prompts in tmp/ or tmp-updating/
# in a separate agent window.
score:
ifndef VERSION
	@echo "Usage: make score VERSION=4.17 [SECTION=installing|updating]"
	@echo ""
	@echo "  Runs deterministic (difflib-based) scoring."
	@echo "  For LLM evaluation, use prompts in tmp-<section>/ in a new agent window."
	@echo ""
	@echo "Available sections:"
	@ls generated/ 2>/dev/null || echo "  (none)"
else
	@python3 scripts/evaluate-generated-docs.py \
		generated/$(SECTION)/$(VERSION) \
		docs-corpus/ocp/$(VERSION)/$(SECTION) \
		--output=evaluation/$(SECTION)/$(VERSION)-fair-eval.md
endif

# Generate enhanced diffs (with full file contents) for a version pair.
# Only works for the installing section (uses generate-enhanced-diffs.py).
#
# Usage:
#   make enhanced-diffs FROM=4.16 TO=4.17
enhanced-diffs:
ifndef FROM
	@echo "Usage: make enhanced-diffs FROM=4.16 TO=4.17"
else ifndef TO
	@echo "Usage: make enhanced-diffs FROM=4.16 TO=4.17"
else
	@python3 scripts/generate-enhanced-diffs.py $(FROM) $(TO)
endif

# Generate diffs for the updating section.
#
# Usage:
#   make updating-diffs                # generates all version pairs
updating-diffs:
	@python3 scripts/generate-updating-diffs.py

# Generate ALL diffs for both sections and all version pairs (4.16→4.22).
#
# Usage:
#   make diffs                          # both sections, all versions
#   make diffs SECTION=installing       # installing only
#   make diffs SECTION=updating         # updating only
#
# This is the recommended way to regenerate diffs after a fresh clone.
# Requires source repos (run `make init` first).
diffs:
ifeq ($(SECTION),installing)
	@echo "=== Generating installing diffs (4.16 → 4.22) ==="
	@for pair in "4.16 4.17" "4.17 4.18" "4.18 4.19" "4.19 4.20" "4.20 4.21" "4.21 4.22"; do \
		set -- $$pair; \
		echo ""; echo "--- Installing: $$1 → $$2 ---"; \
		python3 scripts/generate-enhanced-diffs.py $$1 $$2; \
	done
	@echo ""; echo "=== Installing diffs complete ==="
else ifeq ($(SECTION),updating)
	@echo "=== Generating updating diffs (4.16 → 4.22) ==="
	@python3 scripts/generate-updating-diffs.py
	@echo ""; echo "=== Updating diffs complete ==="
else
	@echo "=== Generating ALL diffs for both sections (4.16 → 4.22) ==="
	@echo ""
	@echo "--- Installing section ---"
	@for pair in "4.16 4.17" "4.17 4.18" "4.18 4.19" "4.19 4.20" "4.20 4.21" "4.21 4.22"; do \
		set -- $$pair; \
		echo ""; echo "--- Installing: $$1 → $$2 ---"; \
		python3 scripts/generate-enhanced-diffs.py $$1 $$2; \
	done
	@echo ""
	@echo "--- Updating section ---"
	@python3 scripts/generate-updating-diffs.py
	@echo ""; echo "=== All diffs complete ==="
endif

# Extract docs for a section from openshift-docs.
#
# Usage:
#   make extract                        # both sections
#   make extract SECTION=installing
#   make extract SECTION=updating
extract:
ifeq ($(SECTION),installing)
	@bash scripts/extract-install-docs.sh
else ifeq ($(SECTION),updating)
	@bash scripts/extract-updating-docs.sh
else ifdef SECTION
	@echo "ERROR: No extraction script for section '$(SECTION)'"
	@echo "Available: installing, updating"
else
	@echo "=== Extracting docs for all sections ==="
	@bash scripts/extract-install-docs.sh
	@bash scripts/extract-updating-docs.sh
	@echo "=== All sections extracted ==="
endif

# Run the training loop for a section.
#
# Usage:
#   make train SECTION=installing              # all versions
#   make train SECTION=updating VERSION=4.17   # single version
train:
ifndef SECTION
	@echo "Usage: make train SECTION=installing|updating [VERSION=4.17]"
else ifdef VERSION
	@bash scripts/run-training-loop.sh $(SECTION) $(VERSION)
else
	@bash scripts/run-training-loop.sh $(SECTION)
endif

help:
	@echo "Available targets:"
	@echo ""
	@echo "  make init [SECTION=installing|updating]"
	@echo "    Clone required source repositories (run this first)"
	@echo ""
	@echo "  make extract [SECTION=installing|updating]"
	@echo "    Extract docs from openshift-docs repo (auto-clones if needed)"
	@echo "    Defaults to both sections if SECTION is not specified"
	@echo ""
	@echo "  make diffs [SECTION=installing|updating]"
	@echo "    Generate ALL code diffs for both sections, all versions (4.16-4.22)"
	@echo "    Requires source repos (run 'make init' first)"
	@echo ""
	@echo "  make enhanced-diffs FROM=4.16 TO=4.17"
	@echo "    Generate enhanced diffs for a single installing version pair"
	@echo ""
	@echo "  make updating-diffs"
	@echo "    Generate diffs for all updating version pairs"
	@echo ""
	@echo "  make compare VERSION=4.17 [SECTION=installing|updating] [PORT=9092]"
	@echo "    Launch the HTML comparison viewer"
	@echo ""
	@echo "  make score VERSION=4.17 [SECTION=installing|updating]"
	@echo "    Run deterministic scoring (difflib, file/section/param coverage)"
	@echo "    NOTE: This is NOT the LLM evaluation. For that, use prompts in"
	@echo "          tmp/ or tmp-updating/ in a separate agent window."
	@echo ""
	@echo "  make train SECTION=installing|updating [VERSION=4.17]"
	@echo "    Run the training loop (baseline copy + evaluate)"
	@echo ""
	@echo "  SECTION defaults to 'installing' if not specified"
	@echo ""
