# Tool Proposal Template
# Copy this file and fill in the sections

## Tool Information

| Field | Value |
|-------|-------|
| **Tool Name** | [name] |
| **Tool Type** | ☐ CLI Tool / ☐ MCP Server / ☐ Internal Tool / ☐ Skill |
| **Category** | [Security/DevOps/Development/etc.] |
| **Proposed By** | [name/role] |
| **Date** | YYYY-MM-DD |
| **Gap ID** | GAP-TOOL-XXX |

---

## 1. Purpose

### 1.1 Description
[2-3 sentences describing what this tool does]

### 1.2 Problem Statement
[What problem does this tool solve?]

### 1.3 Alternative Tools Considered

| Tool | Pros | Cons | Reason Not Selected |
|------|------|------|---------------------|
| [alt 1] | [pros] | [cons] | [reason] |
| [alt 2] | [pros] | [cons] | [reason] |

---

## 2. Evaluation Scoring

| Criterion | Score (0-100) | Weight | Weighted |
|-----------|---------------|--------|----------|
| CLI Relevance | [0-100] | 30% | [calc] |
| Security | [0-100] | 25% | [calc] |
| Reliability | [0-100] | 20% | [calc] |
| Integration | [0-100] | 15% | [calc] |
| Cost | [0-100] | 10% | [calc] |
| **TOTAL** | — | 100% | **[sum]** |

**Threshold:** ≥70 required for approval

---

## 3. Security Assessment

### 3.1 Security Checks

| Check | Status | Notes |
|-------|--------|-------|
| CVE scan | ☐ Pass / ☐ Fail | [details] |
| License | ☐ OK / ☐ Issue | [license type] |
| Permissions | ☐ Minimal / ☐ Elevated | [what it needs] |
| Data access | ☐ None / ☐ Local / ☐ Network | [what it accesses] |

### 3.2 Security Score

| Grade | Description |
|-------|-------------|
| ☐ A (90-100) | No issues, minimal permissions |
| ☐ B (70-89) | Minor issues, reasonable permissions |
| ☐ C (50-69) | Some concerns, needs isolation |
| ☐ D (30-49) | Significant risks |
| ☐ F (<30) | Unacceptable |

### 3.3 Mitigation (if score < A)
[How to mitigate identified risks]

---

## 4. Technical Details

### 4.1 Installation
```bash
# Installation command
[command]
```

### 4.2 Configuration
```json
// For MCP servers (settings.json)
{
  "mcpServers": {
    "[name]": {
      "command": "[cmd]",
      "args": ["[args]"]
    }
  }
}
```

### 4.3 Basic Usage
```bash
# Example commands
[example 1]
[example 2]
```

### 4.4 Dependencies
- [dependency 1]
- [dependency 2]

---

## 5. Integration Plan

### 5.1 Documentation Updates

| Document | Update Required |
|----------|-----------------|
| modules/10-tech-stack.md | ☐ Yes / ☐ No |
| modules/11-mcp.md | ☐ Yes / ☐ No |
| modules/02-security.md | ☐ Yes / ☐ No |
| authorization-levels.md | ☐ Yes / ☐ No |

### 5.2 Examples to Create
- [ ] `examples/tools/[tool]_basic.md`
- [ ] `examples/tools/[tool]_advanced.md`

### 5.3 Authorization Level
| Level | Reason |
|-------|--------|
| ☐ READ | Read-only operations |
| ☐ ANALYZE | Passive scanning |
| ☐ MODIFY | File/config changes |
| ☐ NETWORK_ACTIVE | Network operations |
| ☐ INFRASTRUCTURE | Infrastructure changes |
| ☐ CREDENTIAL | Auth testing |
| ☐ DESTRUCTIVE | Destructive operations |

---

## 6. Resource Estimate

| Task | Effort |
|------|--------|
| Evaluation & testing | [X] min |
| Installation | [X] min |
| Documentation | [X] min |
| Examples | [X] min |
| Integration | [X] min |
| **TOTAL** | **[sum] min** |

---

## 7. Rollback Plan

**If integration fails:**
1. [step 1]
2. [step 2]
3. [step 3]

**Uninstall command:**
```bash
[uninstall command]
```

---

## 8. Approval

| Reviewer | Decision | Date |
|----------|----------|------|
| [name] | ☐ Approve / ☐ Reject / ☐ Revise | YYYY-MM-DD |

**Comments:**
[reviewer feedback]

---

## Checklist

```
☐ Tool type identified
☐ Evaluation score ≥70
☐ Security assessment completed (score ≥C)
☐ Alternatives considered
☐ Installation tested
☐ Integration plan defined
☐ Rollback plan documented
☐ Gap ID assigned
```
