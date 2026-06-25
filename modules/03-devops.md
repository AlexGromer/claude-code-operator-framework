# Module 03: DevOps — Project-Specific Reference

> Module hint: Load this for our infrastructure stack, GitHub auth setup, agent deployment, and LLM observability.
> Claude already knows: Terraform workflow, Ansible, K8s manifests, Helm, GitHub Actions, GitOps, Docker, Prometheus/Grafana/Loki, Git conventions.

---

## 1. Our Stack Decisions

| Layer | Choice | NOT used |
|-------|--------|----------|
| GitOps | ArgoCD | Flux |
| CI/CD | GitHub Actions | GitLab CI, Jenkins |
| Virtualization | Proxmox VE + PBS + PMG | VMware |
| Storage | Ceph (RBD/CephFS) | NFS |
| K8s distribution | K3s (lightweight) | EKS/GKE |
| Bare metal | Tinkerbell (PXE) | Cobbler |
| Image build | Packer → Proxmox templates | CloudInit only |
| Workflow automation | n8n (self-hosted) | Zapier |
| Packages/mirrors | Pulp 3 | Nexus |
| Metrics | VictoriaMetrics (Prometheus drop-in) | Thanos |
| Logs | VictoriaLogs (Loki alternative) | ELK |
| Observability pipeline | Vector | Logstash/Fluentd |
| Cost monitoring | OpenCost | Kubecost SaaS |
| Secrets | `pass` (GPG) + External Secrets Operator | Vault (not deployed) |

---

## 2. GitHub Authentication Map

Two separate auth methods — do NOT mix them up:

| Operation | Tool | Auth source |
|-----------|------|-------------|
| All standard GitHub ops (PR create, merge, comment, list) | MCP GitHub (`mcp__github__*`) | a GitHub token in your environment |
| **Approve your own PRs** | GitHub App (separate bot identity) | App ID + installation ID + private key, kept in your secret manager |
| Git push/pull | SSH | your SSH key |
| Commit signing | GPG | your signing key (keyring or secret manager) |

**Why two methods:** GitHub API blocks self-approval (`"Can not approve your own pull request"`). A GitHub App acts as a separate identity (bot), bypassing this restriction.

**App auth flow:** `App ID + Private Key → JWT (10 min) → Installation Token (1h) → GitHub API`

---

## 3. Git Initialization Protocol (New Projects)

**MANDATORY** when `.git/` doesn't exist or has no remote:

```bash
# Step 1: Init if needed
git init  # only if no .git/

# Step 2: .gitignore — CRITICAL patterns
cp ~/.claude/templates/.gitignore.security ./.gitignore
# Verify .claude/ is excluded:
grep -q "^\.claude/" .gitignore && echo "OK" || echo "MISSING"

# Step 3: Secrets scan BEFORE first commit
gitleaks detect --source . --verbose
# Alternative:
trufflehog filesystem . --only-verified

# Step 4: Remote setup (use MCP GitHub to create, then SSH remote)
git remote add origin git@github.com:username/repo.git

# Step 5: Initial commit
git add .gitignore
git commit -S -m "chore: initial commit"
```

**Security template:** `~/.claude/templates/.gitignore.security` (524 lines, 11 categories including cloud creds, CI/CD secrets, MCP configs, mobile dev, IDE files)

**Critical .gitignore entries (always verify):**
```
.claude/          # NEVER commit
.env*             # All env files
*.pem *.key *.p12 # Keys
credentials.*     # Credential files
pass/ .password-store/
```

**Secrets scan triggers:** Before any commit with new files, before PRs, after modifying .gitignore.

**If secrets found:** HALT, report file:line:type, require rotation before proceeding.

---

## 4. Our Infrastructure Stack — Key Commands

### Proxmox VE
```bash
pvecm status                          # Cluster health
qm create 100 --name vm1 --memory 2048 --net0 virtio,bridge=vmbr0
vzdump 100 --mode snapshot --storage pbs --compress zstd  # Backup to PBS
```
- 3+ node cluster with fencing, Ceph or ZFS storage
- API tokens for automation (not root password)
- Packer (`telmate/proxmox` provider) for template builds

### Proxmox Backup Server (PBS)
```bash
proxmox-backup-manager datastore create backups /mnt/datastore/backups
proxmox-backup-manager namespace create backups/production
proxmox-backup-manager datastore update backups --keep-last 7 --keep-weekly 4 --keep-monthly 6
```
- Separate physical server from PVE nodes; encryption at rest with client-side keys

### Ceph
```bash
ceph -s                    # Health overview
ceph health detail         # Detailed issues
rbd create rbd/vm-disk --size 100G
ceph fs volume create cephfs
```
- Min 3 nodes, separate public/cluster networks (10GbE+), Bluestore OSDs

### K3s
```bash
# HA server bootstrap
curl -sfL https://get.k3s.io | sh -s - server --cluster-init
# Worker join
curl -sfL https://get.k3s.io | K3S_URL=https://<ip>:6443 K3S_TOKEN=<token> sh -s - agent
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```
- Disable Traefik: `--disable traefik --disable servicelb` (use custom ingress)
- Longhorn for distributed storage; embedded etcd for HA (3/5/7 server nodes)

### Tinkerbell (Bare Metal PXE)
```bash
# Hardware + Template + Workflow = provisioning
kubectl apply -f hardware.yaml template.yaml workflow.yaml
kubectl get workflows
kubectl logs -n tinkerbell -l app=tink-worker
```
- VLAN isolation for provisioning network; immutable OS images (rebuild, not update)

### n8n (Workflow Automation)
```bash
docker-compose up -d  # Self-hosted, port 5678
n8n export:workflow --id=<id> --output=workflow.json
n8n import:workflow --input=workflow.json
```
- Store workflows in Git; use environment credentials (not hardcoded); HMAC webhook auth

### Pulp 3 (Package Mirror)
```bash
pulp rpm remote create --name centos-stream --url https://mirror.stream.centos.org/...
pulp rpm repository sync --name centos-stream
pulp container repository sync --name nginx
```

### Packer (VM Templates for Proxmox)
```bash
packer validate proxmox.pkr.hcl
packer build proxmox.pkr.hcl
```
- HCL2 format; timestamp-versioned images; cloud-init for post-deploy config

---

## 5. Agent Config Deployment (Blue-Green for ~/.claude/)

Our agent system uses blue-green deployment for configuration updates:

```bash
# Prepare green environment
cp -r ~/.claude ~/.claude-green
vim ~/.claude-green/CLAUDE.md  # Edit

# Validate green
python ~/.claude/tools/config_manager.py --validate ~/.claude-green/CLAUDE.md

# Switch (symlink)
mv ~/.claude ~/.claude-blue
ln -s ~/.claude-green ~/.claude

# Rollback if needed
rm ~/.claude && ln -s ~/.claude-blue ~/.claude
```

**Canary pattern (gradual agent rollout):**
```
Stage 1: 5% traffic → Monitor 1h → error_rate < 1%, latency_p95 < 500ms
Stage 2: 25% → 50% → 100%
```

**Rollback triggers:**
| Scenario | Strategy | Recovery |
|----------|----------|----------|
| Config syntax error | `git revert` + redeploy | <5 min |
| Error rate > baseline×2 | Blue-green switch | <1 min |
| Performance degradation | Canary abort | <2 min |

---

## 6. LLM Agent Observability — Our SLOs and Targets

### Core Metrics for Claude Agent System

```python
# Prometheus metric names (our standard)
agent_requests_total{model, tool, status}
agent_latency_seconds{model, operation}   # histogram
agent_tokens_total{model, type}
agent_cost_dollars{model, operation}
agent_errors_total{model, error_type}
agent_tool_calls_total{tool, status}
agent_sessions_active  # gauge
```

### SLOs (Our Targets)

| SLO | Target | Alert Threshold |
|-----|--------|-----------------|
| Availability | 99.5% (30d window) | <99% |
| Latency P95 | <10s per request | >1000ms (5m) → warn; >30s (10m) → critical |
| Success rate | 98% (7d window) | <95% |
| Error rate | <1% | >5% (2m) → critical |
| Hallucination rate | <1% | >3% (5m) → alert |
| Token cost | <$1/day | >$5/day → alert; >$10/h → critical |
| Cache hit rate | >80% | <50% |

### Log Paths for Observability

```yaml
# Loki/VictoriaLogs scrape
paths:
  - /home/user/.claude/logs/*.log
  - /home/user/.claude/evaluation/data/*.jsonl
labels:
  job: claude_agent

# LogsQL queries
{job="claude_agent"} |= "ERROR"
{job="claude_agent"} | json | cost_usd > 1.0
{job="claude_agent"} | json | latency_ms > 5000
```

**Evaluation tools:** `~/.claude/evaluation/` (metrics, costs, security, hallucination detection)
**Cost tracking:** `~/.claude/evaluation/costs/budget_manager.py`
**Observability collector:** `~/.claude/tools/observability_collector.py`

---

## 7. DB Patterns for LLM Applications (OpenAI Scale Reference)

From OpenAI's PostgreSQL scaling to 800M ChatGPT users (2026-01-27):

| Technique | Problem | Solution | Impact |
|-----------|---------|----------|--------|
| **PgBouncer** | Connection saturation | 10k clients → 25 DB conns, `pool_mode=transaction` | 50ms → 5ms (-90%) |
| **Cache lock** | Thundering herd | Request coalescing + stale-while-revalidate | 10k → 1 DB query |
| **Read replicas** | Read bottleneck | 1 primary + N replicas, HAProxy LB | Linear scale |
| **Schema discipline** | Blocking migrations | 5s lock timeout, `CREATE INDEX CONCURRENTLY` | Zero downtime |
| **Query limit** | ORM mega-joins | ≤3 joins OK, ≥10 = RED FLAG → denormalize | 2-5s → 5-50ms |
| **MVCC batching** | Table bloat | Batch updates, UNLOGGED for non-critical | 500GB → 50GB/mo |
| **Product isolation** | Noisy neighbor | Separate DB per product + isolated pools | Independent scaling |

**PgBouncer config for our deployments:**
```ini
[pgbouncer]
pool_mode = transaction
max_client_conn = 10000
default_pool_size = 25
reserve_pool_size = 5
```

---

## 8. Infrastructure Change Request Template

```markdown
## CR-[YYYY]-[NNN]: [Title]
Type: Create|Modify|Delete|Migration | Environment: dev|staging|prod
Risk: Low|Medium|High | Rollback time: [estimate]

### Change Plan
1. Pre-flight: [verification commands]
2. Backup: [backup commands]
3. Execute: [change commands]
4. Validate: [health check commands]

### Rollback
[rollback commands]

**[REQUIRES CONFIRMATION BEFORE EXECUTION]**
```

---

## 9. Naming Conventions & Paths

| Resource | Convention |
|----------|------------|
| Working data | `/opt/{domain}/{project}/` (NOT in `~/.claude/`) |
| OSINT cache | `/opt/work/osint/cache/{target}/` |
| Pentest | `/opt/work/pentest/{project}/` |
| Agent config | `~/.claude/` (never in git, always gitignored) |
| Kubernetes namespace | `{app}-{env}` (e.g., `myapp-production`) |
| Git branches | `feature/*`, `fix/*`, `docs/*`, `hotfix/*` |
| Commit format | Conventional Commits: `type(scope): subject` |
| Image tags | `registry.example.com/{app}:{version}` (never `:latest`) |

**Commit types:** feat, fix, docs, test, refactor, perf, chore, ci, build, revert

---

*For generic Terraform/Ansible/K8s/Helm/Docker/CI patterns, Claude already knows them. Load this module only for project-specific decisions.*
