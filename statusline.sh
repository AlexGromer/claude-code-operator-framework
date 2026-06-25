#!/usr/bin/env bash
# Claude Code statusLine v5.0 — OAuth API rate limits + spending tracker
# Outputs exactly 2 lines. Claude Code pipes JSON to stdin.
#
# Rate limits: fetched from https://api.anthropic.com/api/oauth/usage
# via OAuth token from ~/.claude/.credentials.json (cached 120s).
# No manual calibration needed.

export STATUSLINE_INPUT=$(cat)

python3 - <<'PYEOF'
import json, os, subprocess, fcntl, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    raw = os.environ.get("STATUSLINE_INPUT", "{}")
    data = json.loads(raw)
except Exception:
    data = {}

# ═══════════════════════ ANSI ═══════════════════════
R   = "\033[0m"
B   = "\033[1m"
DM  = "\033[2m"
CY  = "\033[36m"
GR  = "\033[32m"
YL  = "\033[33m"
RD  = "\033[31m"
MG  = "\033[35m"
BL  = "\033[34m"
GY  = "\033[90m"
SEP = f" {GY}\u2502{R} "

# ═══════════════════════ PARSE JSON ═══════════════════════

raw_model = data.get("model")
if isinstance(raw_model, dict):
    model = raw_model.get("display_name") or raw_model.get("id", "?")
elif isinstance(raw_model, str):
    model = raw_model
else:
    model = "?"
if model.startswith("claude-"): model = model[len("claude-"):]
model_short = model.replace("Opus 4.6","Opus").replace("Sonnet 4.6","Sonnet").replace("Haiku 4.5","Haiku")

ctx       = data.get("context_window", {})
ctx_pct   = float(ctx.get("used_percentage", -1))
ctx_size  = int(ctx.get("context_window_size", 0))
in_tok    = ctx.get("total_input_tokens", 0)
out_tok   = ctx.get("total_output_tokens", 0)
total_tok = in_tok + out_tok
cost_data = data.get("cost", {})
sess_cost = float(cost_data.get("total_cost_usd", 0))
total_ms  = int(cost_data.get("total_duration_ms", 0))
api_ms    = int(cost_data.get("total_api_duration_ms", 0))
session_id = data.get("session_id", "?")

# Context: show raw % of full context window (1M for Opus, 200K for others)
# Autocompact disabled — 100% = full window, not compaction threshold
if ctx_size > 0 and ctx_pct >= 0:
    ctx_tokens = int(ctx_pct / 100 * ctx_size)
else:
    ctx_tokens = 0

def fmt_tok(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1000:      return f"{n/1000:.0f}k"
    if n > 0:          return str(n)
    return "0"

def fmt_dur(ms):
    if ms <= 0: return "0s"
    s = ms // 1000
    if s < 60:     return f"{s}s"
    if s < 3600:   return f"{s//60}m{s%60:02d}s"
    h = s // 3600; m = (s % 3600) // 60
    return f"{h}h{m:02d}m"

hours = total_ms / 3_600_000 if total_ms > 0 else 0

# ═══════════════════════ SPENDING TRACKER ═══════════════════════

HOME = os.path.expanduser("~")
TRACKER = os.path.join(HOME, ".claude", "evaluation", "data", "spending_tracker.jsonl")

def log_snapshot():
    if session_id == "?" or sess_cost <= 0: return
    ws = data.get("workspace", {})
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "sid": session_id, "cost": round(sess_cost, 4),
        "dur_ms": total_ms, "api_ms": api_ms,
        "in_tok": in_tok, "out_tok": out_tok,
        "project": ws.get("project_dir", ""), "model": model_short,
    }
    try:
        os.makedirs(os.path.dirname(TRACKER), exist_ok=True)
        with open(TRACKER, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)
    except (IOError, BlockingIOError): pass

def read_proj_spending():
    now = datetime.now(timezone.utc)
    week_start = (now.date() - timedelta(days=now.date().weekday())).isoformat()
    sessions = {}
    try:
        with open(TRACKER) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    e = json.loads(line)
                    sid = e.get("sid","")
                    if sid: sessions[sid] = e
                except Exception: continue
    except (IOError, OSError): pass
    proj_totals = {}
    for e in sessions.values():
        ts = e.get("ts",""); proj = e.get("project","")
        if ts[:10] >= week_start and proj:
            proj_totals.setdefault(proj, 0.0)
            proj_totals[proj] += e.get("cost", 0)
    return proj_totals

try:
    log_snapshot()
    proj_spending = read_proj_spending()
except Exception:
    proj_spending = {}

# ═══════════════════════ RATE LIMITS — OAuth API ═══════════════════════
# Fetches real quota data from Anthropic API using OAuth token.
# Endpoint: https://api.anthropic.com/api/oauth/usage
# Header: anthropic-beta: oauth-2025-04-20
# Cached to disk (120s TTL) to avoid excessive API calls.

USAGE_CACHE = os.path.join(HOME, ".claude", "evaluation", "data", "usage_cache.json")
USAGE_CACHE_TTL = 120  # seconds

def fetch_usage():
    """Fetch rate limit data from Anthropic OAuth API with caching."""
    now_ts = time.time()

    # Return cache if fresh
    try:
        with open(USAGE_CACHE) as f:
            cache = json.load(f)
        if now_ts - cache.get("_ts", 0) < USAGE_CACHE_TTL:
            return cache.get("data", {})
    except Exception:
        pass

    # Read OAuth token
    creds_file = os.path.join(HOME, ".claude", ".credentials.json")
    try:
        with open(creds_file) as f:
            creds = json.load(f)
        token = creds.get("claudeAiOauth", {}).get("accessToken", "")
        if not token:
            return {}
        # Check expiry
        expires_at = creds.get("claudeAiOauth", {}).get("expiresAt", 0)
        if expires_at > 0 and expires_at < now_ts * 1000:
            return {"_error": "token_expired"}
    except Exception:
        return {}

    # Call API
    try:
        result = subprocess.run(
            ["curl", "--silent", "--max-time", "3",
             "--header", f"Authorization: Bearer {token}",
             "--header", "anthropic-beta: oauth-2025-04-20",
             "https://api.anthropic.com/api/oauth/usage"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        usage_data = json.loads(result.stdout)
    except Exception:
        return {}

    # Check for API error
    if "error" in usage_data:
        return {"_error": usage_data["error"].get("type", "api_error")}

    # Cache result
    try:
        os.makedirs(os.path.dirname(USAGE_CACHE), exist_ok=True)
        with open(USAGE_CACHE, "w") as f:
            json.dump({"_ts": now_ts, "data": usage_data}, f)
    except Exception:
        pass

    return usage_data

try:
    usage = fetch_usage()
except Exception:
    usage = {}

# Parse usage response
def get_limit(usage_data, key):
    """Extract utilization % and reset time from usage API response."""
    section = usage_data.get(key)
    if not section or not isinstance(section, dict):
        return -1, ""
    pct = section.get("utilization", -1)
    if pct is None: pct = -1
    reset = section.get("resets_at", "")
    if reset is None: reset = ""
    return float(pct), reset

h5_pct, h5_reset = get_limit(usage, "five_hour")
wk_pct, wk_reset = get_limit(usage, "seven_day")
sn_pct, sn_reset = get_limit(usage, "seven_day_sonnet")

# Token expired → show /login hint
usage_error = usage.get("_error", "")

def reset_to_minutes(reset_iso):
    """Convert ISO reset timestamp to minutes remaining."""
    if not reset_iso:
        return -1
    try:
        now = datetime.now(timezone.utc)
        reset_dt = datetime.fromisoformat(reset_iso.replace("Z", "+00:00"))
        diff = (reset_dt - now).total_seconds() / 60
        return max(0, diff)
    except Exception:
        return -1

h5_reset_min = reset_to_minutes(h5_reset)
wk_reset_min = reset_to_minutes(wk_reset)
sn_reset_min = reset_to_minutes(sn_reset)

# ═══════════════════════ VISUAL ═══════════════════════

def bar(p, width=5):
    if p < 0: return f"{GY}{'\u00b7' * width} \u2014{R}"
    p = min(p, 100)
    filled = round(p / 100 * width)
    empty  = width - filled
    if   p >= 85: c = RD + B
    elif p >= 60: c = YL
    else:         c = GR
    return f"{c}{'\u2588' * filled}{GY}{'\u2591' * empty}{R} {c}{p:.0f}%{R}"

def ctx_bar(p, width=8):
    """Context bar showing % of full context window used."""
    if p < 0: return f"{GY}{'\u00b7' * width} \u2014{R}"
    p = min(p, 100)
    filled = round(p / 100 * width)
    empty  = width - filled
    if   p >= 85: c = RD + B; tag = " \u26a0"
    elif p >= 60: c = YL; tag = ""
    else:         c = GR; tag = ""
    return f"{c}{'\u2588' * filled}{GY}{'\u2591' * empty}{R} {c}{p:.0f}%{tag}{R}"

def fmt_reset(minutes):
    if minutes < 0: return ""
    if minutes < 1: return f" {GR}\u21bb now{R}"
    if minutes < 60:
        return f" {GY}\u21bb {int(minutes)}m{R}"
    if minutes < 1440:
        h = int(minutes // 60); m = int(minutes % 60)
        return f" {GY}\u21bb {h}h{m:02d}m{R}"
    d = int(minutes // 1440); h = int((minutes % 1440) // 60)
    return f" {GY}\u21bb {d}d{h:02d}h{R}"

# ═══════════════════════ PROJECT & GIT ═══════════════════════

workspace = data.get("workspace", {})
project_dir = workspace.get("project_dir") or workspace.get("current_dir", "")
cwd = workspace.get("current_dir", "") or data.get("cwd", os.getcwd())
if not project_dir: project_dir = cwd

display_proj = project_dir
if display_proj.startswith(HOME): display_proj = "~" + display_proj[len(HOME):]
if display_proj.startswith("/opt/"): display_proj = display_proj[5:]

proj_week_cost = proj_spending.get(project_dir, 0.0)

try:
    real_cwd = cwd or os.getcwd()
    br = subprocess.run(["git","-C",real_cwd,"rev-parse","--abbrev-ref","HEAD"],
                        capture_output=True, text=True, timeout=1)
    if br.returncode == 0:
        git_branch = br.stdout.strip()
        dt = subprocess.run(["git","-C",real_cwd,"status","--porcelain"],
                            capture_output=True, text=True, timeout=1)
        git_str = f"{git_branch}{'*' if dt.stdout.strip() else ''}"
    else: git_str = "\u2014"
except Exception: git_str = "\u2014"

# ═══════════════════════ OUTPUT ═══════════════════════

cost_str = f"${sess_cost:.2f}"
if hours > 0.01:
    rate_h = f"${sess_cost/hours:.1f}/h"
    tok_h  = f"{fmt_tok(int(total_tok/hours))}/h"
else:
    rate_h = "\u2014"; tok_h = "\u2014"

# Line 1: model │ ctx % │ ↓in ↑out │ $cost (rate) │ ⏱ time
ctx_label = "ctx"
ctx_display = ctx_bar(ctx_pct)
# Show absolute tokens if we have ctx_size
if ctx_size > 0 and ctx_tokens > 0:
    ctx_display += f" {GY}{fmt_tok(ctx_tokens)}/{fmt_tok(ctx_size)}{R}"

parts1 = [
    f"{B}{CY}{model_short}{R}",
    f"{GY}{ctx_label} {R}{ctx_display}",
    f"{GY}\u2193 {CY}{fmt_tok(in_tok)}{R} {GY}\u2191 {CY}{fmt_tok(out_tok)}{R}",
    f"{B}{GR}{cost_str}{R} {GY}({rate_h} \u00b7 {tok_h}){R}",
    f"{GY}\u23f1 {CY}{fmt_dur(total_ms)}{R} {GY}(api {fmt_dur(api_ms)}){R}",
]
print(SEP.join(parts1))

# Line 2: 5h % ↻reset │ wk % ↻reset │ sn % ↻reset │ 📂 project $cost/w │ ⎇ branch
if usage_error == "token_expired":
    parts2 = [f"{YL}/login{R} {GY}(OAuth token expired){R}"]
elif usage_error:
    parts2 = [f"{GY}limits: {usage_error}{R}"]
else:
    parts2 = [
        f"{GY}5h {R}{bar(h5_pct)}{fmt_reset(h5_reset_min)}",
        f"{GY}wk {R}{bar(wk_pct)}{fmt_reset(wk_reset_min)}",
        f"{GY}sn {R}{bar(sn_pct)}{fmt_reset(sn_reset_min)}",
    ]

if proj_week_cost > 0.01:
    parts2.append(f"{GY}\U0001f4c2 {MG}{display_proj}{R} {GY}${proj_week_cost:.0f}/w{R}")
else:
    parts2.append(f"{GY}\U0001f4c2 {MG}{display_proj}{R}")

parts2.append(f"{GY}\u2389 {BL}{git_str}{R}")

print(SEP.join(parts2))
PYEOF
