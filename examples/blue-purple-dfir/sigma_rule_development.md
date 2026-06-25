# Few-Shot Example: Sigma Rule Development for Lateral Movement

**Domain:** Blue Team / Detection Engineering
**Skill Level:** Intermediate
**Pattern:** Creating Sigma rules for SIEM detection with testing methodology

---

## User Query

```
We need to detect lateral movement using PsExec in our environment. Can you help create a Sigma rule for this? We use Windows Event Logs and have Splunk as SIEM.
```

---

## Exemplary Response

┌─ ROUTING ──────────────────────────────────────────────────┐
│ Role: Detection Engineer / Blue Team                       │
│ Confidence: HIGH (90%)                                     │
│ Modules: 18-blue-purple-dfir.md                           │
│ Approach: Sigma rule creation with multi-data source logic│
└────────────────────────────────────────────────────────────┘

## Sigma Rule: Lateral Movement via PsExec

I'll create a comprehensive Sigma rule that detects PsExec lateral movement with low false positive rate.

### Rule File: `lateral_movement_psexec.yml`

```yaml
title: Lateral Movement via PsExec
id: 42d36aa1-e2f3-4e4e-8e2f-9c6b7e3d8f12
status: stable
description: Detects lateral movement using PsExec tool based on multiple indicators including service installation, file creation, and network connections
author: Your Organization SOC Team
date: 2026-02-06
modified: 2026-02-06
tags:
    - attack.lateral_movement
    - attack.t1021.002        # Remote Services: SMB/Windows Admin Shares
    - attack.t1569.002        # System Services: Service Execution
    - detection.emerging_threats
logsource:
    product: windows
    category: process_creation
detection:
    selection_service_install:
        EventID: 7045                    # New Service Installation
        ServiceName|contains: 'PSEXESVC'
        ImagePath|contains:
            - '\PSEXESVC.exe'
            - 'C:\Windows\PSEXESVC.exe'

    selection_process_creation:
        EventID: 4688                    # Process Creation
        NewProcessName|endswith:
            - '\PSEXESVC.exe'
            - '\psexec.exe'
        ParentProcessName: 'services.exe'

    selection_file_creation:
        EventID: 11                      # Sysmon File Creation
        TargetFilename|contains: 'PSEXESVC'
        TargetFilename|endswith: '.exe'

    selection_network_connection:
        EventID: 5145                    # Network Share Access
        ShareName: '\\\*\ADMIN$'
        RelativeTargetName|contains: 'PSEXESVC'

    condition: 1 of selection_*

fields:
    - ComputerName
    - User
    - SourceIP
    - DestinationIP
    - ServiceName
    - ImagePath
    - CommandLine
    - ParentProcessName

falsepositives:
    - Legitimate administrative activity using PsExec (exclude known admin hosts)
    - IT support remote management (whitelist approved admin accounts)
    - Automated deployment tools using PsExec (whitelist known service accounts)

level: high

# Enrichment recommendations
enrichment:
    - Check if source IP is a known admin workstation
    - Verify if user account is authorized for remote administration
    - Correlate with VPN/bastion host access logs
    - Check historical behavior (is this first time user used PsExec?)
```

---

## Rule Explanation

### Detection Logic Breakdown

**1. Service Installation (EventID 7045)**
```yaml
ServiceName|contains: 'PSEXESVC'
```
- PsExec creates a service named PSEXESVC on the remote host
- Service runs as SYSTEM, executes payload
- This is the PRIMARY indicator

**2. Process Creation (EventID 4688 / Sysmon 1)**
```yaml
NewProcessName|endswith: '\PSEXESVC.exe'
ParentProcessName: 'services.exe'
```
- PSEXESVC.exe spawned by services.exe
- Validates service execution context

**3. File Creation (Sysmon EventID 11)**
```yaml
TargetFilename|contains: 'PSEXESVC'
```
- PsExec copies PSEXESVC.exe to `C:\Windows\` on remote host
- File creation precedes service installation

**4. Network Share Access (EventID 5145)**
```yaml
ShareName: '\\\*\ADMIN$'
RelativeTargetName|contains: 'PSEXESVC'
```
- SMB connection to ADMIN$ share
- File transfer to remote system

### Detection Strategy: "1 of selection_*"

```yaml
condition: 1 of selection_*
```

**Why OR logic instead of AND?**

- **Flexibility**: Works even if only partial telemetry available
- **Coverage**: Catches PsExec variants (different log sources)
- **Resilience**: Attackers may disable some logging, not all

**Trade-off**: Higher false positive rate → mitigated by:
- High `level: high` (requires analyst review)
- Detailed `falsepositives` section
- Enrichment recommendations

---

## Advanced Rule: Low False Positives (Option 2)

If your environment has many legitimate PsExec uses, use this stricter version:

```yaml
title: Lateral Movement via PsExec (Low FP)
id: 42d36aa1-e2f3-4e4e-8e2f-9c6b7e3d8f13
status: experimental
description: High-confidence PsExec lateral movement detection requiring multiple indicators
detection:
    selection_service:
        EventID: 7045
        ServiceName|contains: 'PSEXESVC'

    selection_process:
        EventID: 4688
        NewProcessName|endswith: '\PSEXESVC.exe'

    selection_network:
        EventID: 5145
        ShareName: '\\\*\ADMIN$'

    filter_known_admins:
        User|contains:
            - 'DOMAIN\admin_'        # Whitelist admin accounts
            - 'DOMAIN\svc_deploy'    # Whitelist service accounts

    filter_known_sources:
        SourceWorkstation|contains:
            - 'ADMIN-WS-'           # Whitelist admin workstations
            - 'DEPLOY-SRV-'         # Whitelist deployment servers

    condition: (selection_service and selection_process and selection_network) and not 1 of filter_*

level: critical
```

**Key differences:**
- Requires ALL three indicators (AND logic)
- Whitelists known legitimate sources
- `level: critical` (fewer alerts, higher confidence)

---

## Testing the Rule

### Step 1: Convert Sigma to SIEM Query

#### For Splunk:
```bash
# Install sigmac or pySigma
pip install pysigma-backend-splunk

# Convert to Splunk SPL
sigma convert -t splunk -p splunk_windows lateral_movement_psexec.yml

# Output (example):
# (EventID=7045 ServiceName="*PSEXESVC*") OR (EventID=4688 NewProcessName="*\\PSEXESVC.exe" ParentProcessName="services.exe") OR (EventID=11 TargetFilename="*PSEXESVC*.exe") OR (EventID=5145 ShareName="\\\\*\\ADMIN$" RelativeTargetName="*PSEXESVC*")
```

#### For Elasticsearch/ELK:
```bash
sigma convert -t elasticsearch -p ecs_windows lateral_movement_psexec.yml
```

#### For Microsoft Sentinel:
```bash
sigma convert -t kusto lateral_movement_psexec.yml
```

### Step 2: Deploy to SIEM

**Splunk Example:**
```spl
| savedsearch name="Lateral Movement - PsExec"
  search='(EventID=7045 ServiceName="*PSEXESVC*") OR (EventID=4688 NewProcessName="*\\PSEXESVC.exe")'
  cron_schedule="*/5 * * * *"
  alert.severity="high"
  action.email=1
  action.email.to="soc@company.com"
```

### Step 3: Test with Benign Data

```bash
# Test query on historical data (last 30 days)
index=windows (EventID=7045 ServiceName="*PSEXESVC*")
| stats count by ComputerName, User, ServiceName
| sort -count

# Analyze results:
# - Are there legitimate admin uses?
# - Which users/hosts generate most alerts?
# - Tune whitelist accordingly
```

### Step 4: Validate with Attack Simulation

```powershell
# ⚠️ ONLY IN LAB ENVIRONMENT with authorization

# Test 1: Basic PsExec lateral movement (requires admin credentials)
.\PsExec.exe \\TARGET-HOST -u DOMAIN\testuser -p TestPass123 cmd.exe

# Test 2: PsExec with command execution
.\PsExec.exe \\TARGET-HOST -u DOMAIN\testuser -p TestPass123 whoami

# Test 3: PsExec with service name variation (some versions use different names)
.\PsExec.exe \\TARGET-HOST -r CustomServiceName cmd.exe

# Expected Result:
# → Sigma rule should trigger alert in SIEM within 5 minutes
# → Check alert contains: source host, destination host, user, timestamp
```

### Step 5: False Positive Analysis

```bash
# Splunk query to analyze false positives
index=windows EventID=7045 ServiceName="*PSEXESVC*"
| stats count by User, SourceWorkstation, DestinationHost
| where count > 5    # Users with frequent PsExec use

# Candidates for whitelist:
# - IT support accounts (e.g., Domain\helpdeskadmin)
# - Deployment service accounts (e.g., Domain\svc_deploy)
# - Known admin workstations (e.g., ADMIN-WS-001)
```

---

## Tuning Recommendations

### 1. Whitelist Legitimate Admins

```yaml
filter_known_admins:
    User|contains:
        - 'DOMAIN\admin_'           # Prefix for admin accounts
        - 'DOMAIN\svc_deploy'       # Deployment service account
        - 'DOMAIN\svc_ansible'      # Automation account

filter_known_sources:
    SourceWorkstation|contains:
        - 'ADMIN-WS-'               # Admin workstations
        - 'PAW-'                    # Privileged Access Workstations
        - 'DEPLOY-SRV-01'           # Known deployment server

condition: selection_* and not 1 of filter_*
```

### 2. Time-Based Exceptions

```yaml
# Exclude during maintenance windows
filter_maintenance:
    TimeGenerated|gte: '2026-02-06T22:00:00Z'
    TimeGenerated|lte: '2026-02-06T23:00:00Z'
```

### 3. Geographic Filtering (if applicable)

```yaml
# Alert only if source IP is outside expected range
filter_expected_ips:
    SourceIP|cidr:
        - '10.10.0.0/16'    # Corporate network
        - '192.168.1.0/24'  # Management network

condition: selection_* and not filter_expected_ips
```

---

## Monitoring & Maintenance

### Weekly Review
```bash
# Analyze alert volume
index=notable signature="Lateral Movement - PsExec"
| timechart span=1d count
| eventstats avg(count) as avg_count
| where count > (avg_count * 2)    # Spike detection
```

### Monthly Tuning
- Review false positive rate (target: <5%)
- Update whitelist based on organizational changes
- Validate rule still triggers on test dataset
- Check for new PsExec variants (e.g., PsExec64.exe, custom compiled versions)

---

## Alternative Detection Methods

### 1. Network-Based (IDS/IPS)
```yaml
# Suricata rule for SMB PSEXESVC transfer
alert smb any any -> any 445 (msg:"Lateral Movement - PsExec SMB Transfer"; content:"PSEXESVC"; nocase; sid:1000001; rev:1;)
```

### 2. EDR-Based
- Carbon Black: `process_name:psexesvc.exe`
- CrowdStrike: `ImageFileName contains "PSEXESVC"`
- Microsoft Defender: `DeviceProcessEvents | where FileName =~ "PSEXESVC.exe"`

### 3. PowerShell Detection
```yaml
# Detect PowerShell remoting as alternative to PsExec
EventID: 4104    # PowerShell Script Block Logging
ScriptBlockText|contains: 'Enter-PSSession'
```

---

## References

- **Sigma Rule Repository**: https://github.com/SigmaHQ/sigma
- **MITRE ATT&CK T1021.002**: https://attack.mitre.org/techniques/T1021/002/
- **pySigma Documentation**: https://github.com/SigmaHQ/pySigma
- **PsExec Internals**: https://learn.microsoft.com/en-us/sysinternals/downloads/psexec

---

## Key Takeaways

1. **Multi-Indicator Detection**: Combine multiple log sources for better coverage
2. **Balance Precision vs Recall**: OR logic = more coverage, AND logic = fewer false positives
3. **Test Before Deploy**: Validate on historical data, simulate attacks in lab
4. **Continuous Tuning**: False positive rate should decrease over time with proper whitelisting
5. **Document Exceptions**: Every whitelist entry needs business justification

**Authorization Level**: ANALYZE (rule creation) + NETWORK_ACTIVE (if testing with real attacks)
**Compliance Note**: Ensure attack simulation has written authorization from management
