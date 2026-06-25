# Core Metrics — Quick Reference

**Purpose:** Compact reference for agent performance evaluation metrics.

**Full Documentation:** `/opt/project/docs/CORE_METRICS_DEFINITION.md`

---

## 4-Tier Metric Taxonomy

### TIER 1: Quality (4 metrics)

| Metric | Baseline | Stretch | Measurement |
|--------|----------|---------|-------------|
| **Task Success Rate** | ≥90% | ≥95% | Tasks completed correctly / Total tasks |
| **First-Attempt Success** | ≥75% | ≥85% | Correct on first try / Total tasks |
| **Factual Accuracy** | ≥95% | ≥98% | True claims / Total claims |
| **User Satisfaction** | ≥4.0/5.0 | ≥4.5/5.0 | User rating (1-5 scale) |

### TIER 2: Efficiency (5 metrics)

| Metric | Baseline | Stretch | Measurement |
|--------|----------|---------|-------------|
| **Tokens per Task** | ≤15k | ≤10k | Total tokens / Tasks completed |
| **Latency (TTFT)** | ≤8s | ≤5s | Time to first token (avg) |
| **Cost per Task** | ≤$0.50 | ≤$0.30 | Total cost / Tasks completed |
| **Cache Hit Rate** | ≥85% | ≥92% | Cache hits / Total requests |
| **Tool Calls per Task** | ≤8 | ≤5 | Tool invocations / Task |

### TIER 3: Coverage (4 metrics)

| Metric | Baseline | Stretch | Measurement |
|--------|----------|---------|-------------|
| **Feature Coverage** | ≥80% | ≥90% | Documented features / Total features |
| **Example Coverage** | ≥70% | ≥85% | Features with examples / Total features |
| **Test Coverage** | ≥80% | ≥90% | Tested features / Total features |
| **Gap Resolution Rate** | ≥3/week | ≥5/week | Gaps closed / Week |

### TIER 4: Reliability (4 metrics)

| Metric | Baseline | Stretch | Measurement |
|--------|----------|---------|-------------|
| **Uptime** | ≥99.5% | ≥99.9% | Available time / Total time |
| **Error Rate** | ≤2% | ≤1% | Failed tasks / Total tasks |
| **Hallucination Rate** | ≤1% | ≤0.5% | False claims / Total claims |
| **Tool Failure Rate** | ≤3% | ≤1% | Failed tool calls / Total calls |

---

## Quick Commands

```bash
# Generate metrics report
python ~/.claude/evaluation/metrics_tracker.py --report

# Check specific metric
python ~/.claude/evaluation/metrics_tracker.py --metric task_success_rate

# Weekly summary
python ~/.claude/evaluation/metrics_tracker.py --period week

# Monthly dashboard
python ~/.claude/evaluation/metrics_tracker.py --dashboard
```

---

## Reporting Frequency

| Report Type | Frequency | Audience | Format |
|-------------|-----------|----------|--------|
| **Real-time** | Per-task | Agent/Developer | Console log |
| **Daily** | End of day | Developer | Slack/Email |
| **Weekly** | Monday AM | Team | Dashboard |
| **Monthly** | 1st of month | Stakeholders | PDF Report |
| **Quarterly** | Quarterly | Leadership | Executive Summary |

---

## Thresholds & Alerts

**P1 CRITICAL (Immediate Action):**
- Task Success Rate < 85%
- Hallucination Rate > 2%
- Uptime < 99%

**P2 HIGH (Review within 24h):**
- First-Attempt Success < 70%
- Error Rate > 3%
- Cost per Task > $0.60

**P3 MEDIUM (Review weekly):**
- Tokens per Task > 18k
- Tool Calls per Task > 10
- Gap Resolution Rate < 2/week

---

## Integration with metrics_tracker.py

**Expected file locations:**
- Session logs: `~/.claude/evaluation/data/sessions/`
- Metrics DB: `~/.claude/evaluation/data/metrics.db`
- Reports: `~/.claude/evaluation/data/reports/`

**Metrics collection:**
- Automatic: Session hooks capture data
- Manual: User feedback via `/feedback` command
- Hybrid: Automated + periodic manual review

---

**Version:** 1.0.0
**Last Updated:** 2026-01-27
**Related:** research_workflow.md, validation_workflow.md
