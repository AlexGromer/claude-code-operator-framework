# OSINT Report: {TARGET}

**Generated:** {TIMESTAMP}
**Investigator:** Claude Sonnet 4.5 + {USER}
**Sources:** {SOURCES}
**Authorization:** {AUTHORIZATION_STATUS}

---

## Executive Summary

{EXECUTIVE_SUMMARY}

**Key Findings:**
- {KEY_FINDING_1}
- {KEY_FINDING_2}
- {KEY_FINDING_3}

**Risk Level:** {RISK_LEVEL} (CRITICAL / HIGH / MEDIUM / LOW / INFO)

---

## 1. Infrastructure Overview

### 1.1 InternetDB Scan (Free Tier)

**IPs Scanned:** {INTERNETDB_SCAN_COUNT}

| IP | Ports | Vulnerabilities | Tags | Hostnames |
|----|-------|----------------|------|-----------|
{INTERNETDB_TABLE_ROWS}

**Summary:**
- Open Ports: {INTERNETDB_TOTAL_PORTS}
- Vulnerabilities Found: {INTERNETDB_TOTAL_VULNS}
- Tagged Systems: {INTERNETDB_TAGGED_COUNT}

**Notable InternetDB Findings:**
- {INTERNETDB_FINDING_1}
- {INTERNETDB_FINDING_2}

### 1.2 Shodan Deep Scan (Paid Queries)

**Hosts Analyzed:** {SHODAN_RESULTS_COUNT}
**Credits Used:** {SHODAN_CREDITS_USED} / 100

| IP | Port | Service | Version | Country | Organization | Vulnerabilities |
|----|------|---------|---------|---------|--------------|-----------------|
{SHODAN_TABLE_ROWS}

**Notable Shodan Findings:**
- {SHODAN_FINDING_1}
- {SHODAN_FINDING_2}

### 1.3 DNS Records

```
A Records:     {DNS_A_RECORDS}
AAAA Records:  {DNS_AAAA_RECORDS}
MX Records:    {DNS_MX_RECORDS}
TXT Records:   {DNS_TXT_RECORDS}
NS Records:    {DNS_NS_RECORDS}
CNAME Records: {DNS_CNAME_RECORDS}
```

**Analysis:**
- {DNS_ANALYSIS}

### 1.4 WHOIS Information

```
Registrar:     {WHOIS_REGISTRAR}
Created:       {WHOIS_CREATED}
Updated:       {WHOIS_UPDATED}
Expires:       {WHOIS_EXPIRES}
Registrant:    {WHOIS_REGISTRANT}
Admin Contact: {WHOIS_ADMIN}
Tech Contact:  {WHOIS_TECH}
Name Servers:  {WHOIS_NAMESERVERS}
```

**Privacy Protection:** {WHOIS_PRIVACY} (Yes/No)

---

## 2. Subdomain Enumeration

**Total Subdomains Found:** {SUBDOMAIN_COUNT}

**Active Subdomains:**
- {SUBDOMAIN_1} — {SUBDOMAIN_1_IP} ({SUBDOMAIN_1_STATUS})
- {SUBDOMAIN_2} — {SUBDOMAIN_2_IP} ({SUBDOMAIN_2_STATUS})
- {SUBDOMAIN_3} — {SUBDOMAIN_3_IP} ({SUBDOMAIN_3_STATUS})

**High-Risk Subdomains:**
- ⚠️ {HIGH_RISK_SUBDOMAIN_1} — {RISK_REASON_1}
- ⚠️ {HIGH_RISK_SUBDOMAIN_2} — {RISK_REASON_2}

**Sources:**
- Certificate Transparency (crt.sh): {CRT_SH_COUNT} subdomains
- subfinder: {SUBFINDER_COUNT} subdomains
- amass: {AMASS_COUNT} subdomains

---

## 3. Technology Stack

**Web Server:**
- {WEB_SERVER} ({WEB_SERVER_VERSION})

**Frameworks:**
- {FRAMEWORK_1}
- {FRAMEWORK_2}

**CMS/Platform:**
- {CMS} ({CMS_VERSION})

**CDN/Hosting:**
- {CDN_PROVIDER}
- {HOSTING_PROVIDER}

**Security:**
- WAF: {WAF} (Detected/Not Detected)
- SSL/TLS: {SSL_VERSION} ({SSL_ISSUER})
- Certificate: Valid until {SSL_EXPIRY}

**Analytics/Tracking:**
- {ANALYTICS_1}
- {ANALYTICS_2}

---

## 4. Exposed Information

### 4.1 Email Addresses ({EMAIL_COUNT} found)

| Email | Source | Confidence |
|-------|--------|------------|
{EMAIL_TABLE_ROWS}

### 4.2 Social Media Accounts

- **LinkedIn:** {LINKEDIN_PROFILES}
- **Twitter:** {TWITTER_ACCOUNTS}
- **GitHub:** {GITHUB_ACCOUNTS}
- **Other:** {OTHER_SOCIAL}

### 4.3 Leaked Credentials

**Breach Databases:**
- {BREACH_DB_1}: {BREACH_COUNT_1} records
- {BREACH_DB_2}: {BREACH_COUNT_2} records

**Status:** {BREACH_STATUS}

### 4.4 Code Exposure (GitHub/GitLab)

**Repositories Found:** {REPO_COUNT}

- {REPO_1} — {REPO_1_DESCRIPTION}
- {REPO_2} — {REPO_2_DESCRIPTION}

**Potential Leaks:**
- ⚠️ {LEAK_1} (API keys, credentials, configs)
- ⚠️ {LEAK_2}

---

## 5. Attack Surface Analysis

### 5.1 Open Ports & Services

| Port | Protocol | Service | Version | Status |
|------|----------|---------|---------|--------|
{PORT_TABLE_ROWS}

### 5.2 Outdated/Vulnerable Software

| Software | Current Version | Latest Version | Known CVEs |
|----------|----------------|----------------|------------|
{VULN_SOFTWARE_TABLE_ROWS}

**Critical Vulnerabilities:**
- 🔴 {CVE_1} — {CVE_1_DESCRIPTION} (CVSS: {CVE_1_SCORE})
- 🔴 {CVE_2} — {CVE_2_DESCRIPTION} (CVSS: {CVE_2_SCORE})

### 5.3 Security Misconfigurations

- {MISCONFIG_1}
- {MISCONFIG_2}
- {MISCONFIG_3}

---

## 6. Threat Intelligence

### 6.1 Malicious Activity

**Reputation Check:**
- Shodan: {SHODAN_REPUTATION}
- VirusTotal: {VT_REPUTATION}
- AbuseIPDB: {ABUSEIPDB_SCORE}

**Blocklist Status:**
- {BLOCKLIST_1}: {BLOCKLIST_1_STATUS}
- {BLOCKLIST_2}: {BLOCKLIST_2_STATUS}

### 6.2 Historical Data

**Wayback Machine:**
- First Snapshot: {WAYBACK_FIRST}
- Latest Snapshot: {WAYBACK_LAST}
- Total Snapshots: {WAYBACK_COUNT}

**Notable Changes:**
- {WAYBACK_CHANGE_1}
- {WAYBACK_CHANGE_2}

---

## 7. Recommendations

### Priority 1 (CRITICAL — Immediate Action Required)

1. **{REC_P1_1_TITLE}**
   - Impact: {REC_P1_1_IMPACT}
   - Action: {REC_P1_1_ACTION}
   - Timeline: Within 24 hours

2. **{REC_P1_2_TITLE}**
   - Impact: {REC_P1_2_IMPACT}
   - Action: {REC_P1_2_ACTION}
   - Timeline: Within 24 hours

### Priority 2 (HIGH — Action within 1 week)

1. **{REC_P2_1_TITLE}**
   - Action: {REC_P2_1_ACTION}

2. **{REC_P2_2_TITLE}**
   - Action: {REC_P2_2_ACTION}

### Priority 3 (MEDIUM — Action within 1 month)

1. **{REC_P3_1_TITLE}**
   - Action: {REC_P3_1_ACTION}

---

## 8. Investigation Timeline

| Timestamp | Activity | Tool | Result |
|-----------|----------|------|--------|
{TIMELINE_TABLE_ROWS}

---

## 9. Appendix: Raw Data

**Cached Results:**
- InternetDB: `/opt/work/osint/cache/{TARGET}/internetdb_*.json` (free tier)
- Shodan: `/opt/work/osint/cache/{TARGET}/shodan_*.json` (paid queries)
- WHOIS: `/opt/work/osint/cache/{TARGET}/whois_*.txt`
- DNS: `/opt/work/osint/cache/{TARGET}/dns_*.json`
- Subdomains: `/opt/work/osint/cache/{TARGET}/subdomains_*.txt`
- crt.sh: `/opt/work/osint/cache/{TARGET}/crt_sh_*.json`

**Command History:**
```bash
{COMMAND_HISTORY}
```

---

## 10. Methodology & Tools

**OSINT Sources:**
- InternetDB (Shodan free tier — unlimited IP lookups)
- Shodan API (100 credits/month for advanced queries)
- WHOIS databases
- DNS enumeration (dig, host)
- Certificate Transparency logs (crt.sh)
- subdomain enumeration (subfinder, amass)
- theHarvester (email, subdomain collection)
- Wayback Machine (web.archive.org)
- GitHub code search
- Social media OSINT (sherlock, maigret)

**Passive Reconnaissance Only:**
- ✅ No active scanning performed
- ✅ No exploitation attempts
- ✅ Public information only

---

**Report Version:** 1.0
**Last Updated:** {TIMESTAMP}
**Next Review:** {NEXT_REVIEW_DATE}
