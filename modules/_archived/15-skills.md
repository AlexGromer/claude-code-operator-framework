# Module: Skills
# On-demand reference: Load when creating/modifying skills or choosing Skills vs Modules vs MCP
# Version: 2.0.0 | Compacted: 2026-02-25

---

## 1. Decision Table: Skills vs Modules vs MCP

| Feature | Skills | Modules | MCP Servers |
|---------|--------|---------|-------------|
| Format | SKILL.md (Markdown) | .md files | JSON-RPC servers |
| Activation | Automatic (by description) | Manual `Read` | Always connected |
| Scope | Task-specific workflow | Domain knowledge | External tools/APIs |
| State | Stateless instructions | Stateless docs | Stateful connections |
| Best for | Repeatable workflows | Reference docs | External integrations |

**When to use what:**
- SKILLS — "How to do X" (git commit, deploy, pentest workflow)
- MODULES — "What is X" (security knowledge, compliance reference)
- MCP — "Connect to X" (GitHub API, database, external service)

## 2. Our Skill Template Format

```markdown
---
name: skill-name
description: Clear description of what this skill does and when Claude should use it.
  Include trigger keywords. Use when: [conditions]. Do NOT use when: [exclusions].
version: 1.0.0
context: fork
agent: agent-name
---

# Skill Title

## When to Use
- [Trigger condition 1]
- [Trigger condition 2]

## Instructions
### Step 1: [Action]
[Details]

### Step 2: [Action]
[Details]

## Guidelines
1. [Key constraint or rule]
```

**Key fields:**
- `context: fork` — runs in isolated subagent context (81 of 87 skills)
- `agent: <name>` — delegates to custom agent from `~/.claude/agents/`
- `description` — determines auto-activation (include trigger keywords)

## 3. Auto-Invocation Chain

```
User prompt
  → keyword match in skill description
  → Skill loaded (SKILL.md)
  → context: fork → isolated execution
  → agent: <name> → custom agent with full methodology
  → result returned to main context
```

81 of 87 skills use `context: fork` + `agent:` for full agent delegation.
6 utility skills run in main context (commit, pr, sync, gap, report, session-health).

## 4. Our Skill Inventory (87 total)

### Utility Skills (6) — main context, no fork

| Skill | Purpose |
|-------|---------|
| `/commit` | Git commit with secrets scan, tests, .gitignore checks |
| `/pr` | Create Pull Request with proper structure |
| `/sync` | Sync Claude configuration to repository |
| `/session-health` | Check session health metrics |
| `/gap` | Create or update gap in GAPS.md |
| `/report` | Generate workflow completion report |

### Domain Skills (81) — context: fork + agent

Organized by agent group — each skill maps 1:1 to an agent in `~/.claude/agents/`:

| Group | Skills (count) | Example Skills |
|-------|---------------|----------------|
| Security | 11 | web-pentester, infra-pentester, vuln-assessor |
| OSINT/Intel | 6 | osint-recon, cybint-analyst, darkint-analyst |
| DFIR/Blue | 8 | incident-commander, soc-analyst, malware-analyst |
| DevOps | 11 | terraform-engineer, k8s-engineer, ci-cd-engineer |
| Network | 2 | network-engineer, network-scanner |
| Development | 7 | web-developer, api-developer, db-developer |
| Data/ML | 5 | ml-engineer, mlops-engineer, data-analyst |
| Testing/QA | 3 | test-writer, qa-automation-engineer |
| Low-level | 8 | kernel-developer, embedded-developer, binary-analyst |
| Compliance | 3 | eu-compliance, rf-compliance |
| Business/Plan | 7 | business-analyst, system-architect, risk-analyst |
| Legal/Business | 7 | legal-counsel, accountant, corporate-lawyer |
| Writing | 3 | academic-writer, tech-writer, researcher |
| Meta | 9 | validator, decomposer, deep-reviewer, fact-checker |

**Locations:**
- Skills: `~/.claude/skills/` (primary, short names)
- Agents: `~/.claude/agents/`
- Plugins: `~/.claude/plugins/` (hooks + marketplace only, not duplicate skills)

## 5. Skill-Module-MCP Integration Patterns

```
Skill + Module:  skill loads module for reference knowledge
                 Example: /security-audit → modules/02-security.md

Skill + MCP:     skill calls MCP tools for external operations
                 Example: /pr skill → mcp__github__create_pull_request

Skill + Both:    /pentest-report → 02-security.md + mcp__github__* issues
```

**Rule:** Skill references module, never duplicates content. Use `## Reference` section.

## 6. Marketplace Decision

**Custom skills** for all operational workflows (mandatory checks, authorization levels, evaluation hooks, module references — marketplace skills lack all of these).

**Use agentskills.io / anthropics/skills** for discovery and inspiration only. When adapting marketplace skill: extract core logic → add module references → add authorization check → add evaluation hooks.

---

**Version**: 2.0.0 | **Updated**: 2026-02-25 | **Compacted from**: 1065 lines → ~95 lines
