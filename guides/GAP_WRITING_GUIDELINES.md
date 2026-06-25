# Gap Writing Guidelines
# Version: 1.0.0 | Created: 2026-01-27

---

## Purpose

This document defines standards for identifying, documenting, and tracking configuration gaps in `GAPS.md`. It ensures consistent gap format, accurate prioritization, and effective gap lifecycle management.

**Audience:** Gap authors, auditors, configuration maintainers

**Scope:** Gap identification, template format, priority criteria, CLI relevance scoring, tracking

---

## Table of Contents

1. [Gap Template](#1-gap-template)
2. [Priority Guidelines](#2-priority-guidelines)
3. [CLI Relevance Scoring](#3-cli-relevance-scoring)
4. [Gap Categories](#4-gap-categories)
5. [Gap Lifecycle](#5-gap-lifecycle)
6. [Discovery Methods](#6-discovery-methods)
7. [Review Process](#7-review-process)
8. [Anti-Patterns](#8-anti-patterns)
9. [References](#9-references)

---

## 1. Gap Template

### 1.1 Standard Format

```markdown
#### GAP-[CATEGORY]-[NUMBER]: [Concise Title]
- **Status**: 🔴 Open | 🟡 Partial | ✅ Resolved
- **Priority**: P1 🔴 | P2 🟡 | P3 🟢
- **Category**: [Framework/Implementation/Protocol/Standards/etc.]
- **Description**: [1-3 sentences describing the problem]
- **Required**: [Specific deliverables needed]
- **Effort**: [Hours estimate: Xh or X-Yh range]
- **ROI**: [Expected value/impact]
- **CLI Relevance**: ✅✅ CRITICAL | ✅ HIGH | ⚠️ MEDIUM | ❌ LOW
- **Module**: [File path if applicable, e.g., ~/.claude/modules/XX-name.md]
- **Depends On**: [GAP-XXX-YYY] (if dependencies exist)
```

### 1.2 Field Definitions

#### GAP ID Format

**Pattern:** `GAP-[CATEGORY]-[NUMBER]`

**Categories (abbreviated):**

| Category | Abbreviation | Example |
|----------|-------------|---------|
| Orchestration | ORCH | GAP-ORCH-001 |
| Cost Optimization | COST | GAP-COST-SESSION-001 |
| Evaluation | EVAL | GAP-EVAL-METRICS-001 |
| Operational | OP | GAP-OP-011 |
| Security | SEC | GAP-SEC-MCP-001 |
| Prompting | PROMPT | GAP-PROMPT-COT-001 |
| Implementation | IMPL | GAP-COST-IMPL-001 |
| Research-Derived | RD | GAP-RD-OWASP-001 |

**Numbering:**
- Sequential within category (001, 002, 003...)
- Do NOT reuse numbers even if gap resolved

#### Status Indicators

| Status | Symbol | Meaning | Use When |
|--------|--------|---------|----------|
| **Open** | 🔴 | Not started | Gap identified, no work done |
| **Partial** | 🟡 | In progress or partially resolved | Work started, not complete |
| **Resolved** | ✅ | Complete | Fully implemented, tested, documented |

**Resolved gaps:**
- Moved to "Resolved Gaps" section
- Include resolution date and version
- Keep for audit trail (do NOT delete)

#### Priority Levels

| Priority | Symbol | Impact | Urgency | Description |
|----------|--------|--------|---------|-------------|
| **P1** | 🔴 | Critical | Immediate | Blocks functionality, security risk, or core workflow |
| **P2** | 🟡 | High | Soon | Significant value, common use case, quality improvement |
| **P3** | 🟢 | Medium | Eventually | Nice-to-have, niche use case, future enhancement |

**See Section 2 for detailed priority criteria.**

#### Category Field

**Purpose:** Classify gap type for organization

**Common categories:**
- **Framework** - Orchestration frameworks (LangChain, LangGraph, etc.)
- **Implementation** - Code/tool that needs building
- **Protocol** - Process/workflow definition
- **Standards** - Guidelines, templates, documentation
- **Integration** - Tool/service connections
- **Research-Derived** - Gaps from academic/industry research
- **Testing** - QA, benchmarks, evaluation

#### Description Field

**Requirements:**
- 1-3 sentences
- State the problem, not the solution
- Provide context (why this matters)
- Avoid jargon without definition

**Good examples:**
```markdown
✅ "LangChain is the most popular orchestration framework (112K+ stars),
    but current configuration only mentions it without detailed coverage."

✅ "Current hook implementation doesn't capture tool names properly,
    making tool-specific analytics impossible."

✅ "No guidelines exist for writing examples, leading to inconsistent
    quality and format across ~/.claude/examples/."
```

**Bad examples:**
```markdown
❌ "Need LangChain" (no context, vague)
❌ "Tool names don't work" (no impact explanation)
❌ "Examples are bad" (subjective, no specifics)
```

#### Required Field

**Purpose:** Specific deliverables for gap resolution

**Format:**
- Bulleted list of concrete deliverables
- Verifiable completion criteria
- Link to templates if applicable

**Good examples:**
```markdown
✅ **Required**:
   - Module section: LangChain Chains (5+ examples)
   - Integration guide: LCEL syntax, tool calling
   - Comparison table: LangChain vs LangGraph vs CrewAI
   - Few-shot examples: 3 common use cases

✅ **Required**:
   - Script: `session_token_tracker.py` (class + CLI)
   - Dashboard: Token usage, history growth, efficiency
   - Integration: Add to metrics_tracker.py --report option
   - Documentation: Update CLAUDE.md with usage
```

**Bad examples:**
```markdown
❌ "Add LangChain support" (not specific)
❌ "Fix the tool names" (how? what deliverables?)
❌ "Write better examples" (subjective, no criteria)
```

#### Effort Field

**Format:** `Xh` (single estimate) or `X-Yh` (range)

**Estimation guidelines:**

| Effort Range | Description | Example Tasks |
|--------------|-------------|---------------|
| **1-2h** | Quick fix, single file, simple addition | Bug fix, small section, example |
| **2-4h** | Small feature, 1-2 files, basic integration | Script, dashboard, module section |
| **4-8h** | Medium feature, multiple files, testing | Module, protocol, tool integration |
| **8-16h** | Large feature, complex integration, extensive docs | Framework coverage, multi-tool orchestration |
| **16+ h** | Major initiative, multiple deliverables, phased | Research implementation, full category |

**Include time for:**
- Research/learning (if new domain)
- Implementation
- Testing
- Documentation
- Review/iteration

**Estimation accuracy:**
- Use ranges when uncertain
- Track actual vs estimated (improve calibration)
- Include notes if dependencies affect estimate

#### ROI Field

**Purpose:** Justify priority, quantify value

**Types of ROI:**

1. **Cost Savings:**
   ```markdown
   **ROI**: -60-80% cost reduction, $4,600-4,750/year savings
   ```

2. **Time Savings:**
   ```markdown
   **ROI**: -30% session management overhead, saves 15 min/day
   ```

3. **Quality Improvement:**
   ```markdown
   **ROI**: +40% consistency, reduces onboarding time by 50%
   ```

4. **Risk Reduction:**
   ```markdown
   **ROI**: Prevents credential leaks (P1 security impact)
   ```

5. **Enablement:**
   ```markdown
   **ROI**: Unlocks multi-agent workflows, enables 20+ downstream gaps
   ```

**If ROI unknown:**
```markdown
**ROI**: To be determined (estimate after research)
```

#### CLI Relevance Field

**Purpose:** Filter gaps by applicability to Claude Code CLI users

**Scoring criteria:** See Section 3 for detailed rubric.

**Quick reference:**

| Relevance | Symbol | Use Case |
|-----------|--------|----------|
| **CRITICAL** | ✅✅ | Core Claude Code functionality, daily use, blocks common workflows |
| **HIGH** | ✅ | Frequently used, significant quality improvement, common use case |
| **MEDIUM** | ⚠️ | Occasional use, niche scenarios, future potential |
| **LOW** | ❌ | Rare use, research-only, external services, edge cases |

#### Module Field

**When to include:**
- Gap relates to specific module
- Implementation goes in existing file
- Cross-reference for context

**Format:**
```markdown
**Module**: ~/.claude/modules/02-security.md#section-3
**Module**: evaluation/metrics_tracker.py
**Module**: guides/MODULE_WRITING_GUIDELINES.md
```

#### Depends On Field

**Purpose:** Track dependencies between gaps

**Format:**
```markdown
**Depends On**: GAP-COST-SESSION-001 (session tracking must exist first)
**Depends On**: GAP-OP-011, GAP-OP-012 (requires both guidelines)
```

**Dependency types:**
- **Prerequisite** - Must be resolved first
- **Enhancement** - Builds on existing gap
- **Blocker** - Blocks multiple downstream gaps

---

## 2. Priority Guidelines

### 2.1 Priority Matrix

**Priority = Impact × Urgency × Feasibility**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PRIORITY DECISION MATRIX                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  P1 🔴 CRITICAL                                                              │
│  ├─► Impact: Blocks functionality, security risk, high cost                 │
│  ├─► Urgency: Immediate need, daily pain point                              │
│  ├─► Feasibility: Can be resolved (not blocked by external factors)         │
│  └─► Examples: Security vulnerability, broken core feature, cost leak       │
│                                                                              │
│  P2 🟡 HIGH                                                                  │
│  ├─► Impact: Significant value, quality improvement, common use case        │
│  ├─► Urgency: Near-term (weeks-months), frequent need                       │
│  ├─► Feasibility: Straightforward implementation                            │
│  └─► Examples: Optimization, new feature, consistency improvement           │
│                                                                              │
│  P3 🟢 MEDIUM/LOW                                                            │
│  ├─► Impact: Nice-to-have, niche scenario, future potential                 │
│  ├─► Urgency: Low, no pressing need                                         │
│  ├─► Feasibility: May have dependencies or unknowns                         │
│  └─► Examples: Research topics, edge cases, future enhancements             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 P1 Criteria (CRITICAL)

**Assign P1 if ANY of these apply:**

1. **Security Risk**
   - Credential exposure potential
   - Vulnerability in tool usage
   - Unsafe defaults
   - Example: Secrets detection missing

2. **Blocking Functionality**
   - Core workflow broken
   - Cannot complete common task
   - Data loss risk
   - Example: Git operations fail

3. **High Cost Impact**
   - Directly costs money (>$100/month)
   - Prevents cost optimization (>50% savings potential)
   - Example: No caching strategy, token leaks

4. **Data Integrity**
   - Corrupts state
   - Loses user work
   - Incorrect results with high confidence
   - Example: Metrics miscalculation

5. **Frequent Pain Point**
   - Encountered daily by most users
   - Wastes >15 min/day
   - No workaround
   - Example: Session management confusion

**P1 Resolution Timeline:** Within 1-2 weeks

### 2.3 P2 Criteria (HIGH)

**Assign P2 if MULTIPLE of these apply:**

1. **Quality Improvement**
   - Increases consistency by >30%
   - Reduces errors significantly
   - Improves maintainability
   - Example: Documentation standards

2. **Common Use Case**
   - Used weekly by 50%+ users
   - Standard workflow enhancement
   - Completes feature set
   - Example: Additional orchestration framework

3. **Moderate Cost/Time Savings**
   - Saves $20-100/month
   - Saves 5-15 min/day
   - Reduces cognitive load
   - Example: Usage limit tracking

4. **Enablement**
   - Unlocks future capabilities
   - Required for multiple P3 gaps
   - Strategic foundation
   - Example: MCP server infrastructure

5. **Standards Compliance**
   - Aligns with industry best practices
   - Meets regulatory requirements
   - Improves auditability
   - Example: OWASP Top 10 coverage

**P2 Resolution Timeline:** Within 1-3 months

### 2.4 P3 Criteria (MEDIUM/LOW)

**Assign P3 if:**

1. **Niche Use Case**
   - Used occasionally by <20% users
   - Advanced scenario
   - Optional enhancement
   - Example: Edge model deployment

2. **Research/Exploration**
   - Academic interest
   - Future potential (6+ months out)
   - Unproven value
   - Example: Model interpretability

3. **External Dependencies**
   - Requires third-party service
   - Blocked by API access
   - Vendor-specific
   - Example: Chinese LLM integration

4. **Incremental Improvement**
   - Marginal benefit (<10% gain)
   - Refinement, not core
   - Aesthetic preference
   - Example: UI polish

5. **Archival/Historical**
   - For completeness
   - Legacy support
   - Documentation only
   - Example: Deprecated framework reference

**P3 Resolution Timeline:** Eventually (3-12+ months)

### 2.5 Priority Examples by Category

| Gap Example | Priority | Reasoning |
|-------------|----------|-----------|
| Missing secrets detection in git workflow | P1 🔴 | Security risk, prevents credential leaks |
| Session token tracking for cost optimization | P1 🔴 | High cost impact, frequent pain point |
| Module writing guidelines | P1 🔴 | Enables all future module development (blocker) |
| LangChain detailed coverage | P1 🔴 | Most popular framework, blocks common workflows |
| Usage limit budget management | P2 🟡 | Moderate time savings, common for MAX users |
| Caching analytics dashboard | P2 🟡 | Quality improvement, visualizes ROI |
| Example writing guidelines | P2 🟡 | Standards compliance, improves consistency |
| CrewAI enterprise patterns | P2 🟡 | Common use case, completes framework coverage |
| Flowise visual builder | P3 🟢 | Niche use case, low-code preference |
| Model interpretability tools | P3 🟢 | Research topic, unclear immediate value |
| Chinese LLM ecosystem | P3 🟢 | External dependency (API access), niche region |

---

## 3. CLI Relevance Scoring

### 3.1 Scoring Rubric

**Purpose:** Prioritize gaps that improve Claude Code CLI user experience

**Scoring dimensions:**

| Dimension | Weight | Question |
|-----------|--------|----------|
| **Frequency** | 40% | How often is this used? |
| **Impact** | 30% | How much does this improve workflow? |
| **Accessibility** | 20% | Can CLI users leverage this? |
| **Maturity** | 10% | Is this stable/production-ready? |

### 3.2 Relevance Levels

#### ✅✅ CRITICAL (90-100 points)

**Characteristics:**
- Used daily or multiple times per session
- Core Claude Code functionality
- Direct CLI integration possible
- Stable and well-documented
- High impact on user experience

**Examples:**
```markdown
✅✅ GAP-OP-011: Module Writing Guidelines
     - Frequency: Used for every new module (daily potential)
     - Impact: Ensures consistent quality
     - Accessibility: Direct file creation in CLI
     - Maturity: Standards are stable

✅✅ GAP-COST-SESSION-001: Session Token Usage Tracking
     - Frequency: Every session
     - Impact: Prevents cost overruns, improves visibility
     - Accessibility: CLI dashboard integration
     - Maturity: Metrics APIs are stable

✅✅ GAP-RD-OWASP-001: Prompt Injection Defense
     - Frequency: Every user input (security-critical)
     - Impact: Prevents exploitation
     - Accessibility: Implementable in hooks
     - Maturity: OWASP standards well-established
```

#### ✅ HIGH (70-89 points)

**Characteristics:**
- Used weekly or in common workflows
- Significant quality/productivity improvement
- CLI integration feasible
- Mostly stable

**Examples:**
```markdown
✅ GAP-ORCH-002: LangGraph Multi-Agent Patterns
    - Frequency: Weekly for agent users
    - Impact: Enables complex workflows
    - Accessibility: Can document patterns for CLI use
    - Maturity: LangGraph is production-ready

✅ GAP-COST-IMPL-003: Context Budget Tracker
    - Frequency: Every session (background)
    - Impact: Prevents context overflow
    - Accessibility: CLI dashboard integration
    - Maturity: Context APIs are stable

✅ GAP-EVAL-METRICS-001: Fix "unknown" Tool Names
    - Frequency: Every tool call (metrics)
    - Impact: Enables tool-specific analytics
    - Accessibility: Fix in CLI hooks
    - Maturity: Metrics format is stable
```

#### ⚠️ MEDIUM (40-69 points)

**Characteristics:**
- Used occasionally or in specific scenarios
- Moderate benefit
- CLI integration possible but not straightforward
- May have some instability

**Examples:**
```markdown
⚠️ GAP-ORCH-011: Claude-Flow Platform
    - Frequency: Occasional (for multi-agent needs)
    - Impact: Useful for specific workflows
    - Accessibility: External tool, limited CLI integration
    - Maturity: Platform still evolving

⚠️ GAP-BENCH-002: DPAI Arena Benchmarking
    - Frequency: Rare (benchmarking needs)
    - Impact: Quality assessment
    - Accessibility: CLI can trigger, but external service
    - Maturity: Arena is stable but niche

⚠️ GAP-RD-NIST-001: NIST AI Risk Management
    - Frequency: Occasional (compliance reviews)
    - Impact: Governance framework
    - Accessibility: Checklist integration possible
    - Maturity: Framework is mature but complex
```

#### ❌ LOW (0-39 points)

**Characteristics:**
- Rarely used or highly niche
- Minimal direct benefit to CLI users
- Requires external services or specialized hardware
- Experimental or unstable

**Examples:**
```markdown
❌ GAP-ORCH-010: Flowise Visual Builder
    - Frequency: Rare (low-code preference)
    - Impact: GUI-based, not CLI-native
    - Accessibility: External tool, no CLI integration
    - Maturity: Stable but different paradigm

❌ GAP-CHINESE-003: Qwen3-Max Integration
    - Frequency: Very rare (regional, API access)
    - Impact: Limited for non-Chinese users
    - Accessibility: Requires API keys, external service
    - Maturity: Stable but niche market

❌ GAP-EDGE-002: SmolLM3 Deployment
    - Frequency: Rare (edge device deployment)
    - Impact: Specialized use case
    - Accessibility: Requires hardware setup
    - Maturity: Experimental model

❌ GAP-RESEARCH-005: Model Interpretability Tools
    - Frequency: Very rare (research purposes)
    - Impact: Academic interest, not workflow improvement
    - Accessibility: Complex tools, not CLI-native
    - Maturity: Research-stage tools
```

### 3.3 Scoring Calculator

**Formula:**
```
Score = (Frequency × 0.40) + (Impact × 0.30) + (Accessibility × 0.20) + (Maturity × 0.10)
```

**Dimension scales (0-100):**

**Frequency:**
- 90-100: Daily, every session
- 70-89: Weekly, common workflows
- 40-69: Monthly, occasional use
- 0-39: Rarely, niche scenarios

**Impact:**
- 90-100: Critical to workflow, blocks without it
- 70-89: Significant improvement, major time savings
- 40-69: Moderate benefit, nice-to-have
- 0-39: Minimal impact, incremental

**Accessibility:**
- 90-100: Direct CLI integration, native feature
- 70-89: CLI-friendly, straightforward integration
- 40-69: Possible but requires workarounds
- 0-39: External service, difficult integration

**Maturity:**
- 90-100: Stable, production-ready, well-documented
- 70-89: Mostly stable, some edge cases
- 40-69: Evolving, some breaking changes
- 0-39: Experimental, unstable, poor docs

**Example calculation:**
```
GAP-COST-SESSION-001: Session Token Usage Tracking

Frequency: 95 (every session, continuous)
Impact: 85 (prevents cost overruns, high visibility)
Accessibility: 90 (direct CLI integration)
Maturity: 90 (metrics APIs stable)

Score = (95 × 0.40) + (85 × 0.30) + (90 × 0.20) + (90 × 0.10)
      = 38 + 25.5 + 18 + 9
      = 90.5 → ✅✅ CRITICAL
```

---

## 4. Gap Categories

### 4.1 Category Taxonomy

**50 categories organized into 8 groups:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GAP CATEGORY TAXONOMY                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GROUP 1: ORCHESTRATION & FRAMEWORKS (6 categories)                         │
│  ├─► 01. LLM Orchestration Frameworks (ORCH)                                │
│  ├─► 02-03. Local LLM + Workflow (LOCAL, WORKFLOW)                          │
│  ├─► 04. API Gateways & Routing (GATEWAY)                                   │
│  ├─► 13. Vendor-Specific SDK & Frameworks (SDK)                             │
│  └─► 14-15. Extended Local/Workflow (LOCEXT, FLOWEXT)                       │
│                                                                              │
│  GROUP 2: AI CAPABILITIES (6 categories)                                    │
│  ├─► 05. Reasoning (REASON)                                                 │
│  ├─► 06. Multimodal (MULTI)                                                 │
│  ├─► 07. Anthropic-Specific (ANTHRO)                                        │
│  ├─► 16-17. Extended Reasoning/Multimodal (REASONEXT, MULTIEXT)            │
│  ├─► 31. Reasoning Models (REASONING-MODEL)                                 │
│  └─► 33. Code-Specialized Models (CODE-MODEL)                               │
│                                                                              │
│  GROUP 3: OBSERVABILITY & SAFETY (5 categories)                             │
│  ├─► 08. Observability (OBS)                                                │
│  ├─► 09. Safety & Security (SAFETY)                                         │
│  ├─► 18. Extended Observability (OBSEXT)                                    │
│  ├─► 19. Extended Safety & Security (SAFETYEXT)                             │
│  └─► 50. Research-Derived (Authoritative) (RD)                              │
│                                                                              │
│  GROUP 4: OPTIMIZATION & EVALUATION (4 categories)                          │
│  ├─► 10. Performance Optimization (PERF)                                    │
│  ├─► 24. Agent-Level Evaluation (EVAL)                                      │
│  ├─► 25. Agent-Level Cost Optimization (COST)                               │
│  └─► 26. LLM Testing & QA (TEST)                                            │
│                                                                              │
│  GROUP 5: INFRASTRUCTURE & OPERATIONS (6 categories)                        │
│  ├─► 20. Protocols & Architecture (PROTO)                                   │
│  ├─► 27. MLOps for LLMs (MLOPS)                                             │
│  ├─► 28. Data Engineering for LLMs (DATA)                                   │
│  ├─► 38. Research-to-Practice Protocol (R2P)                                │
│  ├─► 39. Operational Protocols (OP)                                         │
│  └─► 48-49. Source Management (SOURCE-REG, SOURCE-DOMAIN)                   │
│                                                                              │
│  GROUP 6: STANDARDS & METHODOLOGIES (4 categories)                          │
│  ├─► 11-12. Examples + Templates (EXAMPLE, TEMPLATE)                        │
│  ├─► 21. Prompting Methodologies (PROMPT)                                   │
│  ├─► 22. Agentic AI Standards (STANDARD)                                    │
│  └─► 23. Advanced Topics (ADVANCED)                                         │
│                                                                              │
│  GROUP 7: AGENT ECOSYSTEM (7 categories)                                    │
│  ├─► 29. Coding Agents & IDEs (CODING)                                      │
│  ├─► 30. Agent Benchmarks (BENCH)                                           │
│  ├─► 32. Chinese LLM Ecosystem (CHINESE)                                    │
│  ├─► 34. Small & Edge Models (EDGE)                                         │
│  ├─► 35. Browser & Computer Use Agents (BROWSER)                            │
│  ├─► 36. Practical Resources & Learning (PRACTICAL)                         │
│  └─► 37. Research Frontiers (RESEARCH)                                      │
│                                                                              │
│  GROUP 8: IMPLEMENTATION (1 category)                                       │
│  └─► IMPL (Implementation) - Cross-cutting implementations                  │
│                                                                              │
│  TOTAL: 50 CATEGORIES                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Category Assignment Rules

**Choose category based on:**

1. **Primary domain** - What is the main focus?
2. **Implementation type** - Framework, tool, protocol, standard?
3. **User activity** - What task is enabled?

**Multi-category gaps:**
- Use primary category in GAP ID
- Mention secondary in description
- Example: `GAP-COST-IMPL-001` (Cost optimization via Implementation)

### 4.3 New Category Creation

**When to create new category:**
- 10+ gaps in similar domain
- Distinct from existing categories
- Long-term strategic area

**Process:**
1. Propose in GAPS.md header comment
2. Get approval (document in gap)
3. Update taxonomy
4. Renumber existing gaps if needed

---

## 5. Gap Lifecycle

### 5.1 Lifecycle States

```
🔴 OPEN → 🟡 PARTIAL → ✅ RESOLVED → 📦 ARCHIVED
   │          │           │            │
   └──────────┴───────────┴────────────┴────► TIME
```

**State transitions:**

| From | To | Trigger | Action |
|------|----|---------|-----------------------------------------|
| N/A | 🔴 OPEN | Discovery | Create gap in GAPS.md |
| 🔴 OPEN | 🟡 PARTIAL | Work started | Update status, add progress notes |
| 🟡 PARTIAL | 🔴 OPEN | Blocked | Revert status, document blocker |
| 🟡 PARTIAL | ✅ RESOLVED | Complete | Move to "Resolved Gaps" section |
| ✅ RESOLVED | 📦 ARCHIVED | After 6-12 months | Move to GAPS_ARCHIVE.md |

### 5.2 Resolution Criteria

**Gap is RESOLVED when ALL of these are met:**

```
✅ Required deliverables completed
✅ Implementation tested (code runs, commands work)
✅ Documentation updated (module, CLAUDE.md, examples)
✅ Git committed (with proper message)
✅ Reviewed (peer check or self-verification)
✅ Integrated (linked from relevant sections)
```

**Resolution entry format:**
```markdown
#### ✅ RESOLVED: GAP-[CATEGORY]-[NUMBER]: [Title]
- **Status**: ✅ Resolved (YYYY-MM-DD)
- **Version**: vX.X.X (when resolved)
- **Priority**: [Original priority]
- **Description**: [Brief description]
- **Deliverables**:
  - File 1: [path]
  - File 2: [path]
- **Effort**: [Actual hours] (Estimated: [original estimate])
- **ROI**: [Measured impact if available]
- **Git Commit**: [commit hash] - [commit message]
```

### 5.3 Progress Tracking

**For PARTIAL gaps, add progress notes:**
```markdown
#### GAP-COST-SESSION-001: Session Token Usage Tracking
- **Status**: 🟡 Partial (30% complete)
- **Priority**: P1 🔴
- **Progress**:
  - [x] Research session JSONL format
  - [x] Design SessionTokenTracker class
  - [ ] Implement parse_session_file()
  - [ ] Add CLI integration
  - [ ] Write tests
- **Blockers**: None
- **Next Steps**: Implement core parsing logic
- **Updated**: 2026-01-26
```

### 5.4 Archival Policy

**When to archive resolved gaps:**
- Gap resolved for 6-12 months
- No longer referenced in active work
- Historical record only

**Archive process:**
1. Create `GAPS_ARCHIVE.md` if doesn't exist
2. Move resolved gap entry
3. Update gap counts in GAPS.md header
4. Keep link to archive for audit trail

---

## 6. Discovery Methods

### 6.1 Gap Discovery Triggers

**How gaps are identified:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GAP DISCOVERY METHODS                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. USER SIGNALS (40%)                                                       │
│     ├─► "This isn't documented"                                              │
│     ├─► "Where is X feature?"                                                │
│     ├─► User corrects Claude's assumption                                    │
│     └─► Repeated questions on same topic                                     │
│                                                                              │
│  2. SELF-DETECTION (30%)                                                     │
│     ├─► No template found for common task                                    │
│     ├─► Tool not in tech stack                                               │
│     ├─► Low routing confidence (<40%)                                        │
│     └─► Missing example for frequent query                                   │
│                                                                              │
│  3. SYSTEMATIC AUDIT (20%)                                                   │
│     ├─► Comprehensive configuration review                                   │
│     ├─► Industry trend analysis                                              │
│     ├─► Academic paper review (prompting, safety, etc.)                      │
│     └─► Competitor analysis (other AI tools)                                 │
│                                                                              │
│  4. COVERAGE FAILURES (10%)                                                  │
│     ├─► Test coverage < 95%                                                  │
│     ├─► Missing authorization level                                          │
│     ├─► No anti-pattern documentation                                        │
│     └─► Broken cross-references                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Discovery Workflow

**When gap is discovered:**

1. **Capture immediately**
   - Create draft gap in GAPS.md or scratchpad
   - Include context of discovery
   - Note who/what triggered discovery

2. **Research**
   - Verify gap is genuine (not already covered)
   - Estimate scope and effort
   - Identify related gaps

3. **Prioritize**
   - Apply priority rubric (Section 2)
   - Score CLI relevance (Section 3)
   - Determine category

4. **Document**
   - Write complete gap entry
   - Link to relevant modules
   - Add to GAPS.md in correct category

5. **Communicate**
   - Notify user if discovered during session
   - Add to session summary if relevant
   - Update UNIFIED_IMPLEMENTATION_ROADMAP.md if in plan

### 6.3 Audit Checklist

**Monthly gap audit (systematic review):**

- [ ] Review recent user questions for patterns
- [ ] Check industry news for new tools/frameworks
- [ ] Scan academic papers (arXiv, conferences)
- [ ] Compare with competitor features (Cursor, Windsurf, etc.)
- [ ] Review existing gaps for changed priorities
- [ ] Verify resolved gaps still valid
- [ ] Update CLI relevance scores if tools evolved

---

## 7. Review Process

### 7.1 Peer Review Checklist

**Before merging gap to GAPS.md:**

**Format:**
- [ ] GAP ID follows convention (GAP-[CAT]-[NUM])
- [ ] All required fields present
- [ ] Status symbol correct (🔴🟡✅)
- [ ] Priority level assigned (P1/P2/P3)

**Content:**
- [ ] Description is clear and concise (1-3 sentences)
- [ ] Required deliverables are specific
- [ ] Effort estimate reasonable
- [ ] ROI justifies priority
- [ ] CLI relevance scored appropriately

**Categorization:**
- [ ] Category matches gap domain
- [ ] Priority aligns with criteria (Section 2)
- [ ] CLI relevance aligns with rubric (Section 3)
- [ ] Dependencies documented if exist

**Integration:**
- [ ] No duplicate of existing gap
- [ ] Cross-referenced to related gaps
- [ ] Module field links to correct file
- [ ] Numbered sequentially in category

### 7.2 Quality Standards

**Minimum quality bar:**

| Aspect | Requirement | Check |
|--------|-------------|-------|
| **Clarity** | Description understandable without context | Read to someone unfamiliar |
| **Specificity** | Deliverables are verifiable | Can you check if done? |
| **Justification** | Priority is defensible | Can you explain to skeptic? |
| **Effort** | Estimate is calibrated | Based on similar gaps? |
| **Relevance** | CLI score aligns with rubric | Run through calculator |

**Red flags (reject or revise):**
- Vague description ("need better X")
- No deliverables listed
- Priority not justified
- Duplicate of existing gap
- CLI relevance obviously wrong

### 7.3 Gap Maintenance

**Quarterly maintenance tasks:**

1. **Reprioritize**
   - Review P2/P3 gaps for promotion
   - Demote gaps if context changed
   - Update effort estimates based on actual data

2. **Consolidate**
   - Merge duplicate gaps
   - Group related gaps into initiatives
   - Create parent gaps for themes

3. **Prune**
   - Archive resolved gaps (>6 months)
   - Remove obsolete gaps (tech deprecated)
   - Mark blocked gaps

4. **Update**
   - Refresh CLI relevance scores
   - Adjust ROI based on data
   - Update dependencies

---

## 8. Anti-Patterns

### 8.1 Common Mistakes

**❌ DON'T:**

1. **Vague Descriptions:**
   ```markdown
   ❌ "Need better documentation"
   ✅ "Module writing guidelines missing, leading to inconsistent structure"
   ```

2. **Solution in Description:**
   ```markdown
   ❌ "Create a SessionTokenTracker class to track tokens"
   ✅ "No visibility into session token usage, making cost optimization difficult"
   ```

3. **Unrealistic Effort:**
   ```markdown
   ❌ "Implement full LangChain coverage: 2h"
   ✅ "Implement full LangChain coverage: 12-16h"
   ```

4. **Generic ROI:**
   ```markdown
   ❌ "Will improve things"
   ✅ "Prevents credential leaks (P1 security risk)"
   ```

5. **Wrong Priority:**
   ```markdown
   ❌ P1 for "Add dark mode theme"
   ✅ P3 for "Add dark mode theme" (aesthetic preference)
   ```

### 8.2 Quality Issues

**Red flags during review:**

| Issue | Impact | Fix |
|-------|--------|-----|
| No deliverables | Can't verify completion | Add specific outputs |
| Priority inflation | Everything is P1 | Apply rubric strictly |
| Duplicate gaps | Wasted effort | Search before creating |
| No CLI relevance | Can't filter for users | Score using rubric |
| Missing dependencies | Blocked implementation | Link prerequisite gaps |

### 8.3 Process Violations

**Enforcement:**
- **Critical violations** (duplicate, wrong format): Reject immediately
- **Medium violations** (unclear description): Request revision
- **Minor violations** (typo, formatting): Fix and merge

---

## 9. References

### 9.1 Related Guidelines

- `MODULE_WRITING_GUIDELINES.md` - For gaps requiring module updates
- `EXAMPLE_WRITING_GUIDELINES.md` - For gaps requiring examples
- `UNIFIED_IMPLEMENTATION_ROADMAP.md` - Sequenced gap resolution plan

### 9.2 Gap Management Tools

**Current tools:**
- `GAPS.md` - Main gap registry
- `UNIFIED_IMPLEMENTATION_ROADMAP.md` - Sequenced implementation plan
- `CHANGELOG.md` - Version history with resolved gaps

**Potential tools:**
- Gap search script (grep by category, priority, relevance)
- Gap statistics dashboard (count by status, priority)
- Effort tracking (actual vs estimated)

### 9.3 Industry Practices

**Gap tracking inspiration:**
- JIRA/Linear issue tracking
- GitHub Issues + Projects
- RFC (Request for Comments) process
- IETF standards tracking

---

## Enforcement

**Gap quality monitoring:**

```
MONTHLY AUDIT
     ↓
Count gaps by status/priority
     ↓
┌──────────────────────────────────┐
│ Metric: <10% gaps in PARTIAL?   │
│ YES → Healthy | NO → Review      │
├──────────────────────────────────┤
│ Metric: P1 gaps <5% of total?   │
│ YES → Healthy | NO → Reprioritize│
└──────────────────────────────────┘
```

**Target metrics:**
- Open gaps: <100 per category
- Partial gaps: <10% (indicates active work)
- Resolved gaps: +10-20% per quarter
- Priority distribution: P1 <10%, P2 ~50%, P3 ~40%

---

**Version:** 1.0.0
**Created:** 2026-01-27
**Resolves:** GAP-OP-013 (P1, Gap Writing Guidelines)
**Related:** MODULE_WRITING_GUIDELINES.md, EXAMPLE_WRITING_GUIDELINES.md, GAPS.md
