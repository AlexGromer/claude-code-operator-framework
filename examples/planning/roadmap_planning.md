# Example: Product Roadmap Planning

## User Request

```
Составь product roadmap на 2026 год для SaaS платформы с приоритизацией фич.
```

## Reasoning

**Domain:** Planning (Product roadmap, prioritization)
**Complexity:** Medium
**Model:** Sonnet

## Response

### Roadmap Planning Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ROADMAP STRUCTURE (Now-Next-Later)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  NOW (Q1 2026)                                                           │
│  ├─► High-confidence items                                              │
│  ├─► Clear requirements & design                                        │
│  ├─► Committed to customers/stakeholders                                │
│  └─► Detailed timelines                                                 │
│                                                                          │
│  NEXT (Q2-Q3 2026)                                                       │
│  ├─► Medium-confidence items                                            │
│  ├─► Research/discovery ongoing                                         │
│  ├─► Rough estimates                                                    │
│  └─► Subject to change                                                  │
│                                                                          │
│  LATER (Q4 2026+)                                                        │
│  ├─► Low-confidence ideas                                               │
│  ├─► Strategic themes only                                              │
│  ├─► No dates/commitments                                               │
│  └─► Direction, not detailed plan                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2026 Roadmap: DevOps SaaS Platform

### Vision Statement

**"Enable engineering teams to deploy code 10× faster with zero manual operations by end of 2026"**

### Strategic Themes (Year-Long)

1. **🚀 Deployment Velocity** — Reduce friction in CI/CD pipeline
2. **🔒 Security & Compliance** — SOC 2 Type II, GDPR, FedRAMP
3. **📊 Observability** — Real-time metrics, logs, traces
4. **💰 Cost Optimization** — Help customers reduce infrastructure spend by 30%

---

## Feature Prioritization (RICE Framework)

```python
# rice_scorer.py - Prioritize features using RICE framework
from dataclasses import dataclass
from typing import List

@dataclass
class Feature:
    id: str
    name: str
    reach: int          # Users impacted per quarter
    impact: float       # 0.25=Minimal, 0.5=Low, 1=Medium, 2=High, 3=Massive
    confidence: float   # 0-100% (how certain are estimates?)
    effort: float       # Person-months

    def rice_score(self) -> float:
        """Calculate RICE score: (Reach × Impact × Confidence) / Effort"""
        return (self.reach * self.impact * (self.confidence / 100)) / self.effort


def prioritize_features(features: List[Feature]) -> List[Feature]:
    """Sort features by RICE score descending."""
    sorted_features = sorted(features, key=lambda f: f.rice_score(), reverse=True)

    print("Feature Prioritization (RICE Score):\n")
    print(f"{'Rank':<5} {'Feature':<40} {'Reach':<8} {'Impact':<8} {'Conf%':<6} {'Effort':<8} {'RICE':<8}")
    print("-" * 90)

    for rank, feature in enumerate(sorted_features, 1):
        print(f"{rank:<5} {feature.name:<40} {feature.reach:<8} {feature.impact:<8.1f} "
              f"{feature.confidence:<6.0f} {feature.effort:<8.1f} {feature.rice_score():<8.1f}")

    return sorted_features


# Example: Prioritize Q1 2026 features
features = [
    Feature(
        id="F-101",
        name="One-click rollback",
        reach=5000,        # 5K customers will use this
        impact=2.0,        # High impact (save 30 min per incident)
        confidence=80,     # 80% confident in estimates
        effort=2.0         # 2 person-months
    ),
    Feature(
        id="F-102",
        name="Kubernetes cost optimization dashboard",
        reach=3000,        # 3K customers with K8s
        impact=3.0,        # Massive impact (save $$$)
        confidence=70,     # 70% confident
        effort=3.0         # 3 person-months
    ),
    Feature(
        id="F-103",
        name="Dark mode UI",
        reach=8000,        # 8K customers requested
        impact=0.5,        # Low impact (aesthetic)
        confidence=95,     # 95% confident (easy)
        effort=0.5         # 0.5 person-months
    ),
    Feature(
        id="F-104",
        name="AI-powered incident root cause analysis",
        reach=5000,        # All customers
        impact=3.0,        # Massive impact (save hours)
        confidence=40,     # 40% confident (experimental)
        effort=6.0         # 6 person-months (complex ML)
    ),
    Feature(
        id="F-105",
        name="Terraform state file import",
        reach=1500,        # 1.5K Terraform users
        impact=1.0,        # Medium impact
        confidence=90,     # 90% confident
        effort=1.0         # 1 person-month
    ),
]

prioritized = prioritize_features(features)

# Output:
# Feature Prioritization (RICE Score):
#
# Rank  Feature                                  Reach    Impact   Conf%  Effort   RICE
# ------------------------------------------------------------------------------------------
# 1     Dark mode UI                             8000     0.5      95     0.5      7600.0
# 2     One-click rollback                       5000     2.0      80     2.0      4000.0
# 3     Kubernetes cost optimization dashboard   3000     3.0      70     3.0      2100.0
# 4     Terraform state file import              1500     1.0      90     1.0      1350.0
# 5     AI-powered incident root cause analysis  5000     3.0      40     6.0      1000.0
```

---

## Q1 2026 Roadmap (NOW)

| Feature | Theme | RICE | Team | Start | Ship | Dependencies |
|---------|-------|------|------|-------|------|--------------|
| **F-103**: Dark mode UI | UX | 7600 | Frontend | Jan 6 | Jan 31 | Design system ready |
| **F-101**: One-click rollback | Velocity | 4000 | Backend | Jan 6 | Feb 28 | — |
| **F-102**: K8s cost dashboard | Cost Opt | 2100 | Data | Feb 1 | Mar 31 | Prometheus metrics |
| **F-105**: Terraform import | Velocity | 1350 | Infra | Mar 1 | Mar 31 | State parser library |

**Q1 Goal:** Ship 4 high-value features, achieve 90% customer satisfaction

---

## Q2-Q3 2026 Roadmap (NEXT)

```yaml
Q2 (Apr-Jun):
  - Multi-region deployments
  - GitHub Actions integration (native)
  - Custom deployment strategies (canary, blue-green)
  - SOC 2 Type II certification prep

Q3 (Jul-Sep):
  - AI incident root cause (pilot program)
  - Self-service cost optimization recommendations
  - API v2.0 (breaking changes, versioned)
  - Enterprise SSO (SAML, LDAP)

Confidence: 60-70% (subject to change based on Q1 learnings)
```

---

## Q4 2026+ Roadmap (LATER)

**Strategic Themes Only:**

1. **Platform Extensibility**
   - Plugin marketplace for custom integrations
   - SDK for 3rd-party tool developers

2. **Advanced Security**
   - FedRAMP certification
   - Runtime threat detection (eBPF-based)

3. **AI-Powered Operations**
   - Predictive scaling recommendations
   - Automated incident remediation

**No Dates** — Direction only, details TBD

---

## Dependency Mapping

```python
# dependency_graph.py - Visualize feature dependencies
import networkx as nx
import matplotlib.pyplot as plt

class RoadmapDependencies:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_feature(self, feature_id, name, quarter):
        """Add feature to dependency graph."""
        self.graph.add_node(feature_id, name=name, quarter=quarter)

    def add_dependency(self, feature_id, depends_on):
        """Add dependency (feature_id depends on depends_on)."""
        self.graph.add_edge(depends_on, feature_id)

    def find_critical_path(self):
        """Find longest path (critical path) in roadmap."""
        try:
            path = nx.dag_longest_path(self.graph)
            print(f"Critical path: {' → '.join(path)}")
            return path
        except nx.NetworkXError:
            print("Error: Dependency cycle detected!")
            cycles = list(nx.simple_cycles(self.graph))
            print(f"Cycles: {cycles}")
            return None

    def find_blockers(self):
        """Find features that block multiple others."""
        blockers = {}

        for node in self.graph.nodes():
            successors = list(self.graph.successors(node))
            if len(successors) > 1:
                blockers[node] = successors

        print("\nCritical blockers (blocking multiple features):")
        for blocker, blocked in blockers.items():
            name = self.graph.nodes[blocker]['name']
            print(f"  {blocker} ({name}): blocks {len(blocked)} features")

        return blockers


# Example usage
roadmap = RoadmapDependencies()

# Add Q1 features
roadmap.add_feature("F-101", "One-click rollback", "Q1")
roadmap.add_feature("F-102", "K8s cost dashboard", "Q1")
roadmap.add_feature("F-103", "Dark mode UI", "Q1")
roadmap.add_feature("F-105", "Terraform import", "Q1")

# Add Q2 features
roadmap.add_feature("F-201", "Multi-region deployments", "Q2")
roadmap.add_feature("F-202", "GitHub Actions integration", "Q2")

# Add dependencies
roadmap.add_dependency("F-102", "F-101")  # K8s dashboard depends on rollback (shared infra)
roadmap.add_dependency("F-201", "F-101")  # Multi-region depends on rollback
roadmap.add_dependency("F-201", "F-102")  # Multi-region depends on cost dashboard

# Find critical path and blockers
roadmap.find_critical_path()
roadmap.find_blockers()

# Output:
# Critical path: F-101 → F-102 → F-201
#
# Critical blockers (blocking multiple features):
#   F-101 (One-click rollback): blocks 2 features
```

---

## Roadmap Communication

### Internal Stakeholder View

```markdown
### Q1 2026 Engineering Roadmap

**Strategic Focus:** Deployment velocity & cost optimization

#### Committed Features (90% confidence)
- ✅ Dark mode UI (Jan 31) — Frontend team
- ✅ One-click rollback (Feb 28) — Backend team
- ✅ K8s cost dashboard (Mar 31) — Data team
- ✅ Terraform import (Mar 31) — Infra team

#### At Risk
- None currently

#### Recently Shipped
- Advanced RBAC (Dec 2025)
- Deployment notifications (Dec 2025)
```

### Customer-Facing View

```markdown
### DevOpsPlatform Roadmap (Public)

**Q1 2026**
- 🎨 Dark mode support
- ⏮️ One-click deployment rollback
- 💰 Kubernetes cost optimization insights
- 🔧 Terraform state file import

**Q2 2026**
- 🌍 Multi-region deployments
- 🔗 Native GitHub Actions integration
- 🚦 Custom deployment strategies (canary, blue-green)

**Later in 2026**
- 🤖 AI-powered incident analysis
- 🔐 Enterprise SSO
- 📊 Advanced analytics

*Note: Dates are estimates and subject to change.*
```

---

## Roadmap Review Cadence

```python
# roadmap_review.py - Schedule roadmap review meetings
from datetime import datetime, timedelta

class RoadmapReview:
    def __init__(self, year):
        self.year = year

    def schedule_reviews(self):
        """Generate roadmap review schedule."""
        reviews = []

        # Quarterly roadmap planning (6 weeks before quarter)
        quarters = [
            ("Q1", datetime(self.year, 1, 1)),
            ("Q2", datetime(self.year, 4, 1)),
            ("Q3", datetime(self.year, 7, 1)),
            ("Q4", datetime(self.year, 10, 1)),
        ]

        for quarter, start_date in quarters:
            planning_date = start_date - timedelta(weeks=6)
            reviews.append({
                'type': 'Quarterly Planning',
                'quarter': quarter,
                'date': planning_date.strftime('%Y-%m-%d'),
                'attendees': ['PM', 'Engineering', 'Design', 'Leadership'],
                'duration': '4 hours'
            })

        # Monthly roadmap sync (3rd week of each month)
        for month in range(1, 13):
            sync_date = datetime(self.year, month, 15)  # Mid-month
            reviews.append({
                'type': 'Monthly Sync',
                'month': sync_date.strftime('%B'),
                'date': sync_date.strftime('%Y-%m-%d'),
                'attendees': ['PM', 'Engineering Leads'],
                'duration': '1 hour'
            })

        return reviews

    def print_schedule(self):
        """Print roadmap review schedule."""
        reviews = self.schedule_reviews()

        print("2026 Roadmap Review Schedule:\n")
        print(f"{'Type':<20} {'Date':<12} {'Attendees':<40} {'Duration':<10}")
        print("-" * 85)

        for review in sorted(reviews, key=lambda r: r['date']):
            attendees = ', '.join(review['attendees'])
            print(f"{review['type']:<20} {review['date']:<12} {attendees:<40} {review['duration']:<10}")


# Example usage
review = RoadmapReview(2026)
review.print_schedule()
```

---

## Roadmap Metrics (KPIs)

```python
# roadmap_metrics.py - Track roadmap execution metrics
from datetime import datetime

class RoadmapMetrics:
    def __init__(self, features):
        self.features = features

    def calculate_on_time_delivery(self):
        """Calculate % of features shipped on time."""
        shipped = [f for f in self.features if f['status'] == 'shipped']
        on_time = [f for f in shipped if f['actual_ship_date'] <= f['planned_ship_date']]

        rate = (len(on_time) / len(shipped)) * 100 if shipped else 0

        print(f"On-time delivery rate: {rate:.1f}% ({len(on_time)}/{len(shipped)} features)")
        return rate

    def calculate_scope_change(self):
        """Calculate % of features that changed scope."""
        changed = [f for f in self.features if f.get('scope_changed', False)]

        rate = (len(changed) / len(self.features)) * 100

        print(f"Scope change rate: {rate:.1f}% ({len(changed)}/{len(self.features)} features)")
        return rate

    def calculate_customer_satisfaction(self):
        """Calculate average CSAT for shipped features."""
        shipped = [f for f in self.features if f['status'] == 'shipped' and 'csat_score' in f]
        avg_csat = sum(f['csat_score'] for f in shipped) / len(shipped) if shipped else 0

        print(f"Average CSAT: {avg_csat:.1f}/5.0")
        return avg_csat


# Example: Q1 2026 metrics
features = [
    {
        'id': 'F-101',
        'status': 'shipped',
        'planned_ship_date': datetime(2026, 2, 28),
        'actual_ship_date': datetime(2026, 2, 25),
        'scope_changed': False,
        'csat_score': 4.5
    },
    {
        'id': 'F-102',
        'status': 'shipped',
        'planned_ship_date': datetime(2026, 3, 31),
        'actual_ship_date': datetime(2026, 4, 5),  # Late
        'scope_changed': True,
        'csat_score': 4.2
    },
    {
        'id': 'F-103',
        'status': 'shipped',
        'planned_ship_date': datetime(2026, 1, 31),
        'actual_ship_date': datetime(2026, 1, 31),
        'scope_changed': False,
        'csat_score': 4.8
    },
]

metrics = RoadmapMetrics(features)
metrics.calculate_on_time_delivery()
metrics.calculate_scope_change()
metrics.calculate_customer_satisfaction()

# Output:
# On-time delivery rate: 66.7% (2/3 features)
# Scope change rate: 33.3% (1/3 features)
# Average CSAT: 4.5/5.0
```

---

## Common Roadmap Anti-Patterns

| Anti-Pattern | Why Bad | Solution |
|--------------|---------|----------|
| **Feature factory** | Shipping features ≠ customer value | Focus on outcomes (metrics), not outputs |
| **Over-commitment** | Roadmap becomes wishlist | Only commit NOW items, keep NEXT/LATER flexible |
| **No prioritization** | Everything is P0 | Use RICE, WSJF, or value/effort matrix |
| **Ignoring dependencies** | Features block each other | Map dependencies, identify critical path |
| **No customer feedback** | Building wrong things | Validate with customers before committing |
| **Waterfall planning** | Rigid 12-month plan | Use Now-Next-Later, adjust quarterly |

---

## Key Takeaways

1. **Now-Next-Later** — Decrease confidence further out (avoid waterfall trap)
2. **RICE prioritization** — Data-driven feature ranking (Reach × Impact × Confidence / Effort)
3. **Dependency mapping** — Identify critical path and blockers early
4. **Quarterly reviews** — Adjust roadmap based on learnings (not set-and-forget)
5. **Customer validation** — Talk to 10+ customers before committing to "NOW"

**Tools:** ProductBoard, Aha!, Roadmunk, Google Sheets
**Cadence:** Review monthly, re-plan quarterly
**Success metric:** >70% on-time delivery, >4.0/5.0 CSAT, <20% scope change
