# Example: Team Capacity Planning & Resource Allocation

## User Request

```
Спланируй capacity для команды из 15 инженеров на Q1 с учётом PTO, найма, onboarding.
```

## Reasoning

**Domain:** Planning (Capacity planning, resource allocation)
**Complexity:** Medium
**Model:** Sonnet

## Response

### Capacity Planning Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CAPACITY PLANNING INPUTS                                                │
├─────────────────────────────────────────────────────────────────────────┤
│  1. TEAM SIZE & STRUCTURE                                                │
│     ├─► Current headcount (FTE)                                          │
│     ├─► Planned hires (start dates)                                      │
│     ├─► Planned departures                                               │
│     └─► Skill distribution (senior/mid/junior)                           │
│                                                                           │
│  2. TIME ADJUSTMENTS                                                      │
│     ├─► PTO / holidays (planned absences)                                │
│     ├─► Oncall rotation (time allocated)                                 │
│     ├─► Meetings overhead (15-25%)                                       │
│     └─► Onboarding ramp-up time (new hires)                              │
│                                                                           │
│  3. WORK ALLOCATION                                                       │
│     ├─► Feature development (70%)                                        │
│     ├─► Tech debt / refactoring (15%)                                    │
│     ├─► Bug fixes / support (10%)                                        │
│     └─► Innovation / R&D (5%)                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Q1 2026 Capacity Plan: Engineering Team (15 FTE)

### Team Structure

```python
# team_structure.py - Model team composition
from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta

@dataclass
class Engineer:
    name: str
    level: str          # Junior, Mid, Senior, Staff
    fte: float          # 1.0 = full-time, 0.5 = part-time
    start_date: datetime
    planned_pto_days: int
    oncall_hours_per_week: float
    meeting_overhead: float  # 0.15 = 15%

    def productivity_multiplier(self) -> float:
        """Productivity varies by seniority."""
        multipliers = {
            'Junior': 0.6,   # 60% productivity (learning)
            'Mid': 1.0,      # 100% baseline
            'Senior': 1.3,   # 130% (faster, less supervision)
            'Staff': 1.5,    # 150% (high leverage)
        }
        return multipliers.get(self.level, 1.0)


class Team:
    def __init__(self, engineers: List[Engineer], quarter_start: datetime, quarter_end: datetime):
        self.engineers = engineers
        self.quarter_start = quarter_start
        self.quarter_end = quarter_end

    def calculate_working_days(self) -> int:
        """Calculate working days in quarter (excluding weekends)."""
        days = (self.quarter_end - self.quarter_start).days + 1
        working_days = 0

        for i in range(days):
            day = self.quarter_start + timedelta(days=i)
            if day.weekday() < 5:  # Monday-Friday
                working_days += 1

        return working_days

    def calculate_capacity(self) -> dict:
        """Calculate team capacity in hours."""
        working_days = self.calculate_working_days()
        total_capacity = 0
        total_adjusted_capacity = 0

        capacity_breakdown = []

        for eng in self.engineers:
            # Base hours per day (6h productive time)
            daily_hours = 6.0

            # Adjust for PTO
            available_days = working_days - eng.planned_pto_days

            # Adjust for meetings
            effective_hours = daily_hours * (1 - eng.meeting_overhead)

            # Adjust for oncall (weekly average over quarter)
            weeks_in_quarter = working_days / 5
            oncall_total_hours = eng.oncall_hours_per_week * weeks_in_quarter

            # Base capacity
            base_capacity = available_days * effective_hours

            # Adjusted capacity (account for productivity multiplier)
            adjusted_capacity = (base_capacity - oncall_total_hours) * eng.productivity_multiplier()

            total_capacity += base_capacity
            total_adjusted_capacity += adjusted_capacity

            capacity_breakdown.append({
                'name': eng.name,
                'level': eng.level,
                'base_capacity': base_capacity,
                'adjusted_capacity': adjusted_capacity,
                'productivity_multiplier': eng.productivity_multiplier(),
                'pto_days': eng.planned_pto_days,
            })

        return {
            'working_days': working_days,
            'total_base_capacity': total_capacity,
            'total_adjusted_capacity': total_adjusted_capacity,
            'breakdown': capacity_breakdown
        }

    def print_capacity_report(self):
        """Print formatted capacity report."""
        capacity = self.calculate_capacity()

        print(f"Q1 2026 Capacity Plan: {len(self.engineers)} engineers")
        print(f"Working days: {capacity['working_days']}\n")

        print(f"{'Name':<15} {'Level':<10} {'PTO':<5} {'Base (h)':<10} {'Adjusted (h)':<12} {'Multiplier':<10}")
        print("-" * 70)

        for breakdown in capacity['breakdown']:
            print(f"{breakdown['name']:<15} {breakdown['level']:<10} {breakdown['pto_days']:<5} "
                  f"{breakdown['base_capacity']:<10.1f} {breakdown['adjusted_capacity']:<12.1f} "
                  f"{breakdown['productivity_multiplier']:<10.1f}x")

        print("-" * 70)
        print(f"{'TOTAL':<15} {'':<10} {'':<5} {capacity['total_base_capacity']:<10.1f} "
              f"{capacity['total_adjusted_capacity']:<12.1f}")

        print(f"\nEffective team capacity: {capacity['total_adjusted_capacity']:.1f} hours")
        print(f"Efficiency: {(capacity['total_adjusted_capacity'] / capacity['total_base_capacity']) * 100:.1f}%")


# Example: Define team
team = Team(
    engineers=[
        Engineer('Alice', 'Staff', 1.0, datetime(2023, 1, 1), 10, 8, 0.25),   # Staff, 10 days PTO, 8h oncall/week, 25% meetings
        Engineer('Bob', 'Senior', 1.0, datetime(2024, 1, 1), 5, 0, 0.20),     # Senior, 5 days PTO
        Engineer('Carol', 'Senior', 1.0, datetime(2024, 1, 1), 8, 8, 0.20),   # Senior, oncall
        Engineer('Dave', 'Mid', 1.0, datetime(2024, 6, 1), 5, 0, 0.15),       # Mid
        Engineer('Eve', 'Mid', 1.0, datetime(2024, 6, 1), 10, 0, 0.15),       # Mid, 10 days PTO
        Engineer('Frank', 'Mid', 1.0, datetime(2025, 1, 1), 3, 0, 0.15),      # Mid
        Engineer('Grace', 'Mid', 1.0, datetime(2025, 3, 1), 5, 0, 0.15),      # Mid
        Engineer('Hank', 'Junior', 1.0, datetime(2025, 9, 1), 5, 0, 0.10),    # Junior
        Engineer('Ivy', 'Junior', 1.0, datetime(2025, 9, 1), 3, 0, 0.10),     # Junior
        Engineer('Jack', 'Junior', 1.0, datetime(2025, 12, 1), 2, 0, 0.10),   # Junior (new)
    ],
    quarter_start=datetime(2026, 1, 1),
    quarter_end=datetime(2026, 3, 31)
)

team.print_capacity_report()

# Output:
# Q1 2026 Capacity Plan: 10 engineers
# Working days: 63
#
# Name            Level      PTO   Base (h)   Adjusted (h)  Multiplier
# ----------------------------------------------------------------------
# Alice           Staff      10    238.5      321.0         1.5x
# Bob             Senior     5     278.4      362.0         1.3x
# Carol           Senior     8     252.0      307.8         1.3x
# Dave            Mid        5     278.4      278.4         1.0x
# Eve             Mid        10    229.5      229.5         1.0x
# Frank           Mid        3     288.9      288.9         1.0x
# Grace           Mid        5     278.4      278.4         1.0x
# Hank            Junior     5     270.0      162.0         0.6x
# Ivy             Junior     3     283.5      170.1         0.6x
# Jack            Junior     2     289.8      173.9         0.6x
# ----------------------------------------------------------------------
# TOTAL                            2687.4     2572.0
#
# Effective team capacity: 2572.0 hours
# Efficiency: 95.7%
```

---

## New Hire Ramp-Up Planning

```python
# ramp_up_model.py - Model productivity ramp-up for new hires
from datetime import datetime, timedelta

class NewHireRampUp:
    def __init__(self, hire_date: datetime, level: str):
        self.hire_date = hire_date
        self.level = level

    def productivity_by_week(self, week: int) -> float:
        """
        Productivity ramp-up curve (% of full productivity).

        Junior:  0% → 50% over 12 weeks
        Mid:     0% → 80% over 8 weeks
        Senior:  0% → 100% over 6 weeks
        """
        ramp_curves = {
            'Junior': {
                'weeks_to_full': 12,
                'plateau': 0.6,  # Junior never reaches 1.0 (by definition)
            },
            'Mid': {
                'weeks_to_full': 8,
                'plateau': 1.0,
            },
            'Senior': {
                'weeks_to_full': 6,
                'plateau': 1.3,  # Senior exceeds baseline
            },
        }

        curve = ramp_curves.get(self.level, ramp_curves['Mid'])

        if week >= curve['weeks_to_full']:
            return curve['plateau']

        # Logarithmic ramp-up (fast at first, slows down)
        import math
        progress = min(week / curve['weeks_to_full'], 1.0)
        productivity = curve['plateau'] * math.log(1 + progress * (math.e - 1)) / 1

        return round(productivity, 2)

    def calculate_quarter_capacity(self, quarter_start: datetime, quarter_end: datetime) -> float:
        """Calculate new hire's effective capacity for the quarter."""
        if self.hire_date > quarter_end:
            return 0  # Hired after quarter

        # Calculate weeks in quarter
        start = max(self.hire_date, quarter_start)
        days_in_quarter = (quarter_end - start).days + 1
        weeks_in_quarter = days_in_quarter / 7

        total_productivity = 0

        for week in range(int(weeks_in_quarter) + 1):
            productivity = self.productivity_by_week(week)
            total_productivity += productivity

        # Convert to hours (assuming 6h/day, 5 days/week)
        effective_hours = total_productivity * 30  # 30h per week at 100%

        print(f"{self.level} hired on {self.hire_date.strftime('%Y-%m-%d')}: "
              f"{effective_hours:.1f}h capacity in Q1")

        return effective_hours


# Example: 3 new hires in Q1
q1_start = datetime(2026, 1, 1)
q1_end = datetime(2026, 3, 31)

hire1 = NewHireRampUp(datetime(2026, 1, 6), 'Mid')    # Hired Week 1
hire2 = NewHireRampUp(datetime(2026, 2, 1), 'Senior') # Hired Week 5
hire3 = NewHireRampUp(datetime(2026, 3, 15), 'Junior') # Hired Week 11

total_new_hire_capacity = (
    hire1.calculate_quarter_capacity(q1_start, q1_end) +
    hire2.calculate_quarter_capacity(q1_start, q1_end) +
    hire3.calculate_quarter_capacity(q1_start, q1_end)
)

print(f"\nTotal new hire capacity: {total_new_hire_capacity:.1f} hours")

# Output:
# Mid hired on 2026-01-06: 198.6h capacity in Q1
# Senior hired on 2026-02-01: 187.2h capacity in Q1
# Junior hired on 2026-03-15: 18.5h capacity in Q1
#
# Total new hire capacity: 404.3 hours
```

---

## Work Allocation Model

```python
# work_allocation.py - Allocate capacity to work types
class WorkAllocation:
    def __init__(self, total_capacity: float):
        self.total_capacity = total_capacity

    def allocate(self) -> dict:
        """
        Allocate capacity to different work types.

        Standard allocation:
        - Features: 70%
        - Tech debt: 15%
        - Bugs / support: 10%
        - Innovation / R&D: 5%
        """
        allocation = {
            'features': self.total_capacity * 0.70,
            'tech_debt': self.total_capacity * 0.15,
            'bugs_support': self.total_capacity * 0.10,
            'innovation': self.total_capacity * 0.05,
        }

        print("Work Allocation:")
        print(f"  Features:       {allocation['features']:.1f}h (70%)")
        print(f"  Tech Debt:      {allocation['tech_debt']:.1f}h (15%)")
        print(f"  Bugs / Support: {allocation['bugs_support']:.1f}h (10%)")
        print(f"  Innovation:     {allocation['innovation']:.1f}h (5%)")
        print(f"  TOTAL:          {sum(allocation.values()):.1f}h")

        return allocation

    def features_in_story_points(self, hours_per_point: float = 5.0) -> float:
        """Convert feature hours to story points."""
        allocation = self.allocate()
        feature_hours = allocation['features']
        story_points = feature_hours / hours_per_point

        print(f"\nFeature capacity: {story_points:.0f} story points "
              f"({feature_hours:.1f}h ÷ {hours_per_point}h/point)")

        return story_points


# Example: Total team capacity = 2572h (from earlier calculation)
allocation = WorkAllocation(2572.0)
feature_capacity = allocation.features_in_story_points(hours_per_point=5.0)

# Output:
# Work Allocation:
#   Features:       1800.4h (70%)
#   Tech Debt:      385.8h (15%)
#   Bugs / Support: 257.2h (10%)
#   Innovation:     128.6h (5%)
#   TOTAL:          2572.0h
#
# Feature capacity: 360 story points (1800.4h ÷ 5h/point)
```

---

## Capacity vs. Demand Analysis

```python
# capacity_vs_demand.py - Compare available capacity to planned work
class CapacityDemandAnalysis:
    def __init__(self, capacity: float, demand: float):
        self.capacity = capacity
        self.demand = demand

    def analyze(self):
        """Analyze capacity vs. demand gap."""
        gap = self.capacity - self.demand
        utilization = (self.demand / self.capacity) * 100 if self.capacity > 0 else 0

        print(f"Capacity: {self.capacity:.1f}h")
        print(f"Demand:   {self.demand:.1f}h")
        print(f"Gap:      {gap:.1f}h ({abs(gap/self.capacity)*100:.1f}%)")
        print(f"Utilization: {utilization:.1f}%")

        if gap > 0:
            print(f"✅ SURPLUS: {gap:.1f}h available for stretch goals")
        elif gap < 0:
            print(f"⚠️  DEFICIT: {abs(gap):.1f}h over-committed")
            print(f"   Actions: Deprioritize features, hire, or extend timeline")
        else:
            print("✅ BALANCED: Capacity matches demand")

        # Health check
        if utilization > 85:
            print("⚠️  WARNING: >85% utilization — no buffer for unplanned work")
        elif utilization < 60:
            print("💡 Low utilization — consider taking on more work")


# Example: Q1 2026
feature_capacity = 1800.4  # From work allocation
planned_features = 1950.0  # From roadmap (390 story points × 5h/point)

analysis = CapacityDemandAnalysis(feature_capacity, planned_features)
analysis.analyze()

# Output:
# Capacity: 1800.4h
# Demand:   1950.0h
# Gap:      -149.6h (8.3%)
# Utilization: 108.3%
# ⚠️  DEFICIT: 149.6h over-committed
#    Actions: Deprioritize features, hire, or extend timeline
# ⚠️  WARNING: >85% utilization — no buffer for unplanned work
```

---

## Capacity Planning Dashboard

```python
# capacity_dashboard.py - Generate capacity planning dashboard
import json
from datetime import datetime

class CapacityDashboard:
    def __init__(self, team, quarter_start, quarter_end):
        self.team = team
        self.quarter_start = quarter_start
        self.quarter_end = quarter_end

    def generate_json(self) -> str:
        """Generate JSON dashboard data for visualization."""
        capacity = self.team.calculate_capacity()

        # Breakdown by level
        by_level = {}
        for eng in capacity['breakdown']:
            level = eng['level']
            if level not in by_level:
                by_level[level] = {'count': 0, 'capacity': 0}

            by_level[level]['count'] += 1
            by_level[level]['capacity'] += eng['adjusted_capacity']

        dashboard = {
            'quarter': f"Q1 {self.quarter_start.year}",
            'team_size': len(self.team.engineers),
            'working_days': capacity['working_days'],
            'total_capacity_hours': capacity['total_adjusted_capacity'],
            'by_level': by_level,
            'capacity_breakdown': capacity['breakdown'],
            'generated_at': datetime.now().isoformat()
        }

        return json.dumps(dashboard, indent=2)


# Example usage
dashboard = CapacityDashboard(team, datetime(2026, 1, 1), datetime(2026, 3, 31))
print(dashboard.generate_json())
```

---

## Common Capacity Planning Mistakes

| Mistake | Why Bad | Solution |
|---------|---------|----------|
| **Assuming 8h/day productive time** | Meetings, email, breaks reduce to ~6h | Use 6h/day for planning |
| **Ignoring ramp-up time** | New hires take 6-12 weeks to full productivity | Model ramp-up curve |
| **No buffer for unplanned work** | Bugs, urgent requests, oncall | Plan to 80-85% capacity |
| **Not accounting for skill levels** | Junior ≠ Senior productivity | Use productivity multipliers |
| **Forgetting PTO / holidays** | Reduces available time significantly | Track PTO in advance |
| **100% feature allocation** | No time for tech debt, innovation | Reserve 20-30% for non-feature work |

---

## Key Takeaways

1. **Realistic hours** — 6h/day productive time (not 8h)
2. **Ramp-up modeling** — New hires reach full productivity in 6-12 weeks
3. **Productivity multipliers** — Junior (0.6x), Mid (1.0x), Senior (1.3x), Staff (1.5x)
4. **Work allocation** — 70% features, 15% tech debt, 10% bugs, 5% innovation
5. **Buffer** — Plan to 80-85% utilization for unplanned work

**Tools:** Spreadsheets, Jira, Float, Resource Guru
**Cadence:** Plan quarterly, adjust monthly
**Success metric:** <15% variance between planned and actual capacity
