# Few-Shot Example: MikroTik VLAN Configuration for Office Network

**Domain:** Network Infrastructure
**Skill Level:** Intermediate
**Pattern:** MikroTik bridge VLAN setup with inter-VLAN routing and firewall

---

## User Query

```
Need to set up VLANs on MikroTik CRS326-24G-2S+ switch. 3 VLANs: Office (VLAN 10), Guests (VLAN 20), Servers (VLAN 30). How do I configure this properly with DHCP and firewall rules?
```

---

## Exemplary Response

┌─ ROUTING ──────────────────────────────────────────────────┐
│ Role: Network Engineer                                     │
│ Confidence: HIGH (93%)                                     │
│ Modules: 21-network-infrastructure.md                     │
│ Approach: Bridge VLAN filtering + Router-on-a-Stick       │
└────────────────────────────────────────────────────────────┘

## MikroTik VLAN Configuration Guide

I'll create a complete VLAN setup for your MikroTik CRS326 with proper segmentation, DHCP, and security.

---

## Network Design

### Topology

```
                    INTERNET
                       │
                  [ether1 WAN]
                       │
         ┌─────────────┴──────────────┐
         │  MikroTik CRS326-24G-2S+   │
         │  (L3 Switch + Router)      │
         └─┬─────┬─────┬──────────────┘
           │     │     │
   VLAN 10 │     │     │ VLAN 30
   (Office)│     │     │ (Servers)
           │     │     │
      [ether2-13]│     [ether14-16]
               │
           VLAN 20
           (Guests)
               │
          [ether17-24]
```

### VLAN Plan

| VLAN ID | Name | Subnet | Gateway | DHCP Pool | Ports | Purpose |
|---------|------|--------|---------|-----------|-------|---------|
| 1 | Management | 192.168.88.0/24 | 192.168.88.1 | .10-.50 | ether1 (WAN), bridge | Device mgmt |
| 10 | Office | 192.168.10.0/24 | 192.168.10.1 | .100-.200 | ether2-ether13 | Employee workstations |
| 20 | Guests | 192.168.20.0/24 | 192.168.20.1 | .100-.200 | ether17-ether24 | Guest Wi-Fi, isolated |
| 30 | Servers | 192.168.30.0/24 | 192.168.30.1 | Static only | ether14-ether16 | Internal servers, NAS |

---

## Step 1: Initial Configuration (via WinBox)

### Connect to Device

```bash
# Connect via MAC address (if IP unknown)
# Use WinBox: Neighbors tab → Click device MAC

# OR via SSH (if default IP 192.168.88.1 is accessible)
ssh admin@192.168.88.1
# Default password: <empty> (press Enter)
```

### Reset to Factory Defaults (OPTIONAL)

⚠️ **WARNING**: This erases all configuration!

```routeros
# Via CLI
/system reset-configuration no-defaults=yes skip-backup=yes

# OR via WinBox
# System → Reset Configuration → [x] No Default Configuration → Reset
```

---

## Step 2: Create Bridge (L2 Switch Base)

```routeros
# Create bridge for all ports
/interface bridge
add name=bridge-vlan protocol-mode=rstp vlan-filtering=no comment="Main bridge - VLAN-aware"

# CRITICAL: Set vlan-filtering=no initially (enable AFTER all config)
# Reason: Prevents lockout during configuration
```

---

## Step 3: Add Ports to Bridge

```routeros
# Add all LAN ports to bridge (ether2-ether24)
# ether1 = WAN (do NOT add to bridge)

/interface bridge port
add bridge=bridge-vlan interface=ether2 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether3 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether4 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether5 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether6 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether7 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether8 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether9 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether10 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether11 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether12 comment="VLAN 10 - Office"
add bridge=bridge-vlan interface=ether13 comment="VLAN 10 - Office"

add bridge=bridge-vlan interface=ether14 comment="VLAN 30 - Servers"
add bridge=bridge-vlan interface=ether15 comment="VLAN 30 - Servers"
add bridge=bridge-vlan interface=ether16 comment="VLAN 30 - Servers"

add bridge=bridge-vlan interface=ether17 comment="VLAN 20 - Guests"
add bridge=bridge-vlan interface=ether18 comment="VLAN 20 - Guests"
add bridge=bridge-vlan interface=ether19 comment="VLAN 20 - Guests"
add bridge=bridge-vlan interface=ether20 comment="VLAN 20 - Guests"
add bridge=bridge-vlan interface=ether21 comment="VLAN 20 - Guests"
add bridge=bridge-vlan interface=ether22 comment="VLAN 20 - Guests"
add bridge=bridge-vlan interface=ether23 comment="VLAN 20 - Guests"
add bridge=bridge-vlan interface=ether24 comment="VLAN 20 - Guests"

# Add bridge itself (for inter-VLAN routing)
add bridge=bridge-vlan interface=bridge-vlan pvid=1 comment="Bridge CPU port"
```

---

## Step 4: Create VLAN Interfaces

```routeros
# VLAN interfaces for L3 routing (one per VLAN)

/interface vlan
add interface=bridge-vlan name=vlan-office vlan-id=10 comment="VLAN 10 - Office"
add interface=bridge-vlan name=vlan-guests vlan-id=20 comment="VLAN 20 - Guests"
add interface=bridge-vlan name=vlan-servers vlan-id=30 comment="VLAN 30 - Servers"
add interface=bridge-vlan name=vlan-mgmt vlan-id=1 comment="VLAN 1 - Management"
```

---

## Step 5: Assign IP Addresses (Gateways)

```routeros
# Assign IP addresses to VLAN interfaces (these become default gateways for VLANs)

/ip address
add address=192.168.10.1/24 interface=vlan-office comment="Office Gateway"
add address=192.168.20.1/24 interface=vlan-guests comment="Guests Gateway"
add address=192.168.30.1/24 interface=vlan-servers comment="Servers Gateway"
add address=192.168.88.1/24 interface=vlan-mgmt comment="Management"

# WAN interface (ether1) - replace with your ISP-provided IP or DHCP client
add address=10.0.0.2/24 interface=ether1 comment="WAN - ISP provided"
# OR for DHCP from ISP:
# /ip dhcp-client add interface=ether1 disabled=no
```

---

## Step 6: Configure Bridge VLAN Table

```routeros
# Define which VLANs are allowed on which ports

/interface bridge vlan
# VLAN 1 (Management) - tagged on bridge (CPU), untagged nowhere
add bridge=bridge-vlan tagged=bridge-vlan vlan-ids=1 comment="Management VLAN"

# VLAN 10 (Office) - tagged on bridge, untagged on ether2-ether13
add bridge=bridge-vlan tagged=bridge-vlan untagged=ether2,ether3,ether4,ether5,ether6,ether7,ether8,ether9,ether10,ether11,ether12,ether13 vlan-ids=10 comment="Office VLAN"

# VLAN 20 (Guests) - tagged on bridge, untagged on ether17-ether24
add bridge=bridge-vlan tagged=bridge-vlan untagged=ether17,ether18,ether19,ether20,ether21,ether22,ether23,ether24 vlan-ids=20 comment="Guests VLAN"

# VLAN 30 (Servers) - tagged on bridge, untagged on ether14-ether16
add bridge=bridge-vlan tagged=bridge-vlan untagged=ether14,ether15,ether16 vlan-ids=30 comment="Servers VLAN"
```

---

## Step 7: Set Port VLAN IDs (PVID)

```routeros
# Set PVID (default VLAN for untagged traffic) on each port

/interface bridge port
# VLAN 10 ports
set [find interface=ether2] pvid=10
set [find interface=ether3] pvid=10
set [find interface=ether4] pvid=10
set [find interface=ether5] pvid=10
set [find interface=ether6] pvid=10
set [find interface=ether7] pvid=10
set [find interface=ether8] pvid=10
set [find interface=ether9] pvid=10
set [find interface=ether10] pvid=10
set [find interface=ether11] pvid=10
set [find interface=ether12] pvid=10
set [find interface=ether13] pvid=10

# VLAN 20 ports
set [find interface=ether17] pvid=20
set [find interface=ether18] pvid=20
set [find interface=ether19] pvid=20
set [find interface=ether20] pvid=20
set [find interface=ether21] pvid=20
set [find interface=ether22] pvid=20
set [find interface=ether23] pvid=20
set [find interface=ether24] pvid=20

# VLAN 30 ports
set [find interface=ether14] pvid=30
set [find interface=ether15] pvid=30
set [find interface=ether16] pvid=30

# Bridge CPU port (management VLAN 1)
set [find interface=bridge-vlan] pvid=1
```

---

## Step 8: Enable VLAN Filtering

⚠️ **CRITICAL**: Do this ONLY after all VLAN config is complete!

```routeros
# Enable VLAN filtering on bridge
/interface bridge
set bridge-vlan vlan-filtering=yes

# Test connectivity IMMEDIATELY after enabling
# If you lose access, reboot device (will load previous config if not saved)
```

**Test Checklist:**
- [ ] Can ping 192.168.88.1 from management VLAN?
- [ ] Can access WinBox/WebFig?
- [ ] If YES → `/system backup save name=vlan-config` (backup)
- [ ] If NO → Reboot device, review steps 6-7

---

## Step 9: Configure DHCP Servers

```routeros
# DHCP Server for VLAN 10 (Office)
/ip pool
add name=pool-office ranges=192.168.10.100-192.168.10.200 comment="Office DHCP Pool"

/ip dhcp-server
add address-pool=pool-office interface=vlan-office name=dhcp-office lease-time=1d disabled=no

/ip dhcp-server network
add address=192.168.10.0/24 gateway=192.168.10.1 dns-server=8.8.8.8,8.8.4.4 comment="Office Network"

# DHCP Server for VLAN 20 (Guests)
/ip pool
add name=pool-guests ranges=192.168.20.100-192.168.20.200 comment="Guests DHCP Pool"

/ip dhcp-server
add address-pool=pool-guests interface=vlan-guests name=dhcp-guests lease-time=2h disabled=no

/ip dhcp-server network
add address=192.168.20.0/24 gateway=192.168.20.1 dns-server=8.8.8.8,8.8.4.4 comment="Guests Network"

# VLAN 30 (Servers) - NO DHCP (static IPs only)
# Manually assign IPs: 192.168.30.10, 192.168.30.11, etc.
```

---

## Step 10: NAT Configuration (Internet Access)

```routeros
# Masquerade (SNAT) for outbound traffic
/ip firewall nat
add chain=srcnat out-interface=ether1 action=masquerade comment="NAT to Internet"

# Port forwarding example (HTTPS to server in VLAN 30)
# Forward external port 443 → 192.168.30.10:443
add chain=dstnat dst-port=443 protocol=tcp in-interface=ether1 \
    action=dst-nat to-addresses=192.168.30.10 to-ports=443 \
    comment="HTTPS to Web Server"
```

---

## Step 11: Firewall Rules (Inter-VLAN Security)

### Default Policy: DENY

```routeros
# Input chain (traffic TO the router itself)
/ip firewall filter
add chain=input action=accept connection-state=established,related comment="Allow established"
add chain=input action=accept in-interface=vlan-mgmt comment="Allow mgmt VLAN"
add chain=input action=accept in-interface=vlan-office protocol=icmp comment="Allow ping from Office"
add chain=input action=drop comment="Drop all other input"

# Forward chain (traffic BETWEEN VLANs)
add chain=forward action=accept connection-state=established,related comment="Allow established"
add chain=forward action=accept in-interface=vlan-office out-interface=ether1 comment="Office → Internet"
add chain=forward action=accept in-interface=vlan-guests out-interface=ether1 comment="Guests → Internet"
add chain=forward action=accept in-interface=vlan-office out-interface=vlan-servers comment="Office → Servers"

# ISOLATE Guests from internal networks
add chain=forward action=drop in-interface=vlan-guests out-interface=vlan-office comment="Block Guests → Office"
add chain=forward action=drop in-interface=vlan-guests out-interface=vlan-servers comment="Block Guests → Servers"

# Drop all other forward traffic (implicit deny)
add chain=forward action=drop comment="Drop all other forward"
```

### Firewall Rules Summary

| Source VLAN | Destination | Action | Rule |
|-------------|-------------|--------|------|
| Office (10) | Internet | **ALLOW** | Employees need internet |
| Office (10) | Servers (30) | **ALLOW** | Access internal resources |
| Office (10) | Guests (20) | **DENY** | No reason to access guest VLAN |
| Guests (20) | Internet | **ALLOW** | Internet-only access |
| Guests (20) | Office (10) | **DENY** | Security: isolate guests |
| Guests (20) | Servers (30) | **DENY** | Security: no internal access |
| Servers (30) | Internet | **DENY** (optional) | Restrict server internet access |
| Servers (30) | Office (10) | **ALLOW** (for responses) | Stateful firewall allows return traffic |

---

## Step 12: DNS Configuration

```routeros
# Set DNS servers (for router itself)
/ip dns
set servers=8.8.8.8,8.8.4.4 allow-remote-requests=yes

# allow-remote-requests=yes → Router acts as DNS forwarder for VLANs
```

---

## Step 13: Management Access

```routeros
# Allow SSH and WinBox only from Office and Management VLANs
/ip service
set telnet disabled=yes
set ftp disabled=yes
set www disabled=no address=192.168.10.0/24,192.168.88.0/24
set ssh disabled=no port=22 address=192.168.10.0/24,192.168.88.0/24
set winbox disabled=no address=192.168.10.0/24,192.168.88.0/24

# Disable unused services
set api disabled=yes
set api-ssl disabled=yes
```

---

## Step 14: Verification & Testing

### Test Connectivity

```routeros
# From Office VLAN (192.168.10.x):
/ping 192.168.10.1          # Gateway (should work)
/ping 8.8.8.8               # Internet (should work)
/ping 192.168.30.10         # Server (should work)
/ping 192.168.20.100        # Guest VLAN (should FAIL - blocked by firewall)

# From Guests VLAN (192.168.20.x):
/ping 192.168.20.1          # Gateway (should work)
/ping 8.8.8.8               # Internet (should work)
/ping 192.168.10.100        # Office VLAN (should FAIL - blocked)
/ping 192.168.30.10         # Servers VLAN (should FAIL - blocked)
```

### Check VLAN Membership

```routeros
# View bridge VLAN table
/interface bridge vlan print

# Output should show:
# VLAN 1: tagged on bridge-vlan
# VLAN 10: tagged on bridge-vlan, untagged on ether2-ether13
# VLAN 20: tagged on bridge-vlan, untagged on ether17-ether24
# VLAN 30: tagged on bridge-vlan, untagged on ether14-ether16
```

### Monitor Traffic

```routeros
# Watch firewall rules hit count
/ip firewall filter print stats

# View DHCP leases
/ip dhcp-server lease print

# Check interface stats
/interface print stats
```

---

## Step 15: Backup Configuration

```routeros
# Create backup
/system backup save name=vlan-config-$(date +%Y%m%d)

# Export configuration (human-readable script)
/export file=vlan-config-export

# Download backups via WinBox: Files → Right-click → Download
```

---

## Troubleshooting

### Issue 1: Lost Access After Enabling VLAN Filtering

**Symptoms**: Cannot ping 192.168.88.1, WinBox disconnected.

**Cause**: Bridge CPU port not properly configured in VLAN table.

**Fix**:
1. Reboot device (hold reset button 5-10 sec while booting to load backup)
2. Verify Step 6: VLAN 1 must be **tagged** on bridge-vlan
3. Verify Step 7: Bridge port PVID must be set to 1

### Issue 2: No Internet from VLANs

**Symptoms**: Cannot ping 8.8.8.8 from Office/Guests VLAN.

**Diagnosis**:
```routeros
# Check if NAT rule exists
/ip firewall nat print

# Check if default route exists
/ip route print

# Check DNS
/ip dns print
/ping 8.8.8.8                # Test by IP
/ping google.com             # Test by hostname (requires DNS)
```

**Fix**:
```routeros
# Add default route (if missing)
/ip route add dst-address=0.0.0.0/0 gateway=10.0.0.1 (replace with ISP gateway)

# Verify NAT rule (Step 10)
```

### Issue 3: Guests Can Access Internal Networks

**Symptoms**: From 192.168.20.x can ping 192.168.10.x.

**Cause**: Firewall rules not blocking inter-VLAN traffic.

**Fix**: Verify Step 11, ensure drop rules for `vlan-guests → vlan-office` exist:
```routeros
/ip firewall filter
add chain=forward action=drop in-interface=vlan-guests out-interface=vlan-office
add chain=forward action=drop in-interface=vlan-guests out-interface=vlan-servers
```

### Issue 4: DHCP Not Working on VLANs

**Symptoms**: Clients get 169.254.x.x (APIPA) address.

**Diagnosis**:
```routeros
# Check DHCP server status
/ip dhcp-server print

# Check if interface is correct
/ip dhcp-server print detail
```

**Fix**:
```routeros
# Ensure DHCP server is enabled and bound to correct VLAN interface
/ip dhcp-server set dhcp-office interface=vlan-office disabled=no
```

---

## Security Best Practices

1. **Change Default Password**
   ```routeros
   /user set admin password=StrongPassword123!
   ```

2. **Disable Unused Services**
   ```routeros
   /ip service set telnet,ftp,api,api-ssl disabled=yes
   ```

3. **Limit Management Access**
   ```routeros
   /ip service set ssh,winbox,www address=192.168.10.0/24,192.168.88.0/24
   ```

4. **Enable Firewall Logging** (for audit)
   ```routeros
   /ip firewall filter
   add chain=forward action=log log-prefix="FW-DROP" comment="Log dropped packets"
   add chain=forward action=drop
   ```

5. **Regular Backups** (weekly automated)
   ```routeros
   /system scheduler
   add name=weekly-backup on-event="/system backup save name=auto-backup" \
       start-time=03:00:00 interval=7d comment="Weekly config backup"
   ```

---

## Configuration Summary

### Complete Script (Copy-Paste)

```routeros
# MikroTik VLAN Configuration Script
# Device: CRS326-24G-2S+
# Date: 2026-02-06

# Step 1: Create bridge
/interface bridge add name=bridge-vlan protocol-mode=rstp vlan-filtering=no

# Step 2: Add ports to bridge
/interface bridge port
add bridge=bridge-vlan interface=ether2 pvid=10 comment="Office"
add bridge=bridge-vlan interface=ether3 pvid=10
add bridge=bridge-vlan interface=ether4 pvid=10
add bridge=bridge-vlan interface=ether5 pvid=10
add bridge=bridge-vlan interface=ether6 pvid=10
add bridge=bridge-vlan interface=ether7 pvid=10
add bridge=bridge-vlan interface=ether8 pvid=10
add bridge=bridge-vlan interface=ether9 pvid=10
add bridge=bridge-vlan interface=ether10 pvid=10
add bridge=bridge-vlan interface=ether11 pvid=10
add bridge=bridge-vlan interface=ether12 pvid=10
add bridge=bridge-vlan interface=ether13 pvid=10
add bridge=bridge-vlan interface=ether14 pvid=30 comment="Servers"
add bridge=bridge-vlan interface=ether15 pvid=30
add bridge=bridge-vlan interface=ether16 pvid=30
add bridge=bridge-vlan interface=ether17 pvid=20 comment="Guests"
add bridge=bridge-vlan interface=ether18 pvid=20
add bridge=bridge-vlan interface=ether19 pvid=20
add bridge=bridge-vlan interface=ether20 pvid=20
add bridge=bridge-vlan interface=ether21 pvid=20
add bridge=bridge-vlan interface=ether22 pvid=20
add bridge=bridge-vlan interface=ether23 pvid=20
add bridge=bridge-vlan interface=ether24 pvid=20
add bridge=bridge-vlan interface=bridge-vlan pvid=1

# Step 3: Create VLAN interfaces
/interface vlan
add interface=bridge-vlan name=vlan-mgmt vlan-id=1
add interface=bridge-vlan name=vlan-office vlan-id=10
add interface=bridge-vlan name=vlan-guests vlan-id=20
add interface=bridge-vlan name=vlan-servers vlan-id=30

# Step 4: Assign IPs
/ip address
add address=192.168.88.1/24 interface=vlan-mgmt
add address=192.168.10.1/24 interface=vlan-office
add address=192.168.20.1/24 interface=vlan-guests
add address=192.168.30.1/24 interface=vlan-servers

# Step 5: Bridge VLAN table
/interface bridge vlan
add bridge=bridge-vlan tagged=bridge-vlan vlan-ids=1
add bridge=bridge-vlan tagged=bridge-vlan untagged=ether2,ether3,ether4,ether5,ether6,ether7,ether8,ether9,ether10,ether11,ether12,ether13 vlan-ids=10
add bridge=bridge-vlan tagged=bridge-vlan untagged=ether17,ether18,ether19,ether20,ether21,ether22,ether23,ether24 vlan-ids=20
add bridge=bridge-vlan tagged=bridge-vlan untagged=ether14,ether15,ether16 vlan-ids=30

# Step 6: Enable VLAN filtering (LAST STEP!)
/interface bridge set bridge-vlan vlan-filtering=yes

# Step 7: DHCP
/ip pool
add name=pool-office ranges=192.168.10.100-192.168.10.200
add name=pool-guests ranges=192.168.20.100-192.168.20.200

/ip dhcp-server
add address-pool=pool-office interface=vlan-office name=dhcp-office disabled=no
add address-pool=pool-guests interface=vlan-guests name=dhcp-guests disabled=no

/ip dhcp-server network
add address=192.168.10.0/24 gateway=192.168.10.1 dns-server=8.8.8.8,8.8.4.4
add address=192.168.20.0/24 gateway=192.168.20.1 dns-server=8.8.8.8,8.8.4.4

# Step 8: NAT
/ip firewall nat
add chain=srcnat out-interface=ether1 action=masquerade

# Step 9: Firewall
/ip firewall filter
add chain=input action=accept connection-state=established,related
add chain=input action=accept in-interface=vlan-mgmt
add chain=input action=drop
add chain=forward action=accept connection-state=established,related
add chain=forward action=accept in-interface=vlan-office out-interface=ether1
add chain=forward action=accept in-interface=vlan-guests out-interface=ether1
add chain=forward action=accept in-interface=vlan-office out-interface=vlan-servers
add chain=forward action=drop in-interface=vlan-guests out-interface=vlan-office
add chain=forward action=drop in-interface=vlan-guests out-interface=vlan-servers
add chain=forward action=drop

# Step 10: DNS
/ip dns set servers=8.8.8.8,8.8.4.4 allow-remote-requests=yes

# Step 11: Secure services
/ip service set telnet,ftp,api,api-ssl disabled=yes
/ip service set ssh,winbox,www address=192.168.10.0/24,192.168.88.0/24

# Step 12: Backup
/system backup save name=vlan-initial-config
```

---

## Key Takeaways

1. **VLAN Filtering**: Enable ONLY after all config is complete (prevents lockout)
2. **Bridge VLAN Table**: Defines which VLANs are allowed on which ports
3. **PVID**: Sets default VLAN for untagged traffic on each port
4. **Inter-VLAN Routing**: Requires VLAN interfaces with IP addresses
5. **Firewall**: Default DENY all, explicitly ALLOW required traffic

**Authorization Level**: INFRASTRUCTURE (network changes)
**Downtime Risk**: MEDIUM (15-30 min during configuration)
**Rollback Plan**: Reboot device to load previous config (if not saved)

## References

- **MikroTik VLAN Guide**: https://help.mikrotik.com/docs/display/ROS/Bridging+and+Switching
- **Bridge VLAN Filtering**: https://wiki.mikrotik.com/wiki/Manual:Bridge_VLAN_Table
- **CRS326 Manual**: https://mikrotik.com/product/crs326_24g_2s_plus_rm
