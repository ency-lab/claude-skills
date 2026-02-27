---
name: codex-review
description: This skill should be used to ensure high-quality output and adherence to project standards. Invoke it at key milestones—after creating or updating plans in ./plans/, after major implementation steps (≥5 files changed, public API modified, or infra-config altered), and before commit/PR/release. It performs a structured review and outputs PASS, PASS WITH SUGGESTIONS, or REVISION REQUIRED, iterating until clean.
---

# Codex Review

## Overview

To enforce quality gates at critical milestones of any project. This skill performs structured code and plan reviews, checking consistency, completeness, readability, and API/infra safety.

## When to Invoke

Invoke this skill in the following situations:

1. **After creating or updating a plan** — any new or modified file under `./plans/`
2. **After major implementation steps** — when ≥5 files are changed, a public API is introduced/modified, or infra configs are altered
3. **Before commit, PR, or release** — as a final gate before sharing code with others

## Review Workflow

### Step 1: Context Analysis

To begin a review, gather context from three sources:

1. **Latest plan** — Read the most recently modified file under `./plans/`. If no plans directory exists, note this and proceed.
2. **Execution standards** — Read `.agent/PLANS.md` if it exists, to understand the project's base execution standards and architectural goals.
3. **Recent changes** — Run `git diff HEAD` (or `git diff --cached` for staged changes) to identify what has changed. If git is unavailable, ask which files were recently modified.

### Step 2: Apply Review Criteria

Evaluate the changes and plan against the following criteria:

#### Consistency
- Does the implementation align with the architectural goals described in `.agent/PLANS.md` and the active plan?
- Are naming conventions, file structure, and coding patterns consistent with the existing codebase?
- Do new APIs follow the same conventions as existing ones?

#### Completeness
- Are edge cases handled (empty inputs, network failures, unexpected file states)?
- Is error handling present at system boundaries (user input, external APIs, file I/O)?
- Are security implications considered (input validation, authentication, secrets management)?
- Does the implementation fully satisfy the requirements in the active plan?

#### Readability
- Is the code self-explanatory, or does complex logic include clarifying comments?
- Is documentation (SKILL.md, README, inline comments) accurate and current?
- Are variable and function names descriptive and unambiguous?

#### API/Infra Check
- If a public API has changed: Is backward compatibility maintained, or is the breaking change intentional and documented?
- If infra configs were changed: Are credentials, secrets, or access policies affected? Have defaults been set safely?
- If a new dependency was added: Is it justified and from a trusted source?

### Step 3: Output the Review Result

Output the result using one of three verdicts:

---

**PASS**
```
✅ PASS

All criteria met. No issues found.
```

---

**PASS WITH SUGGESTIONS**
```
✅ PASS WITH SUGGESTIONS

The implementation is acceptable, but consider the following optimizations:

Optimizations suggested:
- [Specific suggestion 1]
- [Specific suggestion 2]
```

---

**REVISION REQUIRED**
```
❌ REVISION REQUIRED

The following issues must be resolved before proceeding:

Fixes needed:
- [Critical issue 1 — file:line or area of concern]
- [Critical issue 2 — file:line or area of concern]

Please address these issues and re-run /codex-review.
```

---

### Step 4: Iterate

If the verdict is **REVISION REQUIRED**:
1. Wait for the user to acknowledge or ask Claude to fix the issues
2. After fixes are applied, re-run Steps 1–3 from scratch
3. Repeat until the verdict is **PASS** or **PASS WITH SUGGESTIONS**

Do not mark a review cycle as complete until a **PASS** or **PASS WITH SUGGESTIONS** verdict is reached.

## Review Scope Guidance

| Trigger | Minimum review scope |
|---|---|
| Plan created/updated | Step 1 (plans + PLANS.md) + Consistency check |
| ≥5 files changed | All criteria |
| Public API changed | All criteria, emphasis on API/Infra Check |
| Infra config changed | All criteria, emphasis on API/Infra Check |
| Before commit/PR/release | Full review (all criteria) |

## Notes

- If `.agent/PLANS.md` does not exist, skip the execution standards check and note its absence in the output.
- If `./plans/` is empty or absent, skip the plan consistency check.
- Focus review comments on actionable, specific issues — avoid vague feedback like "improve readability".
- Treat security issues (exposed secrets, missing auth, SQL injection risks) as always **REVISION REQUIRED**, regardless of other criteria.
