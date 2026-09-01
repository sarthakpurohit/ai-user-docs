.PHONY: compare score enhanced-diffs diffs extract help

PORT ?= 9092
SECTION ?= installing

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

# Extract docs for a section from openshift-docs.
#
# Usage:
#   make extract SECTION=installing
#   make extract SECTION=updating
extract:
ifndef SECTION
	@echo "Usage: make extract SECTION=installing|updating"
else ifeq ($(SECTION),installing)
	@bash scripts/extract-install-docs.sh
else ifeq ($(SECTION),updating)
	@bash scripts/extract-updating-docs.sh
else
	@echo "ERROR: No extraction script for section '$(SECTION)'"
	@echo "Available: installing, updating"
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
	@echo "  make compare VERSION=4.17 [SECTION=installing|updating] [PORT=9092]"
	@echo "    Launch the HTML comparison viewer"
	@echo ""
	@echo "  make score VERSION=4.17 [SECTION=installing|updating]"
	@echo "    Run deterministic scoring (difflib, file/section/param coverage)"
	@echo "    NOTE: This is NOT the LLM evaluation. For that, use prompts in"
	@echo "          tmp/ or tmp-updating/ in a separate agent window."
	@echo ""
	@echo "  make enhanced-diffs FROM=4.16 TO=4.17"
	@echo "    Generate enhanced diffs for installing section"
	@echo ""
	@echo "  make updating-diffs"
	@echo "    Generate diffs for all updating version pairs"
	@echo ""
	@echo "  make extract SECTION=installing|updating"
	@echo "    Extract docs from openshift-docs repo"
	@echo ""
	@echo "  make train SECTION=installing|updating [VERSION=4.17]"
	@echo "    Run the training loop (baseline copy + evaluate)"
	@echo ""
	@echo "  SECTION defaults to 'installing' if not specified"
	@echo ""
