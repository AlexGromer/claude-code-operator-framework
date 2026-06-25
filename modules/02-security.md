# Module 02: Security Operations

> Только project-specific контекст. Общие знания (PTES, OWASP, MITRE ATT&CK, NIST, Constitutional AI) — в training data модели.

---

## 1. Инфраструктура этого проекта

### Стек инструментов и маппинг на MCP

| Задача | CLI-инструмент | MCP-сервер | Рабочий каталог |
|--------|---------------|------------|-----------------|
| Subdomain enum | subfinder | pd-tools | /opt/work/osint/ |
| DNS resolve | dnsx | pd-tools | /opt/work/osint/ |
| Port scan | naabu | pd-tools | /opt/work/pentest/ |
| HTTP probe | httpx | pd-tools | /opt/work/pentest/ |
| Web crawl | katana | pd-tools | /opt/work/pentest/ |
| Vuln scan | nuclei | pd-tools | /opt/work/pentest/ |
| OSINT username | maigret | maigret MCP | /opt/work/osint/ |
| Attack surface | bbot | bbot MCP | /opt/work/osint/ |
| Threat intel | — | shodan, censys, greynoise, virustotal | /opt/work/osint/ |
| Detection | yara, sigma | yaraflux, wazuh | /opt/work/pentest/ |
| Forensics | volatility3, tshark | volatility-mcp, WireMCP | /opt/work/reverse/ |
| Reverse | ghidra | ghidra-mcp | /opt/work/reverse/ |
| Case mgmt | — | thehive, misp, defectdojo | — |

### Предпочтения (решения проекта)

- **Сканер**: nuclei (НЕ Nessus/OpenVAS) — шаблонный подход, интеграция с pd-tools
- **SIEM**: Wazuh — open source, поддержка российских требований
- **SAST**: Semgrep (НЕ SonarQube) — для code review в CI
- **Container scan**: Trivy — lightweight, CI-friendly
- **SBOM**: Dependency-Track + Trivy SBOM output
- **Vuln tracking**: DefectDojo для агрегации результатов

---

## 2. Авторизация инструментов

> Переопределяет defaults. Без этой таблицы неизвестно, какие инструменты требуют подтверждения.

| Уровень | Инструменты | Подтверждение |
|---------|------------|---------------|
| Пассивный (без подтв.) | whois, dig, host, Burp (passive), Trivy, Semgrep, searchsploit | Нет |
| Активный (YES) | nmap, masscan, nikto, nuclei, ZAP, ffuf, gobuster, wfuzz | Подтвердить цель и scope |
| Аутентификация (YES+SCOPE) | hydra, hashcat, john, CrackMapExec, sqlmap | Подтвердить цель + scope + legal |
| OSINT (YES) | theHarvester, sherlock, maigret, holehe, bbot, spiderfoot, snoop | Подтвердить цель |

---

## 3. Российская специфика

### Bug Bounty платформы РФ

| Платформа | URL | Особенности |
|-----------|-----|-------------|
| BI.ZONE Bug Bounty | bugbounty.bi.zone | Крупнейшая российская |
| Positive Technologies | bugbounty.ptsecurity.com | Экосистема PT |
| Standoff 365 | standoff365.com | Непрерывный bug bounty |

> Международные платформы (HackerOne, Bugcrowd, Intigriti) — в training data.

### Compliance-маппинг для security testing

| Требование | Что проверять | Инструмент |
|-----------|--------------|------------|
| ФЗ-152 (ПДн) | Утечки ПДн, шифрование, локализация | Trivy, Semgrep, ручной review |
| ФСТЭК Приказ №21 | Меры защиты ИСПДн (УЗ1-4) | Lynis, OpenSCAP |
| ГОСТ Р 57580.1 | Банковская безопасность | Ручной аудит по чек-листу |
| ФЗ-187 (КИИ) | Значимые объекты КИИ | ГосСОПКА интеграция |

---

## 4. Ограничения и запреты (project-specific)

- **Всегда** запрашивать авторизацию перед active scanning (даже в лабе)
- **Всегда** кешировать результаты OSINT в `/opt/work/osint/cache/{target}/`
- **Всегда** сохранять raw-данные для повторного анализа
- **Никогда** не запускать сканирование без явного scope
- **Никогда** не хранить результаты пентеста в `~/.claude/` (только `/opt/work/pentest/`)
- Результаты пентеста — НЕ коммитить в git

---

## 5. Шаблоны (только project-specific формат)

### Finding report (наш формат)

```markdown
## Finding: [Title]

**ID**: FINDING-YYYY-NNN
**Severity**: CRITICAL | HIGH | MEDIUM | LOW | INFO
**CVSS 3.1**: X.X (Vector)
**CWE**: CWE-XXX

### Description
[Что найдено]

### PoC
[Шаги воспроизведения]

### Impact
| CIA | Level | Description |
|-----|-------|-------------|
| C   |       |             |
| I   |       |             |
| A   |       |             |

### Remediation
1. **Immediate**: [workaround]
2. **Long-term**: [fix]
```

### Executive summary (наш формат)

```markdown
## Executive Summary

- Client: [Name]
- Type: [External/Internal/Web/Mobile]
- Duration: [Start] - [End]
- Scope: [description]

| Severity | Count |
|----------|-------|
| Critical | X |
| High     | X |
| Medium   | X |
| Low      | X |

### Top 3 Recommendations
1. ...
2. ...
3. ...
```

---

## 6. LLM Security — только наши решения

> OWASP LLM Top 10, MITRE ATLAS, Constitutional AI — в training data. Здесь только то, что специфично для НАШЕГО агента.

### Наши защитные хуки

| Хук | Событие | Что делает |
|-----|---------|-----------|
| `constitutional_pre_hook.py` | PreToolUse | Этические guardrails |
| `atlas_pre_request_hook.py` | PreToolUse | Детект ATLAS-атак на агента |
| `code_review_hook.py` | PostToolUse (Write/Edit) | SAST при записи кода |
| security-toolkit plugin | PreToolUse | Предупреждение перед nmap/nuclei/hydra без scope |

### Наши конкретные риски

- **Prompt injection через файлы**: агент читает untrusted файлы (code repos, web pages) → injection в контекст
- **Tool abuse**: агент имеет Bash → потенциальный RCE через crafted prompts
- **Data exfiltration**: агент может читать `~/.claude/` credentials → нужен мониторинг
- **Budget drain**: adversarial prompts могут вызывать expensive subagents → budget hook

### Наши митигации (уже реализованы)

1. Authorization levels в `rules/authorization-levels.md`
2. Budget enforcement через `unified_budget_hook.py`
3. Safety monitoring через `safety-monitor` agent (on-demand)
4. Tool filtering: BUDGET_BYPASS_TOOLS для предотвращения lockout
5. Session isolation: file-based session ID (не env vars)
