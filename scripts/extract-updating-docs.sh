#!/bin/bash
# Extract updating section docs from openshift-docs for versions 4.16-4.22
# Stores into docs-corpus/ocp/<version>/updating/

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_REPO="${BASE_DIR}/_repos/openshift-docs"
CORPUS_BASE="${BASE_DIR}/docs-corpus/ocp"

if [ ! -d "$DOCS_REPO/.git" ]; then
    echo "openshift-docs repo not found at ${DOCS_REPO}"
    echo "Cloning (bare checkout, this may take a few minutes)..."
    mkdir -p "$(dirname "$DOCS_REPO")"
    git clone --no-checkout https://github.com/openshift/openshift-docs.git "$DOCS_REPO"
fi

echo "Fetching latest branches..."
(cd "$DOCS_REPO" && git fetch --all --prune 2>/dev/null) || true

VERSIONS="4.16 4.17 4.18 4.19 4.20 4.21 4.22"

for VERSION in $VERSIONS; do
    BRANCH="origin/enterprise-${VERSION}"
    DEST="${CORPUS_BASE}/${VERSION}/updating"
    
    echo "=== Extracting updating docs for ${VERSION} from ${BRANCH} ==="
    
    # Clean destination
    rm -rf "$DEST"
    mkdir -p "$DEST"
    
    # Extract assemblies from updating/ directory
    cd "$DOCS_REPO"
    
    # Get the list of .adoc files in updating/ (assemblies)
    ASSEMBLY_FILES=$(git ls-tree -r --name-only "$BRANCH" -- updating/ 2>/dev/null | grep '\.adoc$' | grep -v '^updating/modules/' | grep -v '^updating/_attributes/' | grep -v '^updating/snippets/' | grep -v '^updating/images/')
    
    if [ -z "$ASSEMBLY_FILES" ]; then
        echo "  WARNING: No assembly files found in updating/ for ${BRANCH}"
        continue
    fi
    
    # Extract each assembly
    for f in $ASSEMBLY_FILES; do
        # Create parent directories
        RELATIVE="${f#updating/}"
        mkdir -p "$DEST/$(dirname "$RELATIVE")"
        git show "${BRANCH}:${f}" > "$DEST/$RELATIVE" 2>/dev/null || echo "  WARN: Could not extract $f"
    done
    
    # Extract relevant modules (those referenced by the assemblies)
    mkdir -p "$DEST/modules"
    
    # Find all module includes from the assemblies
    MODULE_NAMES=$(grep -rh "^include::modules/" "$DEST/" 2>/dev/null | sed 's/include::modules\///' | sed 's/\[.*//' | sort -u)
    
    for mod in $MODULE_NAMES; do
        git show "${BRANCH}:modules/${mod}" > "$DEST/modules/${mod}" 2>/dev/null || echo "  WARN: Could not extract modules/$mod"
    done
    
    # Extract _attributes/common-attributes.adoc
    mkdir -p "$DEST/_attributes"
    git show "${BRANCH}:_attributes/common-attributes.adoc" > "$DEST/_attributes/common-attributes.adoc" 2>/dev/null || true
    
    # Count files
    ASSEMBLY_COUNT=$(find "$DEST" -maxdepth 2 -name "*.adoc" ! -path "*/modules/*" ! -path "*/_attributes/*" | wc -l)
    MODULE_COUNT=$(find "$DEST/modules" -name "*.adoc" 2>/dev/null | wc -l)
    
    echo "  Extracted: ${ASSEMBLY_COUNT} assemblies, ${MODULE_COUNT} modules"
    echo ""
done

echo "Done! All versions extracted."
