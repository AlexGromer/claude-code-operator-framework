# Few-Shot Example: Incident Response Playbook for Ransomware

**Domain:** Blue Team / DFIR
**Skill Level:** Intermediate
**Pattern:** Structured incident response with evidence collection and containment

---

## User Query

```
We just detected suspicious file encryption activity on a file server. Multiple users reporting files with .locked extension. Need help with incident response - what should I do first?
```

---

## Exemplary Response

┌─ ROUTING ──────────────────────────────────────────────────┐
│ Role: Blue Team / DFIR Specialist                          │
│ Confidence: HIGH (95%)                                     │
│ Modules: 18-blue-purple-dfir.md, 02-security.md           │
│ Approach: NIST SP 800-61 Incident Response Framework      │
└────────────────────────────────────────────────────────────┘

⚠️ **CRITICAL: Suspected Ransomware - Act Immediately**

## Phase 1: PREPARATION & CONTAINMENT (First 15 minutes)

### 1.1 Immediate Containment
```bash
# ⚠️ AUTHORIZATION CHECK: Do you have authority to isolate systems? [REQUIRED]
# IF YES → Proceed with containment

# Option A: Network isolation (preferred - preserves volatile evidence)
# Disconnect file server from network (pull cable or disable NICs)
# DO NOT shut down - volatile memory evidence will be lost

# Option B: Firewall isolation (if remote access only)
sudo iptables -A INPUT -j DROP
sudo iptables -A OUTPUT -j DROP

# Document action with timestamp
echo "$(date -Iseconds) - Server isolated by [YOUR_NAME]" >> /var/log/incident.log
```

### 1.2 Activate Incident Response Team
- **Notify**: Security team, IT management, legal (data breach potential)
- **Preserve**: Begin evidence collection BEFORE any remediation
- **Document**: Create incident ticket (HIGH severity)

## Phase 2: IDENTIFICATION (15-30 minutes)

### 2.1 Snapshot Current State
```bash
# Capture volatile evidence FIRST (order of volatility)
# ⚠️ Use write-blocker USB or network share for evidence storage

# 1. Memory dump (CRITICAL - do this FIRST before any other commands)
sudo apt install volatility3 lime-forensics-dkms -y
sudo insmod /usr/src/lime-forensics/lime.ko "path=/mnt/evidence/memory.lime format=lime"

# OR use avml (faster)
sudo avml /mnt/evidence/memory.dmp

# 2. Process list
ps auxww > /mnt/evidence/processes_$(date +%s).txt
pstree -p > /mnt/evidence/process_tree_$(date +%s).txt

# 3. Network connections
netstat -anptul > /mnt/evidence/netstat_$(date +%s).txt
ss -tunap > /mnt/evidence/sockets_$(date +%s).txt

# 4. Open files (may reveal ransomware executable)
lsof > /mnt/evidence/lsof_$(date +%s).txt

# 5. Active users
w > /mnt/evidence/users_$(date +%s).txt

# 6. Command history (all users)
for user in /home/*; do
  cat "$user/.bash_history" >> /mnt/evidence/bash_history_all.txt
done
```

### 2.2 Ransomware Sample Collection
```bash
# Locate ransomware executable (look for recently modified files)
find / -type f -mmin -60 -executable 2>/dev/null > /mnt/evidence/recent_executables.txt

# Check for ransom notes
find /srv/fileserver -name "*.txt" -o -name "*.html" -mmin -60 > /mnt/evidence/ransom_notes.txt

# Copy samples to evidence directory (HANDLE AS MALWARE)
# ⚠️ Use isolated analysis VM, not production system
```

### 2.3 Timeline Analysis
```bash
# Filesystem timeline (encrypted files)
find /srv/fileserver -name "*.locked" -ls > /mnt/evidence/encrypted_files.txt

# First and last encrypted file timestamps
ls -lt /srv/fileserver | tail -1  # Oldest (first encryption)
ls -lt /srv/fileserver | head -1  # Newest (last encryption)

# Calculate infection window
# This tells you when encryption started and how long it took
```

## Phase 3: ANALYSIS (30-60 minutes)

### 3.1 Memory Forensics with Volatility
```bash
# Analyze memory dump
cd /mnt/evidence

# Identify OS profile
volatility3 -f memory.lime banners.Banners

# List processes
volatility3 -f memory.lime linux.pslist.PsList > analysis_processes.txt

# Check for suspicious processes (high CPU, unusual names)
volatility3 -f memory.lime linux.psaux.PsAux | grep -E "(crypt|lock|ransom)"

# Network connections from memory
volatility3 -f memory.lime linux.netstat.Netstat > analysis_network.txt

# Check for persistence mechanisms
volatility3 -f memory.lime linux.bash.Bash > analysis_bash_history.txt
```

### 3.2 Ransomware Identification
```bash
# Calculate file hash
sha256sum /path/to/suspicious/binary

# Check against known ransomware databases:
# - VirusTotal API
# - ID Ransomware (https://id-ransomware.malwarehunterteam.com/)
# - NO MORE RANSOM project

# Analyze ransom note for family identification
cat ransom_note.txt
# Look for: contact email, Bitcoin address, Tor payment portal
```

### 3.3 Scope Assessment
- **Systems affected**: File server only or lateral movement?
- **Data encrypted**: Which directories/file types?
- **Backups status**: Are backups intact? (check if ransomware targeted backup locations)
- **C2 communication**: Did ransomware call home? (check network logs)

## Phase 4: CONTAINMENT & ERADICATION (1-2 hours)

### 4.1 Extended Containment
```bash
# Isolate all potentially affected systems
# Check lateral movement indicators:
# - SMB connections from file server
# - Same malware hash on other hosts
# - Similar encryption patterns

# Disable compromised accounts (if credential theft suspected)
# Change all service account passwords
# Rotate domain administrator passwords
```

### 4.2 Disk Imaging (Before Cleanup)
```bash
# Create forensic image of infected system
# ⚠️ Use write-blocker hardware or dd with appropriate flags

# Calculate disk size first
lsblk -b /dev/sda

# Create bit-by-bit image
sudo dcfldd if=/dev/sda of=/mnt/evidence/disk_image.dd hash=sha256 hashlog=/mnt/evidence/disk_image.hash

# OR use FTK Imager (Windows)
# OR use Guymager (Linux GUI)
```

### 4.3 Remove Ransomware
```bash
# Terminate malicious processes (from analysis)
sudo kill -9 <PID>

# Remove ransomware binary
sudo rm /path/to/ransomware/binary

# Check for persistence (cron, systemd, rc.local)
crontab -l
ls -la /etc/cron.*
systemctl list-units --type=service | grep -i suspicious
cat /etc/rc.local
```

## Phase 5: RECOVERY (2-24 hours)

### 5.1 Restore from Backups
```bash
# ⚠️ VERIFY backup integrity BEFORE restore
# Check if backups were encrypted too

# Test restore on isolated VM first
# If successful → restore to production

# Document:
# - Backup date/time used
# - Data loss window (last backup to infection time)
```

### 5.2 Decryption Attempts
```bash
# Check for free decryptors:
# - https://www.nomoreransom.org/en/decryption-tools.html
# - Emsisoft, Avast, Kaspersky free tools

# ⚠️ DO NOT PAY RANSOM without legal/executive approval
# ⚠️ Paying does not guarantee decryption and funds criminal activity
```

## Phase 6: POST-INCIDENT (24-72 hours)

### 6.1 Incident Report
```markdown
# Incident Report Template

**Incident ID**: INC-2026-001
**Classification**: Ransomware Attack
**Severity**: HIGH
**Status**: Contained

## Timeline
- **Detection**: 2026-02-06 14:32 UTC
- **Containment**: 2026-02-06 14:45 UTC (13 min)
- **Eradication**: 2026-02-06 16:20 UTC
- **Recovery**: 2026-02-06 18:45 UTC

## Impact
- **Systems affected**: 1 file server (SRV-FILE-01)
- **Data encrypted**: ~450 GB (documents, spreadsheets)
- **Data loss**: 6 hours (last backup: 08:00 UTC)
- **Downtime**: 4 hours 13 minutes

## Root Cause
- Initial access: Phishing email with malicious attachment
- User: john.doe@company.com opened attachment
- Privilege escalation: Exploited CVE-2024-XXXXX (unpatched)

## Remediation
- ✅ Server rebuilt from clean image
- ✅ Data restored from backup (6hr data loss)
- ✅ All passwords rotated
- ✅ Vulnerability patched (CVE-2024-XXXXX)
- ✅ EDR deployed on all endpoints

## Recommendations
1. User security awareness training (mandatory)
2. Email attachment filtering (block .exe, .scr, .js)
3. Implement application whitelisting
4. Test backup restore procedures quarterly
5. Deploy EDR with behavioral detection
```

### 6.2 Lessons Learned
- What worked well?
- What could be improved?
- Process gaps identified?
- Update incident response playbook

---

## Key Takeaways

1. **Speed matters**: Isolate FIRST, investigate SECOND
2. **Preserve evidence**: Memory dump before ANY other action
3. **Document everything**: Timestamps, actions, decisions
4. **Never trust, always verify**: Check backups before restore
5. **Legal considerations**: Ransomware = data breach → disclosure requirements

## References

- NIST SP 800-61 Rev 2: Computer Security Incident Handling Guide
- SANS Incident Response Process
- CISA Ransomware Guide: https://www.cisa.gov/stopransomware
- NO MORE RANSOM: https://www.nomoreransom.org/

---

**Authorization Level**: INFRASTRUCTURE + CREDENTIAL (system isolation, password rotation)
**Evidence Preservation**: CRITICAL - follow chain of custody
**Legal/Compliance**: Consider breach notification requirements (GDPR 72hr, etc.)
