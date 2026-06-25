# Research-to-Practice Workflow — Quick Reference

**Purpose:** Compact instructions for automated research monitoring and integration.

**Full Documentation:** `/opt/project/docs/RESEARCH_SOURCE_MONITORING.md`

---

## Weekly Research Digest

**Tool:** `~/.claude/tools/research_monitor.py`

**Usage:**
```bash
# Generate weekly digest
python ~/.claude/tools/research_monitor.py

# Save to file
python ~/.claude/tools/research_monitor.py --output ~/digest.md

# Custom period
python ~/.claude/tools/research_monitor.py --since-days 14
```

**Automation:**
```bash
# Install cron job (every Monday 09:00)
bash ~/.claude/tools/setup_cron.sh

# Check status
bash ~/.claude/tools/setup_cron.sh --status

# Uninstall
bash ~/.claude/tools/setup_cron.sh --uninstall
```

**Output Location:** `~/.claude/evaluation/data/research_digests/`

---

## Alert Priority Levels

| Priority | Response Time | Action |
|----------|---------------|--------|
| 🔴 **CRITICAL** | <24h | Immediate review, assess for integration |
| 🟠 **HIGH** | <7 days | Schedule PoC within 1 week |
| 🟡 **MEDIUM** | <30 days | Add to backlog |
| 🟢 **LOW** | Quarterly | Archive for reference |

**Keywords:**
- **CRITICAL:** claude, opus, sonnet, security, vulnerability, breaking
- **HIGH:** api, deprecat, migration, major release, benchmark, sota
- **MEDIUM:** tutorial, guide, best practice, optimization
- **LOW:** blog, discussion, opinion

---

## Source Categories (from AUTHORITATIVE_SOURCES.md)

**Tier 1 (High Trust):**
- Model Providers: Anthropic, OpenAI, Google DeepMind, Meta AI
- Universities: Stanford, MIT, Berkeley, CMU
- Standards: ISO, NIST, IEEE

**Tier 2 (Medium-High Trust):**
- Frameworks: LangChain, LlamaIndex, Hugging Face
- Courses: Anthropic Academy, DeepLearning.AI

**Tier 3 (Medium Trust):**
- Community: Hacker News, Reddit r/MachineLearning, Papers With Code
- Newsletters: The Batch, Import AI

---

## Integration Workflow

```
1. DISCOVERY (automated)
   └─► research_monitor.py generates digest

2. TRIAGE (manual)
   └─► Review digest, flag relevant items

3. SCORING (automated)
   └─► score_discovery.py calculates relevance

4. GAP CREATION (manual)
   └─► Log to GAPS.md with priority

5. PoC TESTING (manual)
   └─► Follow validation_workflow.md

6. INTEGRATION (manual)
   └─► Update modules, commit changes
```

---

## Quick Commands

```bash
# Generate digest for last 14 days
python ~/.claude/tools/research_monitor.py --since-days 14 --output /tmp/digest.md

# View recent digests
ls -lt ~/.claude/evaluation/data/research_digests/ | head -5

# Score a discovery
python ~/.claude/tools/score_discovery.py \
  --title "Chain-of-Verification" \
  --github-url "https://github.com/anthropics/cove" \
  --arxiv-id "2309.11495"
```

---

**Version:** 1.0.0
**Last Updated:** 2026-01-27
**Related:** validation_workflow.md, AUTHORITATIVE_SOURCES.md
