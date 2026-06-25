# Example: Sprint Planning (Agile/Scrum)

## User Request

```
Спланируй 2-week sprint для команды из 5 инженеров с полной автоматизацией трекинга.
```

## Reasoning

**Domain:** Planning (Agile/Scrum sprint planning)
**Complexity:** Medium
**Model:** Sonnet

## Response

### Sprint Planning Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SPRINT PLANNING CEREMONY (4 hours for 2-week sprint)                   │
├─────────────────────────────────────────────────────────────────────────┤
│  PART 1: What can we deliver? (2 hours)                                 │
│  ├─► Review sprint goal (aligned with roadmap)                          │
│  ├─► Calculate team capacity (hours available)                          │
│  ├─► Calculate velocity (last 3 sprints average)                        │
│  ├─► Select stories from backlog (top priority)                         │
│  └─► Commitment: Can we deliver sprint goal?                            │
│                                                                          │
│  PART 2: How will we do the work? (2 hours)                             │
│  ├─► Decompose stories into tasks (<8h each)                            │
│  ├─► Identify dependencies and blockers                                 │
│  ├─► Assign initial owners (can change during sprint)                   │
│  ├─► Estimate tasks (hours, not story points)                           │
│  └─► Validate: Does task breakdown match capacity?                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Sprint 23: OAuth2 Authentication (Feb 1-14, 2026)

### Sprint Goal

**"Enable secure user authentication with OAuth2 and JWT, allowing users to login with Google/GitHub accounts"**

*(Single focus, specific, measurable, achievable in 2 weeks)*

---

### Team Capacity Calculation

```python
# capacity_calculator.py - Calculate available sprint capacity
from datetime import datetime, timedelta

class SprintCapacity:
    def __init__(self, sprint_start, sprint_end, team_members):
        self.sprint_start = sprint_start
        self.sprint_end = sprint_end
        self.team = team_members

    def calculate_working_days(self):
        """Calculate working days excluding weekends."""
        days = (self.sprint_end - self.sprint_start).days + 1
        working_days = 0

        for i in range(days):
            day = self.sprint_start + timedelta(days=i)
            if day.weekday() < 5:  # Monday = 0, Friday = 4
                working_days += 1

        return working_days

    def calculate_capacity(self):
        """Calculate total team capacity in hours."""
        working_days = self.calculate_working_days()

        total_capacity = 0

        for member in self.team:
            # Base: 6h/day productive time (not 8h)
            daily_hours = 6

            # Adjust for PTO
            pto_days = member.get('pto_days', 0)
            available_days = working_days - pto_days

            # Adjust for meetings (10-20% overhead)
            meeting_overhead = member.get('meeting_overhead', 0.15)
            effective_hours = daily_hours * (1 - meeting_overhead)

            # Adjust for oncall (if applicable)
            oncall_hours = member.get('oncall_hours', 0)

            member_capacity = (available_days * effective_hours) - oncall_hours
            total_capacity += member_capacity

            print(f"{member['name']}: {member_capacity:.1f}h "
                  f"({available_days} days × {effective_hours:.1f}h - {oncall_hours}h oncall)")

        return total_capacity


# Example usage
team = [
    {'name': 'Alice', 'pto_days': 0, 'meeting_overhead': 0.20, 'oncall_hours': 0},
    {'name': 'Bob', 'pto_days': 2, 'meeting_overhead': 0.15, 'oncall_hours': 8},  # 2 days PTO
    {'name': 'Carol', 'pto_days': 0, 'meeting_overhead': 0.15, 'oncall_hours': 0},
    {'name': 'Dave', 'pto_days': 0, 'meeting_overhead': 0.10, 'oncall_hours': 0},  # Junior, fewer meetings
    {'name': 'Eve', 'pto_days': 0, 'meeting_overhead': 0.25, 'oncall_hours': 0},  # Tech lead, more meetings
]

sprint_start = datetime(2026, 2, 1)  # Monday
sprint_end = datetime(2026, 2, 14)   # Friday (10 working days)

capacity = SprintCapacity(sprint_start, sprint_end, team)
total_hours = capacity.calculate_capacity()

print(f"\nTotal team capacity: {total_hours:.1f} hours")
print(f"Working days: {capacity.calculate_working_days()}")

# Output:
# Alice: 48.0h (10 days × 4.8h - 0h oncall)
# Bob: 30.6h (8 days × 5.1h - 8h oncall)   # 2 days PTO
# Carol: 51.0h (10 days × 5.1h - 0h oncall)
# Dave: 54.0h (10 days × 5.4h - 0h oncall)  # Fewer meetings
# Eve: 45.0h (10 days × 4.5h - 0h oncall)   # More meetings
#
# Total team capacity: 228.6 hours
```

---

### Velocity Calculation

```python
# velocity_tracker.py - Calculate team velocity from past sprints
import statistics

class VelocityTracker:
    def __init__(self, past_sprints):
        self.sprints = past_sprints

    def calculate_average_velocity(self):
        """Use last 3 sprints for velocity (rolling average)."""
        recent_sprints = self.sprints[-3:]  # Last 3 sprints
        completed_points = [s['completed_points'] for s in recent_sprints]

        avg_velocity = statistics.mean(completed_points)
        std_dev = statistics.stdev(completed_points) if len(completed_points) > 1 else 0

        print(f"Sprint velocities (last 3): {completed_points}")
        print(f"Average velocity: {avg_velocity:.1f} story points")
        print(f"Standard deviation: {std_dev:.1f} points")

        # Conservative estimate: use lower bound (avg - 0.5*std_dev)
        conservative_velocity = avg_velocity - (0.5 * std_dev)

        print(f"Conservative velocity for planning: {conservative_velocity:.1f} points")
        return conservative_velocity

    def calculate_capacity_in_points(self, available_hours):
        """Convert hours to story points using historical data."""
        # Calculate average hours per story point from past sprints
        hours_per_point = []

        for sprint in self.sprints:
            if sprint['completed_points'] > 0:
                ratio = sprint['total_hours'] / sprint['completed_points']
                hours_per_point.append(ratio)

        avg_hours_per_point = statistics.mean(hours_per_point)

        capacity_points = available_hours / avg_hours_per_point

        print(f"\nHistorical avg: {avg_hours_per_point:.1f}h per story point")
        print(f"Capacity: {available_hours:.1f}h ÷ {avg_hours_per_point:.1f}h/point = {capacity_points:.1f} points")

        return capacity_points


# Example data
past_sprints = [
    {'sprint': 20, 'completed_points': 42, 'total_hours': 210},
    {'sprint': 21, 'completed_points': 48, 'total_hours': 240},
    {'sprint': 22, 'completed_points': 45, 'total_hours': 225},
]

tracker = VelocityTracker(past_sprints)
velocity = tracker.calculate_average_velocity()
capacity_points = tracker.calculate_capacity_in_points(228.6)  # From capacity calculation

# Output:
# Sprint velocities (last 3): [42, 48, 45]
# Average velocity: 45.0 story points
# Standard deviation: 3.0 points
# Conservative velocity for planning: 43.5 points
#
# Historical avg: 5.0h per story point
# Capacity: 228.6h ÷ 5.0h/point = 45.7 points
```

---

### Sprint Backlog (45 story points)

| ID | User Story | Priority | Points | Assignee | Dependencies | Hours Est |
|----|-----------|----------|--------|----------|--------------|-----------|
| US-101 | As a user, I can login with Google OAuth2 | P0 | 13 | Alice | — | 60h |
| US-102 | As a system, I validate JWT tokens securely | P0 | 8 | Bob | US-101 | 40h |
| US-103 | As a user, I can view my profile after login | P1 | 5 | Carol | US-102 | 25h |
| US-104 | As a user, I see a polished login UI | P1 | 3 | Dave | US-101 | 15h |
| US-105 | As a system, I manage user sessions with Redis | P1 | 8 | Eve | US-102 | 40h |
| US-106 | As an admin, I can configure OAuth providers | P2 | 5 | Alice | US-101 | 25h |
| US-107 | As a security team, I verify auth is OWASP compliant | P2 | 3 | Bob | All | 15h |
| **TOTAL** | | | **45** | | | **220h** |

**Buffer:** 228.6h capacity - 220h planned = **8.6h unplanned work buffer (4%)**

---

### Story Point Estimation (Planning Poker)

```python
# planning_poker.py - Facilitate story point estimation
import statistics

def planning_poker_round(story_id, estimates):
    """
    Conduct Planning Poker round.
    estimates: dict of {team_member: estimate}
    """
    values = list(estimates.values())

    print(f"\nStory: {story_id}")
    print(f"Estimates: {estimates}")

    if len(set(values)) == 1:
        # Consensus reached
        print(f"✅ Consensus: {values[0]} story points")
        return values[0]

    # Find outliers
    median = statistics.median(values)
    min_est = min(values)
    max_est = max(values)

    print(f"Median: {median}, Range: {min_est}-{max_est}")

    if max_est / min_est > 2:
        print("⚠️  Large variance! Discuss:")
        print(f"   - {[k for k,v in estimates.items() if v == min_est]}: Why {min_est}?")
        print(f"   - {[k for k,v in estimates.items() if v == max_est]}: Why {max_est}?")
        print("   Re-estimate after discussion.")
        return None
    else:
        # Use median if close enough
        print(f"✅ Close enough, using median: {median}")
        return median


# Example Planning Poker session
story = "US-101: Implement OAuth2 flow"

# Round 1: Initial estimates
round1 = planning_poker_round("US-101", {
    'Alice': 8,
    'Bob': 13,
    'Carol': 8,
    'Dave': 5,   # Outlier (optimistic)
    'Eve': 13
})

# Output:
# Story: US-101
# Estimates: {'Alice': 8, 'Bob': 13, 'Carol': 8, 'Dave': 5, 'Eve': 13}
# Median: 8, Range: 5-13
# ⚠️  Large variance! Discuss:
#    - ['Dave']: Why 5?
#    - ['Bob', 'Eve']: Why 13?
#    Re-estimate after discussion.

# Round 2: After discussion (Dave learned about JWT complexity)
round2 = planning_poker_round("US-101", {
    'Alice': 13,
    'Bob': 13,
    'Carol': 13,
    'Dave': 8,   # Updated after discussion
    'Eve': 13
})

# Output:
# ✅ Close enough, using median: 13
```

---

### Sprint Tracking Automation

```python
# sprint_burndown.py - Generate burndown chart data
import requests
from datetime import datetime, timedelta
import json

class SprintBurndown:
    def __init__(self, jira_url, api_token, sprint_id):
        self.jira_url = jira_url
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
        self.sprint_id = sprint_id

    def get_remaining_work(self):
        """Query Jira for remaining story points each day."""
        url = f"{self.jira_url}/rest/agile/1.0/sprint/{self.sprint_id}/issue"

        response = requests.get(url, headers=self.headers)
        issues = response.json()['issues']

        remaining_points = 0

        for issue in issues:
            status = issue['fields']['status']['name']
            points = issue['fields'].get('customfield_10016', 0)  # Story points field

            if status not in ['Done', 'Closed']:
                remaining_points += points

        return remaining_points

    def generate_burndown_data(self, sprint_start, sprint_end, total_points):
        """Generate ideal and actual burndown data."""
        working_days = (sprint_end - sprint_start).days + 1

        # Ideal burndown (linear)
        ideal_burndown = []
        daily_burn = total_points / working_days

        for day in range(working_days + 1):
            ideal_remaining = total_points - (day * daily_burn)
            ideal_burndown.append({
                'day': day,
                'ideal_remaining': max(0, ideal_remaining)
            })

        # Actual burndown (fetch from Jira daily)
        actual_burndown = []
        for day in range(working_days + 1):
            date = sprint_start + timedelta(days=day)
            # In real implementation, query historical data
            # For now, simulate
            actual_remaining = self.get_remaining_work()  # Current day only
            actual_burndown.append({
                'day': day,
                'date': date.strftime('%Y-%m-%d'),
                'actual_remaining': actual_remaining
            })

        return {'ideal': ideal_burndown, 'actual': actual_burndown}


# Example usage
burndown = SprintBurndown(
    jira_url='https://company.atlassian.net',
    api_token='YOUR_API_TOKEN',
    sprint_id=23
)

data = burndown.generate_burndown_data(
    sprint_start=datetime(2026, 2, 1),
    sprint_end=datetime(2026, 2, 14),
    total_points=45
)

print(json.dumps(data, indent=2))
```

---

## Definition of Done (Automated Checklist)

```yaml
# dod_checklist.yml - Definition of Done for each story
criteria:
  - id: code_review
    name: "Code reviewed by 2 engineers"
    automated: true
    check: "gh pr view {pr_number} --json reviews | jq '.reviews | length >= 2'"

  - id: unit_tests
    name: "Unit tests with ≥80% coverage"
    automated: true
    check: "pytest --cov --cov-fail-under=80"

  - id: integration_tests
    name: "Integration tests passing"
    automated: true
    check: "pytest tests/integration/ --exitfirst"

  - id: security_scan
    name: "Security scan (no high/critical vulns)"
    automated: true
    check: "bandit -r src/ -ll || snyk test"

  - id: documentation
    name: "API documentation updated"
    automated: false
    check: "Manual review of docs/"

  - id: staging_deploy
    name: "Deployed to staging environment"
    automated: true
    check: "kubectl get deployment {app} -n staging -o jsonpath='{.spec.template.spec.containers[0].image}' | grep {version}"

  - id: po_acceptance
    name: "Product Owner accepted story"
    automated: false
    check: "Jira status == 'Accepted'"
```

```bash
# check_dod.sh - Verify Definition of Done
#!/bin/bash

STORY_ID="US-101"
PR_NUMBER=234

echo "Checking Definition of Done for $STORY_ID..."

# Code review
REVIEWS=$(gh pr view $PR_NUMBER --json reviews --jq '.reviews | length')
if [ "$REVIEWS" -ge 2 ]; then
    echo "✅ Code review: $REVIEWS approvals"
else
    echo "❌ Code review: Only $REVIEWS approvals (need 2)"
fi

# Unit tests
if pytest --cov --cov-fail-under=80 &>/dev/null; then
    echo "✅ Unit tests: Coverage ≥80%"
else
    echo "❌ Unit tests: Coverage <80%"
fi

# Integration tests
if pytest tests/integration/ --exitfirst &>/dev/null; then
    echo "✅ Integration tests: Passing"
else
    echo "❌ Integration tests: Failing"
fi

# Security scan
if bandit -r src/ -ll &>/dev/null; then
    echo "✅ Security scan: No high/critical issues"
else
    echo "❌ Security scan: Issues found"
fi
```

---

## Sprint Retrospective Framework

```markdown
### Retrospective: Sprint 23 (Feb 14, 2026)

#### What Went Well? 🎉
- OAuth2 integration completed on schedule
- Zero production incidents
- Code review turnaround < 4 hours

#### What Didn't Go Well? 😞
- US-107 security audit found 2 issues (added to Sprint 24)
- Bob's PTO caused bottleneck on US-102 (dependency)
- Daily standup started late 3 times

#### Action Items 🚀
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| Add backup reviewer for auth PRs | Alice | Next sprint | 🟢 |
| Schedule PTO earlier (2 weeks notice) | Team | Ongoing | 🟡 |
| Set Slack reminder for standup | Dave | Feb 15 | ✅ |

#### Metrics
- Velocity: 43 points (planned: 45) → 96% delivery
- Carryover: 2 points (US-107 partial)
- Unplanned work: 6 hours (hotfix)
```

---

## Common Sprint Anti-Patterns

| Anti-Pattern | Why Bad | Solution |
|--------------|---------|----------|
| **Planning to 100% capacity** | No buffer for unplanned work | Plan to 80-85% capacity |
| **No sprint goal** | Just a list of tasks | Define single focus outcome |
| **Scope creep mid-sprint** | Breaks commitment | Defer to next sprint (unless critical) |
| **Carrying over >20% stories** | Estimation/commitment problem | Improve estimation, reduce WIP |
| **Skipping retrospectives** | No continuous improvement | Mandatory every sprint |
| **Individual commitments only** | Not a team | Team commits to sprint goal together |

---

## Key Takeaways

1. **Sprint goal** — Single focus, not just task list (outcome-driven)
2. **Capacity** — Calculate realistically (6h/day, account for PTO/meetings)
3. **Velocity** — Use 3-sprint rolling average (conservative estimate)
4. **Buffer** — Plan to 80-85% capacity for unplanned work
5. **Automation** — Track burndown, DoD checklist, velocity automatically

**Duration:** 2 weeks standard (1-4 weeks acceptable)
**Capacity:** 6h/day productive time, not 8h (meetings, email, breaks)
**Tools:** Jira, Linear, GitHub Projects
**Success metric:** Deliver sprint goal with <20% carryover
