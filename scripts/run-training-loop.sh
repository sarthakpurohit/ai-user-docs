#!/bin/bash
# Orchestrates the iterative training loop for doc generation skills.
# Supports multiple sections (installing, updating, etc.)
#
# Usage:
#   ./run-training-loop.sh <section> [version]
#
# Examples:
#   ./run-training-loop.sh installing          # all versions for installing
#   ./run-training-loop.sh installing 4.17     # single version
#   ./run-training-loop.sh updating            # all versions for updating
#   ./run-training-loop.sh updating 4.18       # single version

set -euo pipefail

BASE_DIR="/home/sapurohi/Desktop/Agentic OKD docs"
CORPUS_DIR="${BASE_DIR}/docs-corpus"
EVAL_SCRIPT="${BASE_DIR}/scripts/evaluate-generated-docs.py"

VERSIONS=(4.17 4.18 4.19 4.20 4.21 4.22)
PREV_VERSIONS=(4.16 4.17 4.18 4.19 4.20 4.21)

# Parse section argument
SECTION="${1:-}"
if [ -z "$SECTION" ]; then
    echo "Usage: $0 <section> [version]"
    echo ""
    echo "Sections available:"
    ls "${BASE_DIR}/skills/" | grep "generate-" | sed 's/generate-/  /' | sed 's/-docs//'
    exit 1
fi

# Resolve paths based on section
DIFFS_DIR="${BASE_DIR}/diffs/${SECTION}"
EVAL_DIR="${BASE_DIR}/evaluation/${SECTION}"
SKILL_FILE="${BASE_DIR}/skills/generate-${SECTION}-docs/SKILL.md"
GENERATED_BASE="${BASE_DIR}/generated/${SECTION}"

if [ ! -f "$SKILL_FILE" ]; then
    echo "ERROR: Skill file not found: ${SKILL_FILE}"
    exit 1
fi

echo "=== ${SECTION^} Docs Generation Training Loop ==="
echo ""
echo "Section: ${SECTION}"
echo "Skill file: ${SKILL_FILE}"
echo "Corpus: ${CORPUS_DIR}/ocp/*/\${SECTION}"
echo "Diffs: ${DIFFS_DIR}"
echo "Evaluation output: ${EVAL_DIR}"
echo ""

mkdir -p "${EVAL_DIR}"

# If a specific version is passed as second argument, only process that one
if [ "${2:-}" != "" ]; then
    TARGET_VER="$2"
    found=false
    for i in "${!VERSIONS[@]}"; do
        if [ "${VERSIONS[$i]}" == "$TARGET_VER" ]; then
            VERSIONS=("${VERSIONS[$i]}")
            PREV_VERSIONS=("${PREV_VERSIONS[$i]}")
            found=true
            break
        fi
    done
    if [ "$found" == "false" ]; then
        echo "ERROR: Version $TARGET_VER not in supported range (4.17-4.22)"
        exit 1
    fi
fi

for i in "${!VERSIONS[@]}"; do
    ver="${VERSIONS[$i]}"
    prev="${PREV_VERSIONS[$i]}"
    
    echo "================================================================"
    echo "  ITERATION: Generate ${SECTION} ${ver} docs from ${prev} + diff"
    echo "================================================================"
    echo ""
    
    PREV_DOCS="${CORPUS_DIR}/ocp/${prev}/${SECTION}"
    DIFF_FILE="${DIFFS_DIR}/${prev}-to-${ver}/combined-diff-${prev}-to-${ver}.md"
    ACTUAL_DOCS="${CORPUS_DIR}/ocp/${ver}/${SECTION}"
    GENERATED_DIR="${GENERATED_BASE}/${ver}"
    EVAL_REPORT="${EVAL_DIR}/${ver}-fair-eval.md"
    
    # Verify inputs exist
    if [ ! -d "$PREV_DOCS" ]; then
        echo "  ERROR: Previous docs not found: ${PREV_DOCS}"
        continue
    fi
    if [ ! -f "$DIFF_FILE" ]; then
        echo "  WARNING: Diff file not found: ${DIFF_FILE}"
        echo "  (You may need to run the diff generation script first)"
    fi
    if [ ! -d "$ACTUAL_DOCS" ]; then
        echo "  ERROR: Actual docs not found: ${ACTUAL_DOCS}"
        continue
    fi
    
    echo "  Inputs:"
    echo "    Previous docs (${prev}): ${PREV_DOCS}"
    echo "    Code diff: ${DIFF_FILE}"
    echo "    Actual docs (${ver}): ${ACTUAL_DOCS}"
    echo ""
    
    # Step 1: Generate docs (LLM step — prepare baseline)
    echo "  Step 1: Preparing generation baseline..."
    rm -rf "$GENERATED_DIR"
    mkdir -p "$GENERATED_DIR"
    
    cp -r --no-preserve=context "${PREV_DOCS}/"* "$GENERATED_DIR/" 2>/dev/null || true
    
    echo "    Baseline copied (${prev} docs → generated/${SECTION}/${ver})"
    echo ""
    echo "  NOTE: Run the LLM with SKILL.md to apply diff changes to the baseline."
    echo "    Skill: ${SKILL_FILE}"
    echo "    Input docs: ${PREV_DOCS}"
    echo "    Diff: ${DIFF_FILE}"
    echo "    Output: ${GENERATED_DIR}"
    echo ""
    
    # Step 2: Evaluate (compare generated against actual)
    echo "  Step 2: Evaluating generated docs against ground truth..."
    
    if [ -d "$GENERATED_DIR" ] && [ "$(ls -A $GENERATED_DIR 2>/dev/null)" ]; then
        python3 "$EVAL_SCRIPT" "$GENERATED_DIR" "$ACTUAL_DOCS" --output="$EVAL_REPORT"
        echo "    Report: ${EVAL_REPORT}"
    else
        echo "    SKIP: No generated content to evaluate."
    fi
    
    echo ""
    echo "  Step 3: Review ${EVAL_REPORT} and update ${SKILL_FILE}"
    echo "  Step 4: Save snapshot → skills/snapshots/${SECTION}/after-${ver}/SKILL.md"
    echo ""
    echo "---"
    echo ""
done

echo "Training loop complete for section: ${SECTION}"
echo ""
echo "Next steps:"
echo "  1. Review evaluation reports in ${EVAL_DIR}/"
echo "  2. Update skill: ${SKILL_FILE}"
echo "  3. Save snapshot: cp ${SKILL_FILE} ${BASE_DIR}/skills/snapshots/${SECTION}/after-<ver>/SKILL.md"
