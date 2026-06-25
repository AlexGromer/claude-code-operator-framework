# Few-Shot Example: OPNSense Firewall Configuration for Segmented Network

**Domain:** Network Infrastructure / Security
**Skill Level:** Intermediate
**Pattern:** OPNSense firewall rules with network segmentation, IDS/IPS, and NAT

---

## User Query

```
Need to configure firewall rules on OPNSense for our office network. We have 3 VLANs (Office, Guests, Servers) and want to isolate guests from internal network while allowing Office to access Servers. Also need IDS/IPS. How do I set this up?
```

---

## Exemplary Response

┌─ ROUTING ──────────────────────────────────────────────────┐
│ Role: Network Engineer / Security Engineer                 │
│ Confidence: HIGH (92%)                                     │
│ Modules: 21-network-infrastructure.md, 02-security.md     │
│ Approach: Defense-in-depth with Suricata IDS/IPS          │
└────────────────────────────────────────────────────────────┘

## OPNSense Firewall Configuration Guide

I'll create a comprehensive firewall configuration with proper segmentation and intrusion detection.

---

## Network Topology

```
                    INTERNET
                       │
                   [WAN Port]
                       │
         ┌─────────────┴──────────────┐
         │     OPNSense Firewall      │
         │   (24.80 Community Edition)│
         └─┬────────┬──────────┬──────┘
           │        │          │
    [LAN1] │  [LAN2]│    [LAN3]│
    Office │  Guests│    Servers
 192.168.10│ 192.168│  192.168
      .0/24│  .20.0 │    .30.0
           │   /24  │      /24
           │        │          │
     Employee   Guest Wi-Fi  Internal
     Workstations   (isolated)  Servers
```

### VLAN/Interface Plan

| Interface | VLAN | Subnet | Gateway | Description |
|-----------|------|--------|---------|-------------|
| **WAN** | — | DHCP/Static (ISP) | — | Internet connection |
| **LAN** | 1 | 192.168.88.0/24 | 192.168.88.1 | Management (unused in this setup) |
| **OPT1** (Office) | 10 | 192.168.10.0/24 | 192.168.10.1 | Employee network |
| **OPT2** (Guests) | 20 | 192.168.20.0/24 | 192.168.20.1 | Guest Wi-Fi (isolated) |
| **OPT3** (Servers) | 30 | 192.168.30.0/24 | 192.168.30.1 | Internal servers, NAS |

---

## Phase 1: Interface Configuration

### Step 1.1: Assign Interfaces

**Interfaces → Assignments**

| Physical Port | Name | Description |
|---------------|------|-------------|
| igb0 | WAN | Internet uplink |
| igb1.10 (VLAN tagged) | OPT1_OFFICE | Office VLAN 10 |
| igb1.20 (VLAN tagged) | OPT2_GUESTS | Guests VLAN 20 |
| igb1.30 (VLAN tagged) | OPT3_SERVERS | Servers VLAN 30 |

**Note**: If using VLAN trunking, create VLAN tags first:
- **Interfaces → Other Types → VLAN**
  - VLAN 10: Parent interface `igb1`, VLAN tag `10`, Description `Office`
  - VLAN 20: Parent interface `igb1`, VLAN tag `20`, Description `Guests`
  - VLAN 30: Parent interface `igb1`, VLAN tag `30`, Description `Servers`

### Step 1.2: Configure Interface IPs

#### OPT1_OFFICE (Office VLAN)

**Interfaces → OPT1_OFFICE**

| Field | Value |
|-------|-------|
| **Enable interface** | ✓ Checked |
| **Description** | Office VLAN |
| **IPv4 Configuration Type** | Static IPv4 |
| **IPv4 Address** | 192.168.10.1/24 |
| **Block private networks** | ☐ Unchecked (we use private IPs) |
| **Block bogon networks** | ✓ Checked |

#### OPT2_GUESTS (Guests VLAN)

| Field | Value |
|-------|-------|
| **Description** | Guests VLAN |
| **IPv4 Address** | 192.168.20.1/24 |
| **Block private networks** | ✓ Checked (prevent access to other RFC1918) |
| **Block bogon networks** | ✓ Checked |

#### OPT3_SERVERS (Servers VLAN)

| Field | Value |
|-------|-------|
| **Description** | Servers VLAN |
| **IPv4 Address** | 192.168.30.1/24 |
| **Block private networks** | ☐ Unchecked |
| **Block bogon networks** | ✓ Checked |

---

## Phase 2: DHCP Server Configuration

### Step 2.1: Enable DHCP

**Services → DHCPv4 → [Interface Name]**

#### OPT1_OFFICE DHCP

| Field | Value |
|-------|-------|
| **Enable** | ✓ Checked |
| **Range** | 192.168.10.100 - 192.168.10.200 |
| **DNS Servers** | 8.8.8.8, 8.8.4.4 (or internal DNS server) |
| **Gateway** | 192.168.10.1 |
| **Domain Name** | company.local (optional) |
| **Lease Time** | 86400 (1 day) |

#### OPT2_GUESTS DHCP

| Field | Value |
|-------|-------|
| **Enable** | ✓ Checked |
| **Range** | 192.168.20.100 - 192.168.20.200 |
| **DNS Servers** | 8.8.8.8, 8.8.4.4 (public DNS only) |
| **Gateway** | 192.168.20.1 |
| **Lease Time** | 7200 (2 hours, short for guests) |

#### OPT3_SERVERS DHCP

**Disabled** — Servers use static IPs (assign manually: .10, .11, .12, etc.)

---

## Phase 3: NAT Configuration

### Step 3.1: Outbound NAT (Internet Access)

**Firewall → NAT → Outbound**

**Mode**: Automatic (Hybrid Outbound NAT)

OPNSense automatically creates rules for:
- Office → WAN (SNAT to WAN IP)
- Guests → WAN (SNAT to WAN IP)
- Servers → WAN (optional, can be disabled with firewall rules)

**Verify Auto-Generated Rules**:
```
Source: 192.168.10.0/24 → Translate to: WAN address
Source: 192.168.20.0/24 → Translate to: WAN address
Source: 192.168.30.0/24 → Translate to: WAN address
```

### Step 3.2: Port Forwarding (Inbound NAT)

**Firewall → NAT → Port Forward**

Example: HTTPS to Web Server (192.168.30.10)

| Field | Value |
|-------|-------|
| **Interface** | WAN |
| **Protocol** | TCP |
| **Destination** | WAN address |
| **Destination Port Range** | HTTPS (443) |
| **Redirect Target IP** | 192.168.30.10 |
| **Redirect Target Port** | HTTPS (443) |
| **Description** | HTTPS to Web Server |
| **NAT Reflection** | Enable |
| **Filter Rule Association** | Add associated filter rule |

**Result**: External `http://YOUR_WAN_IP:443` → `192.168.30.10:443`

---

## Phase 4: Firewall Rules (Core Security)

### Default Policy: DENY ALL

OPNSense default: **Implicit deny** (if no rule matches, traffic is dropped).

### Step 4.1: WAN Rules (Inbound from Internet)

**Firewall → Rules → WAN**

| # | Action | Protocol | Source | Destination | Port | Description |
|---|--------|----------|--------|-------------|------|-------------|
| 1 | **Block** | Any | Any | RFC1918 networks | Any | Block WAN → Private IPs (anti-spoofing) |
| 2 | **Pass** | TCP | Any | WAN address | 443 | HTTPS to Web Server (port forward) |
| 3 | **Block** | Any | Any | Any | Any | **Default deny all inbound** |

**Note**: OPNSense auto-creates Rule #1 if "Block private networks" is checked on WAN.

---

### Step 4.2: Office (OPT1) Rules

**Firewall → Rules → OPT1_OFFICE**

| # | Action | Protocol | Source | Destination | Port | Description |
|---|--------|----------|--------|-------------|------|-------------|
| 1 | **Pass** | ICMP | OPT1_OFFICE net | Any | Any | Allow ping (diagnostic) |
| 2 | **Pass** | TCP/UDP | OPT1_OFFICE net | Any | 53 (DNS) | Allow DNS queries |
| 3 | **Pass** | TCP | OPT1_OFFICE net | OPT3_SERVERS net | Any | Office → Servers (full access) |
| 4 | **Pass** | TCP/UDP | OPT1_OFFICE net | WAN net | Any | Office → Internet |
| 5 | **Block** | Any | OPT1_OFFICE net | OPT2_GUESTS net | Any | Block Office → Guests (no reason) |
| 6 | **Pass** | Any | OPT1_OFFICE net | OPT1 address | Any | Allow access to firewall (management) |
| 7 | **Block** | Any | OPT1_OFFICE net | Any | Any | **Implicit deny** |

**Rule Order**: Most specific → least specific. OPNSense evaluates top-to-bottom, first match wins.

---

### Step 4.3: Guests (OPT2) Rules

**Firewall → Rules → OPT2_GUESTS**

| # | Action | Protocol | Source | Destination | Port | Description |
|---|--------|----------|--------|-------------|------|-------------|
| 1 | **Pass** | ICMP | OPT2_GUESTS net | WAN net | Any | Allow ping to Internet only |
| 2 | **Pass** | TCP/UDP | OPT2_GUESTS net | Any | 53 (DNS) | Allow DNS (Internet DNS only) |
| 3 | **Pass** | TCP | OPT2_GUESTS net | WAN net | 80, 443 | HTTP/HTTPS to Internet |
| 4 | **Block** | Any | OPT2_GUESTS net | RFC1918 | Any | **CRITICAL: Block access to internal networks** |
| 5 | **Block** | Any | OPT2_GUESTS net | OPT1_OFFICE net | Any | Block Guests → Office (redundant, but explicit) |
| 6 | **Block** | Any | OPT2_GUESTS net | OPT3_SERVERS net | Any | Block Guests → Servers |
| 7 | **Block** | Any | OPT2_GUESTS net | Any | Any | **Default deny all** |

**Critical Rule #4**: Blocks ALL private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).

**Advanced**: Create Alias for RFC1918 networks:
- **Firewall → Aliases → Networks**
  - Name: `RFC1918`
  - Type: Network(s)
  - Content: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`

Use alias in rule: Destination = `RFC1918`

---

### Step 4.4: Servers (OPT3) Rules

**Firewall → Rules → OPT3_SERVERS**

| # | Action | Protocol | Source | Destination | Port | Description |
|---|--------|----------|--------|-------------|------|-------------|
| 1 | **Pass** | TCP | OPT1_OFFICE net | OPT3_SERVERS net | Any | Office → Servers (allow incoming) |
| 2 | **Pass** | TCP | OPT3_SERVERS net | OPT1_OFFICE net | Any | Servers → Office (responses, SMB shares) |
| 3 | **Pass** | TCP/UDP | OPT3_SERVERS net | Any | 53 | DNS for updates |
| 4 | **Pass** | TCP | OPT3_SERVERS net | Any | 80, 443 | HTTP/HTTPS (OS updates, package downloads) |
| 5 | **Block** | Any | OPT3_SERVERS net | OPT2_GUESTS net | Any | Servers → Guests (no reason) |
| 6 | **Block** | Any | OPT3_SERVERS net | WAN net | Any | **Block all other Internet** (restrict server egress) |
| 7 | **Pass** | Any | OPT3_SERVERS net | OPT3 address | Any | Servers → Firewall (management) |
| 8 | **Block** | Any | OPT3_SERVERS net | Any | Any | Default deny |

**Rule #6**: Restricts servers from initiating arbitrary Internet connections (security best practice). Only allow ports 80/443 (updates), 53 (DNS).

---

## Phase 5: Aliases (Efficiency & Readability)

### Step 5.1: Create Network Aliases

**Firewall → Aliases → Networks**

| Alias Name | Type | Content | Description |
|------------|------|---------|-------------|
| **RFC1918** | Networks | 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 | Private IP ranges |
| **Internal_Networks** | Networks | 192.168.10.0/24, 192.168.30.0/24 | All internal (non-guest) networks |
| **DNS_Servers** | Host(s) | 8.8.8.8, 8.8.4.4, 1.1.1.1 | Public DNS servers |

### Step 5.2: Create Port Aliases

**Firewall → Aliases → Ports**

| Alias Name | Port(s) | Description |
|------------|---------|-------------|
| **Web_Ports** | 80, 443 | HTTP/HTTPS |
| **Mail_Ports** | 25, 587, 993, 995 | SMTP, IMAP, POP3 |
| **Windows_Shares** | 135, 139, 445 | SMB/CIFS |

**Usage in Rules**: Destination Port = `Web_Ports` (cleaner than "80, 443")

---

## Phase 6: IDS/IPS (Suricata)

### Step 6.1: Install Suricata Plugin

**System → Firmware → Plugins**

Search: `os-suricata`
Click: **Install** (requires reboot)

### Step 6.2: Enable Suricata

**Services → Intrusion Detection → Administration**

| Field | Value |
|-------|-------|
| **Enabled** | ✓ Checked |
| **IPS Mode** | ✓ Checked (block malicious traffic) |
| **Promiscuous Mode** | ☐ Unchecked (not needed for inline IPS) |
| **Interfaces** | WAN, OPT1_OFFICE, OPT2_GUESTS, OPT3_SERVERS (monitor all) |
| **Pattern Matcher** | Hyperscan (fastest, if CPU supports) |
| **Logging** | ✓ Alerts only (reduces log volume) |

### Step 6.3: Download Rulesets

**Services → Intrusion Detection → Download**

| Ruleset | Description | Recommended |
|---------|-------------|-------------|
| **ET Open** | Emerging Threats (free) | ✓ YES |
| **ET Pro** | Emerging Threats (paid, $900/year) | Optional |
| **Abuse.ch** | Malware, C2, ransomware | ✓ YES |
| **OISF TRAFFICID** | Protocol detection | ✓ YES |

Click: **Download & Update Rules** (takes 5-10 minutes)

### Step 6.4: Enable Rule Categories

**Services → Intrusion Detection → Rules**

Filter by Category, enable:
- **emerging-malware** (all rules)
- **emerging-exploit** (all rules)
- **emerging-scan** (port scans, reconnaissance)
- **emerging-web_server** (web attacks, SQLi, XSS)
- **emerging-botnet** (C2 communication)
- **emerging-dos** (DoS attacks)
- **abuse.ch** (all rules)

**Disable Noisy Rules**:
- Some rules generate false positives (e.g., `ET INFO` category)
- Review alerts weekly, disable rules with excessive false positives

### Step 6.5: Configure Actions

**Services → Intrusion Detection → Policy**

| Rule Action | OPNSense Action |
|-------------|----------------|
| **Alert** | Log + Pass (monitor only) |
| **Drop** | Block + Log (IPS mode) |
| **Reject** | Block + Send RST/ICMP unreachable |

**Recommendation**: Start with **Alert** mode for 1 week, review logs, then enable **Drop** for confirmed threats.

### Step 6.6: Start Suricata

**Services → Intrusion Detection → Administration**

Click: **Apply**

Check status: `tail -f /var/log/suricata/suricata.log`

---

## Phase 7: Logging & Monitoring

### Step 7.1: Enable Firewall Logging

**Firewall → Settings → Advanced**

| Field | Value |
|-------|-------|
| **Log Firewall Default Blocks** | ✓ Checked |
| **Log packets matched from default block rules** | ✓ Checked |
| **Log packets matched from default pass rules** | ☐ Unchecked (reduces log volume) |

### Step 7.2: View Firewall Logs

**Firewall → Log Files → Live View**

**Columns**:
- Act (Action): Block/Pass
- Interface: WAN, OPT1, etc.
- Source IP
- Destination IP
- Port
- Rule (rule number)

**Filter Example**: Show all blocked traffic from Guests VLAN:
```
Interface: OPT2_GUESTS
Action: Block
```

### Step 7.3: Suricata Alerts

**Services → Intrusion Detection → Alerts**

**Example Alert**:
```
[**] [1:2024554:4] ET MALWARE Win32/Emotet C2 Check-in [**]
[Classification: A Network Trojan was detected]
[Priority: 1]
2026-02-06 14:32:11.234567 192.168.10.105:49234 -> 45.142.212.61:443
```

**Action**: Investigate source IP (192.168.10.105), check for malware infection.

### Step 7.4: Export Logs (SIEM Integration)

**System → Settings → Logging / Targets**

Forward logs to external SIEM (Splunk, ELK, Wazuh):

| Field | Value |
|-------|-------|
| **Enable** | ✓ Checked |
| **Transport** | UDP |
| **Applications** | firewall, suricata, dhcpd |
| **Levels** | Informational and above |
| **Hostname** | 192.168.30.50 (SIEM server IP) |
| **Port** | 514 (syslog) |

---

## Phase 8: Testing & Verification

### Test 1: Office → Internet

```bash
# From Office workstation (192.168.10.x)
ping 8.8.8.8          # Should work
curl https://google.com   # Should work
```

### Test 2: Office → Servers

```bash
# From Office workstation
ping 192.168.30.10    # Should work
ssh user@192.168.30.10   # Should work (if SSH enabled on server)
```

### Test 3: Guests → Internal Networks (SHOULD FAIL)

```bash
# From Guest device (192.168.20.x)
ping 192.168.10.1     # Should FAIL (blocked by firewall)
ping 192.168.30.10    # Should FAIL
curl http://192.168.30.10   # Should timeout (blocked)
```

**Expected**: "Request timeout" or "Destination unreachable"

**Verify in Logs**: `Firewall → Log Files → Live View`
- Source: 192.168.20.x
- Destination: 192.168.10.x or 192.168.30.x
- Action: **Block**
- Rule: Guests → RFC1918 block rule

### Test 4: Guests → Internet

```bash
# From Guest device
ping 8.8.8.8          # Should work
curl https://google.com   # Should work
```

### Test 5: IDS/IPS Detection

```bash
# Trigger test alert (from Office workstation)
curl "http://testmyids.com/"

# Check Suricata alerts (should detect test signature)
# Services → Intrusion Detection → Alerts
# Expected: "GPL ATTACK_RESPONSE id check returned root"
```

### Test 6: Port Forward (HTTPS to Web Server)

```bash
# From external network (use phone 4G, or ask friend)
curl https://YOUR_WAN_IP

# Should reach 192.168.30.10 (web server)
# Check web server logs: 192.168.30.10:/var/log/nginx/access.log
```

---

## Security Hardening

### 1. Disable Unused Services

**System → Settings → Administration**

- ☐ **Enable Secure Shell (SSH)** (if not used remotely)
- ☐ **Enable web console** (disable HTTP, use HTTPS only)

### 2. Change Default Ports

**System → Settings → Administration**

- **Web GUI TCP Port (HTTPS)**: Change from 443 → 8443 (reduces automated scans)
- **SSH Port**: Change from 22 → 2222

### 3. Limit Management Access

**Firewall → Rules → WAN**

Add rule BEFORE any PASS rules:
- Action: **Block**
- Protocol: TCP
- Destination Port: 22, 80, 443, 8443 (all management ports)
- Description: Block management from Internet

**Exception** (if remote access needed):
- Action: **Pass**
- Source: `YOUR_HOME_IP/32` or VPN subnet
- Destination Port: 8443 (HTTPS GUI)

### 4. Enable 2FA (Two-Factor Authentication)

**System → Access → Servers**

Add TOTP authenticator:
1. **Add** → Type: TOTP
2. Name: Google Authenticator
3. Save

**System → Access → Users → admin**
- **OTP Seed**: Click **Generate** → Scan QR code with Google Authenticator app

### 5. Regular Backups

**System → Configuration → Backups**

- **Download Configuration**: Manual backup (before major changes)
- **Automatic Backup**: Enable (daily, keep 30 versions)
- **Remote Backup**: Encrypted upload to cloud storage (optional)

---

## Troubleshooting

### Issue 1: Guests Can Still Access Internal Networks

**Symptoms**: From 192.168.20.x can reach 192.168.10.x.

**Diagnosis**:
1. Check rule order: Firewall → Rules → OPT2_GUESTS
2. Verify "Block RFC1918" rule is BEFORE any PASS rules
3. Check if there's a floating rule allowing traffic

**Fix**: Move block rule to top of OPT2_GUESTS rule list.

### Issue 2: Office Cannot Access Servers

**Symptoms**: Cannot ping 192.168.30.10 from Office.

**Diagnosis**:
1. Firewall → Rules → OPT1_OFFICE: Check if rule #3 exists (Office → Servers)
2. Firewall → Log Files: Look for blocked packets (Source: 192.168.10.x, Dest: 192.168.30.x)

**Fix**: Add rule: Pass, Source: OPT1_OFFICE net, Destination: OPT3_SERVERS net, Port: Any

### Issue 3: IDS/IPS Blocking Legitimate Traffic

**Symptoms**: Website loads slowly, connection drops randomly.

**Diagnosis**:
1. Services → Intrusion Detection → Alerts: Look for alerts matching legitimate traffic
2. Identify false positive rule (e.g., `ET INFO` category)

**Fix**:
1. Services → Intrusion Detection → Rules
2. Search for rule SID (e.g., `2024554`)
3. Uncheck rule to disable
4. Apply changes

### Issue 4: Port Forward Not Working

**Symptoms**: Cannot access web server from Internet.

**Diagnosis**:
1. Firewall → NAT → Port Forward: Verify rule exists
2. Firewall → Rules → WAN: Check if associated filter rule was created
3. From firewall: `telnet 192.168.30.10 443` (test if server is reachable internally)

**Fix**: Ensure "Filter Rule Association" was set to "Add associated filter rule" when creating port forward.

---

## Maintenance Checklist

### Weekly
- [ ] Review Suricata alerts (Services → Intrusion Detection → Alerts)
- [ ] Check firewall logs for unusual traffic (Firewall → Log Files)
- [ ] Verify all interfaces are UP (Interfaces → Overview)

### Monthly
- [ ] Update Suricata rulesets (Services → Intrusion Detection → Download)
- [ ] Review and tune false positive rules
- [ ] Backup configuration (System → Configuration → Backups → Download)
- [ ] Update OPNSense (System → Firmware → Updates)

### Quarterly
- [ ] Review and optimize firewall rules (remove unused rules)
- [ ] Test disaster recovery (restore from backup on test system)
- [ ] Audit port forwards (remove unused)
- [ ] Performance review (System → Diagnostics → Activity)

---

## Configuration Summary

### Network Segmentation Achieved

| Source VLAN | Internet | Office | Guests | Servers |
|-------------|----------|--------|--------|---------|
| **Office** | ✅ ALLOW | ✅ (same VLAN) | ❌ DENY | ✅ ALLOW |
| **Guests** | ✅ ALLOW (HTTP/HTTPS only) | ❌ DENY | ✅ (same VLAN) | ❌ DENY |
| **Servers** | ⚠️ LIMITED (DNS, HTTP/HTTPS) | ✅ ALLOW (responses) | ❌ DENY | ✅ (same VLAN) |

### Security Features Enabled

- ✅ Default Deny All (implicit block)
- ✅ Guest Isolation (RFC1918 block)
- ✅ IDS/IPS (Suricata with ET Open rules)
- ✅ NAT with Port Forwarding
- ✅ Logging (firewall + Suricata)
- ✅ Anti-spoofing (Block private networks on WAN)
- ✅ Server egress restriction (limit Internet access)

---

## Key Takeaways

1. **Default Deny**: Start with deny all, explicitly allow required traffic
2. **Guest Isolation**: Block RFC1918 on guest VLAN (critical security rule)
3. **IDS/IPS**: Suricata adds detection layer, but test thoroughly (false positives)
4. **Rule Order Matters**: Most specific → least specific, first match wins
5. **Logging is Essential**: Review logs weekly, tune rules based on alerts

**Authorization Level**: INFRASTRUCTURE + CREDENTIAL (firewall access)
**Downtime Risk**: MEDIUM (30-60 min during initial config)
**Rollback Plan**: Keep backup, disable IPS mode if issues

## References

- **OPNSense Documentation**: https://docs.opnsense.org/
- **Suricata IDS/IPS**: https://suricata.io/
- **Emerging Threats Rules**: https://rules.emergingthreats.net/
- **RFC 1918 (Private IP Ranges)**: https://www.rfc-editor.org/rfc/rfc1918.html
