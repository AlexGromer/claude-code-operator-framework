# Module 18: Blue/Purple Team & DFIR — Project Context

## Our Detection Stack

| Component | Tool | Notes |
|-----------|------|-------|
| SIEM/XDR | Wazuh (self-hosted, Elasticsearch backend) | Primary detection platform |
| IDS/IPS | Suricata | Network intrusion detection |
| Pattern matching | YARA | Malware detection, integrated with Wazuh |
| Detection rules | Sigma | Universal format → convert to Wazuh/KQL |
| Threat intel | MISP + OpenCTI | IOC sharing and correlation |
| Live forensics | Velociraptor | Remote artifact collection |
| Memory forensics | Volatility 3 | Memory image analysis |
| Disk forensics | Autopsy + Sleuth Kit | GUI + CLI analysis |
| Network analysis | Zeek + Wireshark | Protocol logging + packet capture |
| EDR/endpoint | Wazuh agent + osquery | Behavioral + SQL telemetry |
| Timeline | Plaso (log2timeline) | Super timeline generation |
| RE (static) | Ghidra + radare2 | Disassembly/decompilation |
| RE (dynamic) | x64dbg + Cuckoo | Debugging + sandboxing |
| Sandbox VM | FlareVM (Windows) + REMnux (Linux) | Isolated malware lab |

## Working Directories

| Use Case | Path |
|----------|------|
| OSINT cache | `/opt/work/osint/cache/{target}/` |
| OSINT reports | `/opt/work/osint/reports/{target}/` |
| Pentest data | `/opt/work/pentest/{project}/` |
| Malware samples | `/opt/work/reverse/{target}/` |
| DFIR evidence | `/opt/work/reverse/{case-id}/evidence/` |
| DFIR timeline | `/opt/work/reverse/{case-id}/timeline/` |
| YARA rules | `/opt/yara-rules/` |
| Zeek logs | `/opt/zeek/logs/` |

DFIR evidence files use SHA256 hash verification. Chain of custody tracked in `/opt/work/reverse/{case-id}/custody.log`.

## OSINT Tool Stack (Project-Specific Choices)

### Curated Tools

| Tool | Why We Use It | Notes |
|------|--------------|-------|
| **Snoop** | Russian-focused username search (2500+ sites, VK/OK/RuTube/Pikabu) | Prioritize over Sherlock for RU targets |
| **Robin** | Multi-module OSINT framework (email, breach, DNS, WHOIS, social, IP) | Integrates with BBOT |
| **BBOT** | Automated subdomain/email/cloud enumeration | Primary recon automation |
| **Maigret** | Extended username OSINT (2500+ sites) | Complement to Snoop for cross-platform |
| **SploitScan** | CVE + exploit search + EPSS + CISA KEV | Vulnerability prioritization |

### OSINT Tool Priority for Russian Targets

1. Snoop (`python3 snoop.py --ru username`) — Russian platforms first
2. Maigret — extended cross-platform
3. Robin — domain/email/breach modules
4. BBOT — infrastructure enumeration

### Key OSINT Resources

- **Awesome-OSINT-For-Everything**: `https://github.com/Astrosp/Awesome-OSINT-For-Everything` — reference catalog for tool selection by investigation type
- **Indetectables toolkit**: malware samples for AV testing / red team (isolated lab only, ФЗ-272-274.2 applies)

## Intelligence Discipline → MCP Server Mapping

| INT | Primary MCP | Secondary |
|-----|------------|-----------|
| OSINT | `mcp__pd-tools__subfinder`, `mcp__pd-tools__httpx`, `mcp__pd-tools__katana` | `mcp__github__search_code` |
| CYBINT | `mcp__pd-tools__nuclei` | `WebSearch` (threat feeds) |
| DARKINT | `WebFetch` (Tor via proxy) | Manual monitoring |
| SOCMINT | `WebSearch` | `WebFetch` (profile pages) |
| COMINT | `mcp__pd-tools__httpx` | `WebFetch` |
| FININT | `WebFetch` (blockchain explorers) | `WebSearch` |
| GEOINT | `WebFetch` (MaxMind, WiGLE) | `WebSearch` |
| TECHINT | `mcp__pd-tools__nuclei` | `mcp__filesystem__*` (local samples) |

## INT Priority for This Project

Cyber-relevant priority (high → low): CYBINT → OSINT → DARKINT → SOCMINT → COMINT → FININT → TECHINT → GEOINT → SIGINT → VATINT

Russian-specific priority boost: SOCMINT (VK/OK/Telegram focus), OSINT (RU registrars, .ru domains)

## AI-Assisted Pentest Tools

| Tool | GitHub | Best For |
|------|--------|----------|
| **PentestAgent** | `0xSojalSec/PentestAgent` | General pentest automation, guided mode |
| **Shannon** | `KeygraphHQ/shannon` | Web app + API, CI/CD integration, Claude Opus backend |

Both require written authorization. Shannon supports `--mode purple-team` for ATT&CK TTP export.

## DFIR Evidence Paths (Project Convention)

```
/opt/work/reverse/{case-id}/
  evidence/          # Raw: memory.lime, disk.img + .sha256 files
  analysis/          # Volatility output, Autopsy workspace
  timeline/          # bodyfile.txt, timeline.csv (Plaso output)
  network/           # capture.pcap, zeek/ logs
  malware/           # extracted samples (isolated)
  custody.log        # Chain of custody log
  report.md          # Investigation notes
```

Memory acquisition: `avml` (Linux), `winpmem_mini.exe` (Windows).
Disk imaging: `dcfldd` (with hash log) or `dd` + manual SHA256.
Verify: SHA256 hash before and after every transfer.

## Purple Team Conventions

- Atomic Red Team tests logged with timestamps to `/opt/work/pentest/{project}/purple/attack_log.jsonl`
- Detection gaps tracked in `/opt/project/GAPS.md` (category: SEC)
- ATT&CK coverage matrix stored per-exercise in `/opt/work/pentest/{project}/purple/coverage_matrix.json`

## Authorization Quick Reference (This Domain)

| Operation | Level | Confirm |
|-----------|-------|---------|
| Log reading, SIEM query, PCAP view | READ | No |
| Log correlation, threat hunting, static malware analysis, Volatility | ANALYZE | No |
| Sigma rule creation, SIEM rule deployment, alert tuning | MODIFY | Yes |
| Atomic Red Team tests, Caldera, lateral movement emulation | NETWORK_ACTIVE | Yes + scope |
| Memory dump (live system), disk imaging | MODIFY | Yes |
| EDR endpoint isolation, firewall block, account disable | INFRASTRUCTURE | Yes |
| Malware execution in VM, Cuckoo submission | NETWORK_ACTIVE | Yes + isolated |
| LSASS dump analysis, hash cracking | CREDENTIAL | Yes + legal basis |
| Wipe system, delete evidence | DESTRUCTIVE | Yes + explicit |

## Examples

Примеры для этого домена: `~/.claude/examples/blue-purple-dfir/`

| Пример | Описание |
|--------|----------|
| `incident_response_playbook.md` | IR playbook template |
| `sigma_rule_development.md` | Sigma rule development workflow |
| `malware_triage_example.md` | Malware triage (30-minute procedure) |

**Version**: 3.0.0 (compact rewrite 2026-02-25)
**Related Modules**: 02-security.md (offensive), 01-compliance.md (governance)
