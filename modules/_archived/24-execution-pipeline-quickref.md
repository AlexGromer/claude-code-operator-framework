# Rule: Universal Execution Pipeline (UEP)
# Auto-loaded by Claude Code from ~/.claude/rules/

## Pipeline Overview (MANDATORY for every task)

**Full Documentation:** `modules/23-execution-pipeline.md`

The UEP orchestrates ALL existing systems into a unified execution framework. Every task follows this pipeline, with depth varying by complexity.

**Core Principle:** Goal → Result → Criteria → Method (in that order, always)

---

## 1. Complexity Scoring & Tier Assignment

### Scoring Factors

| Factor | Calculation | Cap |
|--------|-------------|-----|
| **Word count** | ≤10: +0, 11-30: +10, 31-50: +20, 51+: +30 | — |
| **Domain count** | 1: +0, 2: +15, 3+: +25 | — |
| **Tool keywords** | +5 per tool (nmap, terraform, etc.) | +20 |
| **Action keywords** | +5 per action (audit, create, analyze) | — |
| **Heavy keywords** | +10 per heavy term (comprehensive, full, all) | — |
| **Modifier keywords** | +5 per modifier (with tests, report) | +15 |
| **TOTAL** | Sum all factors | **100** |

### Tier Assignment

| Score | Tier | Pipeline Steps | Iterations |
|-------|------|---------------|------------|
| **0-19** | **Tier 1** (Simple) | QUALIFY → EXECUTE inline → DELIVER | 1 |
| **20-59** | **Tier 2** (Standard) | QUALIFY → DEFINE → DECOMPOSE → EXECUTE → COLLECT → ANALYZE → DELIVER | 3 min |
| **60-100** | **Tier 3** (Complex) | All 12 steps + recursive subagents + DAG | 3-15 per subtask |

### Examples

```
"прочитай config.yml" → 15 pts → Tier 1
"создай тест для модуля X" → 35 pts → Tier 2
"security audit K8s с Trivy, тестами, отчётом" → 85 pts → Tier 3
```

---

## 2. Pipeline Steps (12 Steps, 3 Tiers)

| # | Step | T1 | T2 | T3 | What Happens |
|---|------|----|----|----|--------------|
| 1 | **RECEIVE** | ✅ | ✅ | ✅ | Parse request, calculate complexity score → assign tier |
| 2 | **QUALIFY** | ✅ | ✅ | ✅ | Check context sufficiency (5 dims), clarify if needed, route domain |
| 3 | **DEFINE** | — | ✅ | ✅ | Extract Goal/Result/Criteria (GRC), freeze criteria |
| 4 | **DECOMPOSE** | — | ✅ | ✅ | Break into subtasks, dependency DAG, assign models |
| 5 | **PLAN** | — | — | ✅ | Assemble AWB blocks, define iteration strategy, set thresholds |
| 6 | **RESEARCH** | — | — | ✅ | Gather facts, validate sources (L0-L4), log to knowledge graph |
| 7 | **EXECUTE** | ✅ | ✅ | ✅ | Run work (T1: inline, T2: agent, T3: recursive subagents) |
| 8 | **COLLECT** | — | ✅ | ✅ | Aggregate outputs from all subtasks/agents |
| 9 | **VALIDATE** | — | — | ✅ | Apply domain quality metrics, check coverage ≥95% |
| 10 | **ANALYZE** | — | ✅ | ✅ | Compare output vs criteria, calculate pass/fail/partial |
| 11 | **ITERATE** | — | ✅ | ✅ | If criteria not met + iter < max → refine and re-execute |
| 12 | **DELIVER** | ✅ | ✅ | ✅ | Final output + summary + gaps + next steps |

---

## 3. Goal-Result-Criteria (MANDATORY Order)

**Rule:** Always define in this EXACT order:

```
1. GOAL      → What user wants to achieve (high-level intent)
2. RESULT    → Concrete deliverable (artifacts, format, structure)
3. CRITERIA  → Pass/fail conditions (measurable, testable)
4. METHOD    → How to achieve (tools, approach, steps)
```

**Anti-Pattern:**
```
❌ Method → Result → Goal → Criteria  (WRONG — method locks you in too early)
❌ Goal → Method → Result → Criteria  (WRONG — method before knowing acceptance criteria)
```

**Correct:**
```
✅ Goal: "Deploy secure K8s app"
✅ Result: "Deployed app + Trivy report + network policy YAML"
✅ Criteria: "0 HIGH CVEs, pods running, ingress reachable, policy blocks external egress"
✅ Method: "Use Trivy scan → fix vulns → apply manifests → apply policy → test"
```

---

## 4. Result Evaluation

### Criteria Check Format

```
FOR EACH criterion:
  ├─► PASS: Criterion fully met → mark ✅
  ├─► FAIL: Criterion not met → mark ❌
  └─► PARTIAL: Criterion 50-99% met → mark ⚠️

OVERALL:
  ├─► ALL PASS → DELIVER
  ├─► ANY FAIL + iter < max → ITERATE (fix fails)
  └─► MAX ITER REACHED → User decision (4 options, see §11)
```

### Domain Quality Metrics (Brief)

| Domain | Key Metrics |
|--------|-------------|
| **Code** | Syntax valid, tests ≥80%, complexity ≤10, no secrets |
| **Security** | 0 CRITICAL CVEs, auth verified, scope confirmed |
| **Infrastructure** | Deployed, health checks pass, rollback plan exists |
| **Documentation** | Structure valid, links work, examples tested |
| **Research** | Sources L3+, cross-referenced, no hallucinations |

**Full List:** See `modules/23-execution-pipeline.md` Section 9 (50+ metrics)

---

## 5. Mandatory Iterations

| Tier | Min Iterations | Rule |
|------|----------------|------|
| **Tier 1** | 1 | Execute once, deliver (no iteration unless error) |
| **Tier 2** | 3 | Execute → validate → refine (min 3 rounds) |
| **Tier 3** | 3-15 | Per-subtask iteration until criteria met or max reached |

**Global Limit:** 15 iterations total across all subtasks (to prevent infinite loops)

---

## 6. AWB Block Library (28 Blocks)

### Block Categories

| Category | Blocks | Purpose |
|----------|--------|---------|
| **Input** (3) | clarify, context_check, route | Parse and qualify request |
| **Definition** (3) | grc_extract, criteria_freeze, decompose | Define work structure |
| **Planning** (4) | dag_build, model_select, threshold_set, awb_assemble | Plan execution strategy |
| **Research** (4) | fact_gather, source_validate, web_search, knowledge_store | Gather verified knowledge |
| **Execution** (5) | execute_inline, execute_subagent, execute_recursive, tool_call, skill_invoke | Perform work |
| **Validation** (4) | syntax_check, test_run, coverage_calc, quality_gate | Verify correctness |
| **Analysis** (3) | criteria_eval, gap_detect, cost_calc | Assess results |
| **Iteration** (2) | iterate_decision, refine_prompt | Control refinement loop |

**Total: 28 blocks** — Mix and match per tier/domain

### Runtime Assembly Algorithm

```
1. Tier assigned → load tier-specific base sequence
2. Domain detected → inject domain-specific blocks (e.g., security adds CVE check)
3. User flags detected → add modifier blocks (e.g., "with tests" adds test_run)
4. Dependencies resolved → order blocks in DAG
5. Execute sequence → each block outputs to next
```

### Skills = Pre-Composed AWB Shortcuts

| Skill | AWB Sequence |
|-------|--------------|
| **/commit** | `route(git) → grc_extract → execute_inline(git status+diff) → criteria_eval(secrets) → execute_inline(git commit)` |
| **/pentest** | `route(security) → context_check(authorization) → decompose(PTES phases) → execute_subagent(recon) → execute_subagent(scan) → collect → gap_detect` |
| **/research** | `route(research) → fact_gather → source_validate → web_search → knowledge_store → criteria_eval(L3+ sources)` |

**Full List:** See `modules/15-skills.md` (30 skills, all with AWB mappings)

---

## 7. Context Sufficiency

### 5 Dimensions (Check at QUALIFY)

| Dimension | Threshold | Action if Insufficient |
|-----------|-----------|------------------------|
| **Specificity** | Clear deliverable? | Ask: "What format/structure?" |
| **Scope** | Boundaries defined? | Ask: "Which files/components?" |
| **Authority** | Permission level clear? | Ask: "Authorization for this operation?" |
| **Success Criteria** | Pass/fail defined? | Ask: "How will we know it's done?" |
| **Dependencies** | Inputs available? | Ask: "Do you have X, Y, Z?" |

### Clarification Rules

```
├─► 0-1 insufficient dimensions → Auto-research OR make reasonable assumption + notify
├─► 2-3 insufficient dimensions → Ask 1-2 clarifying questions
└─► 4-5 insufficient dimensions → BLOCK, request full context

Max clarification rounds: 3
After 3 rounds → Auto-research OR proceed with best-effort + warn
```

---

## 8. Subagent Enrichment (MANDATORY)

**Every subagent prompt MUST include:**

1. **Extracted GRC** (Goal/Result/Criteria from parent task)
2. **Iteration context** (Current iteration number, previous attempt summary if iter > 1)
3. **Dependencies** (What this subtask needs from other subtasks)
4. **Quality thresholds** (Domain-specific metrics, e.g., test coverage ≥80%)
5. **Model rationale** (Why this model selected: haiku/sonnet/opus)
6. **Output format** (JSON schema, markdown structure, file path)
7. **Failure fallback** (What to do if subtask fails)
8. **Time limit** (Max execution time before timeout)
9. **Context scope** (Which modules/rules/examples to load)

**Example:**
```
Task(
  subagent_type="general-purpose",
  model="sonnet",
  prompt="""
  GOAL: Deploy secure K8s app
  RESULT: app-deployment.yaml with 0 HIGH CVEs
  CRITERIA: Trivy scan passes, pods running, ingress reachable

  SUBTASK: Scan container image with Trivy
  ITERATION: 1 of 3
  DEPENDENCIES: Image built in previous step (image:tag from ../build/output.json)
  QUALITY: 0 CRITICAL, 0 HIGH CVEs (fail if any found)
  MODEL: sonnet (security scan = medium complexity)
  OUTPUT: JSON with {vulnerabilities: [], severity_counts: {}, passed: bool}
  FALLBACK: If Trivy fails, use Docker Scout as backup
  TIMEOUT: 5 minutes
  CONTEXT: Load modules/02-security.md Section 1.5 (Trivy)
  """
)
```

---

## 9. Recursive UEP & DAG

### Limits (Hard Constraints)

| Limit | Value | Why |
|-------|-------|-----|
| **Max recursion depth** | 3 | Prevent stack overflow, coordination overhead |
| **Max iterations** | 15 | Prevent infinite loops |
| **Max concurrent agents** | 20 | API rate limits, memory |
| **Max subtask timeout** | 10 min | Prevent hung agents |

### Dependency DAG Rules

```
├─► PARALLEL: Independent subtasks → Execute in single Task() call (multiple subagents)
├─► SEQUENTIAL: Dependent subtasks → Execute with chaining (output of A → input of B)
└─► CONDITIONAL: Output-dependent next step → Evaluate first, then branch
```

**Example:**
```
Tier 3 task: "K8s audit + deploy + monitor setup"

DAG:
  ├─► [PARALLEL] Subtask A: Trivy scan (independent)
  ├─► [PARALLEL] Subtask B: Falco policy review (independent)
  ├─► [SEQUENTIAL] Subtask C: Fix vulns (depends on A output)
  ├─► [SEQUENTIAL] Subtask D: Deploy (depends on C completion)
  └─► [SEQUENTIAL] Subtask E: Setup monitoring (depends on D completion)

Execution:
  1. Launch A + B in parallel (2 agents, single Task call)
  2. Wait for A+B completion
  3. Launch C (1 agent, reads A output from file)
  4. Launch D (1 agent, reads C output)
  5. Launch E (1 agent, reads D output)
```

---

## 10. Criteria Freeze

**Rule:** Once criteria defined at DEFINE step, they FREEZE. Cannot change during execution.

### Why?

- Prevents scope creep mid-execution
- Ensures consistent evaluation across iterations
- Forces upfront clarity

### When Frozen?

```
DEFINE step completes → Criteria frozen
ITERATE step → Same criteria applied
DELIVER step → Same criteria reported
```

### How to Unfreeze?

```
User explicitly says: "Change criteria to X"
  → Claude asks: "This will reset iterations to 0. Proceed? [y/N]"
  → If yes: New criteria → reset iter counter → restart EXECUTE
```

**Anti-Pattern:**
```
❌ Iteration 1: "Test coverage ≥80%"
❌ Iteration 2: "Actually, 70% is fine" ← WRONG! Criteria changed mid-flight
```

---

## 11. Max Iterations Exhaustion

**When 15 iterations reached WITHOUT meeting criteria:**

```
┌─ MAX ITERATIONS REACHED ───────────────────────────────────────┐
│ Criteria NOT fully met after 15 iterations.                    │
│                                                                 │
│ Options:                                                        │
│ 1. DELIVER AS-IS — Accept partial result (⚠️ mark failed)      │
│ 2. RELAX CRITERIA — Lower threshold, restart (user confirms)   │
│ 3. CHANGE APPROACH — New method, restart from PLAN             │
│ 4. ABANDON — Mark as infeasible, document why                  │
│                                                                 │
│ Your choice [1-4]:                                              │
└─────────────────────────────────────────────────────────────────┘
```

**Default (if user unavailable):** Option 1 (deliver partial, mark gaps)

---

## 12. AWB Block Lifecycle

### Creation

```
When: New pattern used 3+ times across domains
Process:
  1. Identify repeating sequence (e.g., "research → validate → store")
  2. Abstract into parameterized block
  3. Add to AWB library in modules/23
  4. Update runtime assembly logic
  5. Test in 3 domains
```

### Deletion

```
When: Block unused for 90 days OR superseded by better block
Process:
  1. Mark DEPRECATED (30 days notice)
  2. Migrate existing usages to replacement
  3. Archive to modules/23-execution-pipeline.md (Appendix)
  4. Remove from runtime assembly
```

### Promotion

```
Skill → AWB: When skill becomes generic (used by 5+ domains)
AWB → Rule: When block becomes universal (used by ALL tiers)
```

### Deprecation

```
Replaced: Old block → new block (e.g., fact_gather_v1 → fact_gather_v2 with L0-L4)
Obsolete: No longer needed (e.g., removed when feature changed)
```

---

## 13. Nomenclature & Artifact Creation

### Domain-Specific Artifacts (8 Mandatory)

When creating NEW domain:

```
1. Module (modules/XX-domain.md)
2. Skill (/domain-workflow in skills/)
3. Few-shot examples (examples/domain/)
4. MCP profile (mcp_profile_manager.py domain profile)
5. Routing keywords (role-routing.md entry)
6. Quality metrics (execution-pipeline.md §9)
7. AWB domain blocks (if unique patterns exist)
8. Authoritative sources (AUTHORITATIVE_SOURCES.md)
```

### Deletion (Archive-First, 30 Days)

```
NEVER hard-delete:
  ├─► Archive to _archived/ subdirectory
  ├─► Keep for 30 days
  ├─► After 30 days → compress to .tar.gz
  └─► After 90 days → eligible for deletion (user confirms)
```

---

## 14. Automation Analysis (Every Task)

**At DELIVER step, answer 4 questions:**

| Question | If YES → Action |
|----------|-----------------|
| **1. Should this be a hook?** | Triggered by event? → Create PreToolUse/PostToolUse/SessionStart/SessionEnd hook |
| **2. Should this be anacron?** | Runs periodically? → Add to ~/.anacron/anacrontab (daily/weekly/monthly) |
| **3. Should this be a skill?** | Reusable workflow? → Create /skillname in skills/ |
| **4. Can this be 1-touch?** | Frequent operation? → Create wrapper script in ~/.local/bin/ |

**Example:**
```
Task: "Generate weekly security report"
  ├─► Hook? NO (not event-triggered)
  ├─► Anacron? YES (weekly) → Add: `7 10 security_weekly_report cd ~/.claude && python tools/security_report.py --weekly`
  ├─► Skill? YES → Create /security-report skill
  └─► 1-touch? YES → Create `security-report` wrapper → `alias secreport='security-report'`
```

---

## 15. Learning Mode (Optional)

**For research-heavy tasks (Tier 3 with RESEARCH step):**

```
User says: "Teach me about X" OR "Explain as you go"
  → Activate LEARNING_MODE flag
  → Each step generates TWO outputs:
     1. Work output (normal result)
     2. Learning note (Zettelkasten format)

Learning note format:
  - Title: [Concept]
  - Context: [Why this matters]
  - Key points: [Bullet list]
  - Connections: [Links to related notes]
  - Source: [Where this came from]
  - Confidence: [L0-L4]

Export targets:
  - Obsidian vault
  - Notion workspace
  - Markdown file tree
```

**Default:** OFF (learning notes add 20% overhead)

---

## 16. Edge Cases & Conflict Resolution

### Edge Cases by Stage

| Stage | Edge Case | Handling |
|-------|-----------|----------|
| **RECEIVE** | Ambiguous request | Clarify at QUALIFY (max 3 rounds) |
| **QUALIFY** | Insufficient context after 3 rounds | Auto-research OR proceed with best-effort + warn |
| **DEFINE** | Conflicting criteria | Ask user to prioritize |
| **DECOMPOSE** | Circular dependencies | Break cycle, mark subtask as sequential fallback |
| **EXECUTE** | Subtask timeout | Retry once, then skip with warning |
| **VALIDATE** | Quality metrics unavailable | Use L0 (no verification) + log gap |
| **ANALYZE** | Partial pass (some criteria met) | Iterate on failed criteria only |
| **ITERATE** | Max iterations reached | User decision (4 options, §11) |

### Conflict Types & Resolution

| Conflict | Example | Resolution |
|----------|---------|------------|
| **Criteria vs Method** | Criteria: "100% test coverage", Method: "Legacy code untestable" | Relax criteria OR change method (user decides) |
| **Domain vs Authorization** | Domain: Security scan, Auth: READ only | BLOCK + request permission upgrade |
| **Tier vs Time** | Tier 3 (12 steps), User: "Quick answer" | Downgrade to Tier 1, warn about reduced thoroughness |
| **Quality vs Speed** | High quality (3-15 iter), User: "Fast" | Reduce min iterations, document trade-off |
| **Subagent vs Budget** | Plan: 10 agents, Budget: Low | Use haiku, reduce concurrency, or ask user to increase budget |
| **Frozen Criteria vs New Info** | Midway discovery: "Criteria impossible" | Notify user, offer criteria unfreeze |

---

## 17. Consistency & Self-Protection

### 3 Consistency Levels

| Level | Scope | Check Frequency | Cost |
|-------|-------|-----------------|------|
| **L1** | Internal (single subtask) | Every iteration | Low (1-2% overhead) |
| **L2** | Cross-subtask (DAG integrity) | After each subtask group | Medium (5% overhead) |
| **L3** | Global (entire task + criteria) | At ANALYZE step | High (10-15% overhead) |

**Default:** Tier 1=L1, Tier 2=L2, Tier 3=L3

### Self-Protection Rules

```
├─► UEP cannot modify itself during execution (pipeline structure frozen)
├─► UEP cannot delete mandatory steps (12 steps immutable)
├─► UEP can skip optional steps IF tier allows (e.g., Tier 1 skips RESEARCH)
├─► UEP must log all skip decisions (audit trail)
└─► User can override pipeline order ONLY with explicit "override UEP" command
```

---

## 18. Model Selection Economy

### Model Selection Matrix

| Use Case | Model | Cost (Relative) | When to Use |
|----------|-------|-----------------|-------------|
| **Data extraction** | haiku | 1x | Parse JSON, extract fields, format conversion |
| **Simple scripts** | haiku | 1x | <50 lines, no complex logic |
| **Standard dev** | sonnet | 15x | Normal implementation, 50-500 lines |
| **Complex logic** | sonnet | 15x | Algorithms, state machines, 500+ lines |
| **Security audit** | opus | 75x | CVE analysis, exploit research |
| **Critical systems** | opus | 75x | Production infra, irreversible operations |
| **Research** | sonnet | 15x | Fact gathering, source validation |
| **Coordination** | haiku | 1x | Aggregate outputs, merge results |

### Cost Targets (Per Task)

| Tier | Target Cost | Typical Model Mix |
|------|-------------|-------------------|
| **Tier 1** | <$0.01 | 100% haiku OR single sonnet inline |
| **Tier 2** | $0.01-0.10 | 20% haiku (coord), 80% sonnet (work) |
| **Tier 3** | $0.10-1.00 | 40% haiku (coord/data), 50% sonnet (work), 10% opus (critical) |

**Strategy:** Start cheap (haiku research) → escalate if needed (sonnet implement) → opus only for critical validation

---

## 19. Integration with Existing Systems

### Which System Used at Which Step

| Step | System(s) Used |
|------|----------------|
| **RECEIVE** | Complexity scorer (role-routing.md keywords) |
| **QUALIFY** | Context sufficiency (role-routing.md), Domain routing (role-routing.md) |
| **DEFINE** | GRC extraction (this rule), Authorization levels (authorization-levels.md) |
| **DECOMPOSE** | Subagent orchestration (subagent-orchestration.md), DAG builder (orchestration patterns) |
| **PLAN** | AWB assembly (this rule), Prompting techniques (prompting-techniques.md) |
| **RESEARCH** | Anti-hallucination (anti-hallucination.md), Source validation (L0-L4), WebSearch tool |
| **EXECUTE** | Skills (/skillname), Modules (domain knowledge), MCP profiles (tools), Few-shot examples, 8-phase workflow (modules/14-implementation-workflow.md) |
| **COLLECT** | File passing (scratchpad), Subagent resume |
| **VALIDATE** | Code review (code-before-write.md), Mandatory checks (mandatory-checks.md), Domain metrics |
| **ANALYZE** | Criteria evaluation (this rule), Gap detection (gap-detection.md) |
| **ITERATE** | Refinement logic (this rule), Subagent enrichment |
| **DELIVER** | Response format (response-format.md), Session summary, Automation analysis |

### Override Commands

| Command | Effect |
|---------|--------|
| **"Skip UEP"** | Execute directly without pipeline (Tier 1 equivalent) |
| **"Force Tier X"** | Override automatic tier assignment |
| **"No iterations"** | Single-pass execution (ignore min iteration rules) |
| **"Unfreeze criteria"** | Allow criteria changes mid-execution |
| **"Max agents X"** | Override concurrent agent limit |
| **"Budget bypass"** | Ignore cost constraints (use with caution) |

---

## 20. Quick Decision Trees

### Should I Use UEP?

```
Is this a task request (not a conversation)?
├─► YES → Run complexity scoring
│   ├─► Score 0-19 → Tier 1 (UEP lite: qualify→execute→deliver)
│   ├─► Score 20-59 → Tier 2 (UEP standard: 7 steps)
│   └─► Score 60-100 → Tier 3 (UEP full: 12 steps)
└─► NO → Normal conversational response (no UEP)
```

### Should I Iterate?

```
Are all criteria met?
├─► YES → DELIVER
└─► NO → Is iter < max (15)?
    ├─► YES → Are fails fixable?
    │   ├─► YES → ITERATE (refine approach)
    │   └─► NO → User decision (relax/change/abandon)
    └─► NO (max reached) → User decision (4 options)
```

### Should I Use Subagents?

```
Is task Tier 3 (score 60+)?
├─► YES → Can subtasks run in parallel?
│   ├─► YES → Use parallel subagents (single Task call)
│   └─► NO → Use sequential subagents (chained Task calls)
└─► NO (Tier 1-2) → Execute inline OR single subagent
```

### Should I Research?

```
Is information needed from outside training data?
├─► YES → Is it critical (security/compliance/current)?
│   ├─► YES → RESEARCH step mandatory (WebSearch + validate L3+)
│   └─► NO → Optional (auto-research if 3 clarification rounds fail)
└─► NO → Use training data + modules/examples
```

---

## 21. Anti-Patterns

| Anti-Pattern | Why Bad | Correct Approach |
|--------------|---------|------------------|
| **Method before GRC** | Locks approach too early | Define Goal→Result→Criteria→THEN Method |
| **Criteria change mid-iteration** | Scope creep, inconsistent eval | Freeze criteria at DEFINE, unfreeze only if user requests |
| **Skipping QUALIFY** | Missing context → wrong solution | Always qualify (even Tier 1) |
| **Opus for everything** | 75x cost waste | Use haiku/sonnet, opus only for critical |
| **No iteration on Tier 2/3** | Low quality output | Min 3 iterations, validate criteria each time |
| **Ignoring quality metrics** | Broken code delivered | Apply domain metrics at VALIDATE |
| **No automation analysis** | Repeated manual work | Ask 4 questions at DELIVER |
| **Violating max limits** | Infinite loops, API rate limits | Enforce 15 iter, 3 depth, 20 agents, 10min timeout |

---

## 22. Monitoring & Metrics

### UEP Performance Metrics

```
Tracked automatically by hooks:
├─► Tier distribution (% of tasks in T1/T2/T3)
├─► Avg iterations per tier
├─► Criteria pass rate (% tasks meeting all criteria)
├─► Automation conversion rate (% tasks→hooks/skills/anacron)
├─► Cost per tier (actual vs target)
└─► Time per tier (avg duration)

View: python ~/.claude/evaluation/metrics_tracker.py --report uep
```

### Quality Gates (Block DELIVER if fails)

| Gate | Condition | Block Level |
|------|-----------|-------------|
| **Critical criteria fail** | Any criterion marked CRITICAL fails | BLOCK (must iterate) |
| **Security scan fail** | HIGH/CRITICAL CVEs found | BLOCK (must fix) |
| **Test coverage fail** | Coverage <80% on new code | BLOCK (must add tests) |
| **Secrets detected** | API keys/passwords in output | BLOCK (must remove) |
| **Max iterations** | 15 reached without pass | BLOCK (user decision) |

---

## 23. Glossary (Quick Reference)

| Term | Meaning |
|------|---------|
| **UEP** | Universal Execution Pipeline (this system) |
| **GRC** | Goal-Result-Criteria (definition order) |
| **AWB** | Atomic Work Block (reusable pipeline component) |
| **DAG** | Directed Acyclic Graph (dependency structure) |
| **L0-L4** | Source verification levels (0=none, 4=tested) |
| **Tier 1/2/3** | Complexity tiers (Simple/Standard/Complex) |
| **Criteria Freeze** | Locked success conditions during execution |
| **Subagent Enrichment** | Adding context to subagent prompts (9 items) |
| **Scratchpad** | Temp directory for inter-agent file passing |
| **Quality Gate** | Pass/fail checkpoint at VALIDATE |

---

**Full Documentation:** `modules/23-execution-pipeline.md` (3000+ lines with examples, edge cases, and complete workflows)

**Version:** 1.0.0
**Lines:** ~700
**Style:** Quick reference / cheat sheet
**Integration:** Auto-loaded on every request, orchestrates all other systems
