# Example: GAP Detection & Logging Protocol

## User Request

```
Обнаружил, что Claude не знает о новой фиче Kubernetes 1.29. Как правильно залогировать gap?
```

## Reasoning

**Domain:** Maturity (prompt improvement process)
**Complexity:** Simple
**Model:** Haiku

## Response

### GAP Detection Workflow

```
USER SIGNAL DETECTED: "Claude не знает о X"
        ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: CLASSIFY GAP TYPE                                  │
│  ├─► Knowledge gap (outdated training data)                 │
│  ├─► Coverage gap (missing domain/tool)                     │
│  ├─► Structural gap (missing module/section)               │
│  └─► Process gap (workflow inefficiency)                   │
├─────────────────────────────────────────────────────────────┤
│  STEP 2: ASSIGN PRIORITY                                    │
│  ├─► P1 (Critical): Blocking work, security risk           │
│  ├─► P2 (High): Frequent need, quality impact              │
│  └─► P3 (Medium): Nice-to-have, low frequency              │
├─────────────────────────────────────────────────────────────┤
│  STEP 3: LOG TO GAPS.md                                     │
│  Format:                                                    │
│  ### GAP-[DOMAIN]-[NUMBER]: [Title]                        │
│  **Priority:** P1/P2/P3                                     │
│  **Detected:** [Date]                                       │
│  **Context:** [User feedback / self-detected]              │
│  **Impact:** [Describe consequence]                        │
│  **Solution:** [Proposed fix]                              │
├─────────────────────────────────────────────────────────────┤
│  STEP 4: NOTIFY USER                                        │
│  "⚠️ Gap detected: [description] → Logged as GAP-XXX"      │
└─────────────────────────────────────────────────────────────┘
```

### Example GAP Entry

```markdown
### GAP-KNOWLEDGE-023: Kubernetes 1.29 features missing

**Priority:** P2
**Detected:** 2026-01-27
**Status:** 🔴 Open
**Context:** User asked about StatefulSet ordinal start feature (K8s 1.29+)
**Impact:** Cannot provide guidance on latest K8s features (training cutoff Jan 2025)

**Proposed Solution:**
1. Add K8s 1.29+ release notes to knowledge base
2. Create few-shot example for StatefulSet ordinals
3. Update modules/03-devops.md with K8s version matrix

**Workaround:** Recommend checking official K8s docs for post-training features
```

### Automatic Gap Detection Triggers

| Trigger | Action |
|---------|--------|
| User says "не знаешь", "не умеешь" | Classify as knowledge/capability gap |
| User corrects Claude's response | Log as accuracy gap |
| Tool fails 3+ times | Log as integration gap |
| Coverage <95% in tests | Log as quality gap |
| User repeats question differently | Log as comprehension gap |

---

## Key Takeaways

1. **Capture user feedback** — every "не знаешь" is a signal
2. **Log immediately** — don't wait for session end
3. **Prioritize impact** — P1 blocks work, P2 degrades quality, P3 nice-to-have
4. **Track resolution** — update status when fixed
5. **Notify user** — transparent about limitations

**Target:** <5% knowledge gap rate, <24h resolution for P1
