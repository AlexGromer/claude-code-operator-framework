# Permissions Template v7.4

## settings.json Structure (337 allow / 32 deny / 112 ask)

### Allow — 30 Groups

| # | Group | Count | Rule |
|---|-------|-------|------|
| 1 | Core Read | 4 | `Read(*)`, `Grep(*)`, `Glob(*)`, `WebSearch` |
| 2 | Core Edit/Write | 34 | Global shared dirs (16 paths): osint, pentest, devops, reverse, your-project, dfir, ml, compliance, business, go, cargo, templates, agent_work_directory, rustup, uv-cache, uv-tools + `~/.claude/**`. Project-specific: via `settings.local.json` |
| 3 | MCP github | 26 | All github operations |
| 4 | MCP fetch | 1 | `mcp__fetch__fetch` |
| 5 | MCP filesystem | 14 | All filesystem operations (incl. edit_file, directory_tree, get_file_info, list_allowed_directories, read_file) |
| 6 | MCP memory | 9 | All knowledge graph operations |
| 7 | MCP git | 11 | All except `git_reset` (in ask) |
| 8 | MCP sequential-thinking | 1 | Reasoning tool |
| 9 | MCP sqlite | 6 | All query operations |
| 10 | MCP backlog | 8 | All 8 backlog-mcp tools |
| 11 | MCP terraform | 9 | All registry operations (incl. search_policies, get_policy_details) |
| 12 | MCP Crypto.com | 9 | All read-only market data (get_book, candlestick, ticker, trades, etc.) |
| 13 | MCP GoDaddy | 2 | Domain suggestions and availability checks |
| 14 | MCP profile-mcp | 8 | Profile management (list, show, load, unload, status, load_all, reset, ensure_essential) |
| 15 | MCP doctor-mcp | 3 | Health checks (check, full, json) |
| 16 | MCP gc-mcp | 3 | Garbage collection (run, dry_run, status) |
| 17 | MCP score-mcp | 3 | Task scoring (discovery, dimensions, batch) |
| 18 | Bash git | 2 | git, gitleaks detect |
| 19 | Bash npm/node | 3 | node, npm, npx |
| 20 | Bash python | 5 | python, python3, pip, pip3, pytest |
| 21 | Bash go | 3 | go, gofmt, golangci-lint run |
| 22 | Bash dev tools | 7 | make, cmake, bash, sh, zsh, jq, yq |
| 23 | Bash file ops | 20 | cat, ls, find, grep, awk, sed, head, tail, wc, sort, uniq, cut, tr, file, stat, du, tree, column, comm, command |
| 24 | Bash binary analysis | 7 | strings, xxd, hexdump, objdump, readelf, nm, ldd |
| 25 | Bash network passive | 9 | whois, dig, host, nslookup, ping, traceroute, curl -s, wget -q, dnsx |
| 26 | Bash docker RO | 6 | docker ps/images/logs/inspect, docker-compose ps/logs |
| 27 | Bash k8s/helm/IaC RO | 34 | kubectl get/describe/logs, helm RO (14), helmfile RO (8), terraform RO (6), ansible RO (3) |
| 28 | Bash test | 16 | k6, locust, artillery, wrk, vegeta, hey, ab, mutmut viewers, pact, dredd, schemathesis, stress-ng version, litmusctl get, toxiproxy list |
| 29 | Bash system utils | 34 | echo, env, export, test, seq, tee, xargs, printf, bc, time, source, apt/dpkg, uv/uvx, cron/anacron, logs (journalctl, logrotate), rsync, gpg, kill, OSINT passive (censys, shodan, greynoise, katana, phoneinfoga, tor), Claude CLI |
| 30 | WebFetch domains | 40 | Approved domains |

### Deny — 32 entries

| Category | Count | Examples |
|----------|-------|---------|
| Credential files | 13 | Read(/etc/shadow), Read(**/.env), Read(**/*secret*), Read(**/*password*) |
| Destructive commands | 11 | rm -rf /, dd if=/dev/zero, mkfs, fdisk, parted |
| System shutdown | 4 | shutdown, reboot, halt, poweroff |
| Pipe to shell | 4 | curl/wget piped to sh/bash, wildcard piped to sh/bash |

### Ask — 112 entries

| Category | Count | Examples |
|----------|-------|---------|
| MCP git_reset | 1 | mcp__git__git_reset |
| MCP pd-tools | 7 | subfinder, dnsx, naabu, httpx, katana, nuclei, bug_bounty_workflow |
| Pentest/scan tools | 35 | nmap, masscan, nikto, sqlmap, nuclei, hydra, john, hashcat, etc. |
| Reverse engineering | 6 | radare2, r2, ghidra, gdb, ltrace, strace |
| Docker write ops | 9 | docker run/build/exec/stop/rm/rmi, docker-compose up/down/build |
| K8s write ops | 6 | kubectl apply/delete/exec/edit/scale/rollout |
| Helm write ops | 16 | helm install/upgrade/rollback/uninstall/delete, repo add/update/remove, push/pull/package, etc. |
| Helmfile write ops | 4 | helmfile sync/apply/destroy/delete |
| IaC write ops | 5 | terraform apply/destroy/init, ansible-playbook, ansible |
| Network active | 4 | nc, netcat, ncat, socat |
| Curl write | 3 | curl -X, curl -d, curl --data |
| System admin | 7 | sudo, su, rm, mv, cp, chmod, chown |
| Services | 2 | systemctl, service |
| Mutation/chaos | 10 | mutmut run, cosmic-ray, go-mutesting, gremlins, litmusctl create/delete, pumba, toxiproxy-cli create/toxic/delete |
| Load testing write | 2 | stress-ng (full), gatling, jmeter |

### Conflict Prevention Rules

- **curl**: Only `curl:-s*` in allow. `curl:-X*`, `curl:-d*` stay in ask. NEVER bare `Bash(curl:*)`.
- **docker**: Only read-ops in allow. Write-ops (run, build, exec) stay in ask. NEVER bare `Bash(docker:*)`.
- **Precedence**: deny > allow > ask > defaultMode. If both allow and ask match, allow wins.
- **pd-tools MCP**: All 7 tools in ask (NETWORK_ACTIVE level). Never in allow.
- **git_reset**: In ask, not allow (destructive potential).

### Adding New Entries

1. Determine group (file inspection? dev tool? security?)
2. Check if parent wildcard covers it already
3. Read-only → allow, write/active → ask, catastrophic → deny
4. Add to correct group (maintain alpha order within group)
5. MCP tools: verify tool name against server definition

---

## Per Project Type Templates

Used by project-init agent. `{{project}}` replaced at init time.

### development
```
Edit(/opt/{{project}}/**)
Write(/opt/{{project}}/**)
Bash(npm:*), Bash(pytest:*), Bash(make:*), Bash(docker:ps*), Bash(docker:images*), Bash(docker:logs*)
mcp__github__create_pull_request
# Ask: docker run/build, sudo, rm
```

### security / pentest-engagement
```
Edit(/opt/work/pentest/{{project}}/**)
Write(/opt/work/pentest/{{project}}/**)
Bash(whois:*), Bash(dig:*), Bash(curl:-s*)
# Ask: nmap, nuclei, subfinder, httpx, ffuf, sqlmap, hydra, nikto, gobuster, masscan
# Ask: mcp__pd-tools__* (all 7 tools)
```

### devops
```
Edit(/opt/work/devops/{{project}}/**)
Write(/opt/work/devops/{{project}}/**)
Bash(kubectl:get*), Bash(kubectl:describe*), Bash(kubectl:logs*), Bash(helm:list*), Bash(terraform:plan*)
# Ask: kubectl apply/delete, helm install/upgrade, terraform apply/destroy
```

### osint
```
Edit(/opt/work/osint/{{project}}/**)
Write(/opt/work/osint/{{project}}/**)
Bash(whois:*), Bash(dig:*), Bash(curl:-s*)
# Ask: sherlock, maigret, subfinder, bbot, shodan, censys
```

### research
```
Edit(/opt/{{project}}/**)
Write(/opt/{{project}}/**)
WebFetch(domain:arxiv.org), WebFetch(domain:github.com), WebFetch(domain:habr.com)
# Minimal ask — mostly read-only
```

### dfir
```
Edit(/opt/work/dfir/{{project}}/**)
Write(/opt/work/dfir/{{project}}/**)
Bash(strings:*), Bash(file:*), Bash(xxd:*), Bash(hexdump:*)
# Ask: volatility, vol3, plaso, log2timeline, yara, chainsaw, hayabusa, autopsy
```

### business
```
Edit(/opt/{{project}}/**)
Write(/opt/{{project}}/**)
WebFetch(domain:docs.google.com), WebFetch(domain:habr.com), WebFetch(domain:vc.ru)
# Minimal ask — document generation focused
```

### compliance
```
Edit(/opt/{{project}}/**)
Write(/opt/{{project}}/**)
WebFetch(domain:consultant.ru), WebFetch(domain:fstec.ru), WebFetch(domain:cbr.ru), WebFetch(domain:iso.org)
# Minimal ask — regulatory document generation
```

### network
```
Edit(/opt/{{project}}/**)
Write(/opt/{{project}}/**)
Bash(ping:*), Bash(traceroute:*), Bash(dig:*), Bash(whois:*), Bash(nslookup:*)
# Ask: ssh, telnet, snmpwalk, snmpget
```

### chat
```
Edit(/opt/{{project}}/**)
Write(/opt/{{project}}/**)
# Minimal — mostly read-only, no MCP profiles
```

### mixed
```
Edit(/opt/{{project}}/**)
Write(/opt/{{project}}/**)
# Base permissions only — domain-specific added by workflow autoloader
```

## Per-Type Permission Files

Located in `~/.claude/templates/project-init/permissions/`:

| File | Type | Allow | Ask | MCP Profiles |
|------|------|-------|-----|--------------|
| permissions-development.json | development | 10 entries | 5 entries | github |
| permissions-security.json | security | 7 entries | 17 entries | security, github |
| permissions-pentest.json | pentest-engagement | 7 entries | 22 entries | security, intel, github |
| permissions-devops.json | devops | 12 entries | 9 entries | devops, github |
| permissions-osint.json | osint | 10 entries | 8 entries | osint, github |
| permissions-dfir.json | dfir | 6 entries | 8 entries | dfir, intel, github |
| permissions-research.json | research | 7 entries | 0 entries | github |
| permissions-business.json | business | 5 entries | 0 entries | github |
| permissions-compliance.json | compliance | 6 entries | 0 entries | github |
| permissions-network.json | network | 7 entries | 4 entries | network, github |
| permissions-chat.json | chat | 2 entries | 0 entries | — |
| permissions-mixed.json | mixed | 2 entries | 0 entries | github |

Usage: `project-init` loads the matching file and generates `settings.local.json`.

---

## How to Apply

During `/project-init`:
1. Select template by project type
2. Show permission set for user approval
3. Verify no conflicts with existing ask/deny entries
4. Project-specific Edit/Write granted via `settings.local.json` (generated by project-init from per-type template)
