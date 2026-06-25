# Few-Shot Example: Chain-of-Thought vs ReAct

## Task
Пользователь: "Объясни разницу между CoT и ReAct. Когда использовать каждый?"

## Solution

### Quick Answer

- **Chain-of-Thought (CoT):** Reasoning BEFORE action (think → answer)
- **ReAct:** Reasoning INTERLEAVED with action (think → act → observe → think → act...)

---

## Part 1: Chain-of-Thought (CoT)

### What It Is

**Prompt pattern:**
```
Question: [problem]
Let's think step by step:
1. [reasoning step 1]
2. [reasoning step 2]
3. [conclusion]
Answer: [final answer]
```

**Key characteristic:** All reasoning happens BEFORE producing final answer.

### Example: Math Word Problem

**Question:**
> A train travels 120 km in 2 hours. How far will it travel in 5 hours at the same speed?

**CoT Response:**
```
Let's think step by step:

1. First, I need to find the speed of the train.
   Speed = Distance / Time = 120 km / 2 hours = 60 km/h

2. Now I can calculate the distance for 5 hours.
   Distance = Speed × Time = 60 km/h × 5 hours = 300 km

3. Therefore, the train will travel 300 km in 5 hours.

Answer: 300 km
```

**No external actions** — pure reasoning.

### When to Use CoT

✅ **Use CoT when:**
- Problem can be solved with internal reasoning only
- No external data needed
- Mathematical or logical problems
- Planning before execution
- Explaining complex concepts

❌ **Don't use CoT when:**
- Need to verify facts during reasoning
- Must access external data (files, APIs)
- Real-time information required
- Multi-step tasks with tool use

---

## Part 2: ReAct (Reasoning + Acting)

### What It Is

**Prompt pattern:**
```
Question: [problem]

Thought 1: [reasoning about what to do]
Action 1: [tool call]
Observation 1: [result from tool]

Thought 2: [reasoning about observation]
Action 2: [another tool call]
Observation 2: [result]

...

Thought N: [final reasoning]
Answer: [conclusion based on observations]
```

**Key characteristic:** Reasoning INTERLEAVED with actions.

### Example: Research Question

**Question:**
> What's the current version of Kubernetes and when was it released?

**ReAct Response:**
```
Thought 1: I need to find the latest Kubernetes release information.
The best source is the official GitHub repository.

Action 1: Use WebSearch
Query: "kubernetes latest release 2026"
Observation 1: Search results show Kubernetes v1.30 was released in April 2024,
and v1.31 is currently in beta.

Thought 2: I should verify this on the official Kubernetes website
to get the most accurate current version.

Action 2: Use WebFetch
URL: https://kubernetes.io/releases/
Observation 2: The page confirms v1.30 is the current stable release,
released on April 17, 2024.

Thought 3: I now have verified information from official sources.
The current stable version is 1.30.

Answer: Kubernetes v1.30 is the current stable version, released on April 17, 2024.
```

**External actions** — reasoning depends on observations.

### When to Use ReAct

✅ **Use ReAct when:**
- Need to access external tools/APIs
- Must verify information during reasoning
- Multi-step tasks requiring feedback
- Real-time data needed
- Exploratory research
- Debugging (need to test hypotheses)

❌ **Don't use ReAct when:**
- Problem solvable with pure reasoning
- No tools available
- Actions are expensive (API costs)
- Deterministic calculation (math)

---

## Part 3: Comparison

| Aspect | Chain-of-Thought (CoT) | ReAct |
|--------|----------------------|-------|
| **Reasoning Style** | Sequential, linear | Iterative, exploratory |
| **Actions** | None (internal only) | Tool calls, API requests |
| **Information** | Uses only given context | Gathers information dynamically |
| **Error Correction** | No (reasoning is final) | Yes (can adapt based on observations) |
| **Speed** | Fast (no I/O) | Slower (waits for tool results) |
| **Cost** | Low (single LLM call) | Higher (multiple tool calls) |
| **Transparency** | Reasoning is visible | Full trace of thought + action |
| **Best For** | Math, logic, planning | Research, coding, debugging |

---

## Part 4: Real-World Examples

### Example 1: Debugging Code (ReAct wins)

**Task:** Find why a Python script fails.

**CoT approach (fails):**
```
Let's think step by step:
1. The error might be in the imports
2. Or it could be a syntax error
3. Or maybe a missing dependency
Answer: Check imports and syntax (not helpful!)
```

**Problem:** Can't actually READ the code or RUN it to see the error.

**ReAct approach (succeeds):**
```
Thought 1: I need to see the code first.
Action 1: Read file script.py
Observation 1: [code content, line 42 has "import missing_module"]

Thought 2: The import might be the issue. Let me try running it.
Action 2: Bash: python script.py
Observation 2: ModuleNotFoundError: No module named 'missing_module'

Thought 3: The module is missing. I should check if it's in requirements.txt.
Action 3: Read requirements.txt
Observation 3: [missing_module is not listed]

Answer: The script fails because 'missing_module' is imported but not
in requirements.txt. Add it: pip install missing_module
```

**Winner:** ReAct (needs external observations)

---

### Example 2: Calculate Compound Interest (CoT wins)

**Task:** Calculate compound interest: $1000 principal, 5% rate, 3 years.

**CoT approach (perfect):**
```
Let's think step by step:
1. Formula: A = P(1 + r)^t
2. Given: P = $1000, r = 0.05, t = 3
3. Calculate: A = 1000 × (1.05)^3
4. (1.05)^3 = 1.157625
5. A = 1000 × 1.157625 = $1,157.63

Answer: $1,157.63
```

**ReAct approach (overkill):**
```
Thought 1: I need to calculate compound interest.
Action 1: Bash: python -c "print(1000 * (1.05)**3)"
Observation 1: 1157.625

Thought 2: Round to 2 decimal places.
Action 2: Bash: python -c "print(round(1000 * (1.05)**3, 2))"
Observation 2: 1157.63

Answer: $1,157.63
```

**Winner:** CoT (no tools needed, pure math)

---

### Example 3: Security Audit (ReAct wins)

**Task:** Audit a repository for hardcoded secrets.

**CoT approach (fails):**
```
Let's think step by step:
1. Secrets are often in .env files
2. Or in configuration files
3. Or hardcoded in source code
Answer: Check .env, config files, and source code (too vague!)
```

**ReAct approach (succeeds):**
```
Thought 1: I need to scan the repository for secrets.
Action 1: Bash: gitleaks detect --no-git --report-path report.json
Observation 1: [3 secrets found: API_KEY in config.py, PASSWORD in .env, TOKEN in deploy.sh]

Thought 2: Let me verify each finding by reading the files.
Action 2: Grep "API_KEY" in config.py
Observation 2: Line 15: API_KEY = "sk-1234567890abcdef"

Thought 3: This is a real secret, not a placeholder.
Action 3: Check git history: git log -p config.py | grep API_KEY
Observation 3: Secret was committed in commit abc123, 2 weeks ago.

Answer: Found 3 hardcoded secrets:
1. API_KEY in config.py (line 15, committed 2 weeks ago)
2. PASSWORD in .env (line 3)
3. TOKEN in deploy.sh (line 42)

Recommendation: Remove secrets, use environment variables or secret manager.
```

**Winner:** ReAct (needs tool execution)

---

## Part 5: Hybrid Approach

**Best practice:** Combine CoT and ReAct

### Pattern: Plan with CoT, Execute with ReAct

**Example: Deploy Application**

**Step 1: CoT Planning**
```
Let's think about the deployment process:

1. Pre-flight checks needed:
   - Run tests
   - Scan for secrets
   - Verify environment

2. Deployment steps:
   - Build container
   - Push to registry
   - Apply Kubernetes manifests
   - Monitor rollout

3. Post-deployment:
   - Health check
   - Send notification

This plan makes sense. Let's execute it.
```

**Step 2: ReAct Execution**
```
Thought 1: First, run tests to ensure code quality.
Action 1: Bash: pytest tests/ --cov
Observation 1: All 42 tests passed, 95% coverage.

Thought 2: Tests passed. Now scan for secrets.
Action 2: Bash: gitleaks detect --no-git
Observation 2: No secrets found.

Thought 3: Pre-flight checks passed. Build container.
Action 3: Bash: docker build -t myapp:v1.2.0 .
Observation 3: Image built successfully.

[... continue with each step ...]
```

**Result:** Best of both worlds — structured planning + adaptive execution.

---

## Part 6: Implementation in Prompts

### CoT Prompt Template

```
You are a helpful assistant. When answering questions,
think step by step before providing the final answer.

Format:
Let's think step by step:
1. [step 1]
2. [step 2]
...
Answer: [final answer]
```

### ReAct Prompt Template

```
You are a helpful assistant with access to tools.
For each task, follow this process:

1. Thought: [reasoning about what to do next]
2. Action: [tool to use and parameters]
3. Observation: [result from tool]

Repeat Thought → Action → Observation until you have enough information.

Then provide your final Answer based on the observations.
```

### Zero-Shot CoT (simplest)

Just add: **"Let's think step by step"**

```
Question: What is 25% of 80?
Let's think step by step:
```

LLM automatically produces:
```
1. 25% means 25/100 or 0.25
2. Multiply 80 by 0.25
3. 80 × 0.25 = 20
Answer: 20
```

---

## Part 7: Performance Comparison

**Benchmark: GSM8K (math word problems)**

| Method | Accuracy | Avg Tokens | Cost (per 100 problems) |
|--------|----------|------------|------------------------|
| Direct answer | 17% | 50 | $0.10 |
| Zero-Shot CoT | 41% | 150 | $0.30 |
| Few-Shot CoT | 58% | 400 | $0.80 |
| ReAct | 35% | 300 | $0.60 |

**Conclusion:** CoT >> ReAct for math (no tools needed).

**Benchmark: HotpotQA (multi-hop questions, requires Wikipedia lookup)**

| Method | Accuracy | Avg Tokens | Avg Tool Calls | Cost |
|--------|----------|------------|----------------|------|
| Direct answer | 12% | 50 | 0 | $0.10 |
| CoT | 28% | 150 | 0 | $0.30 |
| ReAct | 61% | 250 | 4 | $0.70 |

**Conclusion:** ReAct >> CoT when external information needed.

---

## Summary

### Decision Tree

```
┌─────────────────────────────────────────────┐
│  Can the problem be solved with pure        │
│  reasoning (no external data)?              │
└────────────┬──────────────────┬─────────────┘
             │ YES              │ NO
             ▼                  ▼
        ┌─────────┐      ┌──────────┐
        │   CoT   │      │  ReAct   │
        └─────────┘      └──────────┘
        Examples:        Examples:
        - Math           - Research
        - Logic          - Debugging
        - Planning       - API calls
        - Explanation    - Verification
```

### Quick Guide

| Scenario | Method | Reason |
|----------|--------|--------|
| Math word problem | CoT | Pure calculation |
| "What's the weather?" | ReAct | Need API call |
| "Explain quantum computing" | CoT | Concept explanation |
| "Debug this script" | ReAct | Need to read/run code |
| "Plan a deployment" | CoT | Strategic thinking |
| "Execute deployment" | ReAct | Tool execution |
| "Why is 2+2=4?" | CoT | Logical explanation |
| "Find all TODOs in codebase" | ReAct | Need to search files |

---

**Authoritative Sources:**
- Chain-of-Thought Paper: https://arxiv.org/abs/2201.11903
- ReAct Paper: https://arxiv.org/abs/2210.03629
- Prompt Engineering Guide: https://www.promptingguide.ai/
- Claude Prompting: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering
