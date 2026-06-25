# Few-Shot Example: NetBox DCIM Initial Setup for Small Office

**Domain:** Network Infrastructure / CMDB
**Skill Level:** Intermediate
**Pattern:** NetBox data model design and initial setup for infrastructure documentation

---

## User Query

```
Need to set up NetBox for our small office (50 devices - servers, switches, workstations). What data should I populate first? How do I structure sites, racks, devices properly?
```

---

## Exemplary Response

┌─ ROUTING ──────────────────────────────────────────────────┐
│ Role: Network Engineer / DCIM Specialist                   │
│ Confidence: HIGH (90%)                                     │
│ Modules: 21-network-infrastructure.md                     │
│ Approach: NetBox data model implementation (v3.7+)        │
└────────────────────────────────────────────────────────────┘

## NetBox Initial Setup Guide

I'll guide you through setting up NetBox as your single source of truth for infrastructure documentation.

---

## NetBox Installation (Prerequisites)

### Option 1: Docker Compose (Recommended for Small Office)

```bash
# Clone netbox-docker repository
cd /opt
sudo git clone https://github.com/netbox-community/netbox-docker.git
cd netbox-docker

# Create docker-compose.override.yml (customize settings)
cat > docker-compose.override.yml << 'EOF'
version: '3.4'
services:
  netbox:
    ports:
      - "8000:8080"
    environment:
      - SUPERUSER_NAME=admin
      - SUPERUSER_EMAIL=admin@company.local
      - SUPERUSER_PASSWORD=ChangeMe123!
      - SUPERUSER_API_TOKEN=0123456789abcdef0123456789abcdef01234567
EOF

# Start NetBox
sudo docker-compose pull
sudo docker-compose up -d

# Access: http://localhost:8000/
# Login: admin / ChangeMe123!
```

### Option 2: Manual Installation (Ubuntu)

See: https://docs.netbox.dev/en/stable/installation/

---

## NetBox Data Model Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                      NETBOX DATA MODEL                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Region (Optional)                                              │
│    ├── Site (Physical location)                                │
│    │    ├── Location (Floor, Room within site)                 │
│    │    │    ├── Rack (42U cabinet)                            │
│    │    │    │    ├── Device (Switch, Server, Firewall)        │
│    │    │    │    │    ├── Interface (ether1, GigabitEthernet0)│
│    │    │    │    │    │    └── IP Address (192.168.1.1/24)    │
│    │    │    │    │    ├── Console Port (COM1)                 │
│    │    │    │    │    ├── Power Port (PSU1, PSU2)             │
│    │    │    │    │    └── Module (Line cards, expansion)      │
│    │    │    └── Non-racked devices (Wi-Fi APs, workstations)  │
│    │    └── VLAN (L2 segmentation)                             │
│    │    └── Prefix (IP subnet: 192.168.1.0/24)                 │
│                                                                 │
│  Manufacturer → Device Type (Model: Cisco 2960, Dell R640)     │
│  Device Role (Switch, Server, Firewall)                        │
│  Platform (Cisco IOS, Linux, VMware ESXi)                      │
│  Tenant (Department, Customer)                                 │
│  Tags (prod, dev, critical, deprecated)                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Foundation Data (10-15 minutes)

### Step 1.1: Create Site

**Organization → Sites → Add**

| Field | Value | Purpose |
|-------|-------|---------|
| **Name** | HQ-Moscow | Primary site name |
| **Slug** | hq-moscow | URL-friendly identifier (auto-generated) |
| **Status** | Active | Site operational status |
| **Region** | Europe (optional) | Grouping for multi-site orgs |
| **Facility** | Office Building A | Physical location name |
| **Physical Address** | 123 Main St, Moscow, Russia, 101000 | Full address |
| **Contact Name** | John Doe | Site contact person |
| **Contact Phone** | +7 (495) 123-4567 | Contact number |
| **Contact Email** | facilities@company.com | Contact email |
| **Comments** | Main office, 3 floors, 100 employees | Notes |

**API Example** (Python):
```python
import pynetbox
nb = pynetbox.api('http://localhost:8000', token='YOUR_API_TOKEN')

site = nb.dcim.sites.create(
    name='HQ-Moscow',
    slug='hq-moscow',
    status='active',
    physical_address='123 Main St, Moscow, Russia, 101000',
    comments='Main office, 3 floors, 100 employees'
)
print(f"Created site: {site.name} (ID: {site.id})")
```

---

### Step 1.2: Create Locations (Rooms)

**Organization → Locations → Add**

| Name | Site | Parent | Description |
|------|------|--------|-------------|
| Floor-1 | HQ-Moscow | — | First floor |
| Floor-2 | HQ-Moscow | — | Second floor |
| Floor-3 | HQ-Moscow | — | Third floor |
| Server-Room | HQ-Moscow | Floor-1 | Server room (climate controlled) |
| Comms-Closet-2F | HQ-Moscow | Floor-2 | Network closet floor 2 |
| Comms-Closet-3F | HQ-Moscow | Floor-3 | Network closet floor 3 |

---

### Step 1.3: Create Manufacturers

**Devices → Manufacturers → Add**

| Name | Slug | Description |
|------|------|-------------|
| Cisco Systems | cisco-systems | Network equipment |
| Dell | dell | Servers, workstations |
| Hewlett Packard Enterprise | hpe | Servers |
| MikroTik | mikrotik | Network equipment |
| Ubiquiti | ubiquiti | Wi-Fi, switches |
| Synology | synology | NAS storage |

---

### Step 1.4: Create Device Roles

**Devices → Device Roles → Add**

| Name | Slug | Color | VM Role | Description |
|------|------|-------|---------|-------------|
| Core Switch | core-switch | Green | No | Network core layer |
| Access Switch | access-switch | Light Green | No | End-user access layer |
| Firewall | firewall | Red | No | Network security |
| Server | server | Blue | Yes | Physical servers |
| Storage | storage | Purple | No | NAS, SAN devices |
| Workstation | workstation | Gray | No | Employee PCs |
| Wi-Fi AP | wifi-ap | Orange | No | Wireless access points |

**Color Options**: Red, Pink, Orange, Yellow, Green, Cyan, Blue, Purple, Gray, Black

---

### Step 1.5: Create Platforms

**Devices → Platforms → Add**

| Name | Slug | Manufacturer | NAPALM Driver | Description |
|------|------|--------------|---------------|-------------|
| Cisco IOS | cisco-ios | Cisco Systems | ios | Cisco switches/routers |
| MikroTik RouterOS | mikrotik-routeros | MikroTik | — | MikroTik devices |
| Linux | linux | — | — | Linux servers |
| VMware ESXi | vmware-esxi | — | — | VMware hypervisor |
| Windows Server | windows-server | — | — | Windows servers |

**NAPALM Driver**: Network automation library (optional, for config management).

---

## Phase 2: Device Types (Library) (15-20 minutes)

### Step 2.1: Create Device Types (Models)

**Devices → Device Types → Add**

Example: **Cisco Catalyst 2960-24TT-L**

| Field | Value |
|-------|-------|
| **Manufacturer** | Cisco Systems |
| **Model** | Catalyst 2960-24TT-L |
| **Slug** | catalyst-2960-24tt-l |
| **Part Number** | WS-C2960-24TT-L |
| **U Height** | 1 (1U rackmount) |
| **Is Full Depth** | No |
| **Weight** | 4.1 kg |
| **Comments** | 24-port Gigabit Ethernet switch |

**Interfaces (add via Component Templates):**
- 24× GigabitEthernet (Type: 1000BASE-T)
- 2× GigabitEthernet (Type: SFP, uplink)
- 1× Console Port (Type: RJ-45)
- 2× Power Ports (Type: IEC 60320 C14)

**API Example** (bulk create device types):
```python
# Load device types from NetBox Device Type Library
# https://github.com/netbox-community/devicetype-library

import requests
import pynetbox

nb = pynetbox.api('http://localhost:8000', token='YOUR_API_TOKEN')

# Download device type JSON from GitHub
url = 'https://raw.githubusercontent.com/netbox-community/devicetype-library/master/device-types/Cisco/WS-C2960-24TT-L.json'
device_type_json = requests.get(url).json()

# Create device type in NetBox
manufacturer = nb.dcim.manufacturers.get(name='Cisco Systems')
device_type = nb.dcim.device_types.create(
    manufacturer=manufacturer.id,
    model=device_type_json['model'],
    slug=device_type_json['slug'],
    u_height=device_type_json.get('u_height', 1),
    is_full_depth=device_type_json.get('is_full_depth', False)
)

# Add interfaces
for iface in device_type_json.get('interfaces', []):
    nb.dcim.interface_templates.create(
        device_type=device_type.id,
        name=iface['name'],
        type=iface['type']
    )
```

**Pre-Built Device Types**: https://github.com/netbox-community/devicetype-library (2000+ models)

---

### Step 2.2: Common Device Types for Small Office

| Model | Manufacturer | Type | U Height | Interfaces |
|-------|--------------|------|----------|------------|
| Catalyst 2960-24TT-L | Cisco | Access Switch | 1U | 24× 1G + 2× SFP |
| CRS326-24G-2S+ | MikroTik | Access Switch | 1U | 24× 1G + 2× 10G SFP+ |
| PowerEdge R640 | Dell | Server | 1U | 4× 1G RJ-45 |
| Synology DS1621+ | Synology | NAS | Non-rack | 4× 1G RJ-45 |
| UniFi AP AC Pro | Ubiquiti | Wi-Fi AP | Non-rack | 2× 1G PoE |

---

## Phase 3: Racks & Devices (30-40 minutes)

### Step 3.1: Create Rack

**Organization → Racks → Add**

| Field | Value | Notes |
|-------|-------|-------|
| **Site** | HQ-Moscow | |
| **Location** | Server-Room | |
| **Name** | RACK-01 | Unique rack ID |
| **Facility ID** | SR-R1 (optional) | Physical label on rack |
| **Status** | Active | |
| **Type** | 4-post cabinet | |
| **Width** | 19 inches | Standard |
| **U Height** | 42 | Standard full-height rack |
| **Desc Units** | No | U1 at bottom (default) |
| **Outer Width** | 600 mm | |
| **Outer Depth** | 1000 mm | |
| **Comments** | Main server rack | |

---

### Step 3.2: Add Devices to Rack

**Devices → Devices → Add**

#### Example 1: Core Switch

| Field | Value |
|-------|-------|
| **Name** | SW-CORE-01 |
| **Device Role** | Core Switch |
| **Device Type** | Cisco Catalyst 2960-24TT-L (or CRS326-24G-2S+) |
| **Site** | HQ-Moscow |
| **Location** | Server-Room |
| **Rack** | RACK-01 |
| **Position** | 40 (U40, near top) |
| **Face** | Front |
| **Status** | Active |
| **Tenant** | IT Department (optional) |
| **Platform** | Cisco IOS (or MikroTik RouterOS) |
| **Serial Number** | FOC1234ABCD |
| **Asset Tag** | IT-SW-001 |
| **Primary IPv4** | 192.168.1.254/24 (management IP) |
| **Comments** | Core layer switch, connects all access switches |

**API Example**:
```python
device = nb.dcim.devices.create(
    name='SW-CORE-01',
    device_type=nb.dcim.device_types.get(model='Catalyst 2960-24TT-L').id,
    device_role=nb.dcim.device_roles.get(name='Core Switch').id,
    site=nb.dcim.sites.get(name='HQ-Moscow').id,
    location=nb.dcim.locations.get(name='Server-Room').id,
    rack=nb.dcim.racks.get(name='RACK-01').id,
    position=40,
    face='front',
    status='active',
    serial='FOC1234ABCD',
    asset_tag='IT-SW-001',
    comments='Core layer switch'
)
```

#### Example 2: Server

| Field | Value |
|-------|-------|
| **Name** | SRV-DC-01 |
| **Device Role** | Server |
| **Device Type** | Dell PowerEdge R640 |
| **Rack** | RACK-01 |
| **Position** | 30 (U30-U31, 2U server) |
| **Serial Number** | SVC1234567 |
| **Primary IPv4** | 192.168.30.10/24 (server VLAN) |
| **Platform** | VMware ESXi (or Linux) |
| **Comments** | Domain controller, DNS, DHCP |

#### Example 3: Non-Racked Device (Workstation)

| Field | Value |
|-------|-------|
| **Name** | WS-FIN-01 |
| **Device Role** | Workstation |
| **Device Type** | Dell OptiPlex 7090 (create custom device type if not in library) |
| **Site** | HQ-Moscow |
| **Location** | Floor-2 |
| **Rack** | — (leave blank for non-racked) |
| **Serial Number** | WS123456 |
| **Primary IPv4** | 192.168.10.101/24 (office VLAN) |
| **Comments** | Finance dept, Jane Doe's workstation |

---

## Phase 4: IP Address Management (IPAM) (20-30 minutes)

### Step 4.1: Create VLANs

**IPAM → VLANs → Add**

| VLAN ID | Name | Site | Status | Description |
|---------|------|------|--------|-------------|
| 1 | Management | HQ-Moscow | Active | Device management |
| 10 | Office | HQ-Moscow | Active | Employee workstations |
| 20 | Guests | HQ-Moscow | Active | Guest Wi-Fi |
| 30 | Servers | HQ-Moscow | Active | Internal servers |

---

### Step 4.2: Create Prefixes (Subnets)

**IPAM → Prefixes → Add**

| Prefix | VLAN | Site | Status | Role | Description |
|--------|------|------|--------|------|-------------|
| 192.168.1.0/24 | Management (1) | HQ-Moscow | Active | — | Management subnet |
| 192.168.10.0/24 | Office (10) | HQ-Moscow | Active | — | Office subnet |
| 192.168.20.0/24 | Guests (20) | HQ-Moscow | Active | — | Guest Wi-Fi |
| 192.168.30.0/24 | Servers (30) | HQ-Moscow | Active | — | Server subnet |

**Prefix Roles** (optional, create in IPAM → Roles):
- Infrastructure (management, transit)
- Production (office, servers)
- Development (dev environment)
- Guest (guest Wi-Fi)

---

### Step 4.3: Assign IP Addresses to Devices

**IPAM → IP Addresses → Add**

#### Example 1: Core Switch Management IP

| Address | Status | VRF | DNS Name | Interface | Description |
|---------|--------|-----|----------|-----------|-------------|
| 192.168.1.254/24 | Active | — | sw-core-01.company.local | SW-CORE-01 → Management1 | Core switch management |

**Link IP to Device:**
1. Create IP address: `192.168.1.254/24`
2. Go to **Devices → SW-CORE-01 → Interfaces**
3. Add interface: `Management1` (type: 1000BASE-T)
4. Assign IP: Select `192.168.1.254/24` from dropdown

**API Example**:
```python
# Create interface
interface = nb.dcim.interfaces.create(
    device=device.id,
    name='Management1',
    type='1000base-t',
    enabled=True
)

# Create IP address
ip = nb.ipam.ip_addresses.create(
    address='192.168.1.254/24',
    status='active',
    dns_name='sw-core-01.company.local',
    assigned_object_type='dcim.interface',
    assigned_object_id=interface.id
)

# Set as primary IP
device.primary_ip4 = ip.id
device.save()
```

#### Example 2: Server IPs

| Address | Device | Interface | DNS Name |
|---------|--------|-----------|----------|
| 192.168.30.10/24 | SRV-DC-01 | eth0 | dc01.company.local |
| 192.168.30.11/24 | SRV-FILE-01 | eth0 | fileserver.company.local |
| 192.168.30.12/24 | NAS-01 | LAN1 | nas.company.local |

---

## Phase 5: Connections & Cabling (10-15 minutes)

### Step 5.1: Create Cables

**Devices → Cables → Add**

Represent physical connections between devices.

#### Example 1: Access Switch Uplink to Core Switch

| Termination A | Termination B | Type | Length | Color | Label |
|---------------|---------------|------|--------|-------|-------|
| SW-ACCESS-01 → GigabitEthernet0/24 | SW-CORE-01 → GigabitEthernet0/1 | Cat6 | 5 m | Blue | CBL-001 |

**API Example**:
```python
# Get interfaces
iface_a = nb.dcim.interfaces.get(device=sw_access_01.id, name='GigabitEthernet0/24')
iface_b = nb.dcim.interfaces.get(device=sw_core_01.id, name='GigabitEthernet0/1')

# Create cable
cable = nb.dcim.cables.create(
    a_terminations=[{'object_type': 'dcim.interface', 'object_id': iface_a.id}],
    b_terminations=[{'object_type': 'dcim.interface', 'object_id': iface_b.id}],
    type='cat6',
    length=5,
    length_unit='m',
    color='0000ff',  # Blue (hex color code)
    label='CBL-001'
)
```

#### Example 2: Server to Switch

| Termination A | Termination B | Type | Length | Label |
|---------------|---------------|------|--------|-------|
| SRV-DC-01 → eth0 | SW-CORE-01 → GigabitEthernet0/10 | Cat6a | 3 m | CBL-SRV-DC-01 |

---

## Phase 6: Custom Fields & Tags (Optional, 10 minutes)

### Custom Fields

**Customization → Custom Fields → Add**

Extend NetBox data model with organization-specific fields.

#### Example: Warranty Expiration Date

| Field | Value |
|-------|-------|
| **Type** | Date |
| **Content Type** | dcim.device |
| **Name** | warranty_expiration |
| **Label** | Warranty Expiration |
| **Required** | No |
| **Default** | — |
| **Help Text** | Date when manufacturer warranty expires |

**Usage**: Go to any device → Custom Fields → Set `warranty_expiration = 2028-12-31`

---

### Tags

**Organization → Tags → Add**

Use tags for filtering, grouping, automation workflows.

| Name | Slug | Color | Description |
|------|------|-------|-------------|
| Production | production | Green | Production environment |
| Development | development | Orange | Dev/test environment |
| Critical | critical | Red | Critical infrastructure (24/7 monitoring) |
| Deprecated | deprecated | Gray | To be decommissioned |
| Under Warranty | under-warranty | Blue | Currently under manufacturer warranty |

**Apply Tags**: Go to device → Tags → Select tags

---

## Phase 7: Reporting & Validation (5 minutes)

### Device Inventory Report

**Devices → Devices**

Filters:
- Site: HQ-Moscow
- Status: Active
- Export as: CSV (for Excel)

**Columns**:
- Name
- Device Type
- Serial Number
- Rack
- Position
- Primary IP
- Status

### IP Address Utilization

**IPAM → Prefixes**

View: `192.168.10.0/24`
- **Utilization**: 45/254 (18%)
- **Available IPs**: 209

### Cabling Report

**Devices → Cables**

Filter by:
- Status: Connected
- Type: Cat6
- Export: CSV (for cable labeling)

---

## Phase 8: API Integration & Automation

### Python Script: Bulk Import Workstations

```python
import pynetbox
import csv

nb = pynetbox.api('http://localhost:8000', token='YOUR_API_TOKEN')

# Device Type: Dell OptiPlex 7090 (pre-created)
device_type = nb.dcim.device_types.get(slug='dell-optiplex-7090')
device_role = nb.dcim.device_roles.get(slug='workstation')
site = nb.dcim.sites.get(slug='hq-moscow')
location = nb.dcim.locations.get(slug='floor-2')

# Read from CSV: hostname,serial,ip,mac
with open('workstations.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Create device
        device = nb.dcim.devices.create(
            name=row['hostname'],
            device_type=device_type.id,
            device_role=device_role.id,
            site=site.id,
            location=location.id,
            serial=row['serial'],
            status='active'
        )

        # Create interface
        interface = nb.dcim.interfaces.create(
            device=device.id,
            name='eth0',
            type='1000base-t',
            mac_address=row['mac']
        )

        # Assign IP
        ip = nb.ipam.ip_addresses.create(
            address=f"{row['ip']}/24",
            status='active',
            assigned_object_type='dcim.interface',
            assigned_object_id=interface.id
        )

        # Set primary IP
        device.primary_ip4 = ip.id
        device.save()

        print(f"Created: {device.name} ({row['ip']})")
```

---

## Best Practices

1. **Start Small**: Populate core infrastructure first (racks, switches, servers), then expand
2. **Consistent Naming**: Use naming conventions (e.g., `SW-CORE-01`, `SRV-DC-01`)
3. **Document Everything**: Use Comments fields liberally
4. **Use Tags**: For bulk operations, filtering, automation
5. **Keep Updated**: NetBox is only useful if it reflects reality — update as you make changes
6. **API-First**: Automate bulk operations with Python scripts
7. **Regular Audits**: Monthly review to verify data accuracy (compare with reality)

---

## Maintenance Workflow

### Weekly Tasks
- Add new devices as they're deployed
- Update cabling changes
- Review IP address allocations

### Monthly Tasks
- Audit device inventory (physical walk-through)
- Update firmware versions (custom field)
- Review decommissioned devices (change status to "Decommissioned")

### Quarterly Tasks
- Export full inventory for asset management
- Review warranty expirations
- Clean up deprecated devices

---

## Key Takeaways

1. **NetBox is your Source of Truth**: All infrastructure documentation in one place
2. **Start with Foundation**: Sites → Racks → Device Types → Devices → IPs
3. **API Automation**: Use Python for bulk operations (save hours)
4. **Keep it Current**: Outdated documentation is worse than no documentation
5. **Integrate with Monitoring**: Zabbix, Prometheus can query NetBox API for auto-discovery

**Authorization Level**: MODIFY (data entry) + ANALYZE (reporting)
**Time Investment**: 2-3 hours initial setup, 1 hour/week maintenance
**ROI**: Saves 5-10 hours/month in manual documentation, troubleshooting

## References

- **NetBox Documentation**: https://docs.netbox.dev/
- **NetBox Device Type Library**: https://github.com/netbox-community/devicetype-library
- **PyNetBox (Python API)**: https://pynetbox.readthedocs.io/
- **NetBox Community**: https://github.com/netbox-community/netbox
