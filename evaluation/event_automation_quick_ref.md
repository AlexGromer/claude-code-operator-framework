# Event-Based Automation — Quick Reference

**Full Documentation:** `/opt/project/docs/PHASE2_EVENT_BASED_AUTOMATION.md`

---

## Triggers

| Trigger | What Happens | File |
|---------|--------------|------|
| **Daily 10:00** | Anacron checks for pending tasks | anacrontab |
| **5 min after boot** | Runs missed tasks | systemd timer |
| **Session startup** | Digest reminder | session_startup_hook.py |
| **cd to project** | Compact reminder | zshrc_project_hook.sh |

---

## Commands

```bash
# Check for new digest
python ~/.claude/hooks/session_startup_hook.py

# Run interactive workflow
python ~/.claude/tools/research_workflow_agent.py

# Check anacron status
systemctl --user status anacron-research.timer

# View recent digests
ls -lht ~/.claude/evaluation/data/research_digests/

# Mark digest as read
echo "\"$digest_file\"" >> ~/.claude/evaluation/data/.digest_read
```

---

## Anacron Tasks

| Task | Period | Description |
|------|--------|-------------|
| **token_check_daily** | 1 day | Check API token expiry |
| **research_weekly** | 7 days | Generate research digest |
| **metrics_cleanup_weekly** | 7 days | Clean old metrics |
| **stats_weekly** | 7 days | Generate weekly stats |
| **gap_analysis_weekly** | 7 days | Automated gap analysis |

---

## Agent Workflow

```
1. Session startup → reminder appears
2. Run: python research_workflow_agent.py
3. Agent shows: top discoveries + recommended actions
4. Copy prompt to Claude Code session
5. Agent executes: scoring → gap creation → PoC recommendation
```

---

**Version:** 1.0.0
**Status:** ✅ Active
