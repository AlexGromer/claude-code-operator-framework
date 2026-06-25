# Few-Shot Example: PCI DSS Compliance Assessment

**Domain:** compliance
**Skill Level:** Advanced
**Pattern:** Scope → Assess → Gap → Remediate

---

## User Query

We're an e-commerce company processing credit cards through Stripe. Our infrastructure:
- Web app on AWS (EC2, RDS, S3)
- Mobile apps (iOS, Android)
- Customer support portal with order history
- Analytics dashboard showing transaction summaries

We need to understand our PCI DSS obligations and create a compliance roadmap.

---

## Exemplary Response

### 1. PCI DSS Scope Determination

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PCI DSS SCOPE ANALYSIS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  QUESTION: Do you store, process, or transmit cardholder data (CHD)?        │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │   CARDHOLDER DATA FLOW                                               │   │
│  │   ════════════════════                                               │   │
│  │                                                                       │   │
│  │   Customer → [Your Web App] → [Stripe.js] → Stripe API               │   │
│  │              ↓                      ↓                                 │   │
│  │         Page served          Token only (no CHD)                     │   │
│  │                                     ↓                                 │   │
│  │                            Payment confirmed                          │   │
│  │                                     ↓                                 │   │
│  │   [Your Backend] ←─────── Stripe Webhook                             │   │
│  │        ↓                  (transaction ID, last4, status)            │   │
│  │   Store order + last4                                                │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  USING STRIPE.JS + STRIPE ELEMENTS:                                         │
│  • CHD never touches your servers (tokenization)                            │
│  • You're eligible for SAQ A or SAQ A-EP                                    │
│  • Scope is significantly reduced                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. SAQ Type Determination

| Scenario | SAQ Type | Requirements |
|----------|----------|--------------|
| Stripe.js with iframe (Elements) | SAQ A | 22 requirements |
| Stripe.js with direct form | SAQ A-EP | 139 requirements |
| Card data on your server | SAQ D | 329 requirements |
| Card-present (terminals) | SAQ B-IP | 82 requirements |

**Your Case (Stripe Elements):** SAQ A — Minimal compliance burden

### 3. SAQ A Requirements Checklist

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SAQ A REQUIREMENTS (v4.0)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Requirement 2: Secure Configurations                                        │
│  ├── 2.1.1  Defined processes for configuration standards     [_] DONE     │
│  └── 2.2.7  Non-console admin access encrypted (HTTPS)        [_] DONE     │
│                                                                              │
│  Requirement 3: Protect Stored Account Data                                  │
│  └── 3.2.1  Do not store SAD after authorization               [_] DONE    │
│             (N/A if using Stripe - they store it)                           │
│                                                                              │
│  Requirement 6: Secure Development                                           │
│  ├── 6.4.1  Public-facing web apps protected against attacks   [_] DONE    │
│  ├── 6.4.2  Automated technical solution for web attacks       [_] DONE    │
│  └── 6.4.3  Payment page scripts integrity verified            [_] DONE    │
│                                                                              │
│  Requirement 8: User Identification                                          │
│  ├── 8.2.1  Unique IDs for all users                          [_] DONE     │
│  ├── 8.3.1  MFA for admin access to CDE                        [_] DONE    │
│  ├── 8.3.4  Lockout after 10 invalid attempts                  [_] DONE    │
│  └── 8.3.6  Passwords min 12 chars or 8 with complexity        [_] DONE    │
│                                                                              │
│  Requirement 9: Physical Access (N/A for fully outsourced)                   │
│  └── N/A - Stripe handles physical card data                                │
│                                                                              │
│  Requirement 11: Security Testing                                            │
│  └── 11.3.2 External vulnerability scans quarterly (ASV)       [_] DONE    │
│                                                                              │
│  Requirement 12: Security Policies                                           │
│  ├── 12.1   Security policy exists and reviewed annually       [_] DONE    │
│  ├── 12.8   Service provider management                        [_] DONE    │
│  └── 12.10  Incident response plan                             [_] DONE    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. Gap Analysis

| # | Requirement | Current State | Gap | Priority |
|---|-------------|---------------|-----|----------|
| 1 | 6.4.3 Script integrity | No SRI implemented | Add SRI hashes to payment scripts | P1 |
| 2 | 8.3.1 MFA | MFA optional | Enforce MFA for admin access | P1 |
| 3 | 11.3.2 ASV scans | Never performed | Schedule quarterly ASV scans | P1 |
| 4 | 12.1 Security policy | Informal practices | Document formal policy | P2 |
| 5 | 12.8 Vendor management | Stripe AOC on file? | Obtain Stripe's AOC annually | P2 |
| 6 | 12.10 Incident response | No documented plan | Create IR playbook | P2 |
| 7 | 2.2.7 Encrypted admin | HTTP allowed | Force HTTPS everywhere | P1 |
| 8 | 6.4.1 Web app protection | Basic WAF | Review WAF rules | P2 |

### 5. Technical Remediation

#### 5.1 Payment Page Script Integrity (Req 6.4.3)

```html
<!-- Before: No integrity verification -->
<script src="https://js.stripe.com/v3/"></script>

<!-- After: Subresource Integrity (SRI) -->
<script
    src="https://js.stripe.com/v3/"
    integrity="sha384-[hash]"
    crossorigin="anonymous"
></script>

<!-- CSP Header for payment page -->
Content-Security-Policy:
    default-src 'self';
    script-src 'self' https://js.stripe.com;
    frame-src 'self' https://js.stripe.com https://hooks.stripe.com;
    connect-src 'self' https://api.stripe.com;
    style-src 'self' 'unsafe-inline';
```

```javascript
// Script inventory for 6.4.3 compliance
const PAYMENT_PAGE_SCRIPTS = {
    'stripe-js': {
        src: 'https://js.stripe.com/v3/',
        purpose: 'Payment form tokenization',
        vendor: 'Stripe, Inc.',
        justification: 'Required for PCI-compliant card collection',
        reviewer: 'security@company.com',
        last_reviewed: '2026-01-15'
    },
    // Document ALL scripts on payment pages
};
```

#### 5.2 MFA Enforcement (Req 8.3.1)

```python
# AWS Cognito MFA enforcement
import boto3

cognito = boto3.client('cognito-idp')

# Enforce MFA for admin users
def enforce_mfa_for_admin_group():
    cognito.admin_set_user_mfa_preference(
        UserPoolId='us-east-1_xxx',
        Username='admin_user',
        SoftwareTokenMfaSettings={
            'Enabled': True,
            'PreferredMfa': True
        }
    )

# Terraform: Enforce MFA on AWS accounts
resource "aws_iam_account_password_policy" "strict" {
    minimum_password_length        = 12
    require_lowercase_characters   = true
    require_uppercase_characters   = true
    require_numbers                = true
    require_symbols                = true
    max_password_age               = 90
    password_reuse_prevention      = 12
}

# IAM policy requiring MFA
data "aws_iam_policy_document" "require_mfa" {
    statement {
        effect = "Deny"
        actions = ["*"]
        resources = ["*"]
        condition {
            test     = "BoolIfExists"
            variable = "aws:MultiFactorAuthPresent"
            values   = ["false"]
        }
    }
}
```

#### 5.3 ASV Scanning Setup (Req 11.3.2)

```yaml
# ASV Scan Schedule
quarterly_scans:
  Q1: 2026-03-15
  Q2: 2026-06-15
  Q3: 2026-09-15
  Q4: 2026-12-15

approved_scanning_vendors:
  - Qualys
  - Tenable
  - Rapid7

scan_scope:
  external_ips:
    - 203.0.113.10  # Web server
    - 203.0.113.11  # API server

  domains:
    - www.example.com
    - api.example.com
    - checkout.example.com  # Payment page

exclusions: []  # All in-scope IPs must be scanned

remediation_sla:
  critical: 24 hours
  high: 7 days
  medium: 30 days
  low: 90 days
```

#### 5.4 Security Policy Template (Req 12.1)

```markdown
# Information Security Policy

## 1. Purpose
This policy establishes the security framework for protecting
cardholder data and complying with PCI DSS requirements.

## 2. Scope
All systems, personnel, and processes involved in payment processing.

## 3. Roles and Responsibilities

| Role | Responsibility |
|------|---------------|
| CISO | Policy owner, compliance oversight |
| Engineering | Technical controls implementation |
| DevOps | Infrastructure security |
| Support | Secure handling of customer inquiries |

## 4. Data Classification

| Classification | Examples | Handling |
|----------------|----------|----------|
| Restricted | Full PAN (N/A - Stripe handles) | Never store |
| Confidential | Customer PII, last4 | Encrypted at rest |
| Internal | Transaction IDs | Access controlled |
| Public | Product info | No restrictions |

## 5. Access Control
- Principle of least privilege
- MFA required for admin access
- Quarterly access reviews
- Immediate revocation on termination

## 6. Change Management
- All changes peer-reviewed
- Security review for payment-related changes
- Documented rollback procedures

## 7. Incident Response
See Incident Response Plan (Appendix A)

## 8. Policy Review
- Annual review (minimum)
- After significant changes
- After security incidents

Approved by: _____________ Date: _____________
Next review: _____________
```

### 6. Vendor Management (Req 12.8)

```yaml
# Service Provider Inventory
service_providers:
  stripe:
    service: Payment processing
    pci_level: Level 1 Service Provider
    aoc_expiry: 2026-12-31
    aoc_location: /compliance/vendor_aocs/stripe_2026.pdf
    contact: compliance@stripe.com
    data_shared:
      - Tokenized card data (handled by them)
      - Transaction amounts
      - Customer email (for receipts)

  aws:
    service: Cloud infrastructure
    pci_level: Level 1 Service Provider
    aoc_expiry: 2026-09-30
    aoc_location: /compliance/vendor_aocs/aws_2026.pdf
    responsibility_matrix: /compliance/aws_shared_responsibility.pdf

  datadog:
    service: Monitoring
    pci_level: N/A - No CHD access
    note: Logs sanitized before sending

annual_review_checklist:
  - [ ] Request updated AOC from each provider
  - [ ] Verify PCI compliance status
  - [ ] Review shared responsibility matrix
  - [ ] Update contracts if needed
  - [ ] Document any changes in scope
```

### 7. Incident Response Plan (Req 12.10)

```markdown
# Payment Card Incident Response Plan

## 1. Incident Classification

| Severity | Definition | Response Time |
|----------|------------|---------------|
| P1 Critical | Confirmed CHD breach | Immediate |
| P2 High | Suspected CHD exposure | 1 hour |
| P3 Medium | Payment system anomaly | 4 hours |
| P4 Low | Policy violation | 24 hours |

## 2. Response Team

| Role | Primary | Backup | Contact |
|------|---------|--------|---------|
| Incident Commander | CTO | VP Eng | +1-xxx |
| Technical Lead | Security Engineer | Sr. Dev | +1-xxx |
| Communications | CEO | Marketing Dir | +1-xxx |
| Legal | General Counsel | External | +1-xxx |

## 3. Response Procedures

### Phase 1: Detection & Analysis (0-1 hour)
1. Confirm incident (not false positive)
2. Classify severity
3. Activate response team
4. Begin evidence preservation

### Phase 2: Containment (1-4 hours)
1. Isolate affected systems
2. Block malicious IPs/accounts
3. Preserve logs and evidence
4. Notify Stripe if payment-related

### Phase 3: Eradication (4-24 hours)
1. Remove threat actor access
2. Patch vulnerabilities
3. Reset compromised credentials
4. Verify clean state

### Phase 4: Recovery (24-72 hours)
1. Restore systems from clean backups
2. Implement additional monitoring
3. Validate payment processing
4. Gradual service restoration

### Phase 5: Post-Incident (1-2 weeks)
1. Root cause analysis
2. Update security controls
3. Regulatory notifications (if required)
4. Lessons learned documentation

## 4. Notification Requirements

| Stakeholder | Trigger | Timeline |
|-------------|---------|----------|
| Stripe | Any payment compromise | Immediate |
| Card Brands | >10,000 cards | 24 hours |
| Customers | Their data affected | 72 hours |
| Regulators | Breach confirmed | Per jurisdiction |

## 5. Evidence Preservation

Collect and preserve:
- [ ] System logs (last 90 days)
- [ ] Network traffic captures
- [ ] Malware samples
- [ ] Affected system images
- [ ] Access logs
- [ ] Timeline documentation
```

### 8. Compliance Calendar

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ANNUAL PCI COMPLIANCE CALENDAR                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  JANUARY                          FEBRUARY                                   │
│  └── Review security policy       └── Update vendor AOC inventory           │
│                                                                              │
│  MARCH                            APRIL                                      │
│  └── Q1 ASV scan                  └── Review access controls                │
│                                                                              │
│  MAY                              JUNE                                       │
│  └── Security awareness training  └── Q2 ASV scan                           │
│                                                                              │
│  JULY                             AUGUST                                     │
│  └── Incident response drill      └── Penetration test                      │
│                                                                              │
│  SEPTEMBER                        OCTOBER                                    │
│  └── Q3 ASV scan                  └── Policy review                         │
│                                                                              │
│  NOVEMBER                         DECEMBER                                   │
│  └── Security training refresh    └── Q4 ASV scan                           │
│                                       Annual SAQ submission                  │
│                                                                              │
│  CONTINUOUS:                                                                 │
│  • Log monitoring                 • Vulnerability management                │
│  • Access reviews (quarterly)     • Change management                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9. Evidence Collection Matrix

| Requirement | Evidence Type | Location | Retention |
|-------------|---------------|----------|-----------|
| 2.2.7 Encrypted admin | TLS config, cert | /etc/nginx/ssl/ | Current |
| 6.4.3 Script integrity | CSP headers, SRI | Nginx config | 1 year |
| 8.3.1 MFA | AWS IAM config | AWS Console | 1 year |
| 8.3.6 Password policy | IAM password policy | AWS Console | 1 year |
| 11.3.2 ASV scans | Scan reports | /compliance/asv/ | 1 year |
| 12.1 Security policy | Policy document | /compliance/policies/ | 3 years |
| 12.8 Vendor management | AOCs, contracts | /compliance/vendors/ | 3 years |
| 12.10 Incident response | IR plan, drill reports | /compliance/ir/ | 3 years |

---

## Why This Is A Good Example

- Correct SAQ type determination for Stripe
- Complete requirement mapping for SAQ A
- Actionable technical remediation steps
- Ready-to-use policy templates
- Compliance calendar for ongoing maintenance

---

## Key Patterns

1. **Scope Reduction** - Using tokenization minimizes PCI scope
2. **SAQ Selection** - Correct SAQ dramatically reduces burden
3. **Vendor Reliance** - Leverage provider's compliance (Stripe)
4. **Evidence-Based** - Document everything for assessor

---

**Tags:** #compliance #pci-dss #payment-security #stripe #saq
**Version:** 1.0.0
**Last Updated:** 2026-01-23
