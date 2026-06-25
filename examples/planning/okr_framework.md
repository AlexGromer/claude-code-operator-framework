# Example: OKR (Objectives & Key Results) Framework

## User Request

```
Составь OKRs для команды DevOps на Q1 2026 с полной методологией и автоматизацией трекинга.
```

## Reasoning

**Domain:** Planning (OKR methodology)
**Complexity:** Medium
**Model:** Sonnet

## Response

### OKR Methodology Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│  OKR STRUCTURE                                                           │
├─────────────────────────────────────────────────────────────────────────┤
│  OBJECTIVE (What)                                                        │
│  ├─► Qualitative, inspirational, time-bound                             │
│  ├─► 3-5 objectives per team per quarter                                │
│  └─► Aligned with company/department goals                              │
│                                                                          │
│  KEY RESULTS (How)                                                       │
│  ├─► Quantitative, measurable, verifiable                               │
│  ├─► 3 key results per objective                                        │
│  ├─► Ambitious: 70-80% completion = success                             │
│  └─► Outcome-focused (not activity-focused)                             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Q1 2026 OKRs: DevOps Team

#### Company Context (Alignment)
```yaml
Company OKR:
  Objective: "Scale infrastructure for 10x user growth"
  Key Results:
    - Support 10M MAU (from 1M)
    - Maintain <100ms API latency at scale
    - Achieve 99.99% uptime

Department (Engineering):
  Objective: "Enable continuous deployment at scale"
  Key Results:
    - Deploy 50+ times/week (from 10/week)
    - Zero production incidents from deployments
    - Reduce infrastructure costs by 25%
```

#### Team OKR 1: Improve Deployment Velocity 🚀

**Objective:** *Enable teams to ship features 5x faster with confidence*

**Key Results:**
1. **Reduce deployment time from 45 min → 10 min (78% reduction)**
   ```bash
   # Measurement: CI/CD pipeline metrics
   Current baseline: 45 min (manual approval gates, sequential stages)
   Target: 10 min (parallel builds, auto-approval for non-prod)

   # Tracking script
   gh api repos/{owner}/{repo}/actions/runs \
     --jq '.workflow_runs[] | {duration: .run_duration_ms, conclusion}' \
     | jq -s 'map(select(.conclusion=="success")) | map(.duration/60000) | add/length'
   ```

2. **Increase deployment frequency from 2/week → 15/week**
   ```python
   # deployment_frequency.py - Track via Git tags
   import subprocess
   from datetime import datetime, timedelta

   def get_deployment_frequency(days=7):
       """Calculate deployments per week from Git tags."""
       result = subprocess.run(
           ['git', 'tag', '--sort=-creatordate',
            f'--since="{days} days ago"'],
           capture_output=True, text=True
       )

       tags = result.stdout.strip().split('\n')
       deployments = [t for t in tags if t.startswith('v')]

       frequency = len(deployments) / (days / 7)
       print(f"Deployment frequency: {frequency:.1f}/week")
       return frequency

   if __name__ == "__main__":
       freq = get_deployment_frequency()
       target = 15
       progress = min(freq / target, 1.0)
       print(f"Progress: {progress*100:.0f}% (target: {target}/week)")
   ```

3. **Achieve 99.5% deployment success rate**
   ```sql
   -- Query CI/CD database for success rate
   SELECT
       COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*) AS success_rate,
       COUNT(*) AS total_deployments
   FROM deployments
   WHERE created_at >= DATE_TRUNC('quarter', CURRENT_DATE)
     AND environment = 'production';
   ```

#### Team OKR 2: Enhance System Reliability 🛡️

**Objective:** *Build unbreakable infrastructure that engineers trust*

**Key Results:**
1. **Reduce MTTR from 120 min → 20 min (83% reduction)**
   ```python
   # mttr_calculator.py - Calculate from PagerDuty API
   import requests
   from datetime import datetime, timedelta

   def calculate_mttr(api_key, days=90):
       """Calculate Mean Time To Resolution from incidents."""
       url = "https://api.pagerduty.com/incidents"
       headers = {
           "Authorization": f"Token token={api_key}",
           "Accept": "application/vnd.pagerduty+json;version=2"
       }

       since = (datetime.now() - timedelta(days=days)).isoformat()
       params = {
           "since": since,
           "statuses[]": ["resolved"],
           "urgency": "high"
       }

       response = requests.get(url, headers=headers, params=params)
       incidents = response.json()["incidents"]

       resolutions = []
       for inc in incidents:
           created = datetime.fromisoformat(inc["created_at"].replace('Z', '+00:00'))
           resolved = datetime.fromisoformat(inc["resolved_at"].replace('Z', '+00:00'))
           resolution_time = (resolved - created).total_seconds() / 60
           resolutions.append(resolution_time)

       mttr = sum(resolutions) / len(resolutions) if resolutions else 0
       print(f"MTTR: {mttr:.1f} minutes (target: 20 min)")
       return mttr
   ```

2. **Achieve 99.95% uptime (4.38 hours downtime/year)**
   ```yaml
   # uptime_monitor.yml - Prometheus alert rule
   groups:
     - name: uptime_sla
       interval: 1m
       rules:
         - alert: UpTimeSLABreach
           expr: |
             (
               sum(up{job="api"}) / count(up{job="api"})
             ) < 0.9995
           for: 5m
           labels:
             severity: critical
           annotations:
             summary: "Uptime below 99.95% SLA"
             description: "Current uptime: {{ $value | humanizePercentage }}"
   ```

3. **Zero high-severity incidents from infrastructure**
   ```bash
   # incident_tracker.sh - Weekly report
   #!/bin/bash

   QUARTER_START="2026-01-01"

   # Count high-severity incidents
   INCIDENTS=$(gh api graphql -f query='
   {
     repository(owner:"company", name:"ops") {
       issues(first:100,
              filterBy:{labels:["severity:high","type:incident"],
                       since:"'$QUARTER_START'"}) {
         totalCount
         nodes { title, createdAt, closedAt }
       }
     }
   }' --jq '.data.repository.issues.totalCount')

   echo "High-severity incidents this quarter: $INCIDENTS"
   echo "Target: 0"

   if [ "$INCIDENTS" -eq 0 ]; then
       echo "✅ OKR ACHIEVED"
   else
       echo "⚠️  Progress: $(python3 -c "print(max(0, 1 - $INCIDENTS/3))")"
   fi
   ```

#### Team OKR 3: Optimize Infrastructure Costs 💰

**Objective:** *Run infrastructure at 50% cost with zero performance impact*

**Key Results:**
1. **Reduce AWS spend from $50K → $35K/month (30% reduction)**
   ```python
   # aws_cost_tracker.py - Daily cost monitoring
   import boto3
   from datetime import datetime, timedelta

   def get_monthly_cost():
       """Get current month AWS cost."""
       ce = boto3.client('ce', region_name='us-east-1')

       start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
       end = datetime.now().strftime('%Y-%m-%d')

       response = ce.get_cost_and_usage(
           TimePeriod={'Start': start, 'End': end},
           Granularity='MONTHLY',
           Metrics=['UnblendedCost']
       )

       cost = float(response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
       target = 35000
       baseline = 50000

       reduction = (baseline - cost) / baseline * 100
       print(f"Current: ${cost:,.0f}/month")
       print(f"Target: ${target:,.0f}/month")
       print(f"Reduction: {reduction:.1f}%")
       print(f"Progress: {min(cost/target, 1.0)*100:.0f}%")

       return cost

   if __name__ == "__main__":
       get_monthly_cost()
   ```

2. **Achieve 70% average resource utilization**
   ```python
   # utilization_monitor.py - CloudWatch metrics
   import boto3
   from datetime import datetime, timedelta

   def calculate_utilization(metric_name='CPUUtilization', days=7):
       """Calculate average resource utilization."""
       cloudwatch = boto3.client('cloudwatch')

       response = cloudwatch.get_metric_statistics(
           Namespace='AWS/EC2',
           MetricName=metric_name,
           Dimensions=[],
           StartTime=datetime.now() - timedelta(days=days),
           EndTime=datetime.now(),
           Period=3600,
           Statistics=['Average']
       )

       datapoints = response['Datapoints']
       avg_utilization = sum(dp['Average'] for dp in datapoints) / len(datapoints)

       print(f"{metric_name}: {avg_utilization:.1f}%")
       print(f"Target: 70%")
       print(f"Progress: {min(avg_utilization/70, 1.0)*100:.0f}%")

       return avg_utilization
   ```

3. **Eliminate 100% of unused resources ($5K/month waste)**
   ```bash
   # cleanup_orphaned_resources.sh - Automated cleanup
   #!/bin/bash

   echo "Scanning for orphaned resources..."

   # Unattached EBS volumes
   aws ec2 describe-volumes \
     --filters Name=status,Values=available \
     --query 'Volumes[*].[VolumeId,Size,CreateTime]' \
     --output table

   # Unused EIPs
   aws ec2 describe-addresses \
     --query 'Addresses[?InstanceId==`null`].[PublicIp,AllocationId]' \
     --output table

   # Stopped instances (>30 days)
   aws ec2 describe-instances \
     --filters Name=instance-state-name,Values=stopped \
     --query 'Reservations[*].Instances[?LaunchTime<=`'$(date -d '30 days ago' -I)'`].[InstanceId,LaunchTime]' \
     --output table

   # Calculate waste
   MONTHLY_WASTE=$(aws ce get-cost-and-usage \
     --time-period Start=$(date -d 'last month' +%Y-%m-01),End=$(date +%Y-%m-01) \
     --granularity MONTHLY \
     --filter file://unused-filter.json \
     --metrics UnblendedCost \
     --query 'ResultsByTime[0].Total.UnblendedCost.Amount' \
     --output text)

   echo "Monthly waste: $$MONTHLY_WASTE"
   echo "Target: $0"
   ```

---

## OKR Tracking Automation

### Weekly Progress Dashboard

```python
# okr_dashboard.py - Automated weekly report
import json
from datetime import datetime

class OKRTracker:
    def __init__(self, config_file='okrs.json'):
        with open(config_file, 'r') as f:
            self.okrs = json.load(f)

    def calculate_progress(self, kr):
        """Calculate progress for a key result."""
        current = kr['current_value']
        target = kr['target_value']
        baseline = kr['baseline_value']

        # Invert for "reduce" metrics
        if kr['direction'] == 'decrease':
            progress = (baseline - current) / (baseline - target)
        else:
            progress = (current - baseline) / (target - baseline)

        return max(0, min(progress, 1.0))

    def generate_report(self):
        """Generate weekly OKR progress report."""
        report = f"# OKR Progress Report - {datetime.now().strftime('%Y-%m-%d')}\n\n"

        for obj in self.okrs['objectives']:
            report += f"## {obj['name']}\n"
            report += f"**Objective:** {obj['description']}\n\n"

            obj_progress = []

            for kr in obj['key_results']:
                progress = self.calculate_progress(kr)
                obj_progress.append(progress)

                status = "🟢" if progress >= 0.7 else "🟡" if progress >= 0.4 else "🔴"
                report += f"- {status} **{kr['name']}**: {progress*100:.0f}%\n"
                report += f"  - Current: {kr['current_value']} | Target: {kr['target_value']}\n"

            avg_progress = sum(obj_progress) / len(obj_progress)
            report += f"\n**Overall Progress:** {avg_progress*100:.0f}%\n\n"

        return report

if __name__ == "__main__":
    tracker = OKRTracker()
    print(tracker.generate_report())
```

---

## Common Pitfalls & Anti-Patterns

| Anti-Pattern | Why Bad | Solution |
|--------------|---------|----------|
| **Output-based KRs** ("Deploy 50 features") | Activity ≠ outcome | Use outcome metrics ("Reduce churn by 20%") |
| **Too many objectives** (>5 per team) | Dilutes focus | 3-5 objectives max per quarter |
| **100% achievable KRs** | Not ambitious enough | Target 70-80% success rate |
| **Individual OKRs only** | Misalignment | Cascade: Company → Team → Individual |
| **Set and forget** | No course correction | Weekly check-ins mandatory |
| **Confidential OKRs** | Reduces transparency | Public by default (unless sensitive) |

---

## OKR Scoring Methodology

```
SCORING SCALE:
├─► 0.0 - 0.3: Failed (red)
├─► 0.3 - 0.7: Progressing (yellow)
├─► 0.7 - 1.0: Success (green)
└─► > 1.0: Exceeded (celebrate, but maybe too easy?)

TARGET: 0.7-0.8 average across all OKRs
```

**End of Q1 2026 Example:**
```
Objective 1: Deployment Velocity → 0.88
├─ KR1: 10 min achieved (1.0) ✅
├─ KR2: 14/week achieved (0.93) ✅
└─ KR3: 99.2% success (0.72) 🟡

Objective 2: Reliability → 0.75
├─ KR1: 18 min MTTR (1.0) ✅
├─ KR2: 99.94% uptime (0.96) ✅
└─ KR3: 1 incident (0.3) 🔴

Objective 3: Cost Optimization → 1.0
├─ KR1: $33K/month (1.0) ✅
├─ KR2: 73% utilization (1.0) ✅
└─ KR3: $0 waste (1.0) ✅

OVERALL: 0.88 (Excellent quarter)
```

---

## Key Takeaways

1. **Alignment cascade** — Company → Department → Team → Individual
2. **70-80% target** — Ambitious but achievable (not sandbagging)
3. **Weekly check-ins** — Track progress, adapt as needed
4. **Public transparency** — Share OKRs across org for alignment
5. **Outcome-focused** — Measure results, not activities

**Tools:** Jira, Linear, Lattice, 15Five, custom dashboards
**Cadence:** Set quarterly, review weekly, score at end
**Success metric:** 0.7-0.8 average score (consistently ambitious)
