# Tool Lifecycle Protocol
# Version: 1.0.0 | Created: 2026-02-05

## Overview

Формализованный протокол управления жизненным циклом инструментов в конфигурации Claude Code.

**Tool Types:**
- **CLI Tools** — Command-line utilities (nmap, terraform, etc.)
- **MCP Servers** — Model Context Protocol integrations
- **Internal Tools** — Python scripts in ~/.claude/tools/
- **Skills** — Workflow templates in ~/.claude/skills/

**Lifecycle Phases:**
```
EVALUATION → APPROVAL → INTEGRATION → ACTIVE → DEPRECATION → REMOVAL
```

---

## Phase 1: EVALUATION

### 1.1 Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **CLI Relevance** | 30% | Direct benefit for CLI tasks |
| **Security** | 25% | No known vulnerabilities, safe defaults |
| **Reliability** | 20% | Stable, maintained, documented |
| **Integration** | 15% | Works with existing stack |
| **Cost** | 10% | Free/affordable, no vendor lock-in |

### 1.2 Tool Evaluation Checklist

```
☐ Purpose clearly defined
☐ CLI relevance score ≥60/100
☐ Security review passed
☐ License compatible (MIT, Apache, BSD preferred)
☐ Active maintenance (commits <6 months)
☐ Documentation available
☐ No conflicting dependencies
☐ Alternative tools considered
```

### 1.3 Security Evaluation

**Mandatory Checks:**
```bash
# Check for known vulnerabilities
npm audit        # for npm packages
pip-audit        # for Python packages
trivy image      # for container images

# Verify source
gh repo view OWNER/REPO --json securityPolicyUrl,vulnerabilityAlerts

# Check permissions required
strace -f TOOL 2>&1 | grep -E 'open|connect|exec'
```

**Security Scoring:**
| Score | Criteria |
|-------|----------|
| A (90-100) | No CVEs, minimal permissions, sandboxed |
| B (70-89) | Minor issues, reasonable permissions |
| C (50-69) | Some concerns, needs isolation |
| D (30-49) | Significant risks, restricted use only |
| F (<30) | ❌ Reject — unacceptable security posture |

### 1.4 Tool Comparison Matrix

| Tool | CLI Score | Security | Reliability | Integration | Cost | Total |
|------|-----------|----------|-------------|-------------|------|-------|
| Tool A | 85 | A | 90% | 80% | Free | **87** |
| Tool B | 70 | B | 85% | 90% | Free | **79** |
| Tool C | 90 | C | 70% | 60% | Paid | **72** |

---

## Phase 2: APPROVAL

### 2.1 Approval Levels

| Tool Type | Approval Required | Reviewer |
|-----------|-------------------|----------|
| CLI Tool (read-only) | Self-approve | User |
| CLI Tool (modify) | Review | User + verification |
| MCP Server | Security review | User + security check |
| Internal Tool | Code review | User + static analysis |

### 2.2 Approval Checklist

```
☐ Evaluation score ≥70/100
☐ Security score ≥C (50/100)
☐ No blocking issues identified
☐ Integration path documented
☐ Rollback plan defined
☐ Approved by: [reviewer]
☐ Date: [YYYY-MM-DD]
```

---

## Phase 3: INTEGRATION

### 3.1 Integration by Tool Type

**CLI Tools:**
```bash
# 1. Install
apt install TOOL  # or brew, npm, pip, etc.

# 2. Document in tech-stack.md
echo "- TOOL: description" >> ~/.claude/modules/10-tech-stack.md

# 3. Add to authorization-levels.md if needed
# (for tools requiring elevated permissions)

# 4. Create examples
mkdir -p ~/.claude/examples/tools/
cat > ~/.claude/examples/tools/TOOL_example.md << 'EOF'
# TOOL Example
[usage example]
EOF
```

**MCP Servers:**
```json
// Add to ~/.claude/settings.json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@package/mcp-server"],
      "env": {}
    }
  }
}
```

**Internal Tools:**
```bash
# 1. Create tool
cat > ~/.claude/tools/tool_name.py << 'EOF'
#!/usr/bin/env python3
"""Tool description."""
# Implementation
EOF
chmod +x ~/.claude/tools/tool_name.py

# 2. Add to anacron if scheduled
echo "1 5 tool_name python3 ~/.claude/tools/tool_name.py" >> ~/.anacron/anacrontab
```

**Skills:**
```bash
# 1. Create skill
cp ~/.claude/templates/skills/SKILL.template.md ~/.claude/skills/skill-name.md

# 2. Edit skill content
vim ~/.claude/skills/skill-name.md

# 3. Register in settings.json (automatic via directory)
```

### 3.2 Integration Checklist

```
☐ Tool installed and accessible
☐ Configuration added (settings.json, etc.)
☐ Documentation updated:
    ☐ modules/10-tech-stack.md (CLI tools)
    ☐ modules/11-mcp.md (MCP servers)
    ☐ modules/15-skills.md (Skills)
☐ Examples created
☐ Authorization level assigned
☐ Integration test passed
☐ GAPS.md updated
```

---

## Phase 4: ACTIVE (Maintenance)

### 4.1 Tool Health Monitoring

**Automated Checks (via anacron):**
```python
# ~/.claude/tools/tool_health_checker.py
TOOLS_TO_CHECK = [
    {"name": "nmap", "cmd": "nmap --version"},
    {"name": "terraform", "cmd": "terraform version"},
    # ...
]

def check_tool_health():
    for tool in TOOLS_TO_CHECK:
        try:
            result = subprocess.run(tool["cmd"], shell=True, capture_output=True)
            if result.returncode != 0:
                log_warning(f"{tool['name']} health check failed")
        except FileNotFoundError:
            log_error(f"{tool['name']} not found")
```

### 4.2 Version Tracking

| Tool | Current | Latest | Status | Last Check |
|------|---------|--------|--------|------------|
| nmap | 7.94 | 7.95 | 🟡 Update available | 2026-02-01 |
| terraform | 1.7.0 | 1.7.0 | ✅ Current | 2026-02-01 |

### 4.3 Update Protocol

```
1. CHECK for updates (weekly via anacron)
2. REVIEW changelog for breaking changes
3. TEST in isolated environment
4. UPDATE tool
5. VERIFY functionality
6. UPDATE documentation if needed
```

---

## Phase 5: DEPRECATION

### 5.1 Deprecation Triggers

| Trigger | Action |
|---------|--------|
| Upstream deprecated | Begin deprecation immediately |
| Security vulnerability (unpatched) | Deprecate within 7 days |
| Better alternative available | Gradual migration over 1-3 months |
| Low usage (<5% for 3 months) | Review for removal |
| Maintenance burden too high | Find alternative or deprecate |

### 5.2 Deprecation Process

```
1. ANNOUNCE
   ├── Add deprecation warning to documentation
   ├── Log in GAPS.md
   └── Suggest alternative

2. MIGRATE
   ├── Document migration path
   ├── Update examples to use alternative
   └── Update skills/workflows

3. DISABLE
   ├── Remove from default configs
   ├── Keep available for manual use
   └── Monitor usage (30 days)

4. REMOVE
   └── Complete removal after deprecation period
```

### 5.3 Deprecation Notice

```markdown
> ⚠️ **DEPRECATED TOOL** (since YYYY-MM-DD)
> `tool-name` is deprecated and will be removed on YYYY-MM-DD.
> Alternative: Use `new-tool` instead.
> Migration: [link to migration guide]
```

---

## Phase 6: REMOVAL

### 6.1 Removal Checklist

```
☐ Deprecation period complete (≥30 days)
☐ Migration guide followed
☐ All references removed:
    ☐ modules/10-tech-stack.md
    ☐ modules/11-mcp.md (for MCP)
    ☐ settings.json (for MCP)
    ☐ Examples
    ☐ Skills
    ☐ Hooks
☐ Uninstall completed
☐ GAPS.md updated (gap closed)
☐ Backup of config (if custom settings)
```

---

## Quick Reference: Tool Addition

**4-Phase Fast Track:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TOOL ADDITION QUICK REFERENCE                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 1: EVALUATE (15 min)                                                 │
│  ☐ CLI relevance ≥60? (direct CLI benefit)                                  │
│  ☐ Security check passed? (no critical CVEs)                                │
│  ☐ Actively maintained? (commits <6 months)                                 │
│  ☐ License OK? (MIT/Apache/BSD)                                             │
│                                                                              │
│  PHASE 2: INSTALL (10 min)                                                  │
│  ☐ Install via package manager                                              │
│  ☐ Verify installation: `tool --version`                                    │
│  ☐ Configure if needed                                                      │
│                                                                              │
│  PHASE 3: DOCUMENT (15 min)                                                 │
│  ☐ Add to modules/10-tech-stack.md                                          │
│  ☐ Create example in examples/tools/                                        │
│  ☐ Assign authorization level                                               │
│                                                                              │
│  PHASE 4: VERIFY (10 min)                                                   │
│  ☐ Test basic functionality                                                 │
│  ☐ Test integration with workflows                                          │
│  ☐ Update GAPS.md                                                           │
│                                                                              │
│  TOTAL: ~50 min                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Server Addition Quick Reference

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  MCP SERVER ADDITION                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. FIND SERVER                                                             │
│     └── Check: mcp.so, npm registry, GitHub                                 │
│                                                                              │
│  2. EVALUATE                                                                │
│     ☐ Stars/downloads (popularity indicator)                                │
│     ☐ Last update (<6 months)                                               │
│     ☐ Security review (permissions, data access)                            │
│                                                                              │
│  3. INSTALL                                                                 │
│     # Test first:                                                           │
│     npx -y @package/mcp-server --help                                       │
│                                                                              │
│  4. CONFIGURE                                                               │
│     # Add to settings.json:                                                 │
│     "mcpServers": {                                                         │
│       "name": {                                                             │
│         "command": "npx",                                                   │
│         "args": ["-y", "@package/mcp-server"]                               │
│       }                                                                     │
│     }                                                                       │
│                                                                              │
│  5. DOCUMENT                                                                │
│     ☐ Add to modules/11-mcp.md Section 7                                    │
│     ☐ Note auth requirements                                                │
│                                                                              │
│  6. TEST                                                                    │
│     # Restart Claude Code, verify server loads                              │
│     claude --mcp-debug                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Internal Tool Addition Quick Reference

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INTERNAL TOOL (Python) ADDITION                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. CREATE FILE                                                             │
│     ~/.claude/tools/tool_name.py                                            │
│                                                                              │
│  2. TEMPLATE                                                                │
│     #!/usr/bin/env python3                                                  │
│     """                                                                     │
│     Tool Name - Description                                                 │
│                                                                              │
│     Usage: python tool_name.py [options]                                    │
│     """                                                                     │
│     import argparse                                                         │
│     # Implementation                                                        │
│                                                                              │
│  3. MAKE EXECUTABLE                                                         │
│     chmod +x ~/.claude/tools/tool_name.py                                   │
│                                                                              │
│  4. TEST                                                                    │
│     python ~/.claude/tools/tool_name.py --help                              │
│                                                                              │
│  5. SCHEDULE (if needed)                                                    │
│     # Add to ~/.anacron/anacrontab                                          │
│     1 5 tool_name python3 ~/.claude/tools/tool_name.py                      │
│                                                                              │
│  6. HOOK (if needed)                                                        │
│     # Add to settings.json hooks section                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix: Tool Categories

| Category | Examples | Documentation Location |
|----------|----------|------------------------|
| Security | nmap, nuclei, burp | modules/02-security.md |
| DevOps | terraform, ansible, kubectl | modules/03-devops.md |
| Development | git, npm, python | modules/07-engineering.md |
| Low-level | gdb, ghidra, radare2 | modules/08-lowlevel.md |
| MCP Servers | github, filesystem, fetch | modules/11-mcp.md |
| Internal | metrics_tracker, staleness_checker | tools/ directory |

---

**Version History:**
- v1.0.0 (2026-02-05): Initial release
