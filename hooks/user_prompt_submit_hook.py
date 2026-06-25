#!/usr/bin/env python3
"""
User Prompt Submit Hook — Session Health + Frozen Criteria + MCP Rotation

Hook that runs on every user message:
1. Session health monitoring (warns when session is degraded)
2. Frozen criteria check (injects reminder if criteria are frozen)
3. MCP profile rotation (auto-loads domain MCP servers based on prompt keywords)
4. Domain-specific context extensions (short, high-stakes domain reminders)

Both outputs are combined into additionalContext injected into system prompt.

Hook Type: UserPromptSubmit
Input: JSON from stdin {session_id, transcript_path, cwd, prompt}
Output: plain text to stdout (injected as additionalContext)

Version: 3.9.0
Created: 2026-01-27
Updated: 2026-06-24 — v3.9: TEAM REQUIRED → TEAM SUGGESTED; TeamCreate removed in v2.1.178, teams now implicit (Agent tool + name).
         v3.8: Domain-specific context extensions per top_domain.
         v3.7: Added TEAM REQUIRED hint for Complex/Critical tiers.
         v3.5: Restored full domain context (tier, modules, skills, MCP rotation) from workflow_autoloader.
         v3.3: Removed workflow autoloader (archived).
         v3.2: Added frozen criteria injection.
         v3.1: Removed UEP pipeline state injection (experiment archived).
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path

import sys as _hsys
from pathlib import Path as _HPath
_hsys.path.insert(0, str(_HPath(__file__).parent))
from hook_stdin import read_hook_stdin
_sys_path_set = True  # hook_stdin import below

# Frozen criteria location
WORK_DIR = Path("/opt/agent_work_directory")


def claude_session_key() -> str:
    """
    ADR-007: per-session storage key derived from the parent (Claude Code) PID
    plus its process start time. Identical for every child of the same Claude
    Code process — this hook, tools-mcp stdio child, Task() subagents — and
    unique across separate Claude Code windows. starttime defeats PID reuse.

    Format: claude-<PPID>-<STARTTIME>

    Must stay in sync with tools-mcp/shared.go:resolveClaudeKey().
    """
    ppid = os.getppid()
    starttime = "0"
    try:
        with open(f"/proc/{ppid}/stat") as f:
            stat = f.read()
        # /proc/<pid>/stat: pid (comm) state ppid ... starttime(field 22).
        # comm may itself contain spaces — locate the LAST ')' to safely split.
        fields = stat[stat.rindex(")") + 2:].split()
        if len(fields) > 19:
            starttime = fields[19]
    except Exception:
        pass
    return f"claude-{ppid}-{starttime}"

# Import autoloader for MCP profile rotation only
HOOKS_DIR = Path(__file__).parent
sys.path.insert(0, str(HOOKS_DIR))

try:
    from workflow_autoloader import score_domains, check_and_load_mcp_profiles, DOMAIN_KEYWORDS, DOMAIN_AGENTS, SKILL_DESCRIPTIONS, compute_complexity_score, get_cwd_domain_bias, get_workflow_hint, compose_workflows
    AUTOLOADER_AVAILABLE = True
except ImportError:
    AUTOLOADER_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────
# DOMAIN-SPECIFIC CONTEXT EXTENSIONS
# Short, high-stakes reminders injected per detected top domain.
# Only for domains where missing context causes real harm.
# Keep each entry to 1-3 sentences maximum.
# ─────────────────────────────────────────────────────────────────
DOMAIN_PROMPT_EXTENSIONS: dict = {
    # ── HIGH-STAKES: keep all, add anti-patterns ──────────────────────────────
    "security":            "SECURITY CONTEXT: Demand written scope+authorization before any active action — no verbal OK. Anti-patterns: running exploits without approval, testing out-of-scope IPs, persisting access beyond PoC. PTES chain: recon → scan (nmap/nuclei) → exploit (burp/sqlmap) → post-exploit → report. Every finding needs evidence hash + screenshot; unconfirmed findings go in 'unverified' section.",
    "dfir":                "DFIR CONTEXT: Chain-of-custody is absolute — NEVER modify original artifacts, mount read-only or use write-blocker. Anti-patterns: running tools directly on live disk, overwriting logs, attributing attacker without 2+ IOC corroboration. Evidence chain: isolate → hash (SHA-256) → image → analyze (volatility/autopsy/plaso). Timeline in UTC only. Follow NIST SP 800-86.",
    "devops":              "DEVOPS CONTEXT: Every infra change requires dry-run/diff output shown before execution, explicit env confirmation (dev/staging/prod), and a rollback plan. Anti-patterns: manual config bypassing IaC, applying to prod without session-level approval, no post-deploy health check. Chain: terraform plan → diff review → apply → smoke test → alert watch.",
    "compliance":          "COMPLIANCE CONTEXT: Every assertion must cite the specific clause (ISO 27001 A.8.1, ФЗ-152 ст.19, PCI DSS 3.4). Anti-patterns: 'generally compliant' without evidence, mapping controls to wrong annex, conflating 'documented' with 'implemented'. Gap states: Compliant / Partial (list gaps) / Non-compliant (list gaps + risk). Evidence must be verifiable artifact, not verbal claim.",

    # ── MEDIUM: rewritten with constraints + toolchain ────────────────────────
    "osint":               "OSINT CONTEXT: Passive collection by default — active recon (DNS brute, port scan) requires explicit authorization each session. Anti-patterns: scraping without rate-limit, storing raw PII beyond investigation scope, single-source attribution. Chain: subfinder → httpx → theHarvester → social/WHOIS. Every finding needs ≥2 independent sources; anonymize PII in reports before sharing.",
    "network":             "NETWORK CONTEXT: No production routing/firewall change without change-window ticket number and explicit session approval. Anti-patterns: making changes then documenting, testing on prod during business hours, no rollback path. Chain: topology snapshot → change plan → out-of-band backup → apply → verify reachability. Confirm MTU/MSS for cross-segment changes before commit.",
    "reverse_engineering": "REVERSE CONTEXT: Static-first, always — strings/imports/entropy before any execution. Anti-patterns: running unknown binaries outside sandbox, patching without authorization, attributing malware family on <3 matching features. Chain: file/strings/binwalk → Ghidra/IDA (no execution) → YARA rules → sandbox (isolated VM) → IOC report. Hash all samples before and after analysis.",
    "business_analysis":   "BA CONTEXT: Freeze AS-IS model before designing TO-BE — changes to AS-IS mid-analysis invalidate gap calculations. Anti-patterns: writing BRD before stakeholder sign-off, acceptance criteria without measurable threshold, user stories without 'so that' clause. Chain: stakeholder map → AS-IS (BPMN) → gap analysis → TO-BE → acceptance criteria (Given/When/Then with threshold).",
    "procurement":         "PROCUREMENT CONTEXT: НМЦК must use ≥3 market price requests per 44-ФЗ ст.22; single-source justification requires documented rationale. Anti-patterns: ТЗ written to fit one vendor, evaluation criteria changed after bids open, no conflict-of-interest declaration. Chain: zakupki.gov.ru registry check → НМЦК calculation → ТЗ (ГОСТ 34.602) → evaluation matrix → protocol.",
    "orchestration":       "ML/AI CONTEXT: Define evaluation metrics and baseline before training — changing metrics post-train invalidates comparison. Anti-patterns: tuning on test set, reporting accuracy without confidence interval, RAG without retrieval quality eval. Chain: dataset version (DVC) → baseline metric → experiment (MLflow/W&B) → ablation → production gate. RAG: evaluate retrieval (recall@k) separately from generation (ROUGE/human).",

    # ── INFO→ACTION: rewritten as behavioral constraints ─────────────────────
    "mcp":                 "MCP CONTEXT: Before adding/removing servers, check current config via `mcp__profile-mcp__profile_load` — never edit .claude.json directly mid-session. Anti-patterns: assuming server is loaded without checking, restarting session without saving task state to MEMORY.md. Diagnose with doctor-mcp first; if server is down use CLI fallback, do not block work. Changes take effect only after session restart.",
    "coding_agents":       "AGENT CONTEXT: Before spawning a new agent, verify the task cannot be done directly (score < 20 = no agent). Anti-patterns: spawning agents for tasks under 5 minutes, missing mode: acceptEdits, re-reading files the parent already read (pass content in prompt). Always set subagent_type to a named agent type from ~/.claude/agents/; use general-purpose only as last resort. Shutdown teammates via SendMessage(shutdown_request) when done.",
}


def run_domain_context(prompt: str, cwd: str = "") -> str:
    """Detect domain, suggest modules/skills, rotate MCP profiles."""
    if not AUTOLOADER_AVAILABLE or len(prompt) < 10:
        return ""

    try:
        # Apply CWD bias to domain scoring
        bias = get_cwd_domain_bias(cwd) if cwd else {}
        scored = score_domains(prompt, cwd_bias=bias if bias else None)

        # Compute complexity regardless of domain match
        complexity_score, tier = compute_complexity_score(prompt, scored if scored else [])
        tier_guidance = {"Simple": "Execute directly", "Standard": "Goal/Result/Criteria", "Complex": "EnterPlanMode + implicit team", "Critical": "EnterPlanMode + implicit team + user approval"}

        # General fallback when no domain matches
        if not scored or scored[0][1] < 2:
            workflow = get_workflow_hint("general")
            first_step = workflow.split('\n')[0].strip() if workflow else ""
            team_hint = f"\nTEAM SUGGESTED: spawn named teammates via the Agent tool (implicit team) for this {tier} task (score {complexity_score})" if tier in ("Complex", "Critical") else ""
            return (
                f"TASK TIER: {tier} (score: {complexity_score}/100) → {tier_guidance.get(tier, tier)} | Domain: general\n"
                f"Workflow: {first_step}...{team_hint}"
            )

        top_domains = scored[:3]

        # MCP profile rotation
        added, removed = check_and_load_mcp_profiles(top_domains)

        parts = []

        # Check for ambiguity: top 2 domains within 1 point, both >= 3
        is_multi_domain = (
            len(top_domains) >= 2
            and top_domains[0][1] >= 3
            and (top_domains[0][1] - top_domains[1][1]) <= 1
        )

        if is_multi_domain:
            domains_str = ", ".join(f"{d}({s})" for d, s in top_domains[:2])
            parts.append(f"TASK TIER: {tier} (score: {complexity_score}/100) → {tier_guidance.get(tier, tier)} | Domains: {domains_str}")
        else:
            parts.append(f"TASK TIER: {tier} (score: {complexity_score}/100) → {tier_guidance.get(tier, tier)}")

        # Agent recommendation
        agents_seen = []
        for domain, score in top_domains:
            if score < 2:
                continue
            for agent in DOMAIN_AGENTS.get(domain, []):
                if agent not in agents_seen:
                    agents_seen.append(agent)
        if agents_seen:
            parts.append(f"Top agents: {', '.join(agents_seen[:5])}")

        # Team suggestion for Complex+ tasks
        if tier in ("Complex", "Critical"):
            parts.append(f"TEAM SUGGESTED: spawn named teammates via the Agent tool (implicit team) for this {tier} task (score {complexity_score})")

        # Workflow hint (compact, single line)
        top_domain = top_domains[0][0]
        if is_multi_domain:
            w1 = get_workflow_hint(top_domains[0][0])
            w2 = get_workflow_hint(top_domains[1][0])
            if w1 and w2:
                workflow = compose_workflows(w1, w2)
            else:
                workflow = w1 or w2 or get_workflow_hint("general")
        else:
            workflow = get_workflow_hint(top_domain) or get_workflow_hint("general")
        if workflow:
            first_step = workflow.split('\n')[0].strip()
            parts.append(f"Workflow: {first_step}...")

        # Domain-specific context extension (high-stakes domains only)
        extension = DOMAIN_PROMPT_EXTENSIONS.get(top_domain, "")
        if extension:
            parts.append(extension)

        # MCP rotation notification
        if added or removed:
            parts.append("")
            parts.append("!" * 72)
            parts.append("MCP PROFILE ROTATED — SESSION REOPEN REQUIRED")
            if added:
                parts.append(f"+ Added: {', '.join(added)}")
            if removed:
                parts.append(f"- Removed: {', '.join(removed)}")
            parts.append("!" * 72)

        return "\n".join(parts)

    except Exception as e:
        print(f"Domain context error: {e}", file=sys.stderr)
        return ""


def check_frozen_criteria() -> str:
    """Check if criteria are frozen and return reminder (or empty)."""
    try:
        # ADR-007: PPID+starttime key, matches tools-mcp resolveClaudeKey
        session_key = claude_session_key()
        freeze_file = WORK_DIR / session_key / "scratchpad" / "frozen_criteria.json"
        if not freeze_file.exists():
            return ""

        with open(freeze_file, 'r') as f:
            data = json.load(f)

        if not data.get("is_frozen"):
            return ""

        # Check expiration (24h TTL)
        from datetime import datetime, timezone
        expires_str = data.get("expires_at")
        if expires_str:
            expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires:
                freeze_file.unlink()
                return ""

        # Build reminder
        goal = data.get("goal", "?")
        result = data.get("expected_result", "?")
        criteria = data.get("acceptance_criteria", [])

        lines = [
            "!" * 72,
            "FROZEN CRITERIA — DO NOT MODIFY",
            "!" * 72,
            f"Goal: {goal}",
            f"Expected result: {result}",
            "Acceptance criteria:",
        ]
        for i, c in enumerate(criteria, 1):
            lines.append(f"  {i}. {c}")
        lines.append("")
        lines.append("If result does not meet criteria → ITERATE on implementation.")
        lines.append("Do NOT change criteria to match output.")
        lines.append("To unfreeze: use MCP tool mcp__tools-mcp__criteria_unfreeze")
        lines.append("!" * 72)

        return "\n".join(lines)

    except Exception as e:
        print(f"Criteria check error: {e}", file=sys.stderr)
        return ""



def main():
    """Main hook execution."""
    try:
        # Read hook input from stdin
        try:
            input_data = read_hook_stdin(timeout_sec=5)
        except json.JSONDecodeError as e:
            print(f"Hook input error: {e}", file=sys.stderr)
            print(json.dumps({}))
            return 0

        prompt = input_data.get("prompt", "")
        session_id = input_data.get("session_id", os.environ.get("CLAUDE_SESSION_ID", ""))
        context_parts = []

        # Detect system-injected content delivered through the prompt channel
        # (task-notifications, slash-command output, system reminders). These are
        # NOT genuine user task prompts — scoring them produces false Complex/Critical
        # tiers and spurious MCP profile rotation, so skip domain scoring/rotation.
        SYSTEM_MARKERS = (
            "<task-notification>", "<command-name>", "<command-message>",
            "<command-args>", "<local-command-stdout>", "<local-command-stderr>",
            "<system-reminder>", "Caveat: The messages below were generated",
        )
        is_system = any(m in prompt for m in SYSTEM_MARKERS)

        # 1. Frozen criteria check (inject reminder if active)
        criteria_output = check_frozen_criteria()
        if criteria_output:
            context_parts.append(criteria_output)

        # 3. Domain detection + module/skill hints + MCP rotation
        #    Skipped for system-injected content (see is_system above).
        if not is_system:
            cwd = input_data.get("cwd", "")
            domain_output = run_domain_context(prompt, cwd=cwd)
            if domain_output:
                context_parts.append(domain_output)

        # Output combined context
        if context_parts:
            combined = "\n\n".join(context_parts)
            # UserPromptSubmit hooks output plain text that gets added as context
            print(combined)
        else:
            # No context to add — output empty
            print("")

        return 0

    except Exception as e:
        print(f"UserPromptSubmit hook error: {e}", file=sys.stderr)
        print("")
        return 0


if __name__ == "__main__":
    sys.exit(main())
