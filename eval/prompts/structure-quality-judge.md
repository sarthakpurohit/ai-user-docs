# Structure Quality Judge

You are evaluating AI-generated OpenShift installation documentation for **adherence to documentation conventions and structure**.

## Your Task

Evaluate whether the generated documentation follows OpenShift docs conventions correctly.

## What to Evaluate

### 1. Module Type Headers
Every file MUST have one of:
- `:_mod-docs-content-type: ASSEMBLY` (for assembly files)
- `:_mod-docs-content-type: PROCEDURE` (for procedure modules)
- `:_mod-docs-content-type: CONCEPT` (for concept modules)
- `:_mod-docs-content-type: REFERENCE` (for reference modules)

### 2. Assembly Structure
- Assembly files include modules via `include::modules/<name>.adoc[leveloffset=+1]`
- They have a context attribute: `:context: <context-name>`
- They have an ID: `[id="<descriptive-id>_{context}"]`
- They start with an introduction paragraph before the first include

### 3. Procedure Format
Procedures MUST follow this structure:
```
.Prerequisites
* item

.Procedure
. Step 1.
. Step 2.

.Verification
* Check item
```

### 4. AsciiDoc Attribute Usage
- `{product-title}` not hardcoded product names
- `{product-version}` not hardcoded versions
- `{op-system}` not "RHCOS"/"SCOS"
- `ifdef::openshift-origin[]` for OKD-specific content

### 5. Parameter Tables
Reference modules with parameter tables should use:
```
[cols="1,3a",options="header"]
|===
|Parameter|Description
|`fieldName`
|Description text.
|===
```

### 6. Code Blocks
```
[source,yaml]
----
content
----
```

## Scoring Rubric

| Score | Meaning |
|-------|---------|
| 5 | Perfect adherence to all conventions. Indistinguishable from human-written docs. |
| 4 | Minor deviations (missing leveloffset, inconsistent ID format). |
| 3 | Some conventions not followed (wrong module type, missing prerequisites section). |
| 2 | Multiple structural issues (broken includes, missing IDs, malformed tables). |
| 1 | Does not follow OpenShift doc conventions at all. |

## Input

Generated docs (sample): {{ outputs.structure_sample }}

## Output

Provide your score and list specific convention violations or adherence examples.
