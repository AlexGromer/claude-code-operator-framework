# Tools Registry

## Purpose

Централизованный реестр всех инструментов в конфигурации с быстрым поиском
по имени, категории, модулю и уровню permissions.

**Version:** 1.0.0
**Last Updated:** 2026-03-22

> **Last verified: 2026-03-22.** Some entries may be outdated — refer to `mcp-servers/` and `hooks/` for current tools.

---

## Quick Search Index

### By First Letter

| Letter | Tools |
|--------|-------|
| **A** | age, alertmanager, amass, ansible, apache-airflow, argocd, artifactory, authelia, authentik |
| **B** | bandit, bitwarden, bbot, bookstack, burp |
| **C** | caddy, cert-manager, cfssl, chef, cilium, clickhouse, cloudstack, cobbler, cockroachdb, containerd, cortex, cri-o, crossplane, crowdsec |
| **D** | dex, dig, digital-rebar, dirb, dirsearch, docker, docker-compose, drone |
| **E** | elasticsearch, element, envoy, esp-idf, esp32, esp8266 |
| **F** | falco, ffuf, fleet, fluentd, fluent-bit, flux, foreman, freeipa |
| **G** | gatling, gdb, gh, ghidra, git, gitlab-ci, glusterfs, go, gobuster, grafana, grafana-oncall, grype, gvm |
| **H** | haproxy, harbor, hashcat, headscale, helm, holehe, host, httpx, hydra |
| **I** | istio |
| **J** | jaeger, jenkins, jmeter, john, jq |
| **K** | k0s, k3s, k6, k9s, keycloak, kubectl, kubernetes |
| **L** | langchain, libvirt, linkerd, litmus, lldb, locust, loki, ltrace |
| **M** | maas, maigret, make, mariadb, masscan, matrix, mattermost, mcp, minio, misp, mongodb, msfconsole, msfvenom, mysql |
| **N** | nc, nebula, netcat, netdata, nextcloud, nginx, nikto, nm, nmap, nomad, nrf52, nslookup, nuclei |
| **O** | objdump, ollama, openbsd, openldap, openshift, openstack, opentofu, openvpn, openvas |
| **P** | packer, pagerduty, passbolt, patroni, pgbouncer, ping, playwright, podman, postgresql, prometheus, proxmox, pulumi, puppet, pytest |
| **Q** | qemu |
| **R** | r2, radare2, rancher, readelf, recon-ng, redis, redis-cli, rocket-chat, rp2040 |
| **S** | salt, samba, searchsploit, security-onion, selenium, semgrep, sherlock, snoop, socat, sonarqube, sops, spiderfoot, sploitscan, sqlmap, stalwart, step-ca, stm32, strace, strings, subfinder, suricata |
| **T** | tailscale, tekton, tempo, temporal, terraform, theharvester, thehive, traceroute, traefik, trivy |
| **V** | valkey, vault, vector, vegeta, victoriametrics, virtualbox, vitess, vless |
| **W** | wazuh, wfuzz, whois, wireguard, woodpecker, wrk |
| **X** | xwiki, xxd |
| **Y** | yq |
| **Z** | zabbix, zap, zeek, zipkin |

---

## Master Registry Table

### Infrastructure & Virtualization

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| proxmox-ve | Hypervisor | 03-devops | 1.1 | — | — |
| proxmox-backup | Backup | 03-devops | 1.1 | — | — |
| proxmox-mail-gateway | Email Security | 03-devops | 1.1 | — | — |
| qemu | Hypervisor | 03-devops | 1.1 | — | — |
| libvirt | VM Management | 03-devops | 1.1 | — | — |
| virtualbox | Hypervisor | 03-devops | 1.1 | — | — |
| openstack | Private Cloud | 03-devops | 1.2 | — | — |
| openshift | PaaS | 03-devops | 1.2 | — | — |
| cloudstack | Private Cloud | 03-devops | 1.2 | — | — |

### Configuration Management & IaC

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| terraform | IaC | 03-devops | 2.1 | allow(plan,show,state,output,validate,fmt) / ask(apply,destroy,init) | INFRA_CHANGE |
| opentofu | IaC | 03-devops | 2.1 | — | INFRA_CHANGE |
| pulumi | IaC | 03-devops | 2.1 | — | INFRA_CHANGE |
| crossplane | IaC | 03-devops | 2.1 | — | INFRA_CHANGE |
| packer | Image Build | 03-devops | 2.1 | — | — |
| ansible | Config Mgmt | 03-devops | 2.2 | allow(--version,--check,lint) / ask(playbook,*) | INFRA_CHANGE |
| puppet | Config Mgmt | 03-devops | 2.2 | — | INFRA_CHANGE |
| salt | Config Mgmt | 03-devops | 2.2 | — | INFRA_CHANGE |
| chef | Config Mgmt | 03-devops | 2.2 | — | INFRA_CHANGE |
| foreman | Provisioning | 03-devops | 2.3 | — | INFRA_CHANGE |
| maas | Bare Metal | 03-devops | 2.3 | — | INFRA_CHANGE |
| digital-rebar | Automation | 03-devops | 2.3 | — | INFRA_CHANGE |
| cobbler | PXE Boot | 03-devops | 2.3 | — | INFRA_CHANGE |

### CI/CD & GitOps

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| gitlab-ci | CI/CD | 03-devops | 3.1 | — | — |
| jenkins | CI/CD | 03-devops | 3.1 | — | — |
| github-actions | CI/CD | 03-devops | 3.1 | — | — |
| tekton | CI/CD | 03-devops | 3.1 | — | — |
| drone | CI/CD | 03-devops | 3.1 | — | — |
| woodpecker | CI/CD | 03-devops | 3.1 | — | — |
| argocd | GitOps | 03-devops | 3.2 | — | — |
| flux | GitOps | 03-devops | 3.2 | — | — |
| fleet | GitOps | 03-devops | 3.2 | — | — |
| harbor | Registry | 03-devops | 3.3 | — | — |
| nexus | Repository | 03-devops | 3.3 | — | — |
| artifactory | Repository | 03-devops | 3.3 | — | — |

### Container & Orchestration

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| docker | Container | 03-devops | 4.1 | allow(ps,images,logs,inspect) / ask(run,build,exec,stop,rm,rmi) | INFRA_CHANGE |
| docker-compose | Container | 03-devops | 4.1 | allow(ps,logs) / ask(up,down,build) | INFRA_CHANGE |
| podman | Container | 03-devops | 4.1 | — | — |
| containerd | Runtime | 03-devops | 4.1 | — | — |
| cri-o | Runtime | 03-devops | 4.1 | — | — |
| kubernetes | Orchestration | 03-devops | 4.2 | — | — |
| kubectl | K8s CLI | 03-devops | 4.2 | allow(get,describe,logs) / ask(apply,delete,exec,edit,scale,rollout) | INFRA_CHANGE |
| k3s | Lightweight K8s | 03-devops | 4.2 | — | INFRA_CHANGE |
| k0s | Lightweight K8s | 03-devops | 4.2 | — | INFRA_CHANGE |
| k9s | K8s TUI | 03-devops | 4.2 | allow(*) | — |
| helm | K8s Package | 03-devops | 4.2 | — | INFRA_CHANGE |
| rancher | K8s Mgmt | 03-devops | 4.2 | — | — |
| nomad | Orchestration | 03-devops | 4.2 | — | — |
| istio | Service Mesh | 03-devops | 4.3 | — | — |
| linkerd | Service Mesh | 03-devops | 4.3 | — | — |
| cilium | Service Mesh | 03-devops | 4.3 | — | — |

### Identity & Access Management

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| freeipa | IdM | 03-devops | 5.1 | — | — |
| samba | AD/DC | 03-devops | 5.1 | — | — |
| openldap | LDAP | 03-devops | 5.1 | — | — |
| 389-directory | LDAP | 03-devops | 5.1 | — | — |
| keycloak | IAM | 03-devops | 5.2 | — | — |
| authentik | IAM | 03-devops | 5.2 | — | — |
| authelia | Auth Proxy | 03-devops | 5.2 | — | — |
| dex | OIDC | 03-devops | 5.2 | — | — |
| vault | Secrets | 03-devops | 5.3 | — | — |
| passbolt | Passwords | 03-devops | 5.3 | — | — |
| bitwarden | Passwords | 03-devops | 5.3 | — | — |
| sops | Encryption | 03-devops | 5.3 | — | — |
| age | Encryption | 03-devops | 5.3 | — | — |

### Networking & Security

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| wireguard | VPN | 03-devops | 6.1 | — | — |
| openvpn | VPN | 03-devops | 6.1 | — | — |
| vless | Tunneling | 03-devops | 6.1 | — | — |
| tailscale | Mesh VPN | 03-devops | 6.1 | — | — |
| headscale | Mesh VPN | 03-devops | 6.1 | — | — |
| nebula | Overlay | 03-devops | 6.1 | — | — |
| nginx | Web/Proxy | 03-devops | 6.2 | — | — |
| haproxy | Load Balancer | 03-devops | 6.2 | — | — |
| traefik | Proxy | 03-devops | 6.2 | — | — |
| envoy | Proxy | 03-devops | 6.2 | — | — |
| caddy | Web Server | 03-devops | 6.2 | — | — |
| cert-manager | Certificates | 03-devops | 6.3 | — | — |
| step-ca | Private CA | 03-devops | 6.3 | — | — |
| cfssl | PKI | 03-devops | 6.3 | — | — |

### Databases & Storage

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| postgresql | RDBMS | 10-tech-stack | 7.1 | — | — |
| patroni | PostgreSQL HA | 10-tech-stack | 7.1 | — | — |
| pgbouncer | Pooling | 10-tech-stack | 7.1 | — | — |
| mysql | RDBMS | 10-tech-stack | 7.1 | — | — |
| mariadb | RDBMS | 10-tech-stack | 7.1 | — | — |
| cockroachdb | Distributed SQL | 10-tech-stack | 7.1 | — | — |
| vitess | MySQL Sharding | 10-tech-stack | 7.1 | — | — |
| redis | Cache/KV | 10-tech-stack | 7.2 | — | — |
| valkey | Redis Fork | 10-tech-stack | 7.2 | — | — |
| mongodb | Document DB | 10-tech-stack | 7.2 | — | — |
| elasticsearch | Search | 10-tech-stack | 7.2 | — | — |
| clickhouse | Analytics | 10-tech-stack | 7.2 | — | — |
| minio | Object Storage | 10-tech-stack | 7.3 | — | — |
| ceph | Distributed | 10-tech-stack | 7.3 | — | — |
| glusterfs | Distributed FS | 10-tech-stack | 7.3 | — | — |
| nextcloud | File Sync | 10-tech-stack | 7.3 | — | — |

### Monitoring & Observability

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| prometheus | Metrics | 03-devops | 8.1 | — | — |
| grafana | Visualization | 03-devops | 8.1 | — | — |
| victoriametrics | Metrics DB | 03-devops | 8.1 | — | — |
| zabbix | Monitoring | 03-devops | 8.1 | — | — |
| netdata | Real-time | 03-devops | 8.1 | — | — |
| loki | Logging | 03-devops | 8.2 | — | — |
| fluentd | Log Shipping | 03-devops | 8.2 | — | — |
| fluent-bit | Log Shipping | 03-devops | 8.2 | — | — |
| vector | Log Pipeline | 03-devops | 8.2 | — | — |
| jaeger | Tracing | 03-devops | 8.3 | — | — |
| tempo | Trace Storage | 03-devops | 8.3 | — | — |
| zipkin | Tracing | 03-devops | 8.3 | — | — |
| alertmanager | Alerting | 03-devops | 8.4 | — | — |
| pagerduty | Incidents | 03-devops | 8.4 | — | — |
| grafana-oncall | On-call | 03-devops | 8.4 | — | — |

### Security Tools - Scanning

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| nmap | Port Scanner | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| masscan | Port Scanner | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| nikto | Web Scanner | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| gobuster | Dir Brute | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| dirb | Dir Brute | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| dirsearch | Dir Brute | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| ffuf | Fuzzer | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| wfuzz | Fuzzer | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| sqlmap | SQL Injection | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| nuclei | Template Scanner | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| httpx | HTTP Probe | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| zap | DAST | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| openvas | Vuln Scanner | 02-security | 10.1 | — | SECURITY_AUDIT |
| gvm | Vuln Scanner | 02-security | 10.1 | — | SECURITY_AUDIT |
| trivy | Container Scan | 02-security | 10.1 | — | — |
| grype | Container Scan | 02-security | 10.1 | — | — |

### Security Tools - OSINT

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| subfinder | Subdomain | 02-security | 10.1 | ask(*) | OSINT_QUERY |
| amass | Subdomain | 02-security | 10.1 | ask(*) | OSINT_QUERY |
| theharvester | Email/Domain | 02-security | 10.1 | ask(*) | OSINT_QUERY |
| recon-ng | Framework | 02-security | 10.1 | ask(*) | OSINT_QUERY |
| sherlock | Username | 02-security | 10.1 | ask(*) | OSINT_QUERY |
| maigret | Username | 02-security | 10.1 | ask(*) | OSINT_QUERY |
| holehe | Email | 02-security | 10.1 | ask(*) | OSINT_QUERY |
| spiderfoot | OSINT | 02-security | 10.1 | ask(*) | OSINT_QUERY |
| snoop | Username | 02-security | 10.1 | ask(*) | OSINT_QUERY |
| bbot | Automation | 02-security | 10.1 | ask(*) | OSINT_QUERY |

### Security Tools - Exploitation & Password

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| hydra | Brute Force | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| john | Password Crack | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| hashcat | Password Crack | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| medusa | Brute Force | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| searchsploit | Exploit DB | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| msfconsole | Metasploit | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| msfvenom | Payload Gen | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| sploitscan | Exploit Search | 02-security | 10.1 | ask(*) | SECURITY_AUDIT |
| burp | Web Proxy | 02-security | 10.1 | — | SECURITY_AUDIT |

### Security Tools - SIEM & Defense

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| wazuh | XDR/SIEM | 02-security | 10.2 | — | — |
| security-onion | NSM | 02-security | 10.2 | — | — |
| thehive | IR Case Mgmt | 02-security | 10.2 | — | — |
| cortex | Analysis | 02-security | 10.2 | — | — |
| misp | Threat Intel | 02-security | 10.2 | — | — |
| suricata | IDS/IPS | 02-security | 10.3 | — | — |
| zeek | Network Analysis | 02-security | 10.3 | — | — |
| falco | Runtime Security | 02-security | 10.3 | — | — |
| crowdsec | IPS | 02-security | 10.3 | — | — |
| semgrep | SAST | 02-security | 10.1 | — | — |
| bandit | Python SAST | 02-security | 10.1 | — | — |
| sonarqube | Code Quality | 07-engineering | 10.1 | — | — |

### Reverse Engineering & Low-Level

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| radare2 | RE Framework | 07-engineering | 10.1 | ask(*) | — |
| r2 | RE (alias) | 07-engineering | 10.1 | ask(*) | — |
| ghidra | Decompiler | 07-engineering | 10.1 | ask(*) | — |
| gdb | Debugger | 07-engineering | 13 | ask(*) | — |
| lldb | Debugger | 07-engineering | 13 | — | — |
| ltrace | Library Trace | 07-engineering | — | ask(*) | — |
| strace | System Trace | 07-engineering | — | ask(*) | — |
| objdump | Binary Analysis | 07-engineering | — | allow(*) | — |
| readelf | ELF Analysis | 07-engineering | — | allow(*) | — |
| nm | Symbol Table | 07-engineering | — | allow(*) | — |
| strings | String Extract | 07-engineering | — | allow(*) | — |
| xxd | Hex Dump | 07-engineering | — | allow(*) | — |
| hexdump | Hex Dump | 07-engineering | — | allow(*) | — |
| ldd | Library Deps | 07-engineering | — | allow(*) | — |

### Network Utilities

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| whois | Domain Lookup | 02-security | — | allow(*) | — |
| dig | DNS Query | 02-security | — | allow(*) | — |
| host | DNS Query | 02-security | — | allow(*) | — |
| nslookup | DNS Query | 02-security | — | allow(*) | — |
| ping | Network Test | 03-devops | — | allow(-c*) | — |
| traceroute | Path Trace | 03-devops | — | allow(*) | — |
| curl | HTTP Client | 03-devops | — | allow(-sI,-s) / ask(-X,-d,--data) | — |
| wget | Download | 03-devops | — | allow(-q) / deny(\|sh,\|bash) | — |
| nc | Netcat | 02-security | — | ask(*) | — |
| netcat | Netcat | 02-security | — | ask(*) | — |
| ncat | Netcat | 02-security | — | ask(*) | — |
| socat | Socket | 02-security | — | ask(*) | — |

### Development & Build

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| git | VCS | 07-engineering | — | allow(*) / hook(push,commit) | CONFIG_COMMIT |
| gh | GitHub CLI | 07-engineering | — | allow(*) | — |
| python | Language | 07-engineering | 13 | allow(*) | — |
| python3 | Language | 07-engineering | 13 | allow(*) | — |
| pip | Package Mgr | 07-engineering | — | allow(*) | — |
| pip3 | Package Mgr | 07-engineering | — | allow(*) | — |
| node | Runtime | 07-engineering | 13 | allow(*) | — |
| npm | Package Mgr | 07-engineering | — | allow(*) | — |
| go | Language | 07-engineering | 13 | allow(*) | — |
| make | Build | 07-engineering | 13 | allow(*) | — |
| cmake | Build | 07-engineering | 13 | allow(*) | — |
| jq | JSON Processor | 07-engineering | — | allow(*) | — |
| yq | YAML Processor | 07-engineering | — | allow(*) | — |

### Testing

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| pytest | Unit Test | 07-engineering | — | — | — |
| jest | JS Test | 07-engineering | — | — | — |
| playwright | E2E Test | 07-engineering | — | — | — |
| selenium | E2E Test | 07-engineering | — | — | — |
| k6 | Load Test | 07-engineering | — | — | — |
| locust | Load Test | 07-engineering | — | — | — |
| jmeter | Load Test | 07-engineering | — | — | — |
| gatling | Load Test | 07-engineering | — | — | — |
| vegeta | Load Test | 07-engineering | — | — | — |
| wrk | Load Test | 07-engineering | — | — | — |
| litmus | Chaos Test | 07-engineering | — | — | — |

### AI & Automation

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| ollama | Local LLM | 10-tech-stack | 11.1 | — | — |
| langchain | LLM Framework | 10-tech-stack | 11.1 | — | — |
| mcp | Tool Integration | 10-tech-stack | 11.1 | — | — |
| n8n | Workflow | 10-tech-stack | 11.2 | — | — |
| apache-airflow | Pipelines | 10-tech-stack | 11.2 | — | — |
| temporal | Workflow | 10-tech-stack | 11.2 | — | — |

### Embedded & IoT

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| stm32 | MCU | 07-engineering | 12.1 | — | — |
| esp32 | MCU | 07-engineering | 12.1 | — | — |
| esp8266 | MCU | 07-engineering | 12.1 | — | — |
| rp2040 | MCU | 07-engineering | 12.1 | — | — |
| nrf52 | MCU | 07-engineering | 12.1 | — | — |
| esp-idf | Framework | 07-engineering | 12.1 | — | — |

### System Administration

| Tool | Category | Module | Tech-Stack | Permission | Hook |
|------|----------|--------|------------|------------|------|
| sudo | Privilege | — | — | ask(*) | — |
| su | User Switch | — | — | ask(*) | — |
| rm | Remove | — | — | ask(*) / deny(-rf /,-rf /*,-rf ~/*) | — |
| mv | Move | — | — | ask(*) | — |
| cp | Copy | — | — | ask(*) | — |
| chmod | Permissions | — | — | ask(*) | — |
| chown | Ownership | — | — | ask(*) | — |
| systemctl | Service Mgmt | — | — | ask(*) | INFRA_CHANGE |
| service | Service Mgmt | — | — | ask(*) | INFRA_CHANGE |

---

## Statistics

| Category | Count |
|----------|-------|
| Infrastructure | 9 |
| IaC/Config Mgmt | 12 |
| CI/CD/GitOps | 12 |
| Containers/K8s | 18 |
| IAM/Secrets | 13 |
| Networking | 12 |
| Databases | 14 |
| Monitoring | 15 |
| Security Scanning | 16 |
| Security OSINT | 10 |
| Security Exploit | 9 |
| Security SIEM | 11 |
| RE/Low-Level | 14 |
| Network Utils | 12 |
| Development | 14 |
| Testing | 11 |
| AI/Automation | 6 |
| Embedded | 6 |
| SysAdmin | 9 |
| **TOTAL** | **~220** |

---

## Adding New Tool

При добавлении нового инструмента:

1. Ðайти соответствующую категорию в таблице выше
2. Добавить строку в формате:

```markdown
| tool-name | Category | Module | Tech-Stack Section | Permission Level | Hook Category |
```

3. Обновить Statistics
4. Обновить Quick Search Index (если новас первас буква)
5. Следовать полной процедуре из `09-maturity.md` Section 7

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-20 | Initial registry creation |
