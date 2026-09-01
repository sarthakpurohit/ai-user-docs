#!/bin/bash
# Extract installation docs from openshift-docs for OCP and OKD versions 4.16-4.22.
# Uses git archive/show from remote branches to extract files without switching working tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_REPO="${BASE_DIR}/_repos/openshift-docs"
CORPUS_DIR="${BASE_DIR}/docs-corpus"
VERSIONS="4.16 4.17 4.18 4.19 4.20 4.21 4.22"

if [ ! -d "$DOCS_REPO/.git" ]; then
    echo "openshift-docs repo not found at ${DOCS_REPO}"
    echo "Cloning (bare checkout, this may take a few minutes)..."
    mkdir -p "$(dirname "$DOCS_REPO")"
    git clone --no-checkout https://github.com/openshift/openshift-docs.git "$DOCS_REPO"
fi

echo "Fetching latest branches..."
(cd "$DOCS_REPO" && git fetch --all --prune 2>/dev/null) || true

extract_version() {
    local version="$1"
    local branch="origin/enterprise-${version}"
    
    echo "=== Extracting version ${version} from ${branch} ==="
    
    cd "$DOCS_REPO"
    
    if ! git rev-parse --verify "$branch" >/dev/null 2>&1; then
        echo "  ERROR: Branch ${branch} not found, skipping"
        return 1
    fi
    
    local ocp_base="${CORPUS_DIR}/ocp/${version}"
    local ocp_dest="${ocp_base}/installing"
    rm -rf "$ocp_base"
    mkdir -p "$ocp_base"
    
    # Extract installing/ assemblies using git archive
    git archive "$branch" -- installing/ | tar -x -C "$ocp_base" 2>/dev/null || {
        echo "  WARNING: No installing/ directory in ${branch}"
        return 1
    }
    
    # Remove symlink files that git archive creates as regular files
    rm -f "$ocp_dest/modules" "$ocp_dest/_attributes" "$ocp_dest/images" "$ocp_dest/snippets" 2>/dev/null || true
    
    # Find which modules are referenced by installing assemblies
    local modules_list
    modules_list=$(grep -rh "include::modules/" "$ocp_dest" 2>/dev/null | \
        sed 's/.*include::modules\///' | sed 's/\[.*//' | sort -u) || true
    
    # Extract referenced modules
    if [ -n "$modules_list" ]; then
        mkdir -p "$ocp_dest/modules"
        local mod_count=0
        echo "$modules_list" | while read -r mod; do
            if [ -n "$mod" ]; then
                git show "${branch}:modules/${mod}" > "$ocp_dest/modules/${mod}" 2>/dev/null || true
            fi
        done
        mod_count=$(find "$ocp_dest/modules" -name "*.adoc" 2>/dev/null | wc -l)
    fi
    
    # Extract common attributes
    mkdir -p "$ocp_dest/_attributes"
    git show "${branch}:_attributes/common-attributes.adoc" > "$ocp_dest/_attributes/common-attributes.adoc" 2>/dev/null || true
    
    # Extract topic map (installation section)
    git show "${branch}:_topic_maps/_topic_map.yml" > "$ocp_dest/_topic_map.yml" 2>/dev/null || true
    
    # OKD extraction (same source content -- OKD vs OCP is via conditionals/attributes)
    local okd_base="${CORPUS_DIR}/okd/${version}"
    rm -rf "$okd_base"
    mkdir -p "$(dirname "$okd_base")"
    cp -r "$ocp_base" "$okd_base"
    
    # Count
    local asm_count mod_count_final
    asm_count=$(find "$ocp_dest" -maxdepth 2 -name "*.adoc" -not -path "*/modules/*" -not -path "*/_attributes/*" | wc -l)
    mod_count_final=$(find "$ocp_dest/modules" -name "*.adoc" 2>/dev/null | wc -l)
    echo "  Extracted ${asm_count} assembly files + ${mod_count_final} modules for version ${version}"
}

echo "Starting installation docs extraction..."
echo "Docs repo: ${DOCS_REPO}"
echo "Output: ${CORPUS_DIR}"
echo ""

for ver in $VERSIONS; do
    extract_version "$ver"
    echo ""
done

echo "=== Extraction complete ==="
echo ""
echo "Summary:"
for ver in $VERSIONS; do
    ocp_asm=$(find "${CORPUS_DIR}/ocp/${ver}/installing" -maxdepth 2 -name "*.adoc" -not -path "*/modules/*" -not -path "*/_attributes/*" 2>/dev/null | wc -l)
    ocp_mod=$(find "${CORPUS_DIR}/ocp/${ver}/installing/modules" -name "*.adoc" 2>/dev/null | wc -l)
    echo "  ${ver}: ${ocp_asm} assemblies, ${ocp_mod} modules"
done
