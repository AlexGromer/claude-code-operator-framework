# Validation Framework — Quick Reference

**Purpose:** Compact instructions for relevance scoring and PoC testing.

**Full Documentation:** `/opt/project/docs/VALIDATION_FRAMEWORK.md`

---

## Relevance Scoring (5-Dimension Matrix)

**Tool:** `~/.claude/tools/score_discovery.py`

**Usage:**
```bash
# Quick scoring
python ~/.claude/tools/score_discovery.py \
  --title "Discovery Title" \
  --github-url "https://github.com/org/repo" \
  --arxiv-id "2406.12345"

# From JSON file
python ~/.claude/tools/score_discovery.py \
  --input discovery.json \
  --output scored.json
```

**Input Format (discovery.json):**
```json
{
  "title": "Chain-of-Verification for Reducing Hallucinations",
  "description": "Novel prompting technique...",
  "github_url": "https://github.com/anthropics/cove",
  "arxiv_id": "2309.11495",
  "category": "prompting",
  "date_discovered": "2026-01-27"
}
```

---

## Scoring Dimensions

| Dimension | Weight | Max Points | Description |
|-----------|--------|------------|-------------|
| **D1** | 30% | 30 | CLI Applicability (tool-use, agent, automation) |
| **D2** | 25% | 25 | Production Readiness (stable, tested, documented) |
| **D3** | 20% | 20 | Performance Impact (quality/cost/latency gains) |
| **D4** | 15% | 15 | Adoption Velocity (stars, citations, traction) |
| **D5** | 10% | 10 | Integration Effort (inverse: lower effort = higher score) |

**Total:** 0-100 points (weighted sum)

---

## Decision Thresholds

| Score | Priority | Action | Timeline |
|-------|----------|--------|----------|
| **80-100** | P1 CRITICAL | Immediate PoC | <1 week |
| **60-79** | P2 HIGH | Planned PoC | <1 month |
| **40-59** | P3 MEDIUM | Backlog | <1 quarter |
| **0-39** | ARCHIVE | Monitor only | — |

---

## PoC Testing Protocol (4 Stages, 6-10h Total)

### Stage 1: Discovery Analysis (1-2h)
**Time Box:** Max 2 hours

**Tasks:**
- [ ] Read paper/documentation
- [ ] Identify core claim (quality/cost/latency improvement)
- [ ] Extract key techniques
- [ ] Define success criteria

**Output:** Analysis document with hypothesis

---

### Stage 2: Minimal Implementation (2-4h)
**Time Box:** Max 4 hours

**Tasks:**
- [ ] Implement minimal viable version
- [ ] Create baseline comparison
- [ ] Write test harness

**Output:** Working PoC code (poc_*.py)

---

### Stage 3: Benchmark Testing (2-3h)
**Time Box:** Max 3 hours

**Tasks:**
- [ ] Run baseline tests (10-20 examples)
- [ ] Run PoC tests (same examples)
- [ ] Measure metrics (quality/cost/latency)
- [ ] Calculate improvement %

**Output:** Benchmark results with statistical significance

---

### Stage 4: Go/No-Go Decision (1h)
**Time Box:** Max 1 hour

**Success Criteria (ANY of):**
- ✅ ≥10% quality improvement (accuracy, hallucination rate)
- ✅ ≥20% cost reduction (tokens, API cost)
- ✅ ≥30% latency reduction (time to first token)
- ✅ Novel capability (previously impossible task)

**Decision:**
- **GO:** Create gap, plan integration
- **NO-GO:** Archive findings, document learnings

---

## Example: Quick Scoring

```bash
# Score Chain-of-Verification technique
python ~/.claude/tools/score_discovery.py \
  --title "Chain-of-Verification reduces hallucinations" \
  --github-url "https://github.com/anthropics/cove" \
  --arxiv-id "2309.11495" \
  --description "Generate claims, verify each, revise response" \
  --output /tmp/cove_score.json

# Expected output:
# D1: 28/30 (high CLI applicability - agent enhancement)
# D2: 20/25 (beta quality, growing adoption)
# D3: 18/20 (major quality improvement - hallucination reduction)
# D4: 12/15 (strong GitHub traction)
# D5: 8/10 (moderate integration effort - prompting change)
# Total: 82/100 → P1 CRITICAL (immediate PoC <1 week)
```

---

## PoC Code Template

**Location:** `/tmp/claude/-opt-your-project/*/scratchpad/`

**Structure:**
```
poc_TECHNIQUE_NAME/
├── poc_implementation.py   # PoC code
├── baseline.py             # Baseline comparison
├── benchmark.py            # Test harness
├── results.json            # Metrics
└── README.md               # Findings
```

**Template:**
```python
# poc_cove.py
import anthropic
import os

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-5-20250929"

def baseline_generate(query):
    """Standard generation (baseline)."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": query}]
    )
    return response.content[0].text

def cove_generate(query):
    """Chain-of-Verification generation (PoC)."""
    # Step 1: Generate baseline response
    baseline = baseline_generate(query)

    # Step 2: Extract claims (simplified)
    claims = extract_claims(baseline)

    # Step 3: Verify each claim
    verifications = {}
    for claim in claims[:5]:  # Limit to top 5
        verifications[claim] = verify_claim(claim)

    # Step 4: Revise response based on verifications
    revised = revise_response(baseline, verifications)

    return revised, verifications

# Benchmark: run 10-20 examples, measure hallucination rate
```

---

## Quick Commands

```bash
# Score discovery
cd ~/.claude/tools && python score_discovery.py --title "..." --github-url "..."

# View scoring dimensions breakdown
cat /tmp/scored.json | jq '.scores'

# Check if PoC recommended
cat /tmp/scored.json | jq '.recommended_action'
```

---

**Version:** 1.0.0
**Last Updated:** 2026-01-27
**Related:** research_workflow.md, CORE_METRICS_DEFINITION.md
