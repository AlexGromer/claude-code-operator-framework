# Few-Shot Example: GDPR Gap Analysis

**Domain:** compliance
**Skill Level:** Intermediate
**Pattern:** Assess → Map → Gap → Remediate

---

## User Query

Our SaaS company collects user data from EU customers. We have:
- User registration with email, name, phone
- Analytics tracking (cookies, IP addresses)
- Third-party integrations (Stripe, Mailchimp, Google Analytics)
- Data stored on AWS in us-east-1

Conduct a GDPR gap analysis and create a remediation roadmap.

---

## Exemplary Response

### 1. Regulatory Context

| Framework | Version | Scope |
|-----------|---------|-------|
| GDPR | EU 2016/679 | Personal data of EU residents |
| Application | B2C SaaS | Customer data processing |

**Key GDPR Definitions:**
- **Personal Data:** Any data relating to identified/identifiable person
- **Data Controller:** Entity determining purposes of processing
- **Data Processor:** Entity processing data on behalf of controller
- **Processing:** Any operation on personal data

### 2. Data Inventory Assessment

| Data Category | Examples | Legal Basis Required | Current Status |
|---------------|----------|---------------------|----------------|
| Identity Data | Name, email | Consent or Contract | Collected |
| Contact Data | Phone, address | Consent or Contract | Collected |
| Technical Data | IP, cookies | Legitimate Interest or Consent | Collected |
| Usage Data | Page views, clicks | Legitimate Interest | Collected |
| Financial Data | Payment info | Contract | Via Stripe |

**Third-Party Processors:**
| Vendor | Data Shared | GDPR Status | DPA Signed |
|--------|-------------|-------------|------------|
| AWS | All user data | Compliant | Check |
| Stripe | Payment data | Compliant | Check |
| Mailchimp | Email addresses | Compliant | Check |
| Google Analytics | IP, behavior | Issue: Data transfer | Check |

### 3. Gap Analysis

| # | Requirement | Reference | Current State | Gap | Severity | Priority |
|---|-------------|-----------|---------------|-----|----------|----------|
| 1 | Lawful basis documented | Art. 6 | Not documented | Document legal basis for each processing activity | High | P1 |
| 2 | Privacy notice | Art. 13-14 | Generic policy | Update with specific data categories, purposes, recipients | High | P1 |
| 3 | Cookie consent | Art. 6, ePR | Implied consent | Implement proper consent banner with granular control | Critical | P1 |
| 4 | Data Subject Rights | Art. 15-22 | No process | Implement access, deletion, portability requests | High | P1 |
| 5 | DPA with processors | Art. 28 | Unknown | Review and sign DPAs with all vendors | High | P2 |
| 6 | Data location | Art. 44-49 | US storage only | Evaluate EU region or SCCs | Critical | P1 |
| 7 | Breach notification | Art. 33-34 | No process | Create incident response plan | High | P2 |
| 8 | DPIA | Art. 35 | Not performed | Conduct DPIA for high-risk processing | Medium | P2 |
| 9 | Records of processing | Art. 30 | None | Create ROPA (Record of Processing Activities) | High | P2 |
| 10 | DPO designation | Art. 37 | None | Assess if DPO required | Medium | P3 |

### 4. Critical Issues (Immediate Action)

#### Issue 1: Cookie Consent Non-Compliance

**Current State:**
```html
<!-- Current - Non-compliant implied consent -->
<div class="cookie-banner">
  We use cookies to improve your experience.
  <button onclick="closeBanner()">OK</button>
</div>
```

**Required State:**
```html
<!-- Compliant - Granular consent -->
<div id="cookie-consent" class="cookie-modal">
  <h3>Cookie Preferences</h3>
  <p>We use cookies for the following purposes:</p>

  <div class="cookie-category">
    <label>
      <input type="checkbox" checked disabled>
      Essential Cookies (Required)
    </label>
    <p>Necessary for the website to function.</p>
  </div>

  <div class="cookie-category">
    <label>
      <input type="checkbox" id="analytics-consent">
      Analytics Cookies (Optional)
    </label>
    <p>Help us understand how you use our site.</p>
  </div>

  <div class="cookie-category">
    <label>
      <input type="checkbox" id="marketing-consent">
      Marketing Cookies (Optional)
    </label>
    <p>Allow personalized advertising.</p>
  </div>

  <button onclick="savePreferences()">Save Preferences</button>
  <button onclick="acceptAll()">Accept All</button>
  <a href="/privacy-policy">Learn More</a>
</div>
```

#### Issue 2: US Data Storage

**Current State:** All data in `us-east-1`
**Problem:** After Schrems II, US transfers require additional safeguards

**Options:**
1. **EU Data Residency** (Recommended)
   - Move to `eu-west-1` (Ireland) or `eu-central-1` (Frankfurt)
   - Cost: Infrastructure migration effort

2. **Standard Contractual Clauses (SCCs)**
   - Sign new EU-approved SCCs with AWS
   - Conduct Transfer Impact Assessment
   - Implement supplementary measures

3. **EU-US Data Privacy Framework**
   - Check if vendor is DPF certified
   - AWS is certified under DPF

### 5. Remediation Roadmap

#### Phase 1: Critical Compliance (0-30 days)

| # | Action | Owner | Effort | Deliverable |
|---|--------|-------|--------|-------------|
| 1.1 | Implement cookie consent manager | Dev | 5 days | Compliant cookie banner |
| 1.2 | Update privacy policy | Legal | 3 days | Privacy notice per Art. 13 |
| 1.3 | Document lawful bases | Legal | 2 days | Legal basis matrix |
| 1.4 | Migrate to EU region | DevOps | 10 days | Data in eu-west-1 |
| 1.5 | Pause GA until compliant | Dev | 1 day | GA disabled or consented |

#### Phase 2: Core Controls (30-90 days)

| # | Action | Owner | Effort | Deliverable |
|---|--------|-------|--------|-------------|
| 2.1 | Build DSR portal | Dev | 15 days | Self-service data access/deletion |
| 2.2 | Sign DPAs | Legal | 5 days | DPAs with all processors |
| 2.3 | Create ROPA | Legal/Dev | 5 days | Record of Processing Activities |
| 2.4 | Incident response plan | Security | 5 days | 72h notification process |
| 2.5 | Conduct DPIA | Legal/Dev | 10 days | Risk assessment document |

#### Phase 3: Optimization (90+ days)

| # | Action | Owner | Effort | Deliverable |
|---|--------|-------|--------|-------------|
| 3.1 | Privacy by Design training | HR | Ongoing | Staff awareness |
| 3.2 | Data minimization review | Dev | 5 days | Remove unnecessary data collection |
| 3.3 | Retention policy automation | Dev | 10 days | Automatic data deletion |
| 3.4 | Vendor assessment process | Legal | 5 days | Third-party risk framework |

### 6. Policy Templates

#### Privacy Policy Key Sections

```markdown
# Privacy Policy

## 1. Data Controller
[Company Name]
[Address]
Email: privacy@company.com

## 2. What Data We Collect
| Data Type | Purpose | Legal Basis | Retention |
|-----------|---------|-------------|-----------|
| Email address | Account creation | Contract | Account lifetime |
| Name | Personalization | Contract | Account lifetime |
| IP address | Security, analytics | Legitimate Interest | 90 days |
| Payment info | Billing | Contract | 7 years (legal req.) |

## 3. Your Rights
Under GDPR, you have the right to:
- **Access** your personal data
- **Rectify** inaccurate data
- **Erase** your data ("right to be forgotten")
- **Restrict** processing
- **Data portability**
- **Object** to processing
- **Withdraw consent** at any time

To exercise these rights, contact: privacy@company.com
Response time: Within 30 days

## 4. International Transfers
We store data in the EU (AWS eu-west-1).
For any transfers outside EU, we use:
- Standard Contractual Clauses
- EU-US Data Privacy Framework (where applicable)

## 5. Data Security
We implement:
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Access controls
- Regular security audits

## 6. Cookies
See our [Cookie Policy] for details.
You can manage preferences anytime via [Cookie Settings].
```

### 7. Evidence Requirements

| Control | Evidence Type | Frequency | Owner |
|---------|---------------|-----------|-------|
| Consent management | Consent logs with timestamp | Real-time | Dev |
| Privacy notice | Version-controlled document | Per change | Legal |
| DPAs | Signed agreements | Per vendor | Legal |
| DSR handling | Request logs, completion proof | Per request | Support |
| Breach notification | Incident reports | Per incident | Security |
| ROPA | Processing inventory | Annual review | Legal |

### 8. Metrics & KPIs

| Metric | Target | Current | Gap |
|--------|--------|---------|-----|
| DSR response time | <30 days | N/A | Implement |
| Cookie consent rate | >50% | N/A | Implement |
| DPA coverage | 100% | Unknown | Audit |
| Data breach incidents | 0 | Unknown | Monitor |
| Privacy training completion | 100% | 0% | Plan |

---

## Why This Is A Good Example

- Specific article references (Art. 6, 13-14, etc.)
- Prioritized gaps by severity
- Actionable remediation with timelines
- Ready-to-use templates
- Evidence requirements for audit

---

## Key Patterns

1. **Risk-Based Prioritization** - Critical issues first
2. **Specific References** - Article numbers, not generic advice
3. **Phased Roadmap** - Realistic timeline
4. **Evidence-Focused** - Auditable deliverables

---

**Tags:** #compliance #gdpr #privacy #data-protection #gap-analysis
**Version:** 1.0.0
**Last Updated:** 2026-01-23
