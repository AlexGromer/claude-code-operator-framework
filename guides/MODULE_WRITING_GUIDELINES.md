# Module Writing Guidelines
# Version: 1.1.0 | Created: 2026-01-27 | Updated: 2026-02-04

---

## Purpose

This document defines standards for creating and maintaining Claude Code configuration modules. It ensures consistency, completeness, and quality across all modules in `~/.claude/modules/`.

**Audience:** Module authors, configuration maintainers, contributors

**Scope:** Structure, style, content requirements, review process

---

## Table of Contents

1. [Module Template](#1-module-template)
2. [Style Guide](#2-style-guide)
3. [Content Requirements](#3-content-requirements)
4. [Examples Integration](#4-examples-integration)
5. [Review Checklist](#5-review-checklist)
6. [Versioning & Updates](#6-versioning--updates)
7. [Anti-Patterns](#7-anti-patterns)
8. [Module vs Skill Decision](#8-module-vs-skill-decision)
9. [References](#9-references)

---

## 1. Module Template

### 1.1 File Structure

```markdown
# Module XX: [Title]
# Version: X.X.X | Created: YYYY-MM-DD

---

## Overview

[1-2 paragraph description of module purpose and scope]

**Key Features:**
- Feature 1
- Feature 2
- Feature 3

**Sources:** (if applicable)
- Source 1
- Source 2

---

## Table of Contents

1. [Section 1](#section-1)
2. [Section 2](#section-2)
...

---

## Section 1: [Section Title]

### 1.1 Subsection

[Content with examples, tables, code blocks]

### 1.2 Subsection

[Content]

---

## Section 2: [Section Title]

...

---

## References

- [Reference 1]
- [Reference 2]
```

### 1.2 Metadata Requirements

**File Naming:**
- Pattern: `XX-name.md` (e.g., `02-security.md`)
- Numbering: Sequential from 00
- Name: Lowercase, hyphen-separated

**Header Metadata:**
```markdown
# Module XX: [Descriptive Title]
# Version: X.X.X | Created: YYYY-MM-DD
```

**Version Format:** Semantic versioning (MAJOR.MINOR.PATCH)
- MAJOR: Breaking changes, structure overhaul
- MINOR: New sections, significant additions
- PATCH: Bug fixes, small improvements

### 1.3 Required Sections

Every module MUST include:

| Section | Purpose | Example |
|---------|---------|---------|
| **Overview** | High-level purpose, scope, key features | "This module covers..." |
| **Table of Contents** | Navigation with anchor links | `1. [Section](#section)` |
| **Core Content** | Main sections (2-8 sections recommended) | Numbered sections |
| **References** | Authoritative sources, documentation | Links, papers, standards |

Optional sections:
- **Prerequisites** - Required knowledge
- **Quick Start** - Minimal example
- **Anti-Patterns** - Common mistakes to avoid
- **Troubleshooting** - FAQ, known issues

---

## 2. Style Guide

### 2.1 Tone & Voice

**Writing Style:**
- ✅ **Active voice:** "Use this technique" (not "This technique can be used")
- ✅ **Imperative for instructions:** "Run the command" (not "You should run")
- ✅ **Declarative for facts:** "Claude supports tool use"
- ✅ **Direct and concise:** Prefer short sentences

**Language:**
- **Primary:** English (technical content)
- **Secondary:** Russian (user communication context in CLAUDE.md)
- **Mixed usage:** Acceptable in context-specific modules (e.g., Russian security platforms)

**Professional Tone:**
- Objective and factual
- No marketing language or superlatives
- Technical precision over colloquialisms
- Respectful of alternative approaches

### 2.2 Formatting Conventions

#### Headings

```markdown
# Module Title (H1) - only once
## Section (H2) - main sections
### Subsection (H3) - subdivisions
#### Sub-subsection (H4) - details
```

**Rules:**
- Max 4 heading levels (H1-H4)
- Use sentence case (not Title Case)
- Include anchor links in ToC

#### Code Blocks

````markdown
```language
code here
```
````

**Languages:** python, bash, yaml, json, markdown, typescript, go, rust

**Rules:**
- Always specify language for syntax highlighting
- Add comments for complex logic
- Keep examples minimal (5-15 lines ideal)
- Use real-world patterns, not toy examples

#### Tables

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
```

**Rules:**
- Use tables for comparisons, checklists, matrices
- Keep columns ≤5 for readability
- Left-align text, right-align numbers

#### Visual Diagrams (Box Drawing)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TITLE                                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Content                                                                     │
│  ├─► Sub-item 1                                                             │
│  ├─► Sub-item 2                                                             │
│  └─► Sub-item 3                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Use for:**
- Workflows (with arrows: →, ↓, ↑)
- Architecture diagrams
- Decision trees
- Taxonomies

**Character Set:**
```
Box: ┌─┐ │ ├─┤ └─┘
Arrows: → ↓ ↑ ←
Bullets: • ● ○ ▪ ▫
Status: ✅ ❌ ⚠️ 🔴 🟡 🟢 ⭕
```

#### Lists

**Unordered:**
```markdown
- Item 1
  - Nested item
- Item 2
```

**Ordered:**
```markdown
1. First step
2. Second step
   - Sub-step
```

**Checklists:**
```markdown
- [ ] Incomplete task
- [x] Completed task
```

#### Emphasis

- **Bold** (`**text**`): Key terms, warnings, priorities
- *Italic* (`*text*`): Emphasis, citations
- `Code` (`` `text` ``): Commands, variables, file names
- ~~Strikethrough~~ (`~~text~~`): Deprecated content

### 2.3 Content Organization

#### Section Length

| Section Type | Target Length | Max Length |
|--------------|---------------|------------|
| Overview | 50-150 words | 200 words |
| Subsection | 100-300 words | 500 words |
| Full section | 500-1500 words | 2500 words |
| Total module | 3k-8k words | 15k words |

**If exceeding limits:**
- Split into multiple modules
- Move details to separate guide
- Link to external documentation

#### Information Hierarchy

```
MODULE (file)
  ├─► SECTION 1 (H2)
  │     ├─► Subsection 1.1 (H3)
  │     │     ├─► Detail 1.1.1 (H4)
  │     │     └─► Detail 1.1.2 (H4)
  │     └─► Subsection 1.2 (H3)
  └─► SECTION 2 (H2)
        └─► ...
```

**Depth guidelines:**
- **Shallow modules** (2 levels): Quick reference, checklists
- **Medium modules** (3 levels): Most common, balanced depth
- **Deep modules** (4 levels): Complex domains (security, DevOps)

---

## 3. Content Requirements

### 3.1 Technical Accuracy

**Fact-Checking Protocol:**

| Content Type | Verification Required | Source |
|--------------|----------------------|--------|
| Commands/Syntax | Test execution | Run locally |
| API Endpoints | Documentation check | Official docs |
| Statistics | Citation required | Paper/report |
| Best Practices | Industry validation | Multiple sources |
| Tool Versions | Current version check | GitHub/website |

**Uncertainty Expression:**
- Use phrases from CLAUDE.md Section "Knowledge Boundaries"
- State training cutoff date (January 2025) for time-sensitive info
- Mark speculation explicitly: "Hypothesis:", "Possible approach:"

### 3.2 Completeness Criteria

**Minimum Coverage:**

```
✅ Problem Definition - What problem does this solve?
✅ Core Concepts - Essential terminology, principles
✅ Implementation - How to apply (patterns, examples)
✅ Tools & Technologies - Ecosystem, integrations
✅ Examples - At least 2 practical examples
✅ References - Authoritative sources
```

**Optional (add if applicable):**
- Anti-patterns (common mistakes)
- Troubleshooting (FAQ)
- Comparison tables (alternatives)
- Metrics/benchmarks (performance data)

### 3.3 Examples Quality

**Every module should include:**
- **2-3 inline examples** - Short snippets within sections
- **1-2 comprehensive examples** - End-to-end scenarios
- **Link to few-shot examples** - Reference `~/.claude/examples/[domain]/`

**Example Structure:**
```markdown
#### Example: [Title]

**Scenario:** [Context]

**Implementation:**
```python
# Code with comments
```

**Output:**
```
Expected result
```

**Explanation:** [Why this works]
```

### 3.4 Cross-References

**Linking Strategy:**

| Link Type | Format | Example |
|-----------|--------|---------|
| **Internal (same module)** | `[Text](#anchor)` | `[See Section 2](#section-2)` |
| **Module-to-module** | `[Text](XX-name.md#anchor)` | `[Security module](02-security.md#pentesting)` |
| **Module-to-CLAUDE.md** | `[Text](../CLAUDE.md#section)` | `[Core Identity](../CLAUDE.md#core-identity)` |
| **External** | `[Text](URL)` | `[OWASP Top 10](https://owasp.org)` |

**When to link:**
- Avoid redundancy - link instead of duplicating
- Create knowledge graph - connect related concepts
- Preserve context - reader shouldn't need to jump for basic understanding

---

## 4. Examples Integration

### 4.1 Inline vs. Separate Examples

**Inline examples** (within module):
- Use for: Quick demonstrations, syntax examples, simple patterns
- Length: 5-20 lines
- Format: Code block with explanation

**Separate examples** (`~/.claude/examples/`):
- Use for: Full workflows, multi-step scenarios, few-shot learning
- Length: 30-150 lines
- Format: See `EXAMPLE_WRITING_GUIDELINES.md`

### 4.2 Linking to Examples

**At end of relevant section:**
```markdown
**Examples:**
- [Example 1: Code Review](../examples/engineering/code_review.md)
- [Example 2: Security Audit](../examples/security/audit_workflow.md)
```

### 4.3 Example Coverage Matrix

Each domain should have examples for:

| Task Type | Priority | Examples Needed |
|-----------|----------|-----------------|
| **Common tasks** | P1 | 3-5 examples |
| **Specialized workflows** | P2 | 2-3 examples |
| **Advanced techniques** | P3 | 1-2 examples |

---

## 5. Review Checklist

### 5.1 Pre-Submission Checklist

**Structure:**
- [ ] File name follows `XX-name.md` convention
- [ ] Header includes version and creation date
- [ ] Table of Contents present with working anchor links
- [ ] All sections have H2/H3/H4 headings
- [ ] References section included

**Content:**
- [ ] Overview clearly states purpose
- [ ] Core concepts defined (no assumed knowledge)
- [ ] At least 2 practical examples included
- [ ] Technical accuracy verified (commands tested)
- [ ] Sources cited for statistics/claims
- [ ] No hallucinated facts (checked against documentation)

**Style:**
- [ ] Active voice used consistently
- [ ] Code blocks have language specified
- [ ] Tables formatted correctly
- [ ] Visual diagrams use box-drawing characters
- [ ] Consistent formatting (bold/italic/code)

**Quality:**
- [ ] No marketing language or superlatives
- [ ] Objective tone maintained
- [ ] Alternative approaches mentioned
- [ ] Edge cases documented
- [ ] Anti-patterns included (if applicable)

**Integration:**
- [ ] Cross-references to other modules
- [ ] Links to examples in `~/.claude/examples/`
- [ ] Mentioned in CLAUDE.md module table
- [ ] Git commit follows convention

### 5.2 Peer Review Questions

**For Reviewers:**

1. **Clarity:** Can someone unfamiliar with the domain understand this?
2. **Accuracy:** Are facts verifiable? Sources cited?
3. **Completeness:** Does it answer "what, why, how"?
4. **Practicality:** Can reader apply this immediately?
5. **Consistency:** Does it match style guide?

**Scoring Rubric:**

| Criteria | Weight | Score (1-5) |
|----------|--------|-------------|
| Technical Accuracy | 30% | ___ |
| Completeness | 25% | ___ |
| Clarity & Organization | 20% | ___ |
| Examples Quality | 15% | ___ |
| Style Compliance | 10% | ___ |
| **Total** | **100%** | **___** |

**Minimum score to merge:** 4.0/5.0 (80%)

### 5.3 Testing Protocol

**Before publishing:**

1. **Command Testing:**
   - Run all bash commands locally
   - Verify exit codes
   - Check output matches description

2. **Code Example Testing:**
   - Execute code snippets
   - Verify outputs
   - Test edge cases

3. **Link Validation:**
   - Check all internal links
   - Verify external URLs (200 OK)
   - Test anchor links

4. **Readability:**
   - Read aloud for flow
   - Check sentence length (<25 words avg)
   - Verify technical terms defined

---

## 6. Versioning & Updates

### 6.1 Version Bumping

**When to bump version:**

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| Typo fix, formatting | PATCH (X.X.+1) | 1.0.0 → 1.0.1 |
| New subsection, examples | MINOR (X.+1.0) | 1.0.1 → 1.1.0 |
| Major restructure, breaking changes | MAJOR (+1.0.0) | 1.1.0 → 2.0.0 |

**Commit message format:**
```bash
git commit -m "feat(module-XX): Add [feature]" # MINOR
git commit -m "fix(module-XX): Correct [error]" # PATCH
git commit -m "refactor(module-XX)!: Restructure" # MAJOR
```

### 6.2 Changelog Entry

**Add to module header:**
```markdown
# Module XX: Title
# Version: 1.2.0 | Created: 2026-01-20 | Updated: 2026-01-27

**Changelog:**
- **v1.2.0 (2026-01-27):** Added Section 5 (Advanced Patterns), 3 new examples
- **v1.1.0 (2026-01-25):** Enhanced Section 3, fixed command syntax
- **v1.0.0 (2026-01-20):** Initial release
```

### 6.3 Deprecation Policy

**If module content becomes obsolete:**

1. **Mark as deprecated** (add warning at top)
2. **Provide alternative** (link to replacement)
3. **Set sunset date** (keep for 3-6 months)
4. **Archive** (move to `~/.claude/archive/`)

**Deprecation Notice Format:**
```markdown
> ⚠️ **DEPRECATED:** This module is superseded by [Module YY](YY-new.md).
> Will be archived on YYYY-MM-DD.
```

---

## 7. Anti-Patterns

### 7.1 Common Mistakes

**❌ DON'T:**

1. **Over-Engineering:**
   ```markdown
   ❌ Creating 20-page module for simple concept
   ✅ Keep focused, link to external resources
   ```

2. **Marketing Language:**
   ```markdown
   ❌ "This amazing technique revolutionizes..."
   ✅ "This technique reduces latency by 40% (benchmark: ...)"
   ```

3. **Assumed Knowledge:**
   ```markdown
   ❌ "Use DAG for orchestration" (no definition)
   ✅ "Use DAG (Directed Acyclic Graph) for orchestration..."
   ```

4. **Outdated Information:**
   ```markdown
   ❌ "Python 3.6 is the latest version"
   ✅ "Python 3.13 as of January 2025 (verify current)"
   ```

5. **No Examples:**
   ```markdown
   ❌ Pure theory with no practical code
   ✅ Theory + 2-3 working examples
   ```

### 7.2 Style Violations

**Inconsistent formatting:**
```markdown
❌ Mixed heading levels (## then ####)
✅ Sequential (## then ### then ####)

❌ Code blocks without language
✅ ```python with syntax highlighting

❌ Tables with misaligned columns
✅ Properly formatted with | separators
```

### 7.3 Content Gaps

**Red flags during review:**
- No "Why" explanation (only "How")
- No troubleshooting section for complex topics
- No references to authoritative sources
- Untested commands/code
- No anti-patterns section

---

## 8. Module vs Skill Decision

### 8.1 When to Create Module vs Skill

| Характеристика контента | Module | Skill |
|------------------------|--------|-------|
| Справочная информация (WHAT) | ✅ | ❌ |
| Повторяющийся workflow (HOW) | ❌ | ✅ |
| Редко используемый (specialty) | ✅ | ❌ |
| Автоматизация задачи | ❌ | ✅ |
| Требует domain knowledge | ✅ | Skill + Module ref |

### 8.2 Module с Workflow = Кандидат на Skill

Если модуль содержит workflow (пошаговый процесс), рассмотрите извлечение в Skill:

```
modules/07-engineering.md Section 2.8 "Test Execution"
  ↓ Извлечь в
skills/run-tests/SKILL.md + reference к module
```

### 8.3 Reference Pattern

Skill должен ссылаться на Module для domain knowledge:

```markdown
## Reference
For detailed test patterns, see: modules/07-engineering.md Section 2.8
```

### 8.4 Decision Tree

```
Контент содержит повторяющийся workflow?
├─► НЕТ → Создать Module (справочник)
└─► ДА → Workflow автономный?
         ├─► ДА → Создать Skill
         └─► НЕТ → Skill + Module reference
```

**Подробнее:** См. `modules/15-skills.md` Section 11

---

## 9. References

### 9.1 Style Guides

- **Markdown:** [CommonMark Spec](https://commonmark.org/)
- **Technical Writing:** [Google Developer Documentation Style Guide](https://developers.google.com/style)
- **API Documentation:** [OpenAPI Specification](https://swagger.io/specification/)

### 9.2 Module Examples

**Exemplary modules (reference for quality):**
- `09-maturity.md` - Comprehensive structure, clear sections
- `12-prompting-reference.md` - Excellent taxonomy, visual diagrams
- `07-engineering.md` - Detailed templates, practical examples
- `15-skills.md` - Skills integration patterns

### 9.3 Tools

- **Markdown Preview:** VS Code, Typora, Obsidian
- **Link Checker:** `markdown-link-check`
- **Linter:** `markdownlint`
- **Diagrams:** ASCII box-drawing, Mermaid (for complex)

---

## Enforcement

**Violations of this guideline:**
- **P1 violations** (no testing, hallucinations): Block merge, require fixes
- **P2 violations** (formatting, style): Request changes, allow merge after corrections
- **P3 violations** (minor style): Note for future improvement

**Gap tracking:**
- Incomplete modules logged in `GAPS.md` (Category: Operational Protocols)
- Tracked until resolved

---

**Version:** 1.0.0
**Created:** 2026-01-27
**Resolves:** GAP-OP-011 (P1, Module Writing Guidelines)
**Related:** EXAMPLE_WRITING_GUIDELINES.md, GAP_WRITING_GUIDELINES.md
