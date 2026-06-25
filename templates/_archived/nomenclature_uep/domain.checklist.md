# Domain Creation Checklist

## Domain: {domain_name}
## Date: {date}
## Status: {In Progress / Complete}

---

## Mandatory Artifacts (8/8 required)

### 1. Module
- [ ] File: `~/.claude/modules/{NN}-{domain}.md`
- [ ] Lines ≥ 500
- [ ] Has Clarification Questions section
- [ ] Has Authorization Levels section

### 2. Routing
- [ ] Primary keywords (+3) added to `rules/role-routing.md`
- [ ] Secondary keywords (+2) added
- [ ] Contextual keywords (+1) added

### 3. Examples
- [ ] Directory: `~/.claude/examples/{domain}/`
- [ ] At least 3 few-shot examples
- [ ] Standard format (Query → Response → Why Good → Tags)

### 4. Skill (optional but scored)
- [ ] File: `~/.claude/skills/{domain}-workflow.md`
- [ ] SKILL.md format
- [ ] Pre-composed AWB chain defined

### 5. Autoloader
- [ ] Keywords added to `workflow_autoloader.py` DOMAIN_KEYWORDS
- [ ] MCP profiles mapped in DOMAIN_MCP_PROFILES (if applicable)

### 6. Authoritative Sources
- [ ] Entries added to `AUTHORITATIVE_SOURCES.md`
- [ ] At least 3 authoritative references

### 7. Gaps
- [ ] Initial gap entry: `GAP-{DOMAIN}-001`
- [ ] "Domain {name} created, needs validation"

### 8. Tests
- [ ] Test file: `evaluation/tests/test_domain_{name}.py`
- [ ] Routing test (keywords → correct domain)
- [ ] Examples exist test
- [ ] Module loads test

---

## Optional Artifacts

### 9. MCP Profile (if domain has tools)
- [ ] Profile added to `mcp_profile_manager.py`
- [ ] Servers defined with correct config

### 10. Tools / Validators
- [ ] Domain-specific tools in `~/.claude/tools/`
- [ ] Tests for tools

---

## Validation

- [ ] Compliance score ≥ 80%
- [ ] Registered in `~/.claude/nomenclature/registry.json`
- [ ] No broken references
- [ ] All tests passing

---

## Completion

**Completed:** {date}
**Compliance Score:** {score}%
**Registered:** {Yes/No}
