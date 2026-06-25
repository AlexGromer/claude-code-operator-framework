# Module: MCP (Model Context Protocol)
# On-demand reference: Load when working with MCP servers or choosing MCP vs Skills
# Version: 2.0.0 | Compacted: 2026-02-25

---

## 1. Decision Matrix: MCP vs Skills vs Tools

| Criteria | MCP Server | Skill | Bash Tool |
|----------|------------|-------|-----------|
| External API | Best | No | Possible |
| Procedural knowledge | No | Best | No |
| Reusable across projects | Best | Yes | No |
| State management | Best | No | Limited |
| Complex workflows | Partial | Best | No |
| One-off task | Overkill | No | Best |

**Decision flowchart:**
```
External service/API needed? → YES → MCP
Procedural how-to workflow? → YES → Skill
State between calls needed? → YES → MCP
One-off / simple task?      → YES → Bash
Otherwise                   → Skill or MCP based on reuse
```

**Examples:**
- GitHub operations → MCP (`mcp__github__*`) — external API, auth, state
- Git commit workflow → Skill (`/commit`) — procedural, multi-step
- One curl request → Bash — simple, one-off
- Code review checklist → Skill — procedural knowledge

## 2. Scope Hierarchy (CRITICAL)

**Scope loading order:** Managed > CLI > **Local** > Project > User

| Scope | Storage | Loaded? | `mcp list`? |
|-------|---------|---------|-------------|
| **Local** (default) | `~/.claude.json` → `projects."*".mcpServers` | YES | YES |
| Project | `.mcp.json` at project root | YES | No (bug #5963) |
| User | `~/.claude.json` → top-level `mcpServers` | **NOT per-project** | NO |

**CRITICAL:** `claude mcp add` defaults to LOCAL scope. User scope is NOT loaded per-project.

```bash
claude mcp list                                    # Shows LOCAL-scope only
mcp__profile-mcp__profile_status                       # Show loaded
mcp__profile-mcp__profile_load(profile_name="security") # Load profile
mcp__profile-mcp__profile_list                          # All profiles
```

## 3. Essential MCP Servers (Always Active)

| Server | Tools Prefix | Purpose | Status |
|--------|--------------|---------|--------|
| GitHub | `mcp__github__*` | GitHub API operations | Active |
| Fetch | `mcp__fetch__*` | HTTP content fetching | Active |
| Filesystem | `mcp__filesystem__*` | File operations | Active |
| Memory | `mcp__memory__*` | Persistent memory | Active |
| Metrics | `mcp__metrics__*` | Custom metrics | Active |

**MANDATORY:** For GitHub operations always use MCP, NOT `gh` CLI.

## 4. GitHub MCP Quick Reference

| Action | Tool |
|--------|------|
| Read file | `mcp__github__get_file_contents` |
| Push files | `mcp__github__push_files` |
| Create PR | `mcp__github__create_pull_request` |
| List PRs | `mcp__github__list_pull_requests` |
| Get PR | `mcp__github__get_pull_request` |
| PR files | `mcp__github__get_pull_request_files` |
| Review PR | `mcp__github__create_pull_request_review` |
| Merge PR | `mcp__github__merge_pull_request` |
| Create issue | `mcp__github__create_issue` |
| List issues | `mcp__github__list_issues` |
| Search code | `mcp__github__search_code` |
| Create branch | `mcp__github__create_branch` |

Required params for most GitHub tools: `owner`, `repo`

## 5. Domain MCP Profiles (On-Demand)

| Profile | Key Servers | Load Command |
|---------|-------------|--------------|
| security | hexstrike, bbot, shodan | `mcp__profile-mcp__profile_load("security")` |
| devops | terraform, kubernetes, gitlab | `mcp__profile-mcp__profile_load("devops")` |
| monitoring | grafana, prometheus | `mcp__profile-mcp__profile_load("monitoring")` |
| browser | playwright | `mcp__profile-mcp__profile_load("browser")` |

## 6. MCP Server Status Matrix

| Server | Package | Status |
|--------|---------|--------|
| GitHub | built-in | Active |
| terraform | `hashicorp/terraform-mcp-server` (Docker) | Configured |
| playwright | `@playwright/mcp` (NPM) | Configured |
| kubernetes | `kubernetes-mcp-server` (NPM) | Configured |
| hexstrike | `hexstrike-ai` | Configured (no key needed) |
| bbot | `bbot-mcp` (uvx) | Configured |
| postgresql | `@modelcontextprotocol/server-postgres` | Pending connection string |
| gitlab | `@sekora/gitlab-mcp` | Pending token |
| grafana | `@leval/mcp-grafana` | Pending token |
| vault | `hashicorp/vault-mcp-server` (Docker) | Pending token |
| shodan | `@burtthecoder/mcp-shodan` | Pending API key |
| netbox | `netbox-community/netbox-mcp` | Pending token |

**Legend:** Active=connected, Configured=in .mcp.json needs key, Pending=requires API key setup

**To enable server:** Set API keys in `.mcp.json` → add to `enabledMcpjsonServers` in `settings.json` → restart session

## 7. Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Tool not found | Server not in LOCAL scope | Check `claude mcp list`, verify scope |
| Auth failed | Token expired/invalid | Refresh token, check env vars |
| Server not loading | USER scope used | Migrate to LOCAL scope |
| Timeout | Server slow | Increase timeout, check network |
| MCP tools missing | Profile not loaded | `mcp__profile-mcp__profile_load` |

**Verify:** `cat ~/.claude.json | jq '.projects."*".mcpServers | keys'`

## 8. Skills + MCP Composition Pattern

```
Skill defines workflow:
  1. Gather context (Read, Grep)
  2. Call MCP for external data (mcp__github__*)
  3. Process results internally
  4. Call MCP to publish (mcp__github__push_files)
```

Example: `/pr` skill calls `mcp__github__create_pull_request` internally.

---

**Version**: 2.0.0 | **Updated**: 2026-02-25 | **Compacted from**: 1222 lines → ~100 lines
