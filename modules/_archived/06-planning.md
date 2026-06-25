# Module 06: Planning & Estimation

Module archived — content (HADI, PDCA, OKR, WBS, PERT, SWOT, 5 Whys, MECE,
sprint planning, capacity planning, roadmaps, resource allocation) is in Claude's training data.

## No Project-Specific Content

No custom planning templates or rules specific to this project were identified.
Use standard planning methodology knowledge directly.

## Quick Bash Helper (convenience only)

```bash
# PERT expected time: pert <optimistic> <realistic> <pessimistic>
pert() { echo "scale=2; ($1 + 4*$2 + $3) / 6" | bc; }
# Example: pert 2 4 8  → 4.33
```

## Few-Shot Examples (planning domain)

- Roadmap: `~/.claude/examples/planning/roadmap_planning.md`
- Sprint Planning: `~/.claude/examples/planning/sprint_planning.md`
- OKR Framework: `~/.claude/examples/planning/okr_framework.md`
- Risk Management: `~/.claude/examples/planning/risk_management.md`
