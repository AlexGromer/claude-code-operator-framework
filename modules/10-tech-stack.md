# Module 10: Technology Stack — Our Choices

Decisions only. Claude knows what each tool does — listed here is what WE use, what we DON'T, and why.

---

## Infrastructure & Virtualization

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| Hypervisor | Proxmox VE | VMware, Hyper-V | KVM+LXC, self-hosted |
| Backup | Proxmox Backup Server | Veeam, Bacula | Integrated with Proxmox |
| Mail security | Proxmox Mail Gateway | SpamAssassin standalone | Pre-MTA deployment |
| Bare metal IaC | Tinkerbell | MAAS, Cobbler | CNCF, PXE declarative |
| Private cloud | — (Proxmox sufficient) | OpenStack, CloudStack | Complexity not justified |
| Image building | Packer | Manual snapshots | Multi-format AMI/OVA/Docker |

---

## IaC & Configuration Management

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| IaC primary | Terraform / OpenTofu | Pulumi, Crossplane | OpenTofu = FOSS fallback |
| Config management | Ansible | Puppet, Chef, SaltStack | Agentless, SSH-based |
| Provisioning | Foreman | Digital Rebar | Ansible integration |
| Repo management | Pulp 3 | Nexus, Artifactory | RPM/DEB/Container/Ansible |

---

## CI/CD & GitOps

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| CI/CD | GitLab CI | Jenkins, GitHub Actions | Self-hosted, integrated |
| GitOps | ArgoCD | Flux, Fleet | UI preferred |
| Container registry | Harbor | GitLab Registry | Enterprise features |
| Artifact repo | Pulp 3 | Nexus | See IaC section |

---

## Containers & Orchestration

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| Container runtime | Docker + Podman | CRI-O | Docker default, Podman rootless |
| K8s distribution | K3s (edge/dev), K8s (prod) | K0s, Deckhouse, Nomad | K3s single binary, <100MB |
| K8s management | Rancher | OpenShift | Multi-cluster UI |
| K8s packaging | Helm + Helmfile | Kustomize, Timoni | Helmfile for multi-env GitOps |
| Service mesh | Cilium | Istio, Linkerd | eBPF-based, performance |

---

## Identity & Access Management

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| Linux IdM | FreeIPA | 389 Directory, OpenLDAP | Kerberos+LDAP+DNS+CA |
| SSO / OIDC | Keycloak | Authentik, Dex | Primary SSO platform |
| Auth proxy (simple) | Authelia | — | For lightweight 2FA |
| Zero-trust access | Teleport | Bastion hosts | SSH+K8s+DB unified |
| Secrets | HashiCorp Vault | SOPS, age | Dynamic secrets, PKI |
| Team passwords | Passbolt | Bitwarden (self-hosted) | GPG-based, audit logs |

---

## Networking

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| VPN | WireGuard | OpenVPN | Performance; OpenVPN for legacy compat |
| Mesh VPN (self-hosted) | Headscale | Tailscale SaaS | FOSS Tailscale controller |
| Circumvention | VLESS/XTLS (Xray) | — | Russia-specific need |
| Reverse proxy | Nginx | Traefik, Caddy | Traefik for K8s auto-discovery |
| Load balancer | HAProxy | Envoy standalone | L4/L7; Envoy is Istio data plane |
| Firewall / router | MikroTik RouterOS | OPNSense | Hardware + BGP/OSPF |
| PKI | step-ca (Smallstep) | CFSSL | Internal CA |
| K8s TLS | cert-manager | — | Auto-renewal |
| IPAM / DCIM | NetBox | — | Source of truth for IP/VLAN/racks |
| NAC | PacketFence | — | 802.1X, RADIUS, BYOD |
| Asset tracking | Snipe-IT | — | Lifecycle + barcode |
| Network discovery | Netdisco | Ntopng | SNMP-based topology |

---

## Databases & Storage

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| RDBMS primary | PostgreSQL | MySQL, CockroachDB | With Patroni HA + PgBouncer pooling |
| Cache / KV | Redis → Valkey | Memcached | Valkey = FOSS Redis fork |
| Document DB | MongoDB | — | When document model needed |
| Analytics | ClickHouse | Elasticsearch for analytics | Column-store, fast aggregation |
| Search | Elasticsearch | — | ELK stack component |
| Object storage | MinIO | AWS S3 | S3-compatible self-hosted |
| Distributed storage | Ceph | GlusterFS | Block+Object+File |
| File sync | NextCloud | — | Self-hosted Dropbox |

---

## Monitoring & Observability

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| Metrics | Prometheus + VictoriaMetrics | Zabbix (new projects) | VM = 10x storage efficiency |
| Dashboards | Grafana | — | Universal frontend |
| Log aggregation | Loki | ELK standalone | Prometheus-style logs |
| Log pipeline | Vector | Fluentd/Fluent Bit | Rust, unified logs+metrics |
| Tracing | Tempo + Jaeger | Zipkin | Tempo = storage, Jaeger = UI |
| Alerting | Alertmanager + Grafana OnCall | PagerDuty | FOSS on-call scheduling |
| K8s cost | OpenCost | — | CNCF, Prometheus integration |
| Legacy infra | Zabbix | — | Kept for existing deployments |

---

## Security

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| SIEM / XDR | Wazuh | Splunk, commercial SIEM | FOSS, host+log+FIM |
| NSM platform | Security Onion | — | Suricata+Zeek+Wazuh stack |
| IDS/IPS | Suricata | Snort | Multi-threaded, Lua scripting |
| Network analysis | Zeek | — | Protocol metadata extraction |
| Runtime security | Falco | — | K8s syscall monitoring |
| Collaborative IPS | CrowdSec | fail2ban | Community blocklists |
| WAF | BunkerWeb | SafeLine | ModSecurity + K8s-native |
| Vuln scanner | OpenVAS/GVM | Nessus | FOSS, 90K+ NVTs |
| Container scanning | Trivy | Grype | Aqua, comprehensive |
| Web scanner | OWASP ZAP | — | DAST, proxy |
| Linux audit | Lynis | — | CIS benchmarks, lightweight |
| SBOM / SCA | Dependency-Track | — | OWASP, VEX support |
| Vuln management | DefectDojo | — | Aggregation + deduplication |
| Code quality | SonarQube | — | SAST + quality gates |
| Multi-linter | Mega-Linter | — | 50+ linters, CI/CD |
| IR case mgmt | TheHive + Cortex | — | Case management + analyzers |
| Threat intel | MISP | — | IOC sharing, STIX/TAXII |
| CVE lookup | SploitScan | Vulnerability-Lookup | EPSS + PoC availability |

---

## Collaboration & Documentation

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| Wiki / docs | BookStack | Confluence, XWiki | Simple books/chapters/pages |
| Static docs | MkDocs (Material) | Sphinx | Git-workflow friendly |
| Team chat | Mattermost | Slack, Rocket.Chat | Open-source, self-hosted |
| Federated chat | Matrix/Element | — | E2E, bridges |
| Mail server | Stalwart | Postfix+Dovecot | Rust, SMTP+IMAP+JMAP all-in-one |

---

## AI & Automation

| Category | Our Choice | Not Using | Notes |
|----------|-----------|-----------|-------|
| Primary LLM API | Claude (Anthropic) | OpenAI as fallback | See model selection below |
| Local LLMs | Ollama | LM Studio | CLI + API server, GPU support |
| LLM serving (prod) | vLLM | TensorRT-LLM | High-throughput, PagedAttention |
| LLM framework | LangChain | LlamaIndex | RAG, chains, agents |
| LLM routing | LiteLLM | — | Unified API + fallback |
| Workflow automation | n8n | Zapier, Make | FOSS, 400+ integrations |
| Data pipelines | Apache Airflow | Temporal, Prefect | DAG-based scheduling |
| MCP integration | MCP servers | — | Tool/resource access protocol |
| OSINT automation | BBOT | Maltego | Recursive, multi-source |
| Username search | Snoop | Sherlock | Russian-focused, 2000+ sources |

---

## AI Model Selection

| Use Case | Model | Cost Level |
|----------|-------|-----------|
| Critical reasoning, security analysis, architecture | claude-opus-4-6 | High |
| Standard development, general tasks | claude-sonnet-4-6 | Medium |
| Formatting, extraction, simple search | claude-haiku-3-5 | Low |
| Local / privacy-sensitive | Ollama + DeepSeek-R1 or Llama | Free |
| Russian language tasks | GigaChat (Sber) or YaLM (Yandex) | Variable |
| Multilingual embeddings | multilingual-e5-large (local) | Free |
| Code embeddings (API) | voyage-2 | Low |

**Fallback chain:** claude-opus-4-6 → claude-sonnet-4-6 → gpt-4o → gemini-2.0-flash

---

## Embedded & IoT

| Category | Our Choice | Notes |
|----------|-----------|-------|
| Industrial MCU | STM32 (ARM Cortex-M) | HAL, CubeMX |
| WiFi/BLE IoT | ESP32 | Arduino + ESP-IDF |
| BLE-only | nRF52 (Nordic) | — |
| IoT messaging | MQTT | Pub/sub, lightweight |
| Smart home | Matter + Zigbee | Matter = new standard |

---

## Languages

| Language | Primary Use | Linter/Test |
|----------|------------|------------|
| Python | Automation, scripts, ML, hooks | ruff, mypy, pytest |
| Go | CLI tools, network services, security | golangci-lint |
| Rust | Systems, performance-critical | cargo, clippy |
| Bash | Scripting, automation | shellcheck |
| TypeScript | Web frontend, Node.js | tsc, eslint |
| HCL | Terraform / OpenTofu IaC | terraform fmt |
| C | Kernel, embedded, low-level | gcc, valgrind, gdb |
| Assembly | RE, exploit dev | nasm, gdb |
