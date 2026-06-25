# Few-Shot Example: Requirements Elicitation for CRM System

**Domain:** Business Analysis
**Skill Level:** Intermediate
**Pattern:** BABOK-based requirements gathering with stakeholder analysis

---

## User Query

```
We need a new CRM system for our sales team (30 users). Help me structure requirements properly - what questions should I ask? How do I document this?
```

---

## Exemplary Response

┌─ ROUTING ──────────────────────────────────────────────────┐
│ Role: Business Analyst                                     │
│ Confidence: HIGH (88%)                                     │
│ Modules: 19-business-analysis.md                          │
│ Approach: BABOK v3 requirements elicitation framework     │
└────────────────────────────────────────────────────────────┘

## Requirements Elicitation Process

I'll guide you through a structured BABOK-compliant requirements gathering process for your CRM system.

---

## Phase 1: Stakeholder Analysis (BABOK 2.2)

### Stakeholder Identification Matrix

| Stakeholder Group | Role | Interest | Influence | Engagement Strategy |
|-------------------|------|----------|-----------|---------------------|
| **Primary** |
| Sales Team (30 users) | End Users | HIGH - Daily usage | MEDIUM | Workshops, interviews |
| Sales Manager | Approver | HIGH - Team efficiency | HIGH | Regular reviews |
| Sales Director | Sponsor | HIGH - Revenue impact | VERY HIGH | Executive briefings |
| **Secondary** |
| IT Department | Technical Implementation | MEDIUM - Maintenance | HIGH | Technical workshops |
| Finance Team | Budget Approval | MEDIUM - Cost | HIGH | Cost-benefit analysis |
| Marketing Team | Lead Management | MEDIUM - Integration | MEDIUM | Requirements review |
| Customer Support | Post-sale tracking | MEDIUM - Customer data | LOW | Consultation |
| **Tertiary** |
| Data Protection Officer | Compliance (GDPR) | MEDIUM - Legal risk | HIGH | Compliance review |
| External Vendor | System Provider | HIGH - Contract | MEDIUM | RFP process |

**Engagement Plan:**
- **Sales Team**: 3 focus group sessions (10 users each)
- **Sales Manager**: Weekly 1-on-1 interviews
- **IT**: Technical feasibility workshop
- **Finance**: Budget approval meeting
- **DPO**: Compliance requirements session

---

## Phase 2: Business Context (BABOK 5.1)

### Business Problem Statement

```
CURRENT STATE:
- Sales team uses Excel spreadsheets + email for customer tracking
- No centralized customer database
- Manual reporting (2-3 hours/week per sales rep)
- Lost follow-ups → estimated 15% revenue loss
- Poor visibility into sales pipeline

DESIRED STATE:
- Centralized CRM with 360° customer view
- Automated workflow (lead → opportunity → deal)
- Real-time reporting and dashboards
- Mobile access for field sales
- Integration with email and calendar

SUCCESS METRICS:
- Reduce manual reporting time by 70% (from 2.5hr to 45min/week)
- Increase conversion rate by 10% (better follow-up)
- Improve forecast accuracy to ±5%
- 90% user adoption within 3 months
```

### Context Diagram (BABOK 5.3.1)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL ENTITIES                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [Customers] ←───────────────┐                                          │
│       ↑                      │                                          │
│       │ contact data         │ lead data                                │
│       │                      │                                          │
│       ↓                      ↓                                          │
│  ┌──────────────────────────────────────────┐                          │
│  │                                          │                          │
│  │          CRM SYSTEM                      │ ←── integration ─── [Email Server]
│  │                                          │                          │
│  │  • Lead Management                       │ ←── integration ─── [Calendar]
│  │  • Opportunity Tracking                  │                          │
│  │  • Customer Database                     │ ←── sync ───────────[Mobile App]
│  │  • Reporting & Analytics                 │                          │
│  │                                          │ ←── data export ────[ERP System]
│  └──────────────────────────────────────────┘                          │
│       ↑           ↑           ↑                                         │
│       │           │           │                                         │
│   [Sales Team] [Manager] [Director]                                    │
│   30 users     reports    dashboards                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 3: Elicitation Questions (BABOK 4.1)

### Interview Script for Sales Team

#### Section A: Current Process Pain Points
1. **Lead Management**
   - How do you currently track new leads?
   - What happens when a lead comes in? (walk me through the process)
   - How often do leads fall through the cracks? Can you estimate percentage?
   - What information do you need to capture about a lead?

2. **Customer Interaction**
   - How do you prepare for a sales call/meeting?
   - Where do you store customer communication history?
   - How long does it take to find customer information?
   - Do you ever call the same customer twice by mistake?

3. **Reporting & Visibility**
   - How do you report on your pipeline? (manual vs automated)
   - How much time per week do you spend on reporting?
   - What metrics does your manager ask for?
   - Can you easily see your deals at each stage?

#### Section B: Future State Requirements
4. **Must-Have Features**
   - What's the ONE feature you can't live without?
   - What tasks eat most of your time that should be automated?
   - Do you need mobile access? What for?

5. **Integration Needs**
   - What tools do you use daily? (email, calendar, LinkedIn, etc.)
   - Should CRM integrate with your email?
   - Do you need calendar sync for meeting tracking?

6. **Usability**
   - How tech-savvy is your team? (rate 1-10)
   - Maximum clicks you'd tolerate to log a call? (2, 3, 5?)
   - Would you use it if data entry takes >30 seconds per interaction?

---

## Phase 4: Requirements Documentation (BABOK 5.2)

### Functional Requirements

#### FR-1: Lead Management
```
ID: FR-1.1
Priority: MUST HAVE (P1)
Description: System SHALL capture lead information from multiple sources
Acceptance Criteria:
  - Manual entry form with fields: Name, Company, Email, Phone, Source
  - Email import (parse lead from forwarded email)
  - Web form integration (marketing website)
  - Bulk import from CSV (legacy data migration)
Rationale: Sales team receives leads via email (60%), web forms (30%), manual entry (10%)
Source: Sales Team Workshop #1, 2026-02-06
Dependencies: None
```

```
ID: FR-1.2
Priority: MUST HAVE (P1)
Description: System SHALL assign leads to sales reps automatically
Acceptance Criteria:
  - Round-robin assignment based on territory
  - Load balancing (equal distribution)
  - Manager override capability
  - Email notification to assigned rep within 5 minutes
Rationale: Current manual assignment causes delays (avg 4 hours)
Source: Sales Manager Interview, 2026-02-07
Dependencies: FR-1.1
```

```
ID: FR-1.3
Priority: SHOULD HAVE (P2)
Description: System SHOULD score leads based on qualification criteria
Acceptance Criteria:
  - Configurable scoring rules (company size, budget, timeline)
  - Visual indicator (HOT/WARM/COLD)
  - Sort/filter by lead score
Rationale: Prioritization helps reps focus on high-value leads
Source: Sales Director requirement, 2026-02-08
Dependencies: FR-1.1
```

#### FR-2: Opportunity Tracking
```
ID: FR-2.1
Priority: MUST HAVE (P1)
Description: System SHALL track opportunities through pipeline stages
Acceptance Criteria:
  - Stages: Lead → Qualified → Proposal → Negotiation → Closed Won/Lost
  - Drag-and-drop stage updates (Kanban view)
  - Required fields per stage (e.g., budget at Qualified stage)
  - Probability % per stage (configurable)
  - Expected close date
Rationale: Visual pipeline is #1 requested feature (28/30 users)
Source: Sales Team Focus Groups
Dependencies: FR-1.2
```

#### FR-3: Customer Database (360° View)
```
ID: FR-3.1
Priority: MUST HAVE (P1)
Description: System SHALL provide unified customer profile
Acceptance Criteria:
  - Contact info (name, email, phone, company)
  - Interaction history (calls, emails, meetings) with timestamps
  - Document attachments (contracts, proposals)
  - Notes section (rich text, taggable)
  - Related opportunities and deals
  - Activity timeline (chronological view)
Rationale: Reps waste 15-20 min per day searching for customer info
Source: Time-motion study, 2026-02-05
Dependencies: None
```

#### FR-4: Reporting & Dashboards
```
ID: FR-4.1
Priority: MUST HAVE (P1)
Description: System SHALL generate real-time sales reports
Acceptance Criteria:
  - Sales rep dashboard: my pipeline, tasks, forecast
  - Manager dashboard: team performance, conversion rates, bottlenecks
  - Director dashboard: revenue forecast, win/loss analysis
  - Export to Excel/PDF
  - Scheduled email reports (daily/weekly)
Rationale: Manual reporting costs 75 hours/month across team
Source: Sales Manager, ROI calculation
Dependencies: FR-2.1, FR-3.1
```

### Non-Functional Requirements (BABOK 5.2.6)

#### NFR-1: Performance
```
ID: NFR-1.1
Type: Performance
Description: System response time SHALL be <2 seconds for 95% of operations
Measurement: Load test with 50 concurrent users
Rationale: User acceptance threshold (UX research)
```

```
ID: NFR-1.2
Type: Availability
Description: System SHALL have 99.5% uptime during business hours (8am-8pm local time)
Measurement: Monthly uptime monitoring
Rationale: Sales team works across time zones
```

#### NFR-2: Usability
```
ID: NFR-2.1
Type: Usability
Description: New user SHALL complete basic tasks (add lead, log call) within 15 minutes of training
Measurement: User onboarding testing with 5 representative users
Rationale: Low tech-savvy team (avg skill 4/10)
```

#### NFR-3: Security & Compliance
```
ID: NFR-3.1
Type: Security
Description: System SHALL comply with GDPR requirements
Acceptance Criteria:
  - Data encryption at rest and in transit (TLS 1.3, AES-256)
  - Right to erasure (delete customer data on request)
  - Data export capability (portable format)
  - Audit log (who accessed what data, when)
  - Role-based access control (RBAC)
Rationale: EU customers (40% of database), GDPR mandatory
Source: Data Protection Officer requirements
```

#### NFR-4: Integration
```
ID: NFR-4.1
Type: Integration
Description: System SHALL integrate with Microsoft 365 (Outlook, Calendar)
Acceptance Criteria:
  - Email sync (log emails to customer record)
  - Calendar sync (meetings auto-logged)
  - Contact sync (bi-directional)
Rationale: Team uses Outlook exclusively
```

---

## Phase 5: Use Cases (BABOK 5.3.4)

### Use Case: Log Sales Call

```
USE CASE ID: UC-01
USE CASE NAME: Log Sales Call
ACTOR: Sales Representative
PRECONDITIONS: User is authenticated, customer exists in CRM
DESCRIPTION: Sales rep logs a phone call with customer after it ends

MAIN FLOW:
1. User opens customer profile
2. User clicks "Log Activity" button
3. System displays activity form
4. User selects activity type: "Phone Call"
5. User enters call notes (required, min 10 characters)
6. User sets follow-up task (optional): date, description
7. User clicks "Save"
8. System timestamps activity (auto-capture)
9. System adds activity to customer timeline
10. System creates follow-up task if specified
11. System displays success message
12. System returns to customer profile

ALTERNATIVE FLOWS:
3a. Quick log (from mobile):
    - System shows simplified form (notes only)
    - Auto-fills: date=now, type=call, duration=blank

7a. Validation error:
    - Notes too short (<10 chars)
    - System highlights field, shows error message
    - User corrects and resubmits

POSTCONDITIONS:
- Activity logged in database
- Customer "Last Contact" date updated
- Follow-up task created (if specified)

SUCCESS CRITERIA:
- Time to log: <30 seconds (target: 20 seconds)
- Mobile support: Yes
- Offline capability: Sync when reconnected

FREQUENCY: 150 calls/day across team (5 per rep)
PRIORITY: HIGH (P1) - core workflow
```

---

## Phase 6: Acceptance Criteria (BABOK 5.2.5)

### Feature: Lead Assignment

| Scenario | Given | When | Then | Test Data |
|----------|-------|------|------|-----------|
| **Happy Path** | New lead submitted via web form | System receives lead | Lead assigned to sales rep with lowest load in territory "West" | Lead: {name: "John Doe", territory: "West"} |
| **Round-Robin** | 3 leads submitted in sequence | Territory = "East", 3 reps available | Leads distributed 1-2-3-1-2-3 pattern | Reps: Alice, Bob, Carol (East) |
| **Manager Override** | Lead auto-assigned to Rep A | Manager reassigns to Rep B | System updates assignment, notifies Rep B | Lead #12345 |
| **Email Notification** | Lead assigned to rep | Within 5 minutes | Rep receives email with lead details and link to CRM | Check email delivery logs |
| **Duplicate Prevention** | Lead with same email exists | New lead submitted | System flags as duplicate, suggests merge | Email: existing@company.com |

---

## Phase 7: Requirements Traceability Matrix (BABOK 5.2.4)

| Req ID | Description | Business Need | Stakeholder | Priority | Status | Test Case |
|--------|-------------|--------------|-------------|----------|--------|-----------|
| FR-1.1 | Capture leads | Lost leads = 15% revenue loss | Sales Team | P1 | Draft | TC-001 |
| FR-1.2 | Auto-assign leads | Manual assignment delay (4hr) | Sales Mgr | P1 | Draft | TC-002 |
| FR-1.3 | Lead scoring | Prioritization | Sales Dir | P2 | Draft | TC-003 |
| FR-2.1 | Pipeline tracking | Visibility | Sales Team | P1 | Draft | TC-004 |
| NFR-3.1 | GDPR compliance | Legal requirement | DPO | P1 | Draft | TC-020 |

---

## Phase 8: Prioritization (MoSCoW Method)

| Priority | Requirements | Justification |
|----------|--------------|---------------|
| **MUST HAVE (P1)** | FR-1.1, FR-1.2, FR-2.1, FR-3.1, FR-4.1, NFR-3.1 | Core functionality, legal compliance, ROI drivers |
| **SHOULD HAVE (P2)** | FR-1.3 (lead scoring), Integration with LinkedIn | Significant value, not blockers |
| **COULD HAVE (P3)** | Advanced analytics, AI-powered insights | Nice-to-have, future phase |
| **WON'T HAVE (v1)** | Marketing automation, customer portal | Out of scope for Phase 1 |

---

## Deliverables Checklist

☑ **Business Requirements Document (BRD)**
  - Problem statement
  - Success metrics
  - Stakeholder analysis
  - Context diagram

☑ **Functional Requirements Specification (FRS)**
  - 25 functional requirements (FR-1.x to FR-8.x)
  - 10 non-functional requirements (NFR-1.x to NFR-4.x)

☑ **Use Case Document**
  - 15 detailed use cases
  - Actor-action-response format

☑ **Requirements Traceability Matrix**
  - Maps requirements → business needs → test cases

☑ **Acceptance Criteria**
  - Given-When-Then scenarios for all P1 requirements

☑ **Wireframes/Mockups** (collaborate with UX designer)
  - Lead entry form
  - Pipeline Kanban view
  - Customer 360° profile
  - Manager dashboard

---

## Next Steps

1. **Validation Workshop** (Week 2)
   - Review requirements with stakeholders
   - Confirm priorities (MoSCoW)
   - Get sign-off from Sales Director

2. **RFP Preparation** (Week 3)
   - Translate requirements into RFP sections
   - Define evaluation criteria
   - Vendor shortlist (Salesforce, HubSpot, Zoho, Pipedrive)

3. **Vendor Demos** (Week 4-5)
   - Provide requirements document to vendors
   - Score against criteria
   - POC with top 2 vendors

4. **Final Selection** (Week 6)
   - Cost-benefit analysis
   - Risk assessment
   - Executive approval

---

## BABOK Knowledge Areas Applied

| Knowledge Area | Techniques Used |
|---------------|-----------------|
| **2.2 Conduct Stakeholder Analysis** | Power/Interest Grid, RACI Matrix |
| **4.1 Prepare for Elicitation** | Interview scripts, workshop planning |
| **4.2 Conduct Elicitation** | Interviews, focus groups, workshops |
| **5.1 Analyze Current State** | Process mapping, pain point analysis |
| **5.2 Define Future State** | Use cases, user stories, acceptance criteria |
| **5.3 Model Requirements** | Context diagrams, data flow diagrams |
| **7.1 Prioritize Requirements** | MoSCoW method, value vs effort matrix |
| **7.5 Assess Requirements Changes** | Traceability matrix, impact analysis |

---

## Key Takeaways

1. **Start with WHY**: Understand business problem before jumping to solutions
2. **Engage Stakeholders Early**: 30 users = 30 different needs, find common ground
3. **Prioritize Ruthlessly**: Not everything is P1, defer nice-to-haves
4. **Validate Frequently**: Requirements workshops every 2 weeks
5. **Trace Everything**: Every requirement → business need → test case
6. **Think Compliance**: GDPR/security are NOT afterthoughts

**Authorization Level**: ANALYZE (requirements gathering) + PLAN (solution design)
**Compliance Note**: GDPR requirements reviewed by Data Protection Officer (mandatory)

## References

- **BABOK v3**: Business Analysis Body of Knowledge (IIBA)
- **IEEE 29148**: Standard for Requirements Engineering
- **ISO/IEC 25010**: Systems and Software Quality Models
