# Module 21: Network Infrastructure & CMDB

**Load when**: User mentions MikroTik, OPNSense, network monitoring, CMDB, NetBox, Snipe-IT, WAF, VLAN, VPN, NAC, PacketFence, Ntopng, Netdisco, mail server, SMTP, IMAP, Stalwart.

---

## Our Stack

**Routers/Firewalls**: MikroTik RouterOS (primary), OPNSense (edge/perimeter). Claude knows both — ask which is in use before generating configs.

**Network Monitoring**: Ntopng + nProbe (traffic analysis, DPI, flow collection). Netdisco (SNMP device discovery, MAC/ARP/port mapping). SNMP v3 preferred.

**CMDB/IPAM**: NetBox (network infrastructure: devices, racks, VLANs, prefixes, IP addresses, cables). Snipe-IT (endpoint assets, licenses, helpdesk). Both in use — NetBox for infra, Snipe-IT for endpoints. Integrated via API.

**Network Security**: BunkerWeb WAF (container-native, ModSecurity CRS, Docker/K8s). SafeLine WAF (AI-based, web UI, used where BunkerWeb is impractical). PacketFence for NAC (802.1X, captive portal, VLAN assignment).

**VPN**: WireGuard (site-to-site and remote access). Managed via MikroTik or OPNSense.

**Mail**: Stalwart (Rust, all-in-one SMTP/IMAP/JMAP). Auth via LDAP (FreeIPA). Spam via Rspamd.

---

## Key Decisions & Conventions

| Area | Choice | Reason |
|------|--------|--------|
| WAF | BunkerWeb (K8s/Docker), SafeLine (standalone) | Environment-dependent |
| CMDB | NetBox + Snipe-IT | Network vs endpoint split |
| NAC | PacketFence | 802.1X + captive portal |
| Mail | Stalwart | Memory-safe, all-in-one |
| Monitoring | Ntopng + Netdisco | Traffic analysis + SNMP |

**VLAN scheme** (standard zones):
- VLAN 10 — Management (10.0.10.0/24)
- VLAN 20 — Users (10.0.20.0/24)
- VLAN 30 — Guest (10.0.30.0/24)
- VLAN 40 — Servers (10.0.40.0/24)
- VLAN 50 — DMZ (10.0.50.0/24)
- VLAN 60 — IoT (10.0.60.0/24)

---

## Integration Points

- Ntopng → Grafana (dashboards), Wazuh (alerts), Suricata (IDS correlation)
- Netdisco → NetBox (IPAM sync via API), PacketFence (MAC tracking)
- BunkerWeb/SafeLine → Wazuh (syslog/CEF), Grafana (metrics), CrowdSec (threat intel)
- Stalwart → FreeIPA (LDAP auth), VictoriaMetrics (monitoring)
- NetBox → Snipe-IT (asset correlation via API)

---

## Clarifying Questions

Before generating configs, always confirm:
- **Equipment**: MikroTik RouterOS version (v6 vs v7 — syntax differs), OPNSense version
- **Topology**: existing VLAN layout, trunk/access ports
- **WAF**: BunkerWeb or SafeLine? Docker/K8s or standalone?
- **VPN**: site-to-site or remote access? WireGuard or IPsec?
- **Scope**: NetBox (infra) or Snipe-IT (endpoints)?

---

## Authorization Levels

| Operation | Level |
|-----------|-------|
| Read config, view topology, log analysis | READ/ANALYZE |
| VLAN design, IP plan, firewall rule proposal | PLAN |
| Apply firewall rule, create VLAN, configure NAT | MODIFY (show diff) |
| Port scan, vulnerability scan | NETWORK_ACTIVE (confirm target+scope) |
| Deploy firewall, firmware upgrade, NAC rollout | INFRASTRUCTURE (show plan + rollback) |

---

**Cross-references**: `modules/02-security.md` (IDS/IPS), `modules/03-devops.md` (Docker/K8s), `modules/18-blue-purple-dfir.md` (network forensics)

**Docs**: wiki.mikrotik.com | docs.opnsense.org | docs.netbox.dev | stalw.art/docs | github.com/bunkerity/bunkerweb
