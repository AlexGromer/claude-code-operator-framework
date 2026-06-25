# Domain Proposal Template
# Copy this file and fill in the sections

## Domain Information

| Field | Value |
|-------|-------|
| **Domain Name** | [lowercase-hyphenated] |
| **Module Number** | XX (see naming convention) |
| **Proposed By** | [name/role] |
| **Date** | YYYY-MM-DD |
| **Gap ID** | GAP-DOM-XXX |

---

## 1. Purpose & Scope

### 1.1 Description
[2-3 sentences describing what this domain covers]

### 1.2 Problem Statement
[What problem does this domain solve?]

### 1.3 Scope Boundaries
**Includes:**
- [topic 1]
- [topic 2]

**Excludes:**
- [out of scope topic 1]
- [out of scope topic 2]

---

## 2. CLI Relevance Scoring

| Factor | Score (0-100) | Weight | Weighted |
|--------|---------------|--------|----------|
| Direct CLI usage | [0-100] | 40% | [calc] |
| Automation potential | [0-100] | 25% | [calc] |
| Cross-domain value | [0-100] | 20% | [calc] |
| User demand | [0-100] | 15% | [calc] |
| **TOTAL** | — | 100% | **[sum]** |

**Threshold:** ≥60 required for approval

### Justification
[Explain why scores are assigned]

---

## 3. Use Cases

### Use Case 1: [Title]
**Scenario:** [description]
**CLI Tasks:**
- [task 1]
- [task 2]

### Use Case 2: [Title]
**Scenario:** [description]
**CLI Tasks:**
- [task 1]
- [task 2]

### Use Case 3: [Title]
**Scenario:** [description]
**CLI Tasks:**
- [task 1]
- [task 2]

---

## 4. Dependencies & Overlaps

### 4.1 Related Domains
| Domain | Relationship | Action |
|--------|--------------|--------|
| [domain 1] | [complement/overlap/depends] | [cross-reference/merge/none] |
| [domain 2] | [complement/overlap/depends] | [cross-reference/merge/none] |

### 4.2 Overlap Check
```bash
# Results of overlap search:
grep -r "[keyword]" ~/.claude/modules/
# [paste results or "No significant overlap"]
```

### 4.3 External Dependencies
- [tool/framework 1]
- [tool/framework 2]

---

## 5. Resource Estimate

| Task | Effort | Complexity |
|------|--------|------------|
| Module creation | [X]h | [Low/Medium/High] |
| Examples (≥3) | [X]h | [Low/Medium/High] |
| Integration | [X]h | [Low/Medium/High] |
| Documentation | [X]h | [Low/Medium/High] |
| **TOTAL** | **[sum]h** | — |

---

## 6. Proposed Structure

```markdown
# Module: [Domain Name]
# Version: 1.0.0

## Section 1: [Topic]
## Section 2: [Topic]
## Section 3: [Topic]
## Few-Shot Examples
## Integration
```

---

## 7. Approval

| Reviewer | Decision | Date |
|----------|----------|------|
| [name] | ☐ Approve / ☐ Reject / ☐ Revise | YYYY-MM-DD |

**Comments:**
[reviewer feedback]

---

## Checklist

```
☐ Domain name follows convention
☐ CLI relevance ≥60
☐ ≥3 use cases provided
☐ Overlap check completed
☐ Dependencies identified
☐ Resource estimate provided
☐ Gap ID assigned
```
