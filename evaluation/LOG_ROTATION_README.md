# Log Rotation System for Claude Code Evaluation Data

## Overview

Comprehensive log rotation and data cleanup system for Claude Code evaluation JSONL files and logs.

**Created:** 2026-02-06
**Components:** 2 logrotate configs, 1 cleanup script, 3 anacron jobs

---

## Components

### 1. Main Log Rotation (`~/.claude/logrotate.conf`)

**Purpose:** Rotate standard log files and generic evaluation data.

**Coverage:**
- `~/.claude/logs/*.log` — Weekly rotation, keep 4 weeks
- `~/.claude/evaluation/data/*.jsonl` — Weekly rotation, keep 4 weeks
- Tool chains, benchmarks, red team results — Monthly rotation

**Run by:** `daily_logrotate` anacron job (daily at 3min delay)

### 2. Evaluation Data Rotation (`~/.claude/evaluation/logrotate.conf`)

**Purpose:** Fine-grained rotation for specific evaluation data files.

**Coverage Groups:**

| Group | Files | Rotation | Retention |
|-------|-------|----------|-----------|
| **Core Metrics** | budget_spending, token_usage, cache_events, agent_metrics, etc. | Weekly | 4 weeks |
| **Security** | injection_alerts, security_eval, owasp_scan_results, safety_tests | Monthly | 12 months (compliance) |
| **RAG & Sources** | rag_evaluation, source_quality, web_verifications | Monthly | 6 months |
| **Benchmarks** | benchmark_metrics, a2a_validation, hitl_history | Monthly | 6 months |
| **Tool Chains** | Session-specific tool chains | Monthly | 3 months |
| **Critical Logs** | cot_safety.log, security_audit.log, infra_audit.log | Weekly | 8 weeks |

**Run by:** `logrotate_eval` anacron job (weekly at 25min delay)

### 3. Data Cleanup Script (`~/.claude/tools/data_cleanup.py`)

**Purpose:** Archive and truncate large JSONL files to prevent disk bloat.

**Features:**
- Archives files >10MB to `~/.claude/evaluation/data/archive/`
- Truncates files >50MB to last 1000 entries (with compressed backup)
- Removes archived files older than 6 months
- Generates JSON reports in `cleanup_reports/`

**Run by:** `data_cleanup_weekly` anacron job (weekly at 55min delay)

---

## Anacron Jobs

### Job 1: daily_logrotate
```bash
1  3  daily_logrotate  logrotate --state ~/.claude/logrotate.state ~/.claude/logrotate.conf
```
- **Frequency:** Daily
- **Delay:** 3 minutes after anacron start
- **Config:** `~/.claude/logrotate.conf`

### Job 2: logrotate_eval
```bash
7  25  logrotate_eval  /usr/sbin/logrotate --state ~/.claude/evaluation/data/logrotate.state ~/.claude/evaluation/logrotate.conf
```
- **Frequency:** Weekly (every 7 days)
- **Delay:** 25 minutes after anacron start
- **Config:** `~/.claude/evaluation/logrotate.conf`

### Job 3: data_cleanup_weekly
```bash
7  55  data_cleanup_weekly  python3 ~/.claude/tools/data_cleanup.py
```
- **Frequency:** Weekly (every 7 days)
- **Delay:** 55 minutes after anacron start
- **Script:** `~/.claude/tools/data_cleanup.py`

---

## File Structure

```
~/.claude/
├── logrotate.conf                          # Main logrotate config
├── logrotate.state                         # Main rotation state
├── logs/
│   ├── *.log                              # Standard log files
│   └── *.log-YYYYMMDD.gz                  # Rotated logs (compressed)
├── evaluation/
│   ├── logrotate.conf                     # Evaluation-specific config
│   ├── data/
│   │   ├── *.jsonl                        # Current data files
│   │   ├── *.jsonl-YYYYMMDD               # Rotated files (uncompressed)
│   │   ├── *.jsonl-YYYYMMDD.gz            # Rotated files (compressed)
│   │   ├── logrotate.state                # Evaluation rotation state
│   │   ├── archive/                       # Archived large files
│   │   │   └── *_YYYYMMDD_HHMMSS.jsonl
│   │   ├── cleanup_reports/               # Cleanup reports
│   │   │   └── cleanup_YYYYMMDD_HHMMSS.json
│   │   └── tool_chains/
│   │       └── session_*.jsonl            # Per-session tool chains
└── tools/
    └── data_cleanup.py                    # Cleanup script
```

---

## Usage

### Manual Rotation

**Rotate main logs:**
```bash
logrotate --state ~/.claude/logrotate.state ~/.claude/logrotate.conf
```

**Rotate evaluation data:**
```bash
logrotate --state ~/.claude/evaluation/data/logrotate.state ~/.claude/evaluation/logrotate.conf
```

**Force rotation (even if not needed):**
```bash
logrotate --force --state ~/.claude/logrotate.state ~/.claude/logrotate.conf
```

### Manual Cleanup

**Dry-run (show what would be done):**
```bash
python3 ~/.claude/tools/data_cleanup.py --dry-run
```

**Run cleanup:**
```bash
python3 ~/.claude/tools/data_cleanup.py
```

**Custom thresholds:**
```bash
python3 ~/.claude/tools/data_cleanup.py --archive-threshold 20 --truncate-threshold 100
```

### Test Configs

**Test logrotate syntax:**
```bash
logrotate -d ~/.claude/logrotate.conf
logrotate -d ~/.claude/evaluation/logrotate.conf
```

**Verbose mode (see what would happen):**
```bash
logrotate -v --state ~/.claude/logrotate.state ~/.claude/logrotate.conf
```

---

## Rotation Policies

### Core Evaluation Data (Weekly)
- **Trigger:** Weekly OR size >10MB
- **Retention:** 4 weeks (28 days)
- **Compression:** Delayed (1 week)
- **Method:** copytruncate (no process restart needed)

### Security Data (Monthly)
- **Trigger:** Monthly OR size >20MB
- **Retention:** 12 months (compliance requirement)
- **Compression:** Delayed (1 month)
- **Method:** copytruncate

### Logs (Weekly)
- **Trigger:** Weekly OR size >5MB
- **Retention:** 8 weeks (56 days)
- **Compression:** Delayed (1 week)
- **Method:** copytruncate

---

## Thresholds

| Threshold | Value | Action |
|-----------|-------|--------|
| **Archive Threshold** | 10MB | Move file to archive/, create new empty file |
| **Truncate Threshold** | 50MB | Keep last 1000 entries, backup original (compressed) |
| **Archive Retention** | 180 days | Delete archived files older than 6 months |
| **Security Retention** | 365 days | Keep security data for 1 year (compliance) |
| **Tool Chain Retention** | 90 days | Clean old session tool chains after 3 months |

---

## Monitoring

### Check Rotation Status

**View last rotation times:**
```bash
cat ~/.claude/logrotate.state | tail -20
cat ~/.claude/evaluation/data/logrotate.state | tail -20
```

**Check file sizes:**
```bash
du -sh ~/.claude/evaluation/data/*.jsonl | sort -hr | head -10
```

**Check archived files:**
```bash
ls -lh ~/.claude/evaluation/data/archive/ | tail -20
```

### Review Cleanup Reports

**Latest cleanup report:**
```bash
ls -lt ~/.claude/evaluation/data/cleanup_reports/ | head -5
cat $(ls -t ~/.claude/evaluation/data/cleanup_reports/*.json | head -1) | jq .
```

### Anacron Logs

**View logrotate output:**
```bash
journalctl -t logrotate-eval | tail -50
```

**View cleanup output:**
```bash
journalctl -t data-cleanup | tail -50
```

---

## Troubleshooting

### Issue: Files not rotating

**Check:**
1. Verify anacron is running: `systemctl status anacron`
2. Check anacron spool: `ls -l /var/spool/anacron/`
3. Force rotation: `logrotate --force --state ~/.claude/logrotate.state ~/.claude/logrotate.conf`
4. Check permissions: `ls -l ~/.claude/evaluation/data/logrotate.state`

### Issue: Disk space still growing

**Check:**
1. Find largest files: `du -sh ~/.claude/evaluation/data/* | sort -hr | head -20`
2. Run cleanup manually: `python3 ~/.claude/tools/data_cleanup.py`
3. Check if compression working: `ls -lh ~/.claude/evaluation/data/*.gz`
4. Force rotation: `logrotate --force --state ~/.claude/evaluation/data/logrotate.state ~/.claude/evaluation/logrotate.conf`

### Issue: Rotation errors in logs

**Common causes:**
1. **Permission denied**: Check file ownership and permissions
2. **No space left**: Free up disk space first
3. **File in use**: `copytruncate` method should handle this, check config

**Debug:**
```bash
# Verbose test mode
logrotate -v -d ~/.claude/evaluation/logrotate.conf

# Check specific file
strace logrotate --force --state /tmp/test.state ~/.claude/evaluation/logrotate.conf 2>&1 | grep -A5 budget_spending
```

### Issue: Cleanup script fails

**Check:**
1. Python version: `python3 --version` (requires 3.8+)
2. Dependencies: All stdlib, no external deps needed
3. Permissions: `ls -l ~/.claude/tools/data_cleanup.py`
4. Run with debug: `python3 -u ~/.claude/tools/data_cleanup.py --dry-run`

---

## Configuration Changes

### Add New File to Rotation

**Edit:** `~/.claude/evaluation/logrotate.conf`

**Add to appropriate group:**
```logrotate
# Core evaluation JSONL files (weekly, keep 1 month)
/home/user/.claude/evaluation/data/budget_spending.jsonl
/home/user/.claude/evaluation/data/token_usage.jsonl
/home/user/.claude/evaluation/data/YOUR_NEW_FILE.jsonl  # ← Add here
{
    weekly
    rotate 4
    ...
}
```

### Change Rotation Frequency

**Edit retention (number of rotations to keep):**
```logrotate
rotate 4    # Keep 4 rotations (4 weeks for weekly rotation)
rotate 8    # Keep 8 rotations (8 weeks for weekly rotation)
rotate 12   # Keep 12 rotations (12 months for monthly rotation)
```

### Change Cleanup Thresholds

**Edit:** `~/.claude/tools/data_cleanup.py`

```python
ARCHIVE_THRESHOLD_MB = 10   # Default: 10MB
TRUNCATE_THRESHOLD_MB = 50  # Default: 50MB
TRUNCATE_KEEP_ENTRIES = 1000  # Default: 1000 entries
```

**Or pass as arguments:**
```bash
python3 ~/.claude/tools/data_cleanup.py --archive-threshold 20 --truncate-threshold 100
```

---

## Best Practices

1. **Monitor disk usage weekly:**
   ```bash
   df -h ~/.claude/evaluation/data
   du -sh ~/.claude/evaluation/data/
   ```

2. **Review cleanup reports monthly:**
   ```bash
   ls -lt ~/.claude/evaluation/data/cleanup_reports/ | head -5
   ```

3. **Check rotation state:**
   ```bash
   cat ~/.claude/evaluation/data/logrotate.state | grep -E "jsonl|log"
   ```

4. **Backup important data before cleanup:**
   - Security evaluation results (kept 12 months)
   - Compliance audit data (kept 12 months)
   - Benchmark results (kept 6 months)

5. **Test changes in dry-run mode:**
   ```bash
   logrotate -d ~/.claude/evaluation/logrotate.conf
   python3 ~/.claude/tools/data_cleanup.py --dry-run
   ```

---

## Compliance Notes

**Security Data Retention:**
- OWASP compliance data: 12 months
- Security evaluation results: 12 months
- Audit logs: 8 weeks (standard) / 12 months (security)

**GDPR/ФЗ-152:**
- No personal data in evaluation files
- Automatic cleanup after retention period
- Archived files removed after 6 months

---

## References

- Logrotate man page: `man logrotate`
- Anacron configuration: `~/.anacron/anacrontab`
- Logrotate config syntax: `/usr/share/doc/logrotate/examples/`
- Claude Code evaluation: `~/.claude/evaluation/`

---

## Change Log

### 2026-02-06
- ✅ Created main logrotate config (`~/.claude/logrotate.conf`)
- ✅ Created evaluation logrotate config (`~/.claude/evaluation/logrotate.conf`)
- ✅ Created data cleanup script (`~/.claude/tools/data_cleanup.py`)
- ✅ Added 3 anacron jobs (daily_logrotate, logrotate_eval, data_cleanup_weekly)
- ✅ Created archive and cleanup_reports directories
- ✅ Tested all components (dry-run mode)
- ✅ Verified syntax of all configs and scripts

---

**Status:** ✅ ACTIVE
**Automation:** ENABLED
**Next Review:** 2026-02-13 (weekly)
