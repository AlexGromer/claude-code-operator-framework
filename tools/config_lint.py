#!/usr/bin/env python3
"""
config_lint.py — static-control linter for the Claude Code config (~/.claude).

Born from the v9.1 ecosystem audit (docs/ECOSYSTEM_AUDIT_2026-05.md, Part D.1):
W1–W3 fixed secrets exposure, permission-widening, version/count drift and dead
references BY HAND. This linter prevents recurrence by checking them mechanically.

Checks (each → 0+ Findings):
  1. secrets        — plaintext API keys/tokens in .claude.json/.mcp.json; .gitignore coverage
  2. permission     — open-ended Bash interpreters in `allow` without a paired `-c`/`-exec` deny
  3. counts         — FS-derived counts vs the numbers claimed in CLAUDE.md / MEMORY.md
  4. dead_refs      — references to things that no longer exist (prompts/ dir, `profile-mcp --list`, metrics server)
  5. hooks          — registered hooks whose script is missing / lacks a timeout; orphan scripts
  6. skills         — custom skills shadowing known built-in skills

Usage:  python3 ~/.claude/tools/config_lint.py [--json] [--home DIR]
Exit:   1 if any HIGH finding, else 0.  stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HOME = Path.home() / ".claude"

# Custom skill names that collide with known harness built-in skills/commands.
# Maintain this set as built-ins evolve (see docs/ECOSYSTEM_AUDIT_2026-05.md).
KNOWN_BUILTINS = {
    "code-review", "security-review", "review", "init", "deep-research",
    "commit", "pr", "doctor", "validate", "report",
}

# Open-ended interpreters that, if auto-allowed, let any command run via `-c`/`-exec`,
# bypassing the deny/ask tier. Each must have a paired deny narrowing the escape.
INTERPRETER_ALLOWS = {
    "Bash(bash:*)":    ["Bash(bash:-c*)"],
    "Bash(sh:*)":      ["Bash(sh:-c*)"],
    "Bash(zsh:*)":     ["Bash(zsh:-c*)"],
    "Bash(find:*)":    ["Bash(find * -exec*)", "Bash(find * -delete*)"],
}

SECRET_PREFIXES = re.compile(
    r"\b(ghp_|gho_|ghu_|ghs_|github_pat_|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{12}|xoxb-|glpat-|Bearer\s+[A-Za-z0-9._-]{16,}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,})"  # last alt = JWT
)
SECRET_KEY_NAME = re.compile(r"(?i)(api[_-]?key|secret|token|password|bearer|authoriz)")


def _looks_like_reference(v: str) -> bool:
    """True for env/secret-manager refs and filesystem paths — not literal secrets."""
    return v.startswith(("$", "env:", "ref:", "vault:", "/", "~", "."))


class Finding:
    __slots__ = ("check", "severity", "where", "msg")

    def __init__(self, check, severity, where, msg):
        self.check, self.severity, self.where, self.msg = check, severity, where, msg

    def as_dict(self):
        return {"check": self.check, "severity": self.severity, "where": self.where, "msg": self.msg}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ── Check 1: secrets ─────────────────────────────────────────────────────────
def check_secrets(home: Path):
    out = []
    # .claude.json is the sibling of the config dir (~/.claude → ~/.claude.json). The --home
    # contract requires home to be a ".claude"-style dir, so home.parent resolves it for both
    # prod and tests. (Reviewer CR-1: deliberately NOT Path.home() — that would break the
    # --home contract and make the clean-config test scan the real secret-laden ~/.claude.json.)
    candidates = [home.parent / ".claude.json", home / ".mcp.json"]
    for f in candidates:
        if not f.exists():
            continue
        text = _read(f)
        hits = len(SECRET_PREFIXES.findall(text))
        # key-named env values that aren't ${VAR} refs
        kv = re.findall(r'"([^"]*(?:key|secret|token|password|bearer|authoriz)[^"]*)"\s*:\s*"([^"]+)"', text, re.I)
        plain = [k for k, v in kv if v and not _looks_like_reference(v) and len(v) > 8]
        if hits or plain:
            out.append(Finding("secrets", "HIGH", str(f),
                               f"{hits} token-prefix hit(s) + {len(plain)} plaintext key-valued field(s) — rotate & move to env/${{VAR}} refs (values not shown)"))
    # .gitignore coverage
    gi = home / ".gitignore"
    gi_text = _read(gi)
    for pat in (".claude.json", ".mcp.json"):
        if pat not in gi_text:
            out.append(Finding("secrets", "HIGH", str(gi),
                               f"missing '{pat}' in ~/.claude/.gitignore (secrets could be committed)"))
    return out


# ── Check 2: permission-widening ──────────────────────────────────────────────
def check_permissions(home: Path):
    out = []
    data = _load_json(home / "settings.json")
    if not data:
        return out
    perms = data.get("permissions", {})
    norm = lambda s: re.sub(r"\s+", "", s)  # whitespace-insensitive rule comparison
    allow = {norm(a) for a in perms.get("allow", [])}
    deny = {norm(d) for d in perms.get("deny", [])}
    for interp, required_denies in INTERPRETER_ALLOWS.items():
        if norm(interp) in allow and not any(norm(d) in deny for d in required_denies):
            out.append(Finding("permission", "HIGH", "settings.json",
                               f"{interp} in allow without a paired deny ({' or '.join(required_denies)}) — shell-escape bypass"))
    # Residual interpreter escapes (python -c, perl -e, awk system(), env/xargs/...).
    # MED, not HIGH: these tools have heavy legitimate dev use — document as defense-in-depth;
    # the permission tier cannot fully block them without breaking workflows.
    residual = ("Bash(env:*)", "Bash(command:*)", "Bash(xargs:*)", "Bash(source:*)",
                "Bash(tee:*)", "Bash(python:*)", "Bash(python3:*)", "Bash(perl:*)",
                "Bash(ruby:*)", "Bash(node:*)", "Bash(awk:*)")
    for interp in residual:
        if norm(interp) in allow:
            out.append(Finding("permission", "MED", "settings.json",
                               f"{interp} in allow is a residual shell-escape vector (legit-use; defense-in-depth)"))
    return out


# ── Check 3: count-consistency ────────────────────────────────────────────────
def _fs_counts(home: Path):
    skills = [p for p in home.glob("skills/*/SKILL.md") if "_archived" not in str(p)]
    return {
        "rules": len(list((home / "rules").glob("*.md"))),
        "agents": len(list((home / "agents").glob("*.md"))),
        "skills": len(skills),
        "modules": len([p for p in (home / "modules").glob("*.md") if "_archived" not in p.name]),
        "output-styles": len(list((home / "output-styles").glob("*.md"))),
    }


def check_counts(home: Path):
    out = []
    fs = _fs_counts(home)
    docs = {"CLAUDE.md": _read(home / "CLAUDE.md"),
            "MEMORY.md": _read(home / "projects" / "-opt-your-project" / "memory" / "MEMORY.md")}
    # (regex, fs-key) — claimed number near a keyword
    # Match only DECLARATIVE count claims, not historical "N agents used" prose:
    # CLAUDE.md uses "N custom subagents" / "N skill wrappers"; MEMORY.md bolds "**N agents**".
    patterns = [
        (r"(\d+)\s+behavior rules", "rules"),
        (r"(\d+)\s+custom subagents", "agents"),
        (r"\*\*(\d+) agents\*\*", "agents"),
        (r"(\d+)\s+skill wrapper", "skills"),
        (r"\*\*(\d+) skills\*\*", "skills"),
    ]
    for doc, text in docs.items():
        if not text:
            continue
        for rx, key in patterns:
            for m in re.finditer(rx, text):
                claimed = int(m.group(1))
                if claimed != fs[key]:
                    out.append(Finding("counts", "MED", doc,
                                       f"claims {claimed} {key} but filesystem has {fs[key]}"))
    return out


# ── Check 4: dead references ──────────────────────────────────────────────────
def check_dead_refs(home: Path):
    out = []
    live_docs = [home / "CLAUDE.md", home / "projects/-opt-your-project/memory/MEMORY.md"]
    live_docs += list((home / "rules").glob("*.md")) + list((home / "modules").glob("*.md"))
    prompts_exists = (home / "prompts").is_dir()
    # Negation markers: a line SAYING prompts/ is gone is not a stale claim.
    NEG = ("does not exist", "not exist", "no prompts", "ghost", "не сущест", "removed", "consolidat")
    for d in live_docs:
        text = _read(d)
        if not prompts_exists:
            for line in text.splitlines():
                if "prompts/" in line and not any(n in line.lower() for n in NEG):
                    out.append(Finding("dead_refs", "MED", str(d),
                                       f"references prompts/ which does not exist: '{line.strip()[:60]}'"))
                    break
        if "profile-mcp --list" in text:
            out.append(Finding("dead_refs", "LOW", str(d), "`profile-mcp --list` flag does not exist (use mcp__profile-mcp__profile_list)"))
    # metrics server file from .mcp.json
    mcp = _load_json(home / ".mcp.json")
    if isinstance(mcp, dict):
        servers = mcp.get("mcpServers", mcp)
        if isinstance(servers, dict):
            for name, cfg in servers.items():
                if name == "metrics" and isinstance(cfg, dict):
                    for tok in cfg.get("args", []) + ([cfg.get("command", "")]):
                        if isinstance(tok, str) and tok.endswith(".py") and not Path(tok).exists():
                            out.append(Finding("dead_refs", "MED", ".mcp.json", f"server 'metrics' points to missing {tok}"))
    return out


# ── Check 5: hook hygiene ─────────────────────────────────────────────────────
def check_hooks(home: Path):
    out = []
    data = _load_json(home / "settings.json")
    if not data:
        return out
    referenced = set()
    for event, entries in (data.get("hooks") or {}).items():
        for entry in entries:
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                m = re.search(r"([~\w./-]+\.(?:py|sh))", cmd)
                if m:
                    p = Path(m.group(1).replace("~", str(Path.home())))
                    referenced.add(p.name)
                    if not p.exists():
                        out.append(Finding("hooks", "HIGH", f"settings.json:{event}", f"registered hook script missing: {m.group(1)}"))
                if h.get("type", "command") == "command" and "timeout" not in h:
                    out.append(Finding("hooks", "LOW", f"settings.json:{event}", f"hook lacks timeout: {cmd[:50]}"))
    # orphan .py (present but unreferenced) — advisory (some are libraries)
    for p in (home / "hooks").glob("*.py"):
        if p.name not in referenced and not p.name.startswith("_"):
            out.append(Finding("hooks", "LOW", str(p), "hook script present but not registered (library or dead?)"))
    return out


# ── Check 6: skill collisions ─────────────────────────────────────────────────
def check_skills(home: Path):
    out = []
    for p in home.glob("skills/*/SKILL.md"):
        name = p.parent.name
        if name in KNOWN_BUILTINS:
            out.append(Finding("skills", "MED", str(p.parent),
                               f"custom skill '{name}' shadows a built-in skill/command of the same name — namespace (cc-{name}) or remove"))
    return out


CHECKS = [check_secrets, check_permissions, check_counts, check_dead_refs,
          check_hooks, check_skills]


def run(home: Path):
    findings = []
    for fn in CHECKS:
        try:
            findings.extend(fn(home))
        except Exception as e:
            findings.append(Finding(fn.__name__, "MED", "-", f"check errored: {e}"))
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Static linter for ~/.claude config")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--home", default=str(HOME), help="config dir (default ~/.claude)")
    args = ap.parse_args(argv)
    home = Path(args.home)

    findings = run(home)
    order = {"HIGH": 0, "MED": 1, "LOW": 2}
    findings.sort(key=lambda f: order.get(f.severity, 3))

    if args.json:
        print(json.dumps([f.as_dict() for f in findings], ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("config_lint: OK — no findings")
        else:
            counts = {}
            for f in findings:
                counts[f.severity] = counts.get(f.severity, 0) + 1
            print(f"config_lint: {len(findings)} finding(s) — " +
                  ", ".join(f"{v} {k}" for k, v in counts.items()))
            for f in findings:
                print(f"  [{f.severity:<4}] {f.check:<11} {f.where}\n         {f.msg}")

    return 1 if any(f.severity == "HIGH" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
