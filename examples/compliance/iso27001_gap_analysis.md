# Example: ISO 27001 Gap Analysis

## User Request

```
Проведи gap analysis для ISO 27001:2022 certification.
```

## Reasoning

**Domain:** Compliance (ISO 27001)
**Complexity:** Medium
**Model:** Sonnet

## Response

### ISO 27001:2022 Gap Analysis Framework

#### Annex A Controls (93 controls across 4 domains)

```markdown
## Domain: Organizational Controls (37 controls)

### 5.1 Policies for Information Security ⚠️ GAP
☐ Current state: No formal InfoSec policy
☑ Required: Documented policy, approved by management
☑ Gap: High (blocking certification)
☑ Action: Draft policy using ISO 27002 template
☑ Owner: CISO
☑ Deadline: 30 days

### 5.7 Threat Intelligence ✅ COMPLIANT
☑ Current state: Security feeds integrated (MISP, OSINT)
☑ Evidence: threat_intel.log, weekly reports
☑ Gap: None

### 5.10 Acceptable Use of Information ⚠️ PARTIAL
☐ Current state: AUP exists but not enforced
☑ Required: AUP + acknowledgment + monitoring
☑ Gap: Medium (enforcement missing)
☑ Action: Implement AUP acknowledgment on onboarding
☑ Owner: HR + IT
☑ Deadline: 60 days

## Domain: People Controls (8 controls)

### 6.1 Screening ⚠️ GAP
☐ Current state: Background checks only for finance team
☑ Required: All employees with access to sensitive data
☑ Gap: High
☑ Action: Extend screening to engineering, support
☑ Owner: HR
☑ Deadline: 90 days (ongoing for new hires)

### 6.3 Awareness Training ✅ COMPLIANT
☑ Current state: Annual security training (95% completion)
☑ Evidence: Training platform logs, certificates
☑ Gap: None

## Domain: Physical Controls (14 controls)

### 7.2 Physical Entry ⚠️ PARTIAL
☐ Current state: Badge access but no logging
☑ Required: Access control + logs + visitor management
☑ Gap: Medium
☑ Action: Enable access logging, implement visitor book
☑ Owner: Facilities
☑ Deadline: 45 days

## Domain: Technological Controls (34 controls)

### 8.1 User Endpoint Devices ✅ COMPLIANT
☑ MDM deployed, encryption enforced
☑ Evidence: Jamf console, FileVault reports

### 8.5 Secure Authentication ⚠️ PARTIAL
☐ Current state: 2FA for VPN only
☑ Required: 2FA for all critical systems
☑ Gap: Medium
☑ Action: Roll out 2FA for AWS, GitHub, DB access
☑ Owner: DevOps
☑ Deadline: 60 days

### 8.9 Configuration Management ⚠️ GAP
☐ Current state: No baseline configurations documented
☑ Required: Hardening standards + compliance checks
☑ Gap: High
☑ Action: Document baselines (CIS Benchmarks), deploy Wazuh
☑ Owner: DevOps
☑ Deadline: 90 days
```

---

### Gap Analysis Summary

```python
# Gap analysis automation
import pandas as pd

controls = [
    {'id': '5.1', 'name': 'InfoSec Policy', 'status': 'gap', 'severity': 'high'},
    {'id': '5.7', 'name': 'Threat Intel', 'status': 'compliant', 'severity': 'none'},
    {'id': '5.10', 'name': 'Acceptable Use', 'status': 'partial', 'severity': 'medium'},
    {'id': '6.1', 'name': 'Screening', 'status': 'gap', 'severity': 'high'},
    {'id': '6.3', 'name': 'Awareness', 'status': 'compliant', 'severity': 'none'},
    # ... (93 total)
]

df = pd.DataFrame(controls)

gap_summary = {
    'total_controls': len(df),
    'compliant': len(df[df['status'] == 'compliant']),
    'partial': len(df[df['status'] == 'partial']),
    'gap': len(df[df['status'] == 'gap']),
    'compliance_rate': len(df[df['status'] == 'compliant']) / len(df) * 100
}

print(f"""
ISO 27001:2022 Gap Analysis
───────────────────────────────────
Total Controls: {gap_summary['total_controls']}
✅ Compliant: {gap_summary['compliant']} ({gap_summary['compliance_rate']:.1f}%)
⚠️ Partial: {gap_summary['partial']}
❌ Gap: {gap_summary['gap']}

Readiness: {'READY' if gap_summary['compliance_rate'] >= 95 else 'NOT READY'}
Estimated remediation: {gap_summary['gap'] * 30} days (if parallelized)
""")
```

---

### Remediation Roadmap

| Phase | Duration | High-Priority Gaps | Owner |
|-------|----------|-------------------|-------|
| 1 | 30 days | InfoSec policy, ISMS scope | CISO |
| 2 | 60 days | 2FA rollout, AUP enforcement | DevOps, HR |
| 3 | 90 days | Config mgmt, screening | DevOps, HR |
| 4 | 120 days | Internal audit, ISMS review | CISO |
| 5 | 150 days | Certification audit readiness | All |

---

## Key Takeaways

1. **93 controls** in Annex A (ISO 27001:2022)
2. **Statement of Applicability (SoA)** required — justify exclusions
3. **Internal audit** before certification audit
4. **ISMS scope** — define boundaries (whole org or specific units)
5. **Continuous improvement** — PDCA cycle mandatory

**Timeline:** 6-12 months for initial certification
**Cost:** $10K-50K (consultant + audit fees)
**Maintenance:** Annual surveillance audits
