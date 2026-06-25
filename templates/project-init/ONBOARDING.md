# Project Onboarding Checklist

## Required (ask user)
1. **Project type**: development / security / pentest-engagement / devops / osint / dfir / research / business / compliance / network / chat / mixed
2. **Primary domains**: [from 19 available] → determines MCP profile + agents
3. **Language**: Python / Go / Rust / JS-TS / Java / C-C++ / other

## Auto-detected (scan project root)
4. **Stack**: package.json→JS, Cargo.toml→Rust, go.mod→Go, pyproject.toml→Python, pom.xml→Java, CMakeLists.txt→C++
5. **CI/CD**: .github/workflows, .gitlab-ci.yml, Jenkinsfile
6. **Containers**: Dockerfile, docker-compose.yml, k8s manifests
7. **Tests**: pytest, jest, go test, cargo test (by file presence)

## Optional
8. **Working directory**: /opt/{{project}}/ (default)
9. **Budget limit**: $5/session (default)
10. **Git remote**: existing or create via MCP GitHub?

## Architecture (optional)
_Answers populate ARCHITECTURE.md. Skip for chat/quick projects._

11. **Architecture style**: monolith / microservices / serverless / event-driven / layered / hexagonal / other
    → Populates: ARCHITECTURE.md §2 Components
12. **Key integrations**: [list external services/APIs the project depends on]
    → Populates: ARCHITECTURE.md §2 Key Interactions + §9 API Contracts (development)
13. **Non-functional requirements (NFR)**: performance targets, availability SLA, data volume
    → Populates: ARCHITECTURE.md §4 Constraints
14. **Compliance requirements**: ФЗ-152 / GDPR / PCI DSS / ISO 27001 / SOC 2 / none
    → Populates: ARCHITECTURE.md §4 Constraints + compliance extension
15. **Deployment environment**: local / VPS / Kubernetes / serverless / on-premise / hybrid
    → Populates: ARCHITECTURE.md §12 Environments (development) or §8 Environments (devops)
16. **Team size**: solo / small (2-5) / medium (6-15) / large (15+)
    → Populates: ARCHITECTURE.md §5 Principles (affects complexity decisions)

_For pentest-engagement type, questions 11-16 are replaced by: target count, methodology (PTES/OWASP), testing window, RoE (Rules of Engagement) — see ARCHITECTURE-security.md.template._

## Git Initialization Rules
- **git-project**: Initialize git, .gitignore, CLAUDE.md, pre-commit hooks
- **no-git**: Skip git setup. Common for: pentest engagements (sensitive data), chat/reference, temp analysis
- Auto-detect: if `.git/` exists → git-project. If pentest/dfir type → suggest no-git.

## Working Directory Structure
```
/opt/<project>/             # Project root
  reports/                  # Delivery reports, audit reports
  scans/                    # Scan results (nmap, nuclei, etc.)
  builds/                   # Build artifacts, compiled binaries
  evidence/                 # DFIR evidence, screenshots
  data/                     # Raw data, exports
```

For chat/reference projects:
```
/opt/<project>/
  notes/                    # Reference notes
  exports/                  # Exported data
```

## New Project Type Discovery

When a user selects "mixed" or describes a project that doesn't fit existing types:

### Detection Triggers
- User explicitly says "this is a {new-type} project"
- User selects "mixed" and describes specific domain characteristics
- Auto-detected stack doesn't match any existing type

### Creation Steps
1. **Interview**: Ask user about domain, tools, deliverables, permissions needs
2. **Generate permissions**: Create `permissions-{type}.json` from closest existing template
3. **Generate ARCHITECTURE extension**: Create `ARCHITECTURE-{type}.md.template` with domain-specific sections
4. **Update ONBOARDING.md**: Add new type to the project type list
5. **Create workflow config**: Generate `~/.claude/workflows/{type}.yaml` with keywords, agents, skills

### Example
```
User: "This is an IoT firmware project"
-> Closest type: development (but needs embedded-specific sections)
-> Create: permissions-iot.json, ARCHITECTURE-iot.md.template, workflows/iot.yaml
-> Add "iot" to project types list
```

### Validation
Before finalizing a new type:
- [ ] permissions file is valid JSON
- [ ] ARCHITECTURE extension follows base template pattern
- [ ] Workflow YAML has required fields
- [ ] At least one agent and skill mapped
- [ ] No conflict with existing type names
