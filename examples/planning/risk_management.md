# Example: Project Risk Management

## User Request

```
Составь risk register для migration проекта (monolith → microservices) с mitigation strategies.
```

## Reasoning

**Domain:** Planning (Risk management, mitigation strategies)
**Complexity:** Medium
**Model:** Sonnet

## Response

### Risk Management Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│  RISK MANAGEMENT PROCESS                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│  1. IDENTIFY → Brainstorm risks (technical, schedule, resource, external)│
│  2. ASSESS → Score probability (1-5) × impact (1-5) = risk score (1-25)  │
│  3. PRIORITIZE → Focus on high-risk items (score >15)                    │
│  4. MITIGATE → Plan preventive actions (reduce probability/impact)       │
│  5. MONITOR → Track triggers, update register weekly                     │
│  6. RESPOND → Execute contingency plans when risks materialize           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Project: Monolith → Microservices Migration

**Timeline:** Q1-Q2 2026 (6 months)
**Team:** 8 engineers
**Budget:** $500K

---

## Risk Register

```python
# risk_register.py - Model and track project risks
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class Risk:
    id: str
    category: str       # Technical, Schedule, Resource, External
    description: str
    probability: int    # 1 (rare) to 5 (almost certain)
    impact: int         # 1 (negligible) to 5 (catastrophic)
    owner: str
    mitigation: str
    contingency: str
    trigger: str        # Warning sign that risk is materializing
    status: str         # Open, Monitoring, Mitigated, Occurred

    def risk_score(self) -> int:
        """Calculate risk score (probability × impact)."""
        return self.probability * self.impact

    def priority(self) -> str:
        """Risk priority based on score."""
        score = self.risk_score()
        if score >= 15:
            return "🔴 Critical"
        elif score >= 10:
            return "🟠 High"
        elif score >= 5:
            return "🟡 Medium"
        else:
            return "🟢 Low"


class RiskRegister:
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.risks: List[Risk] = []

    def add_risk(self, risk: Risk):
        """Add risk to register."""
        self.risks.append(risk)

    def get_top_risks(self, n: int = 5) -> List[Risk]:
        """Get top N risks by score."""
        return sorted(self.risks, key=lambda r: r.risk_score(), reverse=True)[:n]

    def risks_by_category(self, category: str) -> List[Risk]:
        """Get all risks in a category."""
        return [r for r in self.risks if r.category == category]

    def print_register(self):
        """Print formatted risk register."""
        print(f"Risk Register: {self.project_name}\n")
        print(f"{'ID':<8} {'Category':<12} {'Priority':<15} {'Score':<6} {'Description':<40}")
        print("-" * 90)

        for risk in sorted(self.risks, key=lambda r: r.risk_score(), reverse=True):
            desc_short = risk.description[:37] + "..." if len(risk.description) > 40 else risk.description
            print(f"{risk.id:<8} {risk.category:<12} {risk.priority():<15} {risk.risk_score():<6} {desc_short:<40}")

    def export_to_markdown(self) -> str:
        """Export risk register to Markdown."""
        md = f"# Risk Register: {self.project_name}\n\n"
        md += f"Generated: {datetime.now().strftime('%Y-%m-%d')}\n\n"

        for risk in sorted(self.risks, key=lambda r: r.risk_score(), reverse=True):
            md += f"## {risk.id}: {risk.description}\n\n"
            md += f"- **Category:** {risk.category}\n"
            md += f"- **Priority:** {risk.priority()}\n"
            md += f"- **Score:** {risk.risk_score()} (Probability: {risk.probability}, Impact: {risk.impact})\n"
            md += f"- **Owner:** {risk.owner}\n"
            md += f"- **Trigger:** {risk.trigger}\n\n"
            md += f"### Mitigation Strategy\n{risk.mitigation}\n\n"
            md += f"### Contingency Plan\n{risk.contingency}\n\n"
            md += "---\n\n"

        return md


# Example: Microservices migration risk register
register = RiskRegister("Monolith → Microservices Migration")

register.add_risk(Risk(
    id="RISK-001",
    category="Technical",
    description="Data consistency issues during migration (split database)",
    probability=4,  # Likely
    impact=5,       # Catastrophic (data loss/corruption)
    owner="Alice (Tech Lead)",
    mitigation="""
    - Implement dual-write pattern (write to both old and new DBs)
    - Use distributed transactions (Saga pattern)
    - Run data validation queries daily
    - Keep monolith DB as source of truth until cutover
    """,
    contingency="""
    - Rollback to monolith if data inconsistencies detected
    - Restore from backup (tested weekly)
    - Manual data reconciliation script prepared
    """,
    trigger="Data validation queries show >1% discrepancy",
    status="Open"
))

register.add_risk(Risk(
    id="RISK-002",
    category="Schedule",
    description="Migration takes longer than 6 months (scope creep)",
    probability=4,  # Likely
    impact=4,       # Major (budget overrun, missed deadline)
    owner="Bob (PM)",
    mitigation="""
    - Scope locked after kickoff (no new features during migration)
    - Phased approach: migrate 1 service at a time (MVP first)
    - Weekly progress tracking (burn-down chart)
    - Buffer of 2 weeks built into timeline
    """,
    contingency="""
    - If >2 weeks behind by Month 3: cut scope (defer non-critical services)
    - Request budget extension (pre-approved $100K contingency)
    - Hire 2 contractors for 3 months
    """,
    trigger="Behind schedule by >1 week for 2 consecutive sprints",
    status="Monitoring"
))

register.add_risk(Risk(
    id="RISK-003",
    category="Technical",
    description="Network latency between microservices causes performance degradation",
    probability=3,  # Possible
    impact=4,       # Major (user-facing slowness)
    owner="Carol (Senior Engineer)",
    mitigation="""
    - Load testing BEFORE cutover (simulate production traffic)
    - Implement caching (Redis) for frequently accessed data
    - Use gRPC instead of REST for inter-service communication
    - Co-locate services in same AWS region/AZ
    """,
    contingency="""
    - If latency >500ms: add read replicas
    - Enable circuit breakers (fail fast)
    - Rollback to monolith if P95 latency >1s
    """,
    trigger="P95 latency increases by >200ms in staging tests",
    status="Open"
))

register.add_risk(Risk(
    id="RISK-004",
    category="Resource",
    description="Key engineer leaves mid-project",
    probability=2,  # Unlikely (but possible)
    impact=5,       # Catastrophic (knowledge loss, delays)
    owner="Dave (Engineering Manager)",
    mitigation="""
    - Documentation: architecture diagrams, decision logs
    - Pair programming: knowledge shared across team
    - Retention bonuses for key engineers
    - Cross-training: 2 engineers know each service
    """,
    contingency="""
    - Promote from within (identify successors now)
    - Hire replacement immediately (pre-vetted candidates)
    - Extend timeline by 4 weeks if critical person leaves
    """,
    trigger="Engineer announces resignation or starts interviewing",
    status="Open"
))

register.add_risk(Risk(
    id="RISK-005",
    category="External",
    description="AWS outage during migration cutover",
    probability=2,  # Unlikely
    impact=4,       # Major (extended downtime)
    owner="Eve (DevOps Lead)",
    mitigation="""
    - Schedule cutover during low-traffic hours (Sunday 2AM)
    - Multi-region setup (failover to us-west-2 if us-east-1 down)
    - Pre-cutover checklist (AWS health dashboard check)
    - Dry-run cutover in staging (practice)
    """,
    contingency="""
    - Delay cutover if AWS status page shows issues
    - Immediate rollback plan (automated script)
    - Communication plan: notify customers within 15 min
    """,
    trigger="AWS status page shows degraded performance in our region",
    status="Open"
))

register.add_risk(Risk(
    id="RISK-006",
    category="Technical",
    description="Breaking API changes cause client app failures",
    probability=3,  # Possible
    impact=4,       # Major (production incidents)
    owner="Frank (Backend Lead)",
    mitigation="""
    - API versioning (v1 and v2 run in parallel for 3 months)
    - Deprecation warnings sent to clients (email + dashboard)
    - Contract testing (Pact) to detect breaking changes
    - Canary deployments (5% traffic first)
    """,
    contingency="""
    - Rollback to v1 API if error rate >1%
    - Hotfix endpoint to patch critical issues
    - Extend v1 support by 3 months if needed
    """,
    trigger="API error rate increases by >0.5% after deployment",
    status="Open"
))

register.add_risk(Risk(
    id="RISK-007",
    category="Schedule",
    description="Testing phase uncovers critical bugs requiring rework",
    probability=4,  # Likely
    impact=3,       # Moderate (delays, not catastrophic)
    owner="Grace (QA Lead)",
    mitigation="""
    - Early integration testing (start in Month 2, not Month 6)
    - Automated test suite (unit, integration, e2e)
    - Bug triage: P0/P1 fixed immediately, P2 deferred to post-launch
    - Weekly bug review meetings
    """,
    contingency="""
    - Extend testing phase by 2 weeks if >10 P0/P1 bugs
    - Reduce scope: defer non-critical features to post-launch
    - Add 2 QA contractors for 1 month
    """,
    trigger=">5 P0/P1 bugs found in integration testing",
    status="Monitoring"
))

# Print register
register.print_register()
```

---

## Risk Register Output

```
Risk Register: Monolith → Microservices Migration

ID       Category     Priority        Score  Description
------------------------------------------------------------------------------------------
RISK-001 Technical    🔴 Critical      20     Data consistency issues during migrat...
RISK-002 Schedule     🔴 Critical      16     Migration takes longer than 6 months ...
RISK-003 Technical    🟠 High          12     Network latency between microservices...
RISK-006 Technical    🟠 High          12     Breaking API changes cause client app...
RISK-007 Schedule     🟠 High          12     Testing phase uncovers critical bugs ...
RISK-004 Resource     🟠 High          10     Key engineer leaves mid-project
RISK-005 External     🟡 Medium        8      AWS outage during migration cutover
```

---

## Risk Assessment Matrix

```
PROBABILITY vs IMPACT

       │  1 (Negligible)  │  2 (Minor)  │  3 (Moderate)  │  4 (Major)  │  5 (Catastrophic)
────────┼──────────────────┼─────────────┼────────────────┼─────────────┼───────────────────
5       │    5 🟡          │   10 🟠     │    15 🔴       │   20 🔴     │    25 🔴
(Almost │                  │             │                │             │
Certain)│                  │             │                │             │
────────┼──────────────────┼─────────────┼────────────────┼─────────────┼───────────────────
4       │    4 🟢          │    8 🟡     │    12 🟠       │   16 🔴     │    20 🔴
(Likely)│                  │             │  RISK-003      │  RISK-002   │   RISK-001
        │                  │             │  RISK-006      │             │
        │                  │             │  RISK-007      │             │
────────┼──────────────────┼─────────────┼────────────────┼─────────────┼───────────────────
3       │    3 🟢          │    6 🟡     │     9 🟡       │   12 🟠     │    15 🔴
(Poss-  │                  │             │                │             │
ible)   │                  │             │                │             │
────────┼──────────────────┼─────────────┼────────────────┼─────────────┼───────────────────
2       │    2 🟢          │    4 🟢     │     6 🟡       │    8 🟡     │    10 🟠
(Un-    │                  │             │                │  RISK-005   │   RISK-004
likely) │                  │             │                │             │
────────┼──────────────────┼─────────────┼────────────────┼─────────────┼───────────────────
1       │    1 🟢          │    2 🟢     │     3 🟢       │    4 🟢     │     5 🟡
(Rare)  │                  │             │                │             │
```

---

## Risk Monitoring Dashboard

```python
# risk_monitor.py - Track risk triggers and alert
from datetime import datetime
import smtplib

class RiskMonitor:
    def __init__(self, register: RiskRegister):
        self.register = register

    def check_triggers(self, metrics: dict) -> List[Risk]:
        """
        Check if any risk triggers have been activated.

        metrics: dict of current project metrics
        Returns: list of risks whose triggers have been activated
        """
        activated_risks = []

        for risk in self.register.risks:
            if self.is_triggered(risk, metrics):
                activated_risks.append(risk)
                print(f"⚠️  RISK TRIGGERED: {risk.id} - {risk.description}")
                print(f"   Trigger: {risk.trigger}")
                print(f"   Contingency: {risk.contingency[:100]}...")

        return activated_risks

    def is_triggered(self, risk: Risk, metrics: dict) -> bool:
        """Check if specific risk trigger condition is met."""
        # Example trigger checks (in real system, parse risk.trigger string)

        if risk.id == "RISK-001":
            # Data validation query shows >1% discrepancy
            data_discrepancy = metrics.get('data_discrepancy_pct', 0)
            return data_discrepancy > 1.0

        if risk.id == "RISK-002":
            # Behind schedule by >1 week for 2 consecutive sprints
            weeks_behind = metrics.get('weeks_behind_schedule', 0)
            consecutive_sprints_late = metrics.get('consecutive_sprints_late', 0)
            return weeks_behind > 1 and consecutive_sprints_late >= 2

        if risk.id == "RISK-003":
            # P95 latency increases by >200ms
            p95_latency_increase = metrics.get('p95_latency_increase_ms', 0)
            return p95_latency_increase > 200

        # Default: not triggered
        return False

    def send_alert(self, risk: Risk, recipients: List[str]):
        """Send email alert when risk is triggered."""
        subject = f"⚠️ RISK ALERT: {risk.id} - {risk.description}"
        body = f"""
Risk Triggered: {risk.id}
Priority: {risk.priority()}
Score: {risk.risk_score()}
Owner: {risk.owner}

Trigger Condition:
{risk.trigger}

Contingency Plan:
{risk.contingency}

Action Required: Review contingency plan and execute as needed.
"""
        print(f"📧 Alert sent to: {', '.join(recipients)}")
        print(f"Subject: {subject}")

        # In real implementation, send email via SMTP
        # smtplib.SMTP(...).sendmail(...)


# Example: Monitor risks weekly
monitor = RiskMonitor(register)

# Simulate metrics from project tracking system
metrics = {
    'data_discrepancy_pct': 0.5,        # OK
    'weeks_behind_schedule': 1.5,        # TRIGGERED
    'consecutive_sprints_late': 2,       # TRIGGERED
    'p95_latency_increase_ms': 50,       # OK
}

activated = monitor.check_triggers(metrics)

if activated:
    for risk in activated:
        monitor.send_alert(risk, [risk.owner, 'pmo@company.com'])

# Output:
# ⚠️  RISK TRIGGERED: RISK-002 - Migration takes longer than 6 months (scope creep)
#    Trigger: Behind schedule by >1 week for 2 consecutive sprints
#    Contingency: If >2 weeks behind by Month 3: cut scope (defer non-critical services)
#                Request budget extension...
#
# 📧 Alert sent to: Bob (PM), pmo@company.com
# Subject: ⚠️ RISK ALERT: RISK-002 - Migration takes longer than 6 months (scope creep)
```

---

## Pre-Mortem Exercise

**"Imagine it's July 2026 and the migration was a disaster. What went wrong?"**

```markdown
### Pre-Mortem Results (Team Brainstorm)

1. **"We underestimated data migration complexity"**
   - Edge cases in legacy data (NULL values, orphaned records)
   - No ETL testing environment
   - → Mitigation: Create data migration pipeline with validation (RISK-001)

2. **"Third-party API rate limits broke our microservices"**
   - Didn't test under production load
   - → Mitigation: Load testing with realistic API call volumes (NEW RISK-008)

3. **"No one understood the new architecture after Bob left"**
   - Single point of failure (knowledge)
   - → Mitigation: Documentation, pair programming (RISK-004)

4. **"Security audit found critical vulnerabilities post-launch"**
   - Didn't test auth between services
   - → Mitigation: Security review before cutover (NEW RISK-009)

5. **"Production deployment took 12 hours instead of 2"**
   - Never practiced cutover in staging
   - → Mitigation: Dry-run cutover 2 weeks before go-live
```

---

## Risk Response Strategies

| Strategy | Description | When to Use | Example |
|----------|-------------|-------------|---------|
| **Avoid** | Eliminate risk entirely | High impact, feasible to eliminate | Don't migrate critical service (leave in monolith) |
| **Mitigate** | Reduce probability or impact | High/medium risk, can't eliminate | Load testing, dual-write pattern, backups |
| **Transfer** | Shift risk to 3rd party | High impact, not core competency | Use managed service (AWS RDS) instead of self-hosting |
| **Accept** | Acknowledge risk, no action | Low risk, cost of mitigation > cost of risk | Minor UI glitches during migration |

---

## Weekly Risk Review Checklist

```markdown
### Risk Review Meeting (Every Monday, 30 min)

**Attendees:** PM, Tech Lead, Engineering Manager

#### Agenda:
1. ✅ Review risk register (any new risks?)
2. ✅ Check risk triggers (any activated this week?)
3. ✅ Update risk scores (probability/impact changed?)
4. ✅ Review mitigation progress (actions on track?)
5. ✅ Close mitigated risks (score now <5?)
6. ✅ Escalate critical risks (score >15 to leadership)

#### Outputs:
- Updated risk register (committed to Git)
- Action items assigned (added to Jira)
- Escalation email (if critical risks)
```

---

## Common Risk Management Mistakes

| Mistake | Why Bad | Solution |
|---------|---------|----------|
| **Ignoring low-probability, high-impact risks** | Black swan events can kill projects | Track all risks with impact ≥4 |
| **No risk owner** | No one accountable for mitigation | Assign owner to every risk |
| **Risk register created once, never updated** | Stale data, false sense of security | Weekly reviews mandatory |
| **No trigger conditions** | Can't detect when risk materializes | Define measurable triggers |
| **Only identify risks, no mitigation** | Identification without action is useless | Every risk needs mitigation + contingency |
| **Overly optimistic estimates** | Underestimate probability/impact | Pre-mortem exercise to uncover hidden risks |

---

## Key Takeaways

1. **Risk score** = Probability (1-5) × Impact (1-5) → Focus on score >10
2. **Mitigation** reduces probability/impact BEFORE risk occurs
3. **Contingency** is the response plan AFTER risk occurs
4. **Triggers** are measurable warning signs (track in dashboard)
5. **Pre-mortem** uncovers risks the team wouldn't think of otherwise

**Tools:** Spreadsheets, Jira Risk Register plugin, Monday.com
**Cadence:** Review weekly (30 min), update immediately when triggered
**Success metric:** <10% of identified risks materialize, all critical risks have mitigation
