#!/usr/bin/env python3
"""
Human-in-the-Loop Approval Hook (GAP-WORKFLOW-006)

Implements approval gates for high-risk operations.
Logs decisions and enforces review requirements.

Triggers: PreToolUse for high-risk operations
"""

import sys
import json
import os
import fcntl
import re
import shlex
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_stdin import read_hook_stdin
from pathlib import Path
from typing import Dict, Tuple

LOG_FILE = Path.home() / ".claude" / "logs" / "hitl_approvals.log"
DATA_FILE = Path.home() / ".claude" / "evaluation" / "data" / "hitl_decisions.jsonl"

# Operations requiring HITL approval
HIGH_RISK_OPERATIONS = {
    # Destructive operations
    "rm -rf": {"risk": "CRITICAL", "reason": "Recursive deletion"},
    "git push --force": {"risk": "CRITICAL", "reason": "Force push to remote"},
    "git reset --hard": {"risk": "HIGH", "reason": "Discard all changes"},
    "DROP TABLE": {"risk": "CRITICAL", "reason": "Database table deletion"},
    "DROP DATABASE": {"risk": "CRITICAL", "reason": "Database deletion"},
    "DELETE FROM": {"risk": "HIGH", "reason": "Database row deletion"},
    "TRUNCATE": {"risk": "HIGH", "reason": "Table truncation"},

    # Infrastructure
    "terraform destroy": {"risk": "CRITICAL", "reason": "Infrastructure destruction"},
    "kubectl delete namespace": {"risk": "CRITICAL", "reason": "Namespace deletion (all resources)"},
    "kubectl delete": {"risk": "HIGH", "reason": "Kubernetes resource deletion"},
    "helm uninstall": {"risk": "HIGH", "reason": "Helm release removal"},
    "docker system prune": {"risk": "HIGH", "reason": "Remove all unused Docker data"},
    "docker rm": {"risk": "MEDIUM", "reason": "Container removal"},
    "docker rmi": {"risk": "MEDIUM", "reason": "Image removal"},
    "git branch -D": {"risk": "HIGH", "reason": "Force-delete branch"},
    "pkill": {"risk": "MEDIUM", "reason": "Process termination by name"},
    "kill -9": {"risk": "MEDIUM", "reason": "Force kill process"},

    # Security sensitive
    "chmod 777": {"risk": "HIGH", "reason": "World-writable permissions"},
    "chown root": {"risk": "HIGH", "reason": "Ownership change to root"},
    "chown root:": {"risk": "HIGH", "reason": "Ownership change to root (user:group)"},
    "passwd": {"risk": "CRITICAL", "reason": "Password change"},

    # Network
    "nmap": {"risk": "MEDIUM", "reason": "Network scanning"},
    "masscan": {"risk": "HIGH", "reason": "Mass network scanning"},
    "sqlmap": {"risk": "HIGH", "reason": "SQL injection testing"},
}

# Tool-specific risk levels
TOOL_RISK_LEVELS = {
    "Bash": "VARIABLE",  # Depends on command
    "Edit": "LOW",
    "Write": "LOW",
    "Read": "NONE",
    "Glob": "NONE",
    "Grep": "NONE",
    "mcp__github__merge_pull_request": "MEDIUM",
    "mcp__github__create_pull_request": "LOW",
    "mcp__github__push_files": "MEDIUM",
}


def ensure_dirs():
    """Ensure log directories exist."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


_WRAPPERS = {"sudo", "doas", "env", "nice", "ionice", "time", "timeout",
             "nohup", "stdbuf", "command", "watch"}
_DB_CLIENTS = {"psql", "mysql", "mariadb", "sqlite3", "clickhouse-client",
               "mysqlsh", "mongo", "mongosh"}
_SQL_PATTERNS = {"drop table", "drop database", "delete from", "truncate"}


def _split_subcommands(command: str):
    """
    Split a command line into candidate invocations on genuine shell separators.

    Deliberately does NOT split on bare ( ) < > : those usually appear inside
    quoted text (e.g. echo "(rm -rf is bad)") and splitting on them re-exposes
    substrings as false positives. Command substitution $( and pipes/&&/;/`` are
    real separators and ARE split.
    """
    return re.split(r";|\n|&&|\|\||\||\$\(|" + "`", command)


_SHELLS = {"bash", "sh", "zsh", "ksh", "dash"}
_WRAPPERS_WITH_ARG = {"timeout", "nice", "ionice"}


def _strip_leading(tokens):
    """
    Skip leading VAR=val assignments and wrappers (sudo/env/...) to reach the
    real executable. If a shell interpreter (bash/sh/...) is invoked with -c,
    return its inner command string so the caller can re-parse it.

    Returns: (effective_tokens, inner_shell_string_or_None)
    """
    i = 0
    while i < len(tokens):
        t = tokens[i]
        base = os.path.basename(t)
        if base in _SHELLS:
            # bash/sh/zsh ... -c '<cmd>' : surface the inner command for re-parsing.
            j = i + 1
            while j < len(tokens) and tokens[j].startswith("-") and tokens[j] != "-c":
                j += 1
            if j < len(tokens) and tokens[j] == "-c" and j + 1 < len(tokens):
                return [], tokens[j + 1]
            i += 1
            continue
        if base in _WRAPPERS:
            i += 1
            if base in _WRAPPERS_WITH_ARG:
                # Skip numeric/duration args and flags (timeout 5, timeout 30s,
                # nice -n 10, ionice -c 3) so the wrapped executable (e.g. bash -c)
                # is still reached.
                while i < len(tokens) and (
                    re.match(r"^[0-9.]+[smhd]?$", tokens[i]) or tokens[i].startswith("-")
                ):
                    i += 1
            continue
        if not t.startswith("-") and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
            i += 1
            continue
        break
    return tokens[i:], None


def _tok_eq(cand: str, ptok: str, first: bool) -> bool:
    """Token match: basename-normalise the executable position so /usr/bin/rm
    matches 'rm'; allow user:group (chown root:root) to match a bare-name token."""
    c = os.path.basename(cand) if first else cand
    if c == ptok:
        return True
    # A pattern token ending in ':' (e.g. "chown root:") matches the user:group
    # form via prefix, without over-matching bare 'name:tag' tokens elsewhere.
    if ptok.endswith(":") and c.startswith(ptok):
        return True
    return False


def check_command_risk(command: str) -> Tuple[str, str, str]:
    """
    Argument-aware risk detection (replaces naive substring matching).

    Tokenizes with shlex so a dangerous pattern inside a QUOTED argument
    (e.g. grep "rm -rf" file) is NOT flagged, while a real invocation
    (rm -rf /x, sudo rm -rf, /usr/bin/git push --force, bash -c 'rm -rf /x')
    still is.

    ADVISORY only — bypassable (rm -r -f, base64, ...). The permission tier
    (settings.json deny/ask) is the primary control, not this hook.

    Returns: (risk_level, operation, reason)
    """
    if not command:
        return "LOW", "", ""

    queue = list(_split_subcommands(command))
    processed = 0
    while queue and processed < 200:  # bound guards against nested bash -c recursion
        sub = queue.pop(0).strip()
        processed += 1
        if not sub:
            continue
        try:
            tokens = shlex.split(sub)
        except ValueError:
            tokens = sub.split()
        if not tokens:
            continue

        eff, inner = _strip_leading(tokens)
        if inner:
            # bash -c '<inner>' — re-parse the inner shell string as new sub-commands.
            queue.extend(_split_subcommands(inner))
        if not eff:
            continue
        low = [t.lower() for t in eff]
        exe = os.path.basename(low[0])

        for pattern, info in HIGH_RISK_OPERATIONS.items():
            p = pattern.lower()
            ptoks = p.split()

            # SQL statements only matter as args to a DB client; quoted SQL is one
            # token, so substring-check the args only when the exe is a DB client.
            if p in _SQL_PATTERNS:
                if exe in _DB_CLIENTS and any(p in tok.lower() for tok in eff[1:]):
                    return info["risk"], pattern, info["reason"]
                continue

            if len(ptoks) == 1:
                # Single-token command pattern: match only at the executable position.
                if exe == ptoks[0]:
                    return info["risk"], pattern, info["reason"]
            else:
                # Multi-token: contiguous run of SEPARATE tokens (a quoted multi-word
                # arg collapses to one token and is excluded). Executable position is
                # basename-normalised via _tok_eq.
                m = len(ptoks)
                for i in range(len(low) - m + 1):
                    if all(_tok_eq(low[i + k], ptoks[k], k == 0) for k in range(m)):
                        return info["risk"], pattern, info["reason"]

    return "LOW", "", ""


def log_decision(tool: str, args: str, risk: str, decision: str, reason: str):
    """Log HITL decision."""
    ensure_dirs()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool,
        "args_preview": args[:200] if args else "",
        "risk_level": risk,
        "decision": decision,
        "reason": reason,
    }

    # JSONL log (with file locking)
    with open(DATA_FILE, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(json.dumps(entry) + "\n")
        f.flush()
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Human-readable log (with file locking)
    with open(LOG_FILE, "a") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(f"[{entry['timestamp']}] {decision} | {tool} | {risk} | {reason}\n")
        f.flush()
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def format_output(risk: str, operation: str, reason: str, blocked: bool) -> Dict:
    """Format hook output for PreToolUse (must include 'decision' field)."""
    if not blocked:
        return {"decision": "approve", "status": "pass", "risk": risk}

    return {
        "decision": "block",
        "status": "blocked",
        "risk": risk,
        "operation": operation,
        "reason": f"HITL APPROVAL REQUIRED: {reason}",
        "action": "Request explicit user approval before proceeding",
    }


def main():
    """Main hook entry point."""
    try:
        # Read stdin with timeout protection
        tool_name = ""
        tool_args = ""
        command_str = ""
        try:
            input_data = read_hook_stdin()
            tool_name = input_data.get("tool_name", "")
            tool_input = input_data.get("tool_input", {})
            tool_args = json.dumps(tool_input)
            if isinstance(tool_input, dict):
                command_str = tool_input.get("command", "") or ""
        except Exception:
            pass

        # Fallback to environment/args
        if not tool_name:
            tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
        if not tool_args:
            tool_args = os.environ.get("CLAUDE_TOOL_INPUT", "")
        if len(sys.argv) > 1 and not tool_name:
            tool_name = sys.argv[1]
        if len(sys.argv) > 2 and not tool_args:
            tool_args = sys.argv[2]

        # Check tool-level risk
        tool_risk = TOOL_RISK_LEVELS.get(tool_name, "LOW")

        # For Bash, check command content
        if tool_name == "Bash" and (command_str or tool_args):
            cmd_risk, operation, reason = check_command_risk(command_str or tool_args)

            if cmd_risk in ["CRITICAL", "HIGH"]:
                try:
                    log_decision(tool_name, tool_args, cmd_risk, "BLOCKED", reason)
                except Exception:
                    pass
                result = format_output(cmd_risk, operation, reason, blocked=True)
                print(json.dumps(result))
                return 1

            if cmd_risk == "MEDIUM":
                try:
                    log_decision(tool_name, tool_args, cmd_risk, "WARNING", reason)
                except Exception:
                    pass
                result = format_output(cmd_risk, operation, reason, blocked=False)
                result["status"] = "warning"
                print(json.dumps(result))
                return 0

        # Check other high-risk tools
        if tool_risk in ["CRITICAL", "HIGH"]:
            reason = f"High-risk tool: {tool_name}"
            try:
                log_decision(tool_name, tool_args, tool_risk, "WARNING", reason)
            except Exception:
                pass
            result = format_output(tool_risk, tool_name, reason, blocked=False)
            result["status"] = "warning"
            print(json.dumps(result))
            return 0

        # Low risk - pass through
        print(json.dumps({"decision": "approve", "status": "pass", "risk": "LOW"}))
        return 0
    except Exception:
        print(json.dumps({"decision": "approve", "status": "pass", "risk": "LOW"}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
