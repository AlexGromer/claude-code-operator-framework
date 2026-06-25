# Few-Shot Example: Parallel Security Audit with Subagents

## Task
Пользователь: "Проведи полный security audit кодовой базы в ~/myproject. Используй параллельные subagents для ускорения."

## Solution

### Strategy

**Serial approach (slow):** 1 agent → 4 hours
**Parallel approach (fast):** 4 agents → 1 hour

**Audit domains:**
1. **Static Analysis** — code quality, vulnerabilities
2. **Secret Scanning** — hardcoded secrets, API keys
3. **Dependency Audit** — vulnerable dependencies
4. **Configuration Review** — misconfigurations, weak settings

---

## Implementation

### Orchestrator Agent (main Claude Code session)

```python
# Orchestrator plan

## Phase 1: Decompose Task
audit_tasks = [
    {
        "name": "static_analysis",
        "description": "Run SAST tools (Bandit, Semgrep) on Python code",
        "model": "sonnet",  # Standard complexity
        "tools": ["Bash", "Read", "Write"]
    },
    {
        "name": "secret_scanning",
        "description": "Scan for hardcoded secrets using gitleaks and trufflehog",
        "model": "haiku",  # Simple task
        "tools": ["Bash", "Write"]
    },
    {
        "name": "dependency_audit",
        "description": "Check dependencies for known vulnerabilities (pip-audit, safety)",
        "model": "haiku",  # Simple task
        "tools": ["Bash", "Read", "Write"]
    },
    {
        "name": "config_review",
        "description": "Review configs (YAML, JSON, env files) for misconfigurations",
        "model": "sonnet",  # Requires judgment
        "tools": ["Read", "Grep", "Write"]
    }
]

## Phase 2: Spawn Subagents in Parallel
# In Claude Code, issue ONE message with 4 Task calls

subagent_prompts = []

for task in audit_tasks:
    prompt = f"""
Security Audit Task: {task['description']}

## Scope
Repository: ~/myproject
Output: JSON report at /tmp/claude-{uid}/myproject/scratchpad/{task['name']}_report.json

## Instructions
1. Run relevant security tools
2. Analyze findings
3. Classify severity: CRITICAL, HIGH, MEDIUM, LOW
4. Generate structured report

## Report Format
{{
  "task": "{task['name']}",
  "timestamp": "2026-02-06T12:00:00Z",
  "findings": [
    {{
      "severity": "HIGH",
      "category": "SQL Injection",
      "file": "app.py",
      "line": 42,
      "description": "Unsafe SQL query construction",
      "recommendation": "Use parameterized queries"
    }}
  ],
  "summary": {{
    "critical": 2,
    "high": 5,
    "medium": 10,
    "low": 3
  }}
}}

## Quality Requirements
- Zero false positives (verify each finding)
- Include file path + line number
- Actionable recommendations
- Confidence level for each finding

Begin audit now.
"""
    subagent_prompts.append({
        "task": task,
        "prompt": prompt
    })

# Spawn all subagents in parallel
```

### Subagent 1: Static Analysis (Sonnet)

```bash
# Task call from orchestrator
Task(
    subagent_type="general-purpose",
    model="sonnet",
    prompt=subagent_prompts[0]["prompt"]
)
```

**Subagent execution:**
```bash
# Subagent 1 (static_analysis)

# Step 1: Run Bandit (Python security linter)
cd ~/myproject
bandit -r . -f json -o /tmp/bandit_report.json

# Step 2: Run Semgrep (advanced SAST)
semgrep --config=auto --json --output=/tmp/semgrep_report.json .

# Step 3: Analyze results
python3 << 'EOF'
import json

# Load Bandit results
with open('/tmp/bandit_report.json') as f:
    bandit_data = json.load(f)

# Load Semgrep results
with open('/tmp/semgrep_report.json') as f:
    semgrep_data = json.load(f)

findings = []

# Process Bandit findings
for result in bandit_data.get('results', []):
    if result['issue_confidence'] in ['HIGH', 'MEDIUM']:
        findings.append({
            "severity": result['issue_severity'],
            "category": result['issue_text'],
            "file": result['filename'],
            "line": result['line_number'],
            "description": result['issue_text'],
            "recommendation": "Review Bandit documentation for " + result['test_id'],
            "confidence": result['issue_confidence']
        })

# Process Semgrep findings
for result in semgrep_data.get('results', []):
    findings.append({
        "severity": result['extra']['severity'].upper(),
        "category": result['check_id'],
        "file": result['path'],
        "line": result['start']['line'],
        "description": result['extra']['message'],
        "recommendation": result['extra'].get('fix', 'Manual review required'),
        "confidence": "HIGH"
    })

# Generate report
report = {
    "task": "static_analysis",
    "timestamp": "2026-02-06T12:00:00Z",
    "findings": findings,
    "summary": {
        "critical": sum(1 for f in findings if f['severity'] == 'CRITICAL'),
        "high": sum(1 for f in findings if f['severity'] == 'HIGH'),
        "medium": sum(1 for f in findings if f['severity'] == 'MEDIUM'),
        "low": sum(1 for f in findings if f['severity'] == 'LOW')
    },
    "tools_used": ["Bandit 1.7.5", "Semgrep 1.45.0"]
}

# Write report
import os
output_path = f"/tmp/claude-{os.getuid()}/myproject/scratchpad/static_analysis_report.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"Static analysis complete: {len(findings)} findings")
print(f"CRITICAL: {report['summary']['critical']}")
print(f"HIGH: {report['summary']['high']}")
print(f"Report: {output_path}")
EOF
```

---

### Subagent 2: Secret Scanning (Haiku — cost-optimized)

```bash
# Task call from orchestrator
Task(
    subagent_type="general-purpose",
    model="haiku",  # Simple task, use cheapest model
    prompt=subagent_prompts[1]["prompt"]
)
```

**Subagent execution:**
```bash
# Subagent 2 (secret_scanning)

cd ~/myproject

# Step 1: Run gitleaks
gitleaks detect --no-git --report-path=/tmp/gitleaks_report.json --report-format=json

# Step 2: Run trufflehog (finds high-entropy strings)
trufflehog filesystem . --json > /tmp/trufflehog_report.json 2>/dev/null

# Step 3: Merge results
python3 << 'EOF'
import json
import os

findings = []

# Process gitleaks
try:
    with open('/tmp/gitleaks_report.json') as f:
        gitleaks_data = json.load(f)
        for result in gitleaks_data:
            findings.append({
                "severity": "CRITICAL",
                "category": "Hardcoded Secret",
                "file": result['File'],
                "line": result['StartLine'],
                "description": f"Found {result['RuleID']}: {result['Match'][:50]}...",
                "recommendation": "Remove secret, use environment variable or secret manager",
                "confidence": "HIGH"
            })
except FileNotFoundError:
    pass  # No secrets found

# Process trufflehog
try:
    with open('/tmp/trufflehog_report.json') as f:
        for line in f:
            result = json.load(line)
            if result.get('verified'):  # Only verified secrets
                findings.append({
                    "severity": "CRITICAL",
                    "category": "Verified Secret",
                    "file": result['SourceMetadata']['Data']['Filesystem']['file'],
                    "line": result['SourceMetadata']['Data']['Filesystem'].get('line', 0),
                    "description": f"Verified secret: {result['DetectorName']}",
                    "recommendation": "Revoke and rotate this secret immediately",
                    "confidence": "VERIFIED"
                })
except:
    pass

report = {
    "task": "secret_scanning",
    "timestamp": "2026-02-06T12:00:00Z",
    "findings": findings,
    "summary": {
        "critical": len(findings),  # All secrets are CRITICAL
        "high": 0,
        "medium": 0,
        "low": 0
    },
    "tools_used": ["gitleaks 8.18.0", "trufflehog 3.63.0"]
}

output_path = f"/tmp/claude-{os.getuid()}/myproject/scratchpad/secret_scanning_report.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"Secret scan complete: {len(findings)} secrets found")
print(f"Report: {output_path}")
EOF
```

---

### Subagent 3: Dependency Audit (Haiku)

```bash
# Task call
Task(
    subagent_type="general-purpose",
    model="haiku",
    prompt=subagent_prompts[2]["prompt"]
)
```

**Execution:**
```bash
cd ~/myproject

# Python dependencies
if [ -f requirements.txt ]; then
    pip-audit --format=json --output=/tmp/pip_audit.json || true
    safety check --json --file=requirements.txt > /tmp/safety.json 2>/dev/null || true
fi

# Node.js dependencies
if [ -f package.json ]; then
    npm audit --json > /tmp/npm_audit.json 2>/dev/null || true
fi

# Process results
python3 << 'EOF'
import json
import os

findings = []

# Process pip-audit
try:
    with open('/tmp/pip_audit.json') as f:
        data = json.load(f)
        for vuln in data.get('vulnerabilities', []):
            findings.append({
                "severity": vuln['severity'].upper() if 'severity' in vuln else "MEDIUM",
                "category": "Vulnerable Dependency",
                "file": "requirements.txt",
                "line": 0,
                "description": f"{vuln['name']} {vuln['version']} - {vuln['id']}",
                "recommendation": f"Upgrade to {vuln['fixed_versions'][0] if vuln.get('fixed_versions') else 'latest'}",
                "confidence": "HIGH"
            })
except:
    pass

# Process npm audit
try:
    with open('/tmp/npm_audit.json') as f:
        data = json.load(f)
        for adv_id, advisory in data.get('advisories', {}).items():
            findings.append({
                "severity": advisory['severity'].upper(),
                "category": "Vulnerable NPM Package",
                "file": "package.json",
                "line": 0,
                "description": f"{advisory['module_name']} - {advisory['title']}",
                "recommendation": f"Run: npm update {advisory['module_name']}",
                "confidence": "HIGH"
            })
except:
    pass

report = {
    "task": "dependency_audit",
    "timestamp": "2026-02-06T12:00:00Z",
    "findings": findings,
    "summary": {
        "critical": sum(1 for f in findings if f['severity'] == 'CRITICAL'),
        "high": sum(1 for f in findings if f['severity'] == 'HIGH'),
        "medium": sum(1 for f in findings if f['severity'] == 'MEDIUM'),
        "low": sum(1 for f in findings if f['severity'] == 'LOW')
    }
}

output_path = f"/tmp/claude-{os.getuid()}/myproject/scratchpad/dependency_audit_report.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"Dependency audit complete: {len(findings)} vulnerabilities")
print(f"Report: {output_path}")
EOF
```

---

### Subagent 4: Configuration Review (Sonnet)

```bash
# Task call
Task(
    subagent_type="general-purpose",
    model="sonnet",  # Requires judgment
    prompt=subagent_prompts[3]["prompt"]
)
```

**Execution:**
```bash
cd ~/myproject

# Find all config files
find . -type f \( -name "*.yml" -o -name "*.yaml" -o -name "*.json" -o -name "*.env*" -o -name "config.*" \) > /tmp/config_files.txt

# Analyze each config
python3 << 'EOF'
import json
import yaml
import os
import re

findings = []

# Insecure patterns to check
INSECURE_PATTERNS = [
    (r'debug\s*[:=]\s*true', "DEBUG mode enabled in production", "MEDIUM"),
    (r'ssl_verify\s*[:=]\s*false', "SSL verification disabled", "HIGH"),
    (r'chmod\s+777', "Insecure file permissions (777)", "HIGH"),
    (r'password\s*[:=]\s*["\']?\w+["\']?', "Hardcoded password", "CRITICAL"),
    (r'AllowOverride\s+All', "Apache AllowOverride All (security risk)", "MEDIUM"),
    (r'PermitRootLogin\s+yes', "SSH root login enabled", "HIGH"),
]

with open('/tmp/config_files.txt') as f:
    for filepath in f:
        filepath = filepath.strip()

        try:
            with open(filepath) as cf:
                content = cf.read()

                # Check patterns
                for pattern, desc, severity in INSECURE_PATTERNS:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        findings.append({
                            "severity": severity,
                            "category": "Configuration Issue",
                            "file": filepath,
                            "line": line_num,
                            "description": desc,
                            "recommendation": "Review and secure this configuration",
                            "confidence": "MEDIUM"
                        })
        except:
            pass  # Skip files that can't be read

report = {
    "task": "config_review",
    "timestamp": "2026-02-06T12:00:00Z",
    "findings": findings,
    "summary": {
        "critical": sum(1 for f in findings if f['severity'] == 'CRITICAL'),
        "high": sum(1 for f in findings if f['severity'] == 'HIGH'),
        "medium": sum(1 for f in findings if f['severity'] == 'MEDIUM'),
        "low": sum(1 for f in findings if f['severity'] == 'LOW')
    }
}

output_path = f"/tmp/claude-{os.getuid()}/myproject/scratchpad/config_review_report.json"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"Config review complete: {len(findings)} issues")
print(f"Report: {output_path}")
EOF
```

---

## Phase 3: Aggregate Results (Orchestrator)

After all 4 subagents complete, orchestrator aggregates:

```python
import json
import glob

# Read all reports
reports_pattern = "/tmp/claude-*/myproject/scratchpad/*_report.json"
report_files = glob.glob(reports_pattern)

all_findings = []
all_summaries = {}

for report_file in report_files:
    with open(report_file) as f:
        report = json.load(f)
        all_findings.extend(report['findings'])
        all_summaries[report['task']] = report['summary']

# Sort by severity
severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
all_findings.sort(key=lambda x: severity_order[x['severity']])

# Generate master report
master_report = {
    "audit_timestamp": "2026-02-06T12:00:00Z",
    "repository": "~/myproject",
    "total_findings": len(all_findings),
    "summary": {
        "critical": sum(1 for f in all_findings if f['severity'] == 'CRITICAL'),
        "high": sum(1 for f in all_findings if f['severity'] == 'HIGH'),
        "medium": sum(1 for f in all_findings if f['severity'] == 'MEDIUM'),
        "low": sum(1 for f in all_findings if f['severity'] == 'LOW')
    },
    "breakdown_by_task": all_summaries,
    "findings": all_findings
}

# Write master report
with open('~/myproject/security_audit_report.json', 'w') as f:
    json.dump(master_report, f, indent=2)

# Generate human-readable markdown report
markdown_report = f"""
# Security Audit Report
**Repository:** ~/myproject
**Date:** 2026-02-06
**Total Findings:** {len(all_findings)}

## Executive Summary

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | {master_report['summary']['critical']} |
| 🟠 HIGH | {master_report['summary']['high']} |
| 🟡 MEDIUM | {master_report['summary']['medium']} |
| 🟢 LOW | {master_report['summary']['low']} |

## Findings by Category

"""

for task, summary in all_summaries.items():
    markdown_report += f"\n### {task.replace('_', ' ').title()}\n"
    markdown_report += f"- CRITICAL: {summary['critical']}\n"
    markdown_report += f"- HIGH: {summary['high']}\n"
    markdown_report += f"- MEDIUM: {summary['medium']}\n"
    markdown_report += f"- LOW: {summary['low']}\n"

markdown_report += "\n## Detailed Findings\n\n"

for i, finding in enumerate(all_findings, 1):
    markdown_report += f"### {i}. {finding['severity']} - {finding['category']}\n"
    markdown_report += f"**File:** `{finding['file']}`:{finding['line']}\n"
    markdown_report += f"**Description:** {finding['description']}\n"
    markdown_report += f"**Recommendation:** {finding['recommendation']}\n\n"

with open('~/myproject/SECURITY_AUDIT_REPORT.md', 'w') as f:
    f.write(markdown_report)

print("✅ Security audit complete!")
print(f"📊 Total findings: {len(all_findings)}")
print(f"🔴 CRITICAL: {master_report['summary']['critical']}")
print(f"🟠 HIGH: {master_report['summary']['high']}")
print(f"📄 Reports:")
print(f"  - JSON: ~/myproject/security_audit_report.json")
print(f"  - Markdown: ~/myproject/SECURITY_AUDIT_REPORT.md")
```

---

## Performance Comparison

| Approach | Time | Cost | Parallelization |
|----------|------|------|-----------------|
| **Serial (1 agent)** | 4 hours | $0.40 | None |
| **Parallel (4 agents, all Sonnet)** | 1 hour | $0.60 | 4x |
| **Parallel (optimized models)** | 1 hour | $0.30 | 4x (2 haiku, 2 sonnet) |

**Cost breakdown (optimized):**
- Subagent 1 (Sonnet): $0.10
- Subagent 2 (Haiku): $0.02
- Subagent 3 (Haiku): $0.02
- Subagent 4 (Sonnet): $0.10
- Orchestrator (Sonnet): $0.06
- **Total: $0.30** (vs $0.40 serial)

**Time savings:** 75% faster (4 hours → 1 hour)

---

## Best Practices

1. ✅ **Use scratchpad directory** for inter-agent communication
2. ✅ **JSON format** for structured data passing
3. ✅ **Model selection:** haiku for simple tasks, sonnet for complex
4. ✅ **Clear I/O contracts:** Each subagent knows input/output locations
5. ✅ **Independent tasks:** No dependencies between subagents
6. ✅ **Fail-safe:** Each subagent handles errors gracefully

---

**Authoritative Sources:**
- Subagent Orchestration: `~/.claude/rules/subagent-orchestration.md`
- Model Selection: `~/.claude/modules/13-orchestration-reference.md`
