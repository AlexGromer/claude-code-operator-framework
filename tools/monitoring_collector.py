#!/usr/bin/env python3
"""
monitoring_collector.py — cross-session metrics aggregator (backlog e37496c5).

Reads append-only JSONL telemetry and aggregates it into a SQLite DB for
cross-session trend analysis:
  - evaluation/data/metrics.jsonl       — tool calls {ts, tool, session, dur_ms}
  - evaluation/data/agent_metrics.jsonl — subagent spawns {timestamp, subagent_type, session_id}

Watermark (size+mtime per source in collector_state) skips work when a source is
unchanged; on change it FULLY recomputes that source's aggregates (correct counts
AND percentiles). Schema: docs/MONITORING_SYSTEM.md §3.2. stdlib-only.

Usage:  python3 ~/.claude/tools/monitoring_collector.py [--db PATH] [--data DIR]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_tool_stats (
    date TEXT NOT NULL, tool TEXT NOT NULL, call_count INTEGER NOT NULL,
    p50_ms REAL, p95_ms REAL, p99_ms REAL, session_count INTEGER,
    PRIMARY KEY (date, tool));
CREATE TABLE IF NOT EXISTS daily_session_stats (
    date TEXT PRIMARY KEY, session_count INTEGER, total_calls INTEGER);
CREATE TABLE IF NOT EXISTS feature_adoption (
    feature_type TEXT NOT NULL, feature_name TEXT NOT NULL,
    first_seen TEXT, last_seen TEXT, total_calls INTEGER DEFAULT 0,
    sessions_used INTEGER DEFAULT 0, PRIMARY KEY (feature_type, feature_name));
CREATE TABLE IF NOT EXISTS anomaly_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, anomaly_type TEXT NOT NULL,
    metric_name TEXT, observed REAL, expected REAL, sigma REAL, details TEXT);
CREATE TABLE IF NOT EXISTS hook_health (
    date TEXT NOT NULL, hook_name TEXT NOT NULL, fire_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0, last_error TEXT, PRIMARY KEY (date, hook_name));
CREATE TABLE IF NOT EXISTS collector_state (
    source TEXT PRIMARY KEY, last_size INTEGER, last_mtime REAL);
"""


def _pct(vals, p):
    """Linear-interpolated percentile (p in [0,100]); None if no data."""
    assert 0 <= p <= 100, f"p must be a percentage in [0,100], got {p}"
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    if f + 1 < len(s):
        return s[f] + (s[f + 1] - s[f]) * (k - f)
    return s[f]


def _iter_jsonl(path: Path):
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except FileNotFoundError:
        return


def _changed(con, path: Path) -> bool:
    """True if the source file changed since last run (and records the new state)."""
    if not path.exists():
        return False
    st = path.stat()
    row = con.execute("SELECT last_size, last_mtime FROM collector_state WHERE source=?",
                      (str(path),)).fetchone()
    if row and row[0] == st.st_size and abs((row[1] or 0) - st.st_mtime) < 1e-6:
        return False
    con.execute("INSERT OR REPLACE INTO collector_state(source, last_size, last_mtime) VALUES(?,?,?)",
                (str(path), st.st_size, st.st_mtime))
    return True


def collect_tools(con, path: Path):
    """Full recompute of daily_tool_stats + daily_session_stats from metrics.jsonl."""
    by_tool = defaultdict(lambda: defaultdict(lambda: {"n": 0, "durs": [], "sessions": set()}))
    date_sessions = defaultdict(set)
    date_calls = defaultdict(int)
    for r in _iter_jsonl(path):
        date = str(r.get("ts", ""))[:10]
        if not date:
            continue
        tool = r.get("tool", "unknown")
        sess = r.get("session", "")
        cell = by_tool[date][tool]
        cell["n"] += 1
        cell["sessions"].add(sess)
        d = r.get("dur_ms")
        if isinstance(d, (int, float)) and d > 0:
            cell["durs"].append(float(d))
        date_sessions[date].add(sess)
        date_calls[date] += 1

    con.execute("DELETE FROM daily_tool_stats")
    for date, tools in by_tool.items():
        for tool, c in tools.items():
            con.execute("INSERT OR REPLACE INTO daily_tool_stats VALUES(?,?,?,?,?,?,?)",
                        (date, tool, c["n"], _pct(c["durs"], 50), _pct(c["durs"], 95),
                         _pct(c["durs"], 99), len(c["sessions"])))
    con.execute("DELETE FROM daily_session_stats")
    for date in date_sessions:
        con.execute("INSERT OR REPLACE INTO daily_session_stats(date, session_count, total_calls) VALUES(?,?,?)",
                    (date, len(date_sessions[date]), date_calls[date]))


def collect_agents(con, path: Path):
    """Full recompute of feature_adoption (type='agent') from agent_metrics.jsonl."""
    fa = {}
    for r in _iter_jsonl(path):
        name = r.get("subagent_type")
        if not name or name == "unknown":
            continue
        ts = str(r.get("timestamp", ""))
        sess = r.get("session_id", "")
        f = fa.setdefault(name, {"first": ts, "last": ts, "calls": 0, "sessions": set()})
        f["calls"] += 1
        f["sessions"].add(sess)
        if ts and (not f["first"] or ts < f["first"]):
            f["first"] = ts
        if ts and ts > f["last"]:
            f["last"] = ts
    con.execute("DELETE FROM feature_adoption WHERE feature_type='agent'")
    for name, f in fa.items():
        con.execute(
            "INSERT OR REPLACE INTO feature_adoption"
            "(feature_type, feature_name, first_seen, last_seen, total_calls, sessions_used) "
            "VALUES('agent',?,?,?,?,?)",
            (name, f["first"], f["last"], f["calls"], len(f["sessions"])))


def run(db_path, data_dir: Path, force: bool = False):
    # timeout: tolerate a brief overlap with a concurrent (e.g. anacron) run.
    con = sqlite3.connect(str(db_path), timeout=30)
    try:
        con.executescript(SCHEMA)
        metrics = Path(data_dir) / "metrics.jsonl"
        agents = Path(data_dir) / "agent_metrics.jsonl"
        changed = []
        if force or _changed(con, metrics):
            collect_tools(con, metrics)
            changed.append("metrics")
        if force or _changed(con, agents):
            collect_agents(con, agents)
            changed.append("agent_metrics")
        con.commit()
        return {
            "changed": changed,
            "daily_tool_rows": con.execute("SELECT COUNT(*) FROM daily_tool_stats").fetchone()[0],
            "features": con.execute("SELECT COUNT(*) FROM feature_adoption").fetchone()[0],
        }
    finally:
        con.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cross-session metrics aggregator → SQLite")
    ap.add_argument("--db", default=str(DATA_DIR / "monitoring.db"))
    ap.add_argument("--data", default=str(DATA_DIR))
    ap.add_argument("--force", action="store_true", help="ignore watermark, recompute all")
    args = ap.parse_args(argv)
    try:
        res = run(args.db, Path(args.data), force=args.force)
    except sqlite3.OperationalError as exc:
        # Another instance holds the DB lock — not an error, it will have run.
        print(f"monitoring_collector: skipped — {exc}", file=sys.stderr)
        return 0
    print(f"monitoring_collector: changed={res['changed'] or 'none'} "
          f"daily_tool_rows={res['daily_tool_rows']} features={res['features']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
