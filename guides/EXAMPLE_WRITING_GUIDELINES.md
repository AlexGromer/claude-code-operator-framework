# Example Writing Guidelines
# Version: 1.0.0 | Created: 2026-01-27

---

## Purpose

This document defines standards for creating few-shot examples in `~/.claude/examples/`. Examples train Claude on domain-specific patterns, workflows, and response quality.

**Audience:** Example authors, domain experts, contributors

**Scope:** Structure, quality criteria, review process, prompt engineering best practices

---

## Table of Contents

1. [Example Template](#1-example-template)
2. [Quality Rubric](#2-quality-rubric)
3. [Domain-Specific Guidelines](#3-domain-specific-guidelines)
4. [Prompt Engineering Integration](#4-prompt-engineering-integration)
5. [Review Checklist](#5-review-checklist)
6. [Anti-Patterns](#6-anti-patterns)
7. [References](#7-references)

---

## 1. Example Template

### 1.1 File Structure

```markdown
# Few-Shot Example: [Descriptive Title]

**Domain:** [Security/DevOps/Engineering/Education/Writing/Planning/etc.]
**Task Type:** [Code Review/Debugging/Documentation/Architecture/etc.]
**Complexity:** [Low/Medium/High]

---

## User Request

[Realistic user query - verbatim style]

## Claude Response

[Structured, high-quality response demonstrating best practices]

---

## Key Takeaways

[2-5 bullet points highlighting patterns to learn]
```

### 1.2 Metadata Fields

#### Domain

Primary domains (align with modules):
- **Security** - Pentesting, vulnerability analysis, threat modeling
- **DevOps** - Infrastructure, CI/CD, containerization
- **Engineering** - Software design, testing, architecture
- **Education** - Teaching, curriculum, CTF design
- **Writing** - Documentation, papers, technical writing
- **Planning** - Project management, estimation, OKRs
- **Low-Level** - Systems programming, kernel, embedded
- **Common** - General tasks, code review, debugging

**Multi-domain examples:**
```markdown
**Domain:** Security + DevOps
**Task Type:** Kubernetes Security Audit
```

#### Task Type

Common task types by domain:

| Domain | Task Types |
|--------|------------|
| **Security** | Vulnerability analysis, exploit development, security audit, threat modeling, incident response |
| **DevOps** | Infrastructure provisioning, CI/CD setup, container orchestration, monitoring setup, disaster recovery |
| **Engineering** | Code review, refactoring, architecture design, testing strategy, API design |
| **Education** | Concept explanation, tutorial creation, CTF challenge design, skill assessment |
| **Writing** | Technical documentation, academic paper, API docs, user guide |
| **Planning** | Effort estimation, roadmap creation, OKR definition, sprint planning |

#### Complexity

**Complexity Levels:**

| Level | Characteristics | Example |
|-------|-----------------|---------|
| **Low** | Single-file, <50 lines, 1-2 concepts, <10 min to solve | Fix typo, simple function, single command |
| **Medium** | Multi-file, 50-200 lines, 3-5 concepts, 10-30 min to solve | Code review, debug multi-step issue, small refactor |
| **High** | Multi-file/system, >200 lines, 6+ concepts, >30 min to solve | Architecture design, security audit, full feature implementation |

### 1.3 Example Length

**Target lengths by complexity:**

| Complexity | User Request | Claude Response | Total |
|------------|--------------|-----------------|-------|
| **Low** | 20-100 words | 200-500 words | ~500 words |
| **Medium** | 50-200 words | 500-1500 words | ~1500 words |
| **High** | 100-500 words | 1500-4000 words | ~4000 words |

**If exceeding limits:**
- Split into multiple examples (Part 1/2)
- Focus on critical patterns
- Link to external documentation

---

## 2. Quality Rubric

### 2.1 Scoring Criteria

**Rate each criterion 1-5:**

| Criteria | Weight | Description | Score |
|----------|--------|-------------|-------|
| **Realism** | 25% | User request is authentic, real-world scenario | ___ |
| **Clarity** | 20% | Response is clear, well-structured, easy to follow | ___ |
| **Completeness** | 20% | All aspects of request addressed, edge cases considered | ___ |
| **Best Practices** | 20% | Demonstrates domain expertise, follows standards | ___ |
| **Actionability** | 15% | Reader can apply immediately, code works | ___ |
| **Total** | **100%** | **Minimum: 4.0/5.0 (80%)** | **___** |

### 2.2 Quality Thresholds

**Example approval criteria:**

| Score Range | Status | Action |
|-------------|--------|--------|
| **4.5-5.0** | ⭐ Exemplary | Publish, feature as reference |
| **4.0-4.4** | ✅ Good | Publish as-is |
| **3.5-3.9** | 🟡 Needs Work | Revise and resubmit |
| **<3.5** | ❌ Reject | Major rewrite required |

### 2.3 Detailed Scoring Guide

#### Realism (25%)

**5/5 - Excellent:**
- Real-world scenario from actual work
- Natural user language (not over-specified)
- Includes context/constraints
- Authentic complexity

**3/5 - Acceptable:**
- Plausible but simplified
- Somewhat artificial phrasing
- Missing some context

**1/5 - Poor:**
- Toy problem with no real use
- Overly contrived setup
- Template-like language

**Example comparison:**
```markdown
❌ 1/5: "Write a function to add two numbers"
✅ 3/5: "Write a function to calculate shipping cost"
⭐ 5/5: "Our e-commerce app needs shipping calculation that accounts for weight tiers,
        destination zones, and bulk discounts. Current code has edge case bugs."
```

#### Clarity (20%)

**5/5 - Excellent:**
- Logical structure (problem → analysis → solution)
- Clear section headings
- Progressive complexity
- No jargon without definition

**3/5 - Acceptable:**
- Organized but could be clearer
- Some sections hard to follow
- Minor structural issues

**1/5 - Poor:**
- Disorganized stream of consciousness
- No clear structure
- Jumps between topics

#### Completeness (20%)

**5/5 - Excellent:**
- All requirements addressed
- Edge cases documented
- Alternatives discussed
- Limitations acknowledged

**3/5 - Acceptable:**
- Main requirements covered
- Some edge cases missed
- Brief alternative mention

**1/5 - Poor:**
- Partial solution only
- Ignores constraints
- No edge case handling

#### Best Practices (20%)

**5/5 - Excellent:**
- Follows industry standards
- Security considerations included
- Performance implications discussed
- Maintainability prioritized

**3/5 - Acceptable:**
- Mostly follows best practices
- Some shortcuts acceptable for clarity
- Basic quality standards met

**1/5 - Poor:**
- Anti-patterns present
- Security vulnerabilities
- No consideration for production

#### Actionability (15%)

**5/5 - Excellent:**
- Code runs without modification
- Step-by-step instructions
- Prerequisites documented
- Testable immediately

**3/5 - Acceptable:**
- Code mostly works
- Minor modifications needed
- Basic guidance provided

**1/5 - Poor:**
- Pseudocode only
- Missing critical steps
- Cannot be executed

---

## 3. Domain-Specific Guidelines

### 3.1 Security Examples

**Required elements:**
- Scope verification (authorization, legal compliance)
- Risk assessment (impact analysis)
- Evidence documentation (screenshots, logs)
- Remediation recommendations

**Ethical considerations:**
```markdown
## Security Example Template

### Scope Verification
- Authorization: [Yes/No, document reference]
- Targets: [Explicit list]
- Out-of-scope: [Exclusions]

### Analysis
[Vulnerability details]

### Impact
| Dimension | Rating | Justification |
|-----------|--------|---------------|
| Confidentiality | High/Med/Low | |
| Integrity | High/Med/Low | |
| Availability | High/Med/Low | |

### Remediation
[Actionable fixes]
```

**Do NOT include:**
- Exploit code for CVEs without disclosure
- Full credentials or API keys
- Attack scripts for production systems

### 3.2 DevOps Examples

**Required elements:**
- Infrastructure-as-Code (prefer declarative)
- Idempotency verification
- Rollback strategy
- Observability integration

**Best practices:**
```markdown
## DevOps Example Template

### Infrastructure
[Terraform/Ansible/Kubernetes manifests]

### Deployment
[Step-by-step with verification]

### Monitoring
[Metrics, logs, alerts]

### Rollback
[How to revert if failed]
```

**Include:**
- Cost implications (if cloud)
- Security hardening
- Disaster recovery notes

### 3.3 Engineering Examples

**Required elements:**
- Requirements analysis
- Design decisions (with alternatives)
- Testing strategy
- Documentation

**Code quality standards:**
```markdown
## Engineering Example Template

### Requirements
[Functional + non-functional]

### Design
[Architecture, patterns, trade-offs]

### Implementation
[Code with inline comments]

### Tests
[Unit, integration, coverage]

### Documentation
[API docs, usage examples]
```

**Include:**
- Performance characteristics (Big-O)
- Thread safety considerations
- Error handling strategy

### 3.4 Education Examples

**Required elements:**
- Learning objectives
- Scaffolding (beginner → advanced)
- Common misconceptions addressed
- Practice exercises

**Pedagogical structure:**
```markdown
## Education Example Template

### Learning Objectives
- Students will be able to...

### Explanation
[Concept introduction with analogy]

### Example
[Worked example with annotations]

### Common Mistakes
[Pitfalls and corrections]

### Practice
[Exercise for student]
```

**Include:**
- Prerequisite knowledge
- Difficulty progression
- Assessment criteria

---

## 4. Prompt Engineering Integration

### 4.1 Few-Shot Learning Principles

Examples are used for **in-context learning** - Claude learns patterns from examples.

**Effective few-shot examples:**
1. **Diverse scenarios** - Cover common + edge cases
2. **Consistent format** - Same structure across examples
3. **Progressive complexity** - Easy → Medium → Hard
4. **Pattern highlighting** - Make key techniques obvious

### 4.2 Prompting Techniques (Module 11 Integration)

**Techniques to demonstrate in examples:**

| Technique | Use In Examples | Effectiveness |
|-----------|-----------------|---------------|
| **Chain-of-Thought (CoT)** | Show step-by-step reasoning | ⭐⭐⭐⭐⭐ Critical |
| **ReAct (Reason+Act)** | Demonstrate tool use with reasoning | ⭐⭐⭐⭐⭐ Critical |
| **Self-Consistency** | Show verification steps | ⭐⭐⭐⭐ High |
| **Least-to-Most** | Break complex problems | ⭐⭐⭐⭐ High |
| **Self-Refinement** | Show iteration/improvement | ⭐⭐⭐ Medium |

**Example incorporating CoT:**
```markdown
## Claude Response

Let me analyze this step-by-step:

**Step 1: Understand Requirements**
- Input: User data (name, age)
- Output: Filtered list of adults
- Constraint: Handle missing data

**Step 2: Identify Issues**
- Current code uses dict access → KeyError risk
- No validation → crash on None input

**Step 3: Design Solution**
- Use .get() with defaults
- Add type hints
- Validate input at boundary

**Step 4: Implementation**
[Code with fixes]
```

### 4.3 Response Structure Patterns

**Standard response format (adapt per domain):**

```markdown
## Claude Response

### [1. Understanding/Analysis]
[Parse request, identify requirements, state assumptions]

### [2. Planning/Design]
[Approach, alternatives considered, chosen solution]

### [3. Implementation]
[Code/commands/configuration]

### [4. Verification/Testing]
[How to test, expected output, edge cases]

### [5. Recommendations/Next Steps]
[Optional improvements, related considerations]
```

**Length by section:**
- Understanding: 10-15% of response
- Planning: 15-20%
- Implementation: 40-50%
- Verification: 15-20%
- Recommendations: 5-10%

### 4.4 Key Takeaways Section

**Purpose:** Explicit pattern extraction for learning

**Format:**
```markdown
## Key Takeaways

- **Pattern 1:** [Specific technique demonstrated]
  - Example: "Always validate input at system boundaries"
- **Pattern 2:** [Decision-making criterion]
  - Example: "Prefer composition over inheritance for flexibility"
- **Pattern 3:** [Domain-specific best practice]
  - Example: "Run secrets detection before git commit"
```

**Guidelines:**
- 2-5 takeaways per example
- Specific, not generic ("Use .get()" vs "Write good code")
- Actionable and memorable

---

## 5. Review Checklist

### 5.1 Pre-Submission Checklist

**Metadata:**
- [ ] Domain correctly categorized
- [ ] Task type clearly defined
- [ ] Complexity level appropriate

**Content:**
- [ ] User request is realistic and well-scoped
- [ ] Claude response demonstrates best practices
- [ ] All code examples tested and working
- [ ] Key takeaways section included (2-5 points)

**Quality:**
- [ ] Follows domain-specific template (if applicable)
- [ ] Demonstrates at least one prompting technique (CoT, ReAct, etc.)
- [ ] Includes error handling and edge cases
- [ ] Security/safety considerations addressed

**Style:**
- [ ] Clear section headings
- [ ] Code blocks have language specified
- [ ] Consistent formatting (bold/italic/code)
- [ ] Professional tone (no marketing language)

**Integration:**
- [ ] Referenced in relevant module
- [ ] File path follows convention (`domain/task_type.md`)
- [ ] Git commit message descriptive

### 5.2 Peer Review Protocol

**Reviewer responsibilities:**

1. **Run the code/commands**
   - Verify examples execute correctly
   - Check outputs match description
   - Test edge cases

2. **Assess realism**
   - Is this a real-world scenario?
   - Would users actually ask this?
   - Is complexity appropriate?

3. **Evaluate learning value**
   - Are patterns clear?
   - Could reader replicate approach?
   - Do takeaways highlight key lessons?

4. **Score using rubric (Section 2.1)**
   - Rate each criterion 1-5
   - Calculate weighted score
   - Approve if ≥4.0/5.0

### 5.3 Testing Requirements

**Required tests by example type:**

| Example Type | Testing Required | Tools |
|--------------|------------------|-------|
| **Code** | Execute code, verify output | pytest, unittest, manual |
| **Infrastructure** | Dry-run or sandbox deploy | terraform plan, --check flag |
| **Commands** | Run locally, check exit codes | bash, manual testing |
| **Documentation** | Render and review | markdown preview |

**Test documentation:**
```markdown
## Testing Notes (internal, not in published example)

**Environment:** Python 3.13, Ubuntu 22.04
**Date:** 2026-01-27
**Tester:** [Name]
**Results:**
- Code executed successfully: ✅
- Output matched expected: ✅
- Edge cases tested: ✅ (None input, empty list)
```

---

## 6. Anti-Patterns

### 6.1 Common Mistakes

**❌ DON'T:**

1. **Toy Problems:**
   ```markdown
   ❌ "Write a function to print 'Hello World'"
   ✅ "Write a CLI tool for log parsing with filtering"
   ```

2. **Over-Specification:**
   ```markdown
   ❌ "Create a class named UserManager with methods add_user,
       delete_user, and update_user taking parameters..."
   ✅ "Our app needs user management. Currently using a dict,
       but need better structure as we add features."
   ```

3. **Perfect Code Only:**
   ```markdown
   ❌ Only showing flawless final solution
   ✅ Show analysis of flawed code → improvements
   ```

4. **No Context:**
   ```markdown
   ❌ "Fix this bug: [code]"
   ✅ "Our e-commerce checkout fails for users with coupons.
       Error: KeyError on 'discount'. Code: [...]"
   ```

5. **Missing Takeaways:**
   ```markdown
   ❌ Example ends with code
   ✅ Example ends with "Key Takeaways" section
   ```

### 6.2 Quality Issues

**Red flags during review:**

| Issue | Impact | Fix |
|-------|--------|-----|
| Code doesn't run | ❌ Critical | Test before submission |
| Unrealistic scenario | 🟡 Medium | Add context, constraints |
| No best practices | 🟡 Medium | Highlight domain standards |
| Missing error handling | 🟡 Medium | Add try/except, validation |
| No explanation | 🟡 Medium | Add "Why" for each decision |

### 6.3 Style Violations

**Common formatting errors:**
```markdown
❌ No language in code block: ```
✅ Language specified: ```python

❌ Inconsistent heading levels
✅ H2 for sections, H3 for subsections

❌ Metadata missing or incomplete
✅ All three fields: Domain, Task Type, Complexity
```

---

## 7. References

### 7.1 Prompting Research

**Key papers (Module 11 integration):**
- Wei et al. 2022: Chain-of-Thought Prompting
- Yao et al. 2023: Tree of Thoughts
- React: Synergizing Reasoning and Acting
- Self-Consistency: Sampling diverse reasoning paths

**See:** `~/.claude/rules/prompting-techniques.md` for full taxonomy

### 7.2 Few-Shot Learning

- **Brown et al. 2020:** Language Models are Few-Shot Learners (GPT-3 paper)
- **Min et al. 2022:** Rethinking the Role of Demonstrations
- **Anthropic 2024:** Claude Prompt Engineering Guide

### 7.3 Example Repositories

**High-quality example sources:**
- [Anthropic Cookbook](https://github.com/anthropics/anthropic-cookbook)
- [OpenAI Examples](https://platform.openai.com/examples)
- [LangChain Cookbook](https://github.com/langchain-ai/langchain/tree/master/cookbook)

### 7.4 Domain Resources

**Security:**
- OWASP Testing Guide
- PTES Penetration Testing Methodology
- CIS Benchmarks

**DevOps:**
- The DevOps Handbook
- Site Reliability Engineering (Google)
- Infrastructure as Code (Terraform docs)

**Engineering:**
- Design Patterns (Gang of Four)
- Clean Code (Robert Martin)
- The Pragmatic Programmer

---

## Enforcement

**Example approval process:**

```
SUBMIT EXAMPLE
     ↓
AUTOMATED CHECKS (metadata, format, links)
     ↓
PEER REVIEW (score using rubric)
     ↓
┌─────────────────────────────────────┐
│ Score ≥4.0? YES → APPROVE → PUBLISH │
│ Score <4.0? NO → FEEDBACK → REVISE  │
└─────────────────────────────────────┘
```

**Gap tracking:**
- Missing examples for common tasks → GAP-OP-XXX in GAPS.md
- Low-quality examples → Flag for rewrite

**Quality metrics:**
- Target: 80%+ examples score ≥4.0/5.0
- Monitor: Example usage in sessions (most referenced = high quality)

---

**Version:** 1.0.0
**Created:** 2026-01-27
**Resolves:** GAP-OP-012 (P1, Example Writing Guidelines)
**Related:** MODULE_WRITING_GUIDELINES.md, GAP_WRITING_GUIDELINES.md, 11-prompting.md
