# Module 22: Security Workflows — Practical Runbook
# On-demand | Loaded on security workflow keywords
# References: 02-security.md (theory), 18-blue-purple-dfir.md (INT taxonomy, detection)

---

## Section 0: Infrastructure Map

### CLI Tools → MCP Servers → Working Dirs

| Category | CLI Tools | MCP Servers | Working Dir |
|----------|-----------|-------------|-------------|
| **Recon** | subfinder, amass, theharvester, dnsrecon, dnsx, naabu, httpx, whatweb, wafw00f | pd-tools, shodan, censys-platform, censys-asm, greynoise, hexstrike | /opt/work/osint/ |
| **Crawling** | katana, gau, waybackurls | pd-tools, wayback | /opt/work/osint/ |
| **Scanning** | nuclei, nikto, wpscan, zaproxy | pd-tools, pentest-mcp, mcp-kali-server | /opt/work/pentest/ |
| **Fuzzing** | ffuf, gobuster, feroxbuster | pentest-mcp, mcp-kali-server | /opt/work/pentest/ |
| **Exploit** | searchsploit, sploitscan, metasploit | PentestAgent, hexstrike, mcp-kali-server | /opt/work/pentest/ |
| **OSINT** | maigret, holehe, phoneinfoga, bbot, spiderfoot | maigret, bbot, spiderfoot-mcp, hibp, whoisxml | /opt/work/osint/ |
| **Intel** | nrich, shodan CLI, censys CLI, greynoise CLI | shodan, censys-*, greynoise, virustotal, threatintel, vulners, ipinfo | /opt/work/osint/ |
| **Detection** | yara, sigma, suricata | yaraflux, security-detections, suricata, wazuh | /opt/work/pentest/ |
| **Forensics** | volatility3, tshark/wireshark | volatility-mcp, WireMCP, velociraptor | /opt/work/reverse/ |
| **Reverse** | ghidra, radare2, strings, file | ghidra-mcp | /opt/work/reverse/ |
| **Case Mgmt** | — | thehive, misp, elasticsearch, defectdojo | — |
| **Malware Intel** | yara | abusech, virustotal, yaraflux | /opt/work/reverse/ |

### Python venv
```bash
source /opt/work/osint/venv/bin/activate
# Contains: shodan, censys, holehe, greynoise, vt-py, OTXv2, etc.
```

### Output Directory Structure
```
/opt/work/osint/
├── cache/{target}/       # Raw OSINT data (timestamped)
├── reports/{target}/     # Generated reports
└── venv/                 # Python tools

/opt/work/pentest/
├── {target}/             # Per-target pentest data
├── internal/             # Internal pentest data
├── sigma/                # Custom Sigma rules
├── suricata/             # Custom Suricata rules
└── webapp/               # Web app test results

/opt/work/reverse/
├── samples/              # Malware/binary samples
├── analysis/{sample}/    # Per-sample analysis
├── rules/                # YARA rules
├── ghidra_projects/      # Ghidra project files
└── timeline/             # Forensic timelines
```

---

## Section 0b: API Cost Optimization

**Principle**: Free-first → Local-second → Paid-last.

| Priority | Source | Cost | Use Case |
|----------|--------|------|----------|
| 1 | InternetDB (internetdb.shodan.io) | FREE, unlimited | IP → ports, CVEs, tags |
| 2 | GreyNoise Community | FREE, 50/day | IP noise classification |
| 3 | abuse.ch (MalwareBazaar/URLhaus) | FREE, unlimited | Hash/URL malware |
| 4 | HIBP | FREE limited, 10/min | Email breach check |
| 5 | Hexstrike (local, 150+ tools) | FREE, local | Active scanning |
| 6 | Shodan Search | 100 credits/month | Deep host intel |
| 7 | Censys | 250 queries/month | Cert/host search |
| 8 | VirusTotal | 500 lookups/day, 4/min | File/URL/domain rep |
| 9 | GreyNoise Enterprise | Budget-dependent | Full IP context |
| 10 | Vulners | Budget-dependent | Vulnerability intel |

**Anti-waste rules**:
1. NEVER use Shodan search when InternetDB has the same data
2. ALWAYS filter InternetDB results before querying paid APIs
3. PREFER hexstrike (local) over MCP API for active scanning
4. CACHE all results to `/opt/work/osint/cache/{target}/` — never re-query same IP
5. BATCH queries where possible

```bash
# Check credits
curl -s "https://api.shodan.io/api-info?key=$SHODAN_API_KEY" | jq '.query_credits'
# Budget log: ~/.claude/evaluation/data/budget_spending.jsonl
```

---

## Section 1: Bug Bounty Pipeline

**Skill**: `/bugbounty` | **Auth**: NETWORK_ACTIVE | **Output**: `/opt/work/osint/cache/{target}/`

| Phase | CLI | MCP | Output file |
|-------|-----|-----|-------------|
| Subdomain (passive) | subfinder -all, amass -passive | pd-tools | subs_*.txt → subdomains.txt |
| DNS resolve | dnsx -resp -a -cname | pd-tools | resolved.txt → alive_hosts.txt |
| HTTP probe | httpx -sc -cl -title -tech-detect | pd-tools | httpx.json |
| Port scan | naabu -top-ports 1000 | pd-tools | ports.txt |
| URL collect | gau, waybackurls, katana -d 3 -jc | pd-tools, wayback | all_urls.txt |
| Vuln scan | nuclei -severity critical,high,medium | pd-tools | nuclei.json |
| Dir fuzz | ffuf -w common.txt -mc 200,301,302,403 | pentest-mcp | ffuf_dirs.json |
| WAF detect | wafw00f | — | waf.txt |

**URL filtering**: `grep -iE '\.(php|asp|jsp)\?'` (dynamic) | `grep -iE '(api|graphql|v[0-9])'` (API endpoints)

---

## Section 2: OSINT Pipelines

**Skill**: `/osint-workflow` | **Auth**: READ/ANALYZE

| Target Type | CLI | MCP | Output |
|-------------|-----|-----|--------|
| Domain | subfinder, dnsrecon, whatweb | pd-tools, shodan, censys-platform, greynoise, virustotal, whoisxml | /opt/work/osint/cache/{domain}/ |
| Person/Username | maigret, holehe, phoneinfoga | maigret, hibp, spiderfoot-mcp | /opt/work/osint/cache/{username}/ |
| IP | nrich, shodan CLI, greynoise CLI | shodan, greynoise, threatintel, censys-platform, ipinfo | /opt/work/osint/cache/{ip}/ |
| Email | theHarvester | hibp, spiderfoot-mcp | /opt/work/osint/cache/{domain}/ |
| Hash | — | virustotal, abusech | /opt/work/reverse/analysis/ |

**Cert transparency**: `curl -s "https://crt.sh/?q=%25.${TARGET}&output=json" | python3 -c "import sys,json; [print(e['name_value']) for e in json.load(sys.stdin)]" | sort -u`

---

## Section 3: INT Integration Matrix

**Skill**: `/intel-workflow` | **Auth**: READ/ANALYZE

| IOC Type | CYBINT | SOCMINT | DARKINT | FININT | GEOINT |
|----------|--------|---------|---------|--------|--------|
| IP | Shodan, Censys, GN | — | Tor exit check | — | IPinfo geo |
| Domain | DNS, CT, Subfinder | — | .onion links | WHOIS registrar | Hosting geo |
| Email | Breach check | holehe, maigret | Paste sites | — | — |
| Username | — | Maigret, Holehe | Forum search | Wallet links | — |
| Hash | VT, MalwareBazaar | — | Malware markets | — | — |

**SOCMINT tools**: maigret (2500+ sites), holehe (email → accounts), platform APIs (tweepy/vk_api/telethon in venv)
**FININT**: EGRUL (egrul.nalog.ru), SEC EDGAR (sec.gov), blockchain explorers (blockchain.com, etherscan.io)
**GEOINT**: exiftool for EXIF GPS, ipinfo MCP for IP geolocation

---

## Section 4: DFIR / Forensics

**Skill**: `/dfir-workflow` | **Auth**: ANALYZE/MODIFY | **Ref**: 18-blue-purple-dfir.md

### IR Checklist
```
IMMEDIATE (0-15 min): Classify → Contain (isolate) → Preserve (no reboot!) → Notify
EVIDENCE (15-60 min): Memory dump first → Network capture → Logs → Disk image
ANALYSIS (1-24h): Timeline → IOC extraction → Root cause → Lateral movement → Exfil
```

### Key Commands
```bash
# Memory (Linux) — before anything else
sudo insmod lime.ko "path=/opt/work/reverse/memdump.lime format=lime"
vol3 -f memdump.raw windows.pslist / windows.netscan / windows.malfind / windows.cmdline

# Disk forensics
sudo dd if=/dev/sda of=/opt/work/reverse/disk.raw bs=4M status=progress
sudo mount -o ro,loop /opt/work/reverse/disk.raw /mnt/evidence
log2timeline.py /opt/work/reverse/timeline.plaso /mnt/evidence

# Network forensics
sudo tshark -i eth0 -w /opt/work/reverse/capture.pcap -a duration:300
tshark -r capture.pcap -Y "http.request" -T fields -e ip.src -e http.host -e http.request.uri

# Log analysis
grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn | head
```

**MCP**: volatility-mcp (memory), WireMCP (pcap), velociraptor (endpoint), wazuh (SIEM/EDR), elasticsearch (logs)

---

## Section 5: Reverse Engineering

**Skill**: `/reverse-workflow` | **Auth**: ANALYZE

| Phase | CLI | MCP | Output |
|-------|-----|-----|--------|
| Triage | file, sha256sum, strings -n 8 | virustotal, abusech | hashes.txt, strings.txt |
| Static | r2 -AA, readelf, pefile | ghidra-mcp | r2_analysis.txt, pe_info.txt |
| Dynamic (VM only) | strace -e trace=network,file, ltrace | — | strace.txt |
| IOC extract | grep -oP (IPs/URLs from strings.txt) | virustotal, threatintel, misp | ioc_ips.txt, ioc_urls.txt |

**Output dir**: `/opt/work/reverse/analysis/$(basename $SAMPLE)/`

---

## Section 6: Blue Team / Defense

**Skill**: `/blueteam-workflow` | **Auth**: READ/ANALYZE

### IOC Enrichment: MCP Pipeline
- **IP**: shodan → greynoise → threatintel (OTX/AbuseIPDB) → ipinfo → censys-platform
- **Hash**: virustotal → abusech (MalwareBazaar) → yaraflux
- **Domain**: virustotal → whoisxml → shodan → censys-asm

**Bulk IP enrichment CLI**: `while read IOC; do nrich - <<< "$IOC"; done < ioc_file.txt`

**Detection files**: Sigma → `/opt/work/pentest/sigma/*.yml` (sigma-cli/sigmac, MCP: security-detections, wazuh) | Suricata → `/opt/work/pentest/suricata/custom.rules` (MCP: suricata) | YARA → `/opt/work/reverse/rules/*.yar` (MCP: yaraflux)

**CVE**: `sploitscan CVE-XXXX` | MCP: cve-intelligence, vulners, defectdojo

---

## Section 7: Red Team / Pentest

**Skill**: `/redteam-workflow` | **Auth**: NETWORK_ACTIVE/CREDENTIAL

**External** (`/opt/work/pentest/{target}/`): Passive recon (S2) → `nmap -sC -sV` → nikto/nuclei/ffuf → OWASP manual
**Internal** (`/opt/work/pentest/internal/`): `nmap -sn {net}` → `nmap -sV -sC -iL targets.txt` → smb-enum-shares/users → CREDENTIAL: hydra/crackmapexec (written auth required)

**OWASP tools**: A01 IDOR → ffuf | A02 TLS → nmap ssl-enum-ciphers | A03 SQLi → sqlmap (mcp-kali-server) | A05 misconfig → nuclei -tags misconfig | A10 SSRF → qsreplace+Interactsh

---

## Section 8: Quick Reference

### Task → CLI + MCP

| Task | CLI | MCP |
|------|-----|-----|
| Subdomain discovery | subfinder, amass | pd-tools |
| Port scan (NETWORK_ACTIVE) | nmap, naabu | pd-tools, mcp-kali-server |
| HTTP probing | httpx | pd-tools |
| Vuln scan | nuclei | pd-tools |
| Web crawl | katana, gau | pd-tools, wayback |
| Dir fuzzing | ffuf, gobuster | pentest-mcp |
| IP lookup | nrich, shodan CLI | shodan, greynoise, ipinfo, threatintel |
| Username OSINT | maigret | maigret, spiderfoot-mcp |
| Email/breach | holehe | hibp |
| Hash check | — | virustotal, abusech |
| Memory forensics | volatility3 | volatility-mcp |
| Pcap analysis | tshark | WireMCP |
| YARA scan | yara | yaraflux |
| Decompile | ghidra, r2 | ghidra-mcp |
| CVE research | sploitscan | cve-intelligence, vulners |
| Detection rules | sigma-cli | security-detections, wazuh, suricata |
| Case / vuln mgmt | — | thehive, defectdojo, misp |
| Attack surface | bbot | censys-asm, censys-platform |
| Log search | — | elasticsearch, wazuh |

### MCP Key Functions

| MCP | Functions |
|-----|-----------|
| pd-tools | subfinder, nuclei, httpx, katana, naabu, dnsx |
| shodan | host lookup, search, exploits, honeypot check |
| censys-platform/asm | host/service/cert search, attack surface |
| greynoise | IP noise/malicious/benign classification |
| virustotal | file/URL/domain/IP analysis |
| threatintel | OTX pulses, AbuseIPDB |
| maigret | username → 2500+ sites |
| bbot/spiderfoot-mcp | automated recon, 200+ OSINT modules |
| hibp | breach + password check |
| whoisxml | WHOIS, DNS, IP geo |
| abusech | MalwareBazaar, URLhaus, ThreatFox |
| wayback | historical snapshots |
| ipinfo | IP geo, ASN |
| vulners | 4M+ vuln bulletins |
| pentest-mcp | nmap, gobuster, nikto, john, hashcat |
| mcp-kali-server | 55+ tools: nmap, sqlmap, hydra |
| PentestAgent / hexstrike | metasploit, ffuf, sqlmap, 150+ tools (local) |
| volatility-mcp / WireMCP | memory + pcap forensics |
| ghidra-mcp / yaraflux | decompilation, YARA mgmt |
| security-detections / suricata | Sigma rules, network IDS |
| wazuh / velociraptor | SIEM/EDR, endpoint investigation |
| thehive / defectdojo / misp | case mgmt, vuln mgmt, threat intel |
| elasticsearch | log search |
| cve-intelligence | CVE search, NVD data |

### Authorization Levels

| Workflow | Auth | Confirm? |
|----------|------|---------|
| OSINT passive, breach check | READ | No |
| Enrichment, DFIR analysis, RE | ANALYZE | No |
| Active scan (nmap, nuclei) | NETWORK_ACTIVE | Yes + scope |
| Credential testing | CREDENTIAL | Yes + written auth |
| Exploitation | DESTRUCTIVE | Explicit approval |

---

**Version**: 2.0.0 (compact) | **Lines**: ~220
**Dependencies**: 33 MCP servers, 36+ CLI tools, modules 02, 18
