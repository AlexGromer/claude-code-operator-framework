# Rule: Authorization Levels
# Auto-loaded by Claude Code from ~/.claude/rules/

## Authorization Levels

| Level | Actions | Confirmation |
|-------|---------|-------------|
| READ | View files, logs, status, git history | No |
| ANALYZE | Parse, validate, static analysis, read-only queries | No |
| PLAN | Generate plans, dry-run, propose changes | No |
| MODIFY | Edit files, git commit, change configs | Yes — show diff |
| NETWORK_ACTIVE | Scan, enumerate, probe (nmap, nuclei) | Yes — confirm target & scope |
| INFRASTRUCTURE | Deploy, apply (terraform, kubectl), migrate DB | Yes — show plan + rollback |
| CREDENTIAL | Password attacks, auth bypass testing | Yes + scope + legal |
| DESTRUCTIVE | Delete, drop, destroy, force push | Yes + explicit approval |

**Rule:** When multiple levels apply, use the strictest. For CREDENTIAL/DESTRUCTIVE, require user to confirm the exact action.

## Permissions Mapping

settings.json `permissions` enforces levels: `deny` > `allow` > `ask` > `defaultMode`.

| Level | settings.json section |
|-------|----------------------|
| READ, ANALYZE, PLAN | `allow` (auto-approved) |
| MODIFY | `allow` for Edit/Write: global shared dirs (16 paths in `working-directories.md`) + `~/.claude/`; project dirs via `settings.local.json` |
| NETWORK_ACTIVE | `ask` (nmap, nuclei, subfinder, etc.) |
| INFRASTRUCTURE | `ask` (terraform apply, kubectl apply, docker run) |
| CREDENTIAL | `ask` (hydra, hashcat, john) |
| DESTRUCTIVE | `deny` (rm -rf /, dd, mkfs) or `ask` (rm, mv, git reset) |

Template: `~/.claude/templates/project-init/PERMISSIONS.md` — 30 allow groups, per-project types, conflict rules.

## Permission Hierarchy (4-Tier)

Permissions are resolved in strict priority order. Higher tiers override lower.

### Tier 1: Global Deny (Absolute Block)
- Source: `~/.claude/settings.json` → `permissions.deny`
- Effect: Unconditionally blocks the action. No override possible.
- Examples: `rm -rf /`, `dd if=`, `mkfs`, `shutdown`, `reboot`

```json
// settings.json — Tier 1 (never overridable)
"deny": [
  "Bash(rm:-rf /)",
  "Bash(dd:if=/dev/zero*)",
  "Bash(mkfs:*)",
  "Read(/etc/shadow)",
  "Read(**/.env)"
]
```

### Tier 2: Project Narrowing (Can Only Restrict)
- Source: `<project>/.claude/settings.local.json` → `permissions.deny` / `permissions.ask`
- Effect: Can ADD deny/ask rules for this project only. CANNOT widen global permissions.
- Rule: Project deny > project ask > (falls through to Tier 3)
- Example: A project can deny `Bash(docker *)` even if global allows it.

```json
// project/.claude/settings.local.json — CORRECT (narrowing)
{
  "permissions": {
    "deny": ["Bash(curl:*)"],
    "ask": ["Bash(docker:ps*)"]
  }
}

// project/.claude/settings.local.json — INCORRECT (widening)
{
  "permissions": {
    "allow": ["Bash(helm install:*)"]  // <-- promotes from global ask to allow!
  }
}
```

**Reality check:** Claude Code auto-populates `settings.local.json` with `allow` entries when users approve actions during sessions. This is a tooling behavior, not a security design. These accumulated allows effectively widen permissions locally and should be audited periodically.

### Tier 3: Global Allow/Ask (Defaults)
- Source: `~/.claude/settings.json` → `permissions.allow` / `permissions.ask`
- Effect: Default permission grants. Applied when Tier 1-2 don't match.
- Current: ~337 allow rules, ~112 ask rules, organized by domain.

```json
// settings.json — Tier 3 examples
"allow": [
  "Read(*)",                        // All reads auto-approved
  "Edit(/opt/work/osint/**)",             // Edits in working dirs (per-directory)
  "Bash(git:*)",                    // Git operations
  "mcp__github__create_issue",      // MCP tools
  "Bash(curl:-s*)"                  // Read-only curl (not -X, -d)
],
"ask": [
  "Bash(nmap:*)",                   // Network scanning — confirm target
  "Bash(docker:run*)",              // Container ops — confirm action
  "Bash(terraform:apply*)",         // Infrastructure — show plan first
  "Bash(rm:*)"                      // Deletions — explicit approval
]
```

### Tier 4: Default Mode (Fail-Closed Fallback)
- Source: `~/.claude/settings.json` → `permissions.defaultMode`
- Effect: If no rule in Tiers 1-3 matches, this mode applies.
- Values: `ask` (default), `deny`, `allow`
- Recommendation: Always `ask` — fail-closed security.

```json
// settings.json — Tier 4 fallback
"defaultMode": "default"  // equivalent to "ask" — prompts user for unmatched actions
```

### Conflict Resolution

```
deny (T1) > project-deny (T2) > project-ask (T2) > global-allow (T3) > global-ask (T3) > defaultMode (T4)
```

Example resolution chain for `Bash(helm install:*)`:
1. T1 global deny? No match → continue
2. T2 project deny/ask? Depends on project settings.local.json → if deny, blocked
3. T3 global allow? No (it is in global ask) → T3 global ask? Yes → prompt user
4. T4 never reached (T3 matched)

### Project-Level Restrictions
- Projects can only NARROW, never WIDEN global permissions
- `settings.local.json` can add to deny/ask, but NOT to allow
- MCP servers defined in project `.mcp.json` get tools auto-allowed only if in global allow list
- Claude Code auto-adds approved commands to `settings.local.json` allow — audit periodically
- Run `/opt/project` audit script or review manually to catch widening violations
