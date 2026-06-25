# Example: Prompt Optimization Cycle

## User Request

```
Claude часто дает слишком длинные ответы. Как оптимизировать промпт?
```

## Reasoning

**Domain:** Maturity (prompt engineering)
**Complexity:** Simple
**Model:** Haiku

## Response

### Optimization Cycle (PDCA)

```
┌────────────────────────────────────────────────────────────┐
│  1. PLAN — Identify issue                                  │
│     Problem: Responses too verbose                         │
│     Metric: Avg response length 500 words (target: 200)    │
│     Hypothesis: Missing brevity instruction                │
├────────────────────────────────────────────────────────────┤
│  2. DO — Test change                                       │
│     Add to CLAUDE.md: "Keep responses under 200 words"    │
│     Test on 10 sample queries                             │
├────────────────────────────────────────────────────────────┤
│  3. CHECK — Measure impact                                 │
│     New avg: 180 words ✅                                  │
│     User satisfaction: +20%                                │
├────────────────────────────────────────────────────────────┤
│  4. ACT — Deploy or iterate                                │
│     If success → commit change                             │
│     If failure → rollback, try alternative                 │
└────────────────────────────────────────────────────────────┘
```

### Prompt Optimization Techniques

**1. Brevity Control:**
```markdown
# Before
[No instruction]

# After
Response Requirements:
- Keep under 200 words for simple queries
- Use bullet points over paragraphs
- Only expand for complex topics (user request)
```

**2. Output Format Control:**
```markdown
# Before
Explain X

# After
Explain X using:
- 1 sentence summary
- 3 bullet points
- 1 example
- Max 150 words total
```

**3. Tone Adjustment:**
```markdown
# Before
[Default tone]

# After
Communication Style:
- Professional, not academic
- Direct, no filler words
- No excessive praise ("Great question!", "Excellent!")
```

### A/B Testing Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Avg response length | 500 words | 180 words | -64% ✅ |
| Time to useful info | 30s reading | 10s reading | -67% ✅ |
| User "too long" feedback | 15% | 2% | -87% ✅ |

---

## Key Takeaways

1. **Measure before optimizing** — baseline metrics required
2. **Test incrementally** — change one thing at a time
3. **A/B test on samples** — 10-20 queries sufficient
4. **Document rationale** — why this change, what problem it solves
5. **Version prompts** — track changes in git for rollback

**Process:** Problem → Hypothesis → Test → Measure → Deploy/Iterate
