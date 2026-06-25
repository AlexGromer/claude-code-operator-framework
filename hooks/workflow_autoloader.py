#!/usr/bin/env python3
"""
Workflow Autoloader — Automatic Module, Skill, Example, and MCP Loading

Analyzes user prompts for domain keywords and returns relevant context:
- Modules to load (on-demand)
- Skills to suggest
- Few-shot examples to reference
- Workflow steps to propose
- Clarification questions
- MCP server profiles (loaded automatically, session reopen advised)

Hook Type: Called from UserPromptSubmit hook
Input: user prompt text
Output: formatted additionalContext string (or empty)

Version: 3.2.0
Created: 2026-02-06
Updated: 2026-03-01 — v3.2: Missing parameter detection for NETWORK_ACTIVE/Standard+ tasks.
         v3.1: Restored complexity scoring (simplified from UEP).
         v3: Profile rotation (unload old, load new). v2: MCP profile auto-loading.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

MODULES_DIR = Path.home() / ".claude" / "modules"
EXAMPLES_DIR = Path.home() / ".claude" / "examples"
SKILLS_DIR = Path.home() / ".claude" / "skills"
CONFIG_FILE = Path.home() / ".claude.json"
ACTIVE_PROFILE_FILE = Path.home() / ".claude" / "evaluation" / "data" / "active_mcp_profiles.json"

# ─────────────────────────────────────────────────────────────────
# DOMAIN → MCP PROFILE MAPPING
# Maps detected domains to MCP server profiles that should be loaded.
# Profiles are defined in ~/.claude/mcp-servers/profile-mcp/profiles.go
# ─────────────────────────────────────────────────────────────────

DOMAIN_MCP_PROFILES: Dict[str, List[str]] = {
    "security":             ["security", "intel"],
    "osint":                ["osint", "intel"],
    "dfir":                 ["dfir", "intel", "case-mgmt"],
    "reverse_engineering":  ["reverse"],
    "devops":               ["devops"],
    "network":              ["network"],
    "lowlevel":             ["reverse"],
    "engineering":          ["browser"],
    "testing":              ["browser"],
    "compliance":           ["intel"],
    "education":            ["browser"],
}

# Essential profile — never unloaded during rotation
ESSENTIAL_PROFILE = "essential"

# ─────────────────────────────────────────────────────────────────
# CWD → DOMAIN BIAS
# Adds scoring bonus when working directory matches a domain
# ─────────────────────────────────────────────────────────────────

CWD_DOMAIN_MAP = {
    "/opt/work/pentest/": "security",
    "/opt/work/osint/": "osint",
    "/opt/work/devops/": "devops",
    "/opt/work/reverse/": "reverse_engineering",
    "/opt/work/dfir/": "dfir",
    "/opt/work/compliance/": "compliance",
    "/opt/work/business/": "business_analysis",
    "/opt/work/ml/": "orchestration",
}


# ─────────────────────────────────────────────────────────────────
# PROJECT TYPE → DOMAIN MAPPING
# Maps ONBOARDING.md project types to workflow autoloader domains
# ─────────────────────────────────────────────────────────────────

PROJECT_TYPE_DOMAIN_MAP: Dict[str, str] = {
    "development":          "engineering",
    "security":             "security",
    "pentest-engagement":   "security",
    "devops":               "devops",
    "osint":                "osint",
    "dfir":                 "dfir",
    "research":             "writing",
    "business":             "business_analysis",
    "compliance":           "compliance",
    "network":              "network",
    "chat":                 "engineering",
    "mixed":                "engineering",
}


def get_cwd_domain_bias(cwd: str) -> Dict[str, int]:
    """Return domain → bonus score based on working directory."""
    bias: Dict[str, int] = {}
    for path_prefix, domain in CWD_DOMAIN_MAP.items():
        if cwd.startswith(path_prefix):
            bias[domain] = 2  # +2 bonus for CWD-aligned domain
    return bias

# ─────────────────────────────────────────────────────────────────
# KEYWORD → MODULE MAPPING
# Weights: primary (+3), secondary (+2), contextual (+1)
# ─────────────────────────────────────────────────────────────────

DOMAIN_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "security": {
        "primary": ["nmap", "burp", "nuclei", "sqlmap", "metasploit", "owasp-zap", "nikto",
                     "masscan", "hydra", "hashcat", "john", "gobuster", "ffuf", "feroxbuster",
                     "rustscan", "amass", "subfinder", "httpx", "trivy", "grype", "wazuh"],
        "secondary": ["pentest", "vulnerability", "exploit", "cve", "injection", "xss",
                       "security audit", "bug bounty", "red team", "blue team", "threat",
                       "owasp", "atlas", "mitre", "attack surface", "scan", "recon",
                       "безопасност", "уязвимост", "rbac", "пентест",
                       "эксплойт", "взлом", "защит", "угроз"],
        "contextual": ["scan", "audit", "attack", "defend", "hardening", "patch",
                        "аудит безопасности", "политик", "просканируй", "атак",
                        "харденинг", "защити", "провер"],
        "modules": ["02-security.md", "22-security-workflows.md"],
        "examples": ["security"],
        "skills": ["security-audit", "pentest", "bugbounty", "redteam-workflow"],
    },
    "devops": {
        "primary": ["terraform", "ansible", "kubernetes", "helm", "docker-compose",
                     "jenkins", "gitlab-ci", "argocd", "flagger", "argo-rollouts",
                     "k3s", "k8s", "kubectl", "docker", "podman", "prometheus",
                     "grafana", "loki", "jaeger", "vault", "consul", "nginx",
                     "traefik", "caddy", "github-actions"],
        "secondary": ["deploy", "pipeline", "infrastructure", "container", "orchestration",
                       "canary", "blue-green", "rollout", "ci/cd", "iac", "gitops",
                       "monitoring", "observability", "service mesh", "ingress",
                       "развёртыван", "разверн", "инфраструктур", "контейнер", "оркестрац", "пайплайн"],
        "contextual": ["automate", "scale", "monitor", "release", "provision", "cluster",
                        "автоматизац", "масштабирован", "мониторинг", "деплой", "кластер"],
        "modules": ["03-devops.md", "10-tech-stack.md"],
        "examples": ["devops"],
        "skills": ["deploy"],
    },
    "osint": {
        "primary": ["sherlock", "maltego", "theharvester", "shodan", "censys",
                     "spiderfoot", "recon-ng", "theHarvester", "holehe",
                     "maigret", "phoneinfoga", "bbot", "nrich"],
        "secondary": ["reconnaissance", "footprint", "dork", "breach", "osint",
                       "social media", "email lookup", "domain recon",
                       "intelligence", "cybint", "socmint", "darkint",
                       "разведк", "расследован", "утечк", "утечка"],
        "contextual": ["investigate", "find", "trace", "lookup", "discover",
                        "исследова", "найти", "найди", "отследи", "пробить", "пробей"],
        "modules": ["02-security.md", "22-security-workflows.md"],
        "examples": ["osint"],
        "skills": ["osint", "intel-workflow"],
    },
    "dfir": {
        "primary": ["volatility", "autopsy", "sleuthkit", "plaso", "log2timeline",
                     "yara", "sigma", "suricata", "zeek", "velociraptor",
                     "chainsaw", "hayabusa", "crowdstrike", "wazuh"],
        "secondary": ["incident response", "forensics", "dfir", "memory forensics",
                       "disk forensics", "malware analysis", "ioc", "detection rule",
                       "siem", "soar", "edr", "ndr", "threat hunting", "triage",
                       "инцидент", "форензик", "вредонос", "расследование инцидента"],
        "contextual": ["investigate", "detect", "eradicate",
                        "расследуй", "расследова", "обнаруж", "сдерж"],
        "modules": ["18-blue-purple-dfir.md", "22-security-workflows.md"],
        "examples": ["blue-purple-dfir"],
        "skills": ["incident-response", "dfir-workflow", "blueteam-workflow"],
    },
    "reverse_engineering": {
        "primary": ["ghidra", "ida", "radare2", "r2", "x64dbg", "ollydbg",
                     "binary ninja", "cutter", "rizin"],
        "secondary": ["disassemble", "decompile", "binary", "malware", "firmware",
                       "elf", "pe", "mach-o", "shellcode", "rop", "gadget",
                       "дизассемблирован", "декомпиляц", "бинарн", "прошивк", "вредоносн"],
        "contextual": ["reverse engineer", "reverse-engineer",
                        "реверс-инжен", "анализ бинар"],
        "modules": ["07-engineering.md", "22-security-workflows.md"],
        "examples": ["lowlevel"],
        "skills": ["lowlevel-debug", "reverse-workflow"],
    },
    "writing": {
        "primary": ["latex", "bibtex", "mendeley", "zotero", "overleaf"],
        "secondary": ["paper", "thesis", "diploma", "dissertation", "article",
                       "publication", "abstract", "literature review", "journal",
                       "статья", "статью", "диплом", "диссертаци", "курсов", "реферат", "публикаци"],
        "contextual": ["research", "publish", "cite", "review", "write",
                        "напиши", "написа", "опубликова", "цитирован"],
        "modules": [],
        "examples": ["writing"],
        "skills": ["academic-writing"],
    },
    "education": {
        "primary": ["ctf", "hackthebox", "tryhackme", "picoctf", "overthewire"],
        "secondary": ["tutorial", "course", "lesson", "workshop", "curriculum",
                       "training", "learning path", "certification", "exam",
                       "обучение", "курс", "урок", "тренинг", "сертификация"],
        "contextual": ["teach", "explain", "learn", "practice", "study",
                        "научи", "объясни", "учить", "учёба", "изучи",
                        "покажи", "расскажи", "обучени"],
        "modules": [],
        "examples": ["education"],
        "skills": ["teaching"],
    },
    "planning": {
        "primary": ["jira", "confluence", "notion", "gantt", "miro"],
        "secondary": ["sprint", "okr", "roadmap", "estimate", "milestone",
                       "backlog", "kanban", "scrum", "agile", "waterfall",
                       "wbs", "pert", "gantt chart",
                       "спринт", "бэклог", "дорожная карта", "веха", "релиз"],
        "contextual": ["plan", "track", "deadline", "timeline", "effort",
                       "человекочас", "оценк", "планирован", "план", "дедлайн",
                       "сроки", "график", "задач"],
        "modules": [],
        "examples": ["planning"],
        "skills": ["project-planning"],
    },
    "engineering": {
        "primary": ["pytest", "jest", "sonarqube", "coverage", "k6", "locust",
                     "gatling", "pact", "litmus", "mutmut", "pit", "ruff",
                     "pylint", "eslint", "mypy", "black", "prettier"],
        "secondary": ["test", "debug", "refactor", "optimize", "review",
                       "chaos", "contract", "mutation", "load", "performance",
                       "tdd", "bdd", "unit test", "integration test",
                       "тестирован", "отладк", "рефакторинг", "оптимизир", "оптимизаци", "ревью"],
        "contextual": ["develop", "code", "build", "benchmark", "fix", "bug",
                        "разработа", "код", "собери", "собрать", "исправ", "баг", "ошибк"],
        "modules": ["07-engineering.md"],
        "examples": ["engineering"],
        "skills": ["code-review"],
    },
    "compliance": {
        "primary": ["iso27001", "nist", "gdpr", "pci-dss", "фз-152",
                     "hipaa", "sox", "гост", "fstec", "фстэк",
                     "фнс", "фссп", "ифнс", "росфинмониторинг"],
        "secondary": ["compliance", "certification", "audit", "standard",
                       "regulation", "gdpr", "policy", "framework", "risk management",
                       "сертификац", "аудит", "стандарт", "регуляц", "нормативн", "соответстви",
                       "бухгалтер", "проводк", "пбу", "фсбу", "налог", "декларац", "отчётност", "баланс", "ндс", "ндфл", "усн", "камеральн"],
        "contextual": ["certify", "assess", "gap analysis", "remediate",
                        "проверк", "оценк", "аттестац", "лицензирован"],
        "modules": ["01-compliance.md"],
        "examples": ["compliance"],
        "skills": ["compliance-audit", "fns-response", "accounting-report", "tax-calc"],
    },
    "lowlevel": {
        "primary": ["ebpf", "kernel", "syscall", "assembly", "gdb",
                     "strace", "ltrace", "dtrace", "perf", "ftrace"],
        "secondary": ["driver", "module", "interrupt", "memory", "elf",
                       "linker", "loader", "heap", "stack", "buffer overflow",
                       "драйвер", "модуль ядра", "прерыван", "память", "стек", "куч"],
        "contextual": ["hook", "trace", "patch", "debug", "exploit",
                        "ассемблер", "трассировк", "перехват", "отладк"],
        "modules": ["07-engineering.md"],
        "examples": ["lowlevel"],
        "skills": ["lowlevel-debug"],
    },
    "business_analysis": {
        "primary": ["babok", "bpmn", "uml", "togaf", "archimate",
                     "c4 model", "c4model", "sparx", "enterprise architect"],
        "secondary": ["requirements", "stakeholder", "as-is", "to-be",
                       "business process", "use case", "user story",
                       "enterprise architecture", "system analysis",
                       "decision matrix", "gap analysis",
                       "требован", "заинтересован", "бизнес-процесс", "сценарий использован",
                       "системный анализ", "корпоративн", "архитектур"],
        "contextual": ["analyze", "model", "diagram", "requirements elicitation",
                        "анализ", "моделирован", "диаграмм", "выявлени"],
        "modules": [],
        "examples": ["business-analysis"],
        "skills": ["business-analysis", "architecture-review"],
    },
    "procurement": {
        "primary": ["44-фз", "223-фз", "44-fz", "223-fz", "zakupki",
                     "тендер", "eis", "еис"],
        "secondary": ["закупка", "тз", "rfp", "tco", "vendor", "procurement",
                       "tender", "bid", "specification", "техническое задание",
                       "критерии оценки", "реестр по"],
        "contextual": ["купить", "поставщик", "контракт", "цена", "оценка"],
        "modules": ["20-procurement.md"],
        "examples": ["procurement"],
        "skills": ["rfp-writer"],
    },
    "network": {
        "primary": ["mikrotik", "opnsense", "pfsense", "netbox", "snipe-it",
                     "routeros", "packetfence", "zabbix", "librenms", "cacti"],
        "secondary": ["vlan", "cmdb", "ipam", "firewall", "router", "switch",
                       "vpn", "wireguard", "openvpn", "ipsec", "bgp", "ospf",
                       "network audit", "network infrastructure", "nac"],
        "contextual": ["acl", "nat",
                        "сеть", "сетев", "маршрутизац", "сегментац", "коммутац",
                        "подсет", "шлюз", "интерфейс"],
        "modules": ["21-network-infrastructure.md"],
        "examples": ["network-infrastructure"],
        "skills": ["network-audit"],
    },
    "mcp": {
        "primary": ["mcp server", "mcp tool", "model context protocol",
                     "mcp registry", "mcp oauth"],
        "secondary": ["mcp", "tool server", "tool integration",
                       "server integration", "mcp configuration",
                       "mcp сервер", "подключ", "интеграц"],
        "contextual": ["connect", "integrate", "server", "plugin",
                        "настрой", "подключи"],
        "modules": ["11-mcp.md"],
        "examples": ["mcp"],
        "skills": [],
    },
    "orchestration": {
        "primary": ["langchain", "langgraph", "crewai", "autogen",
                     "llamaindex", "haystack", "dspy", "semantic kernel"],
        "secondary": ["agent framework", "multi-agent", "rag", "chain",
                       "pipeline", "retrieval", "embedding", "vector store",
                       "workflow automation", "agentic",
                       "мультиагент", "агентн", "оркестрац"],
        "contextual": ["orchestrate", "chain", "pipeline", "automate",
                        "координац", "делегирован"],
        "modules": ["13-orchestration-reference.md"],
        "examples": ["orchestration"],
        "skills": [],
    },
    "prompting": {
        "primary": ["chain-of-thought", "cot", "react", "tot", "tree of thought",
                     "few-shot", "zero-shot", "pal", "self-consistency"],
        "secondary": ["prompt engineering", "prompting", "prompt", "technique",
                       "jailbreak defense", "system prompt", "prompt template",
                       "промпт", "инструкц"],
        "contextual": ["prompt", "instruct", "format", "template",
                        "формулировк", "шаблон"],
        "modules": [],
        "examples": ["prompting"],
        "skills": [],
    },
    "testing": {
        "primary": ["agent testing", "llm testing", "eval", "benchmark",
                     "evals", "promptfoo"],
        "secondary": ["test suite", "test harness", "regression test",
                       "quality assurance", "qa", "evaluation",
                       "тестовый набор", "регрессион", "качеств"],
        "contextual": ["test", "evaluate", "measure", "validate",
                        "протестируй", "проверк", "валидац", "измер"],
        "modules": ["16-testing-reference.md"],
        "examples": ["testing"],
        "skills": [],
    },
    "coding_agents": {
        "primary": ["claude code", "cursor", "windsurf", "cline", "aider",
                     "copilot", "devin", "codex", "bolt", "v0"],
        "secondary": ["coding agent", "code assistant", "ide agent",
                       "autonomous coding", "code generation",
                       "агент кодирован", "ассистент кода", "генерац кода"],
        "contextual": ["code", "implement", "generate",
                        "генерир", "реализ"],
        "modules": [],
        "examples": ["coding-agents"],
        "skills": [],
    },
}

# ─────────────────────────────────────────────────────────────────
# SKILL → DESCRIPTION MAPPING
# ─────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────
# DOMAIN → AGENT MAPPING
# Maps detected domains to recommended subagents (from ~/.claude/agents/).
# First agent in list = primary recommendation.
# ─────────────────────────────────────────────────────────────────

DOMAIN_AGENTS: Dict[str, List[str]] = {
    "security":             ["web-pentester", "infra-pentester", "vuln-assessor", "appsec-engineer", "exploit-researcher", "red-teamer", "cloud-security-engineer", "llm-security-engineer", "mobile-pentester", "purple-teamer", "iam-engineer"],
    "osint":                ["osint-recon", "cybint-analyst", "socmint-analyst", "darkint-analyst", "finint-analyst", "geoint-analyst"],
    "dfir":                 ["incident-commander", "soc-analyst", "detection-engineer", "memory-forensics", "disk-forensics", "network-forensics", "malware-analyst", "log-analyst"],
    "reverse_engineering":  ["binary-analyst", "malware-analyst", "lowlevel-debug", "systems-programmer"],
    "devops":               ["terraform-engineer", "ansible-engineer", "k8s-engineer", "ci-cd-engineer", "deployer", "sre-engineer", "observability-engineer", "devsecops-engineer", "chaos-engineer", "virtualization-engineer", "dr-capacity-planner"],
    "network":              ["network-engineer", "network-scanner"],
    "engineering":          ["web-developer", "api-developer", "test-writer", "qa-automation-engineer", "performance-engineer", "data-engineer", "data-analyst", "deep-reviewer", "db-developer", "database-engineer", "desktop-developer", "mobile-developer"],
    "writing":              ["academic-writer", "tech-writer", "researcher"],
    "education":            ["teacher"],
    "planning":             ["project-planner", "delivery-reporter", "financial-modeler", "risk-analyst"],
    "compliance":           ["eu-compliance", "intl-compliance", "rf-compliance", "tax-advisor", "accountant", "enforcement-responder"],
    "business_analysis":    ["business-analyst", "system-analyst", "system-architect"],
    "lowlevel":             ["kernel-developer", "embedded-developer", "lowlevel-debug", "systems-programmer", "hw-architect", "rf-engineer", "iot-developer", "edge-developer"],
    "procurement":          ["procurement", "tender-analyst", "contract-manager"],
    "mcp":                  ["hook-scaffolder", "agent-factory"],
    "orchestration":        ["ml-engineer", "mlops-engineer", "deep-learning-engineer", "blockchain-developer"],
    "prompting":            ["researcher"],
    "testing":              ["test-writer", "qa-automation-engineer", "performance-engineer"],
    "coding_agents":        ["agent-factory", "hook-scaffolder"],
}

SKILL_DESCRIPTIONS = {
    "security-audit": "Security assessment (OWASP/ATLAS): /security-audit",
    "pentest": "Penetration testing (PTES methodology): /pentest",
    "deploy": "Deployment with pre-flight checks: /deploy",
    "code-review": "Code review (security+quality): /code-review",
    "research": "Structured research workflow: /research",
    "commit": "Git commit with security checks: /commit",
    "pr": "Pull Request creation: /pr",
    "sync": "Configuration sync: /sync",
    "session-health": "Session health check: /session-health",
    "gap": "Gap management: /gap",
    "report": "Workflow report: /report",
    "compliance-audit": "Compliance audit (ISO/GDPR/ФЗ-152): /compliance-audit",
    "incident-response": "Incident response workflow: /incident-response",
    "network-audit": "Network infrastructure audit: /network-audit",
    "rfp-writer": "RFP/ТЗ creation (44-ФЗ/223-ФЗ): /rfp-writer",
    "architecture-review": "Architecture review (C4/ADR): /architecture-review",
    "business-analysis": "Business analysis (BABOK): /business-analysis",
    "academic-writing": "Academic paper writing: /academic-writing",
    "teaching": "Educational content creation: /teaching",
    "project-planning": "Project planning (WBS/PERT): /project-planning",
    "lowlevel-debug": "Low-level debugging (kernel/firmware): /lowlevel-debug",
    "bugbounty": "Bug bounty pipeline (recon→scan→report): /bugbounty",
    "osint": "OSINT investigation by target type: /osint",
    "dfir-workflow": "DFIR forensics pipeline (memory/disk/network): /dfir-workflow",
    "reverse-workflow": "Reverse engineering (triage→analysis→IOC): /reverse-workflow",
    "blueteam-workflow": "Blue team defense (IOC/detection/hunting): /blueteam-workflow",
    "redteam-workflow": "Red team pentest pipeline: /redteam-workflow",
    "intel-workflow": "INT collection (CYBINT/SOCMINT/DARKINT): /intel-workflow",
}


def score_domains(prompt: str, cwd_bias: Optional[Dict[str, int]] = None) -> List[Tuple[str, int]]:
    """Score each domain against the user prompt.

    Returns sorted list of (domain, score) with score > 0.
    Args:
        prompt: User prompt text.
        cwd_bias: Optional domain → bonus score mapping from CWD context.
    """
    prompt_lower = prompt.lower()
    scores = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for word in keywords.get("primary", []):
            if word.lower() in prompt_lower:
                score += 3
        for word in keywords.get("secondary", []):
            if word.lower() in prompt_lower:
                score += 2
        for word in keywords.get("contextual", []):
            # Only match whole words for short contextual keywords
            if len(word) <= 4:
                if re.search(r'\b' + re.escape(word.lower()) + r'\b', prompt_lower):
                    score += 1
            elif word.lower() in prompt_lower:
                score += 1
        if score > 0:
            scores[domain] = score

    # Apply CWD-based domain bias
    if cwd_bias:
        for domain, bonus in cwd_bias.items():
            if domain in scores:
                scores[domain] += bonus
            elif bonus >= 2:
                # CWD alone can activate a domain if bonus is strong enough
                scores[domain] = bonus

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def compute_complexity_score(prompt: str, domain_scores: List[Tuple[str, int]]) -> Tuple[int, str]:
    """Compute task complexity score from prompt analysis.

    7-factor scoring (v7.0):
    - Word count: 0-15 points
    - Domain strength: 0-25 points
    - Tool/technology mentions: 0-20 points
    - Action complexity: 0-20 points
    - Concept complexity: 0-15 points (architectural/design patterns)
    - Multi-step modifiers: 0-10 points
    - File count: 0-5 points

    Returns (score, tier):
        score: 0-100
        tier: "Simple" (<20), "Standard" (20-65), "Complex" (65-80), "Critical" (>80)
    """
    score = 0
    prompt_lower = prompt.lower()
    words = prompt_lower.split()
    word_count = len(words)

    # 1. Word count (0-15 pts, lowered thresholds)
    if word_count > 60:
        score += 15
    elif word_count > 25:
        score += 10
    elif word_count > 8:
        score += 5
    elif word_count > 4:
        score += 2

    # 2. Domain detection strength (0-25 pts, lowered threshold to >= 2)
    top_score = domain_scores[0][1] if domain_scores else 0
    active_domains = len([d for d, s in domain_scores if s >= 2])
    if active_domains >= 3:
        score += 25
    elif active_domains == 2:
        score += 15
    elif active_domains == 1:
        score += 8
    elif top_score >= 1:
        score += 3
    # Bonus for very strong domain match
    if top_score >= 8:
        score += 5

    # 3. Tool/technology mentions (0-20 pts, expanded list)
    tool_keywords = [
        # Security tools
        "nmap", "burp", "nuclei", "ghidra", "volatility", "sigma", "suricata",
        "hydra", "hashcat", "metasploit", "sqlmap", "nikto", "radare2",
        "wazuh", "sonarqube", "trivy", "frida", "wireshark", "yara",
        # DevOps tools
        "terraform", "ansible", "kubernetes", "k8s", "docker", "helm",
        "prometheus", "grafana", "vault", "argocd", "jenkins", "gitlab-ci",
        "github actions", "istio", "envoy", "nginx", "haproxy",
        # Dev technologies
        "react", "vue", "nextjs", "fastapi", "django", "flask", "express",
        "postgresql", "mongodb", "redis", "elasticsearch", "kafka", "rabbitmq",
        "pytorch", "tensorflow", "langchain", "openai",
    ]
    tool_count = sum(1 for t in tool_keywords if t in prompt_lower)
    score += min(tool_count * 5, 20)

    # 4. Action complexity (0-20 pts, expanded RU/EN keywords)
    complex_actions = [
        # English
        "audit", "comprehensive", "full", "complete", "entire",
        "migrate", "refactor", "redesign", "integrate", "deploy",
        "implement", "create", "build", "develop", "configure",
        "pentest", "analyze", "design", "architect", "optimize",
        "automate", "orchestrate", "provision", "set up", "write",
        # Russian
        "аудит", "полный", "комплексный", "мигрир", "рефакторинг",
        "развернуть", "разверни", "интеграц", "реализуй", "создай",
        "настрой", "пентест", "сканиру", "исследу", "проанализируй",
        "напиши", "разработай", "спроектируй", "оптимизируй",
        "автоматизируй", "построй", "сделай", "добавь", "внедри",
        "реализуй", "имплементируй", "задеплой", "разверн",
    ]
    action_count = sum(1 for a in complex_actions if a in prompt_lower)
    score += min(action_count * 5, 20)

    # 5. Concept complexity (0-15 pts, architectural/design pattern detection)
    concepts = [
        # Architecture
        "api", "rest", "graphql", "grpc", "microservice", "микросервис",
        "authentication", "аутентификац", "authorization", "авторизац",
        "jwt", "oauth", "rbac", "acl",
        # Data
        "database", "база данных", "бд", "schema", "migration", "миграци",
        "replication", "репликац", "backup", "бэкап",
        # Infrastructure
        "ci/cd", "pipeline", "пайплайн", "load balanc", "балансировк",
        "ssl", "tls", "certificate", "сертификат", "dns", "vpc", "subnet",
        "firewall", "файрвол", "мониторинг", "monitoring", "alerting",
        # Security concepts
        "vulnerability", "уязвимост", "exploit", "эксплойт",
        "incident", "инцидент", "forensic", "форензик", "malware",
        "threat", "ioc", "siem", "edr", "xdr",
        # Dev patterns
        "тест", "test", "coverage", "рефактор", "архитектур",
        "паттерн", "pattern", "service mesh", "event-driven",
    ]
    concept_count = sum(1 for c in concepts if c in prompt_lower)
    score += min(concept_count * 4, 15)

    # 6. Multi-step modifiers (0-10 pts, expanded)
    step_indicators = [
        " and ", " then ", " after ", " before ", " with ",
        " также ", " затем ", " потом ", " после ", " а потом ",
        ", and ", " + ", " плюс ", " а также ",
        " и ", " с ", ",",  # lighter indicators
    ]
    # Heavy indicators (clear multi-step)
    heavy_steps = sum(1 for s in step_indicators[:10] if s in prompt_lower)
    # Light indicators (commas, " и ", " с ") — count but cap at 1
    light_steps = min(1, sum(1 for s in step_indicators[10:] if s in prompt_lower))
    step_count = heavy_steps + light_steps
    score += min(step_count * 3, 10)

    # 7. File count (0-5 pts, reduced weight)
    import re as _re
    file_paths = _re.findall(r'[./~]\S+\.\w{1,5}', prompt)
    file_count = len(set(file_paths))
    score += min(file_count * 2, 5)

    # Clamp to 0-100
    score = max(0, min(100, score))

    # Assign tier (4-tier system)
    if score < 20:
        tier = "Simple"
    elif score <= 65:
        tier = "Standard"
    elif score <= 80:
        tier = "Complex"
    else:
        tier = "Critical"

    return score, tier


def get_module_sections(module_name: str, max_chars: int = 500) -> str:
    """Read first N chars of module to extract its table of contents."""
    module_path = MODULES_DIR / module_name
    if not module_path.exists():
        return ""

    try:
        text = module_path.read_text(encoding="utf-8")
        # Extract section headers (## and ###)
        headers = []
        for line in text.split("\n"):
            if line.startswith("## ") or line.startswith("### "):
                headers.append(line.strip())
            if len(headers) >= 15:
                break
        if headers:
            return "Sections: " + " | ".join(h.lstrip("#").strip() for h in headers[:10])
        return ""
    except Exception:
        return ""


def get_example_list(example_dir: str) -> List[str]:
    """List available examples in a domain directory."""
    example_path = EXAMPLES_DIR / example_dir
    if not example_path.exists():
        return []

    try:
        files = sorted(example_path.glob("*.md"))
        return [f.stem for f in files[:5]]
    except Exception:
        return []


def _load_profiles_cache() -> dict:
    """Profile cache removed — profiles managed by profile-mcp Go server."""
    return {}


def get_loaded_servers(project_path: Optional[str] = None) -> Dict[str, dict]:
    """Get currently loaded MCP servers for the project from LOCAL scope."""
    if project_path is None:
        project_path = os.getcwd()
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        return data.get("projects", {}).get(project_path, {}).get("mcpServers", {})
    except Exception:
        return {}


def get_profile_servers(profile_name: str) -> Dict[str, dict]:
    """Get servers defined in a profile. Returns empty (managed by profile-mcp)."""
    return {}


def get_all_profile_names() -> List[str]:
    """Get all available profile names."""
    return list(_load_profiles_cache().keys())


def get_active_profiles(project_path: str) -> List[str]:
    """Read which domain profiles were loaded in the last rotation."""
    try:
        data = json.loads(ACTIVE_PROFILE_FILE.read_text())
        return data.get(project_path, [])
    except Exception:
        return []


def save_active_profiles(project_path: str, profiles: List[str]) -> None:
    """Save which domain profiles are currently active.

    Uses a lock file to prevent concurrent sessions from corrupting the JSON
    when two sessions perform profile rotation at the same moment.
    """
    import fcntl
    lock_path = str(ACTIVE_PROFILE_FILE) + ".lock"
    try:
        ACTIVE_PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                try:
                    data = json.loads(ACTIVE_PROFILE_FILE.read_text())
                except Exception:
                    data = {}
                data[project_path] = profiles
                ACTIVE_PROFILE_FILE.write_text(json.dumps(data, indent=2))
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass


def rotate_and_load_profiles(
    needed_profiles: List[str],
    project_path: Optional[str] = None,
) -> Tuple[List[str], List[str]]:
    """Rotate MCP profiles via profile-mcp CLI.

    Keeps essential profile untouched. Only rotates domain-specific servers.
    Calls profile-mcp --unload/--load to actually modify .claude.json.
    Returns (loaded_profiles, unloaded_profiles).
    """
    import subprocess

    if project_path is None:
        project_path = os.getcwd()

    if not needed_profiles:
        return [], []

    prev_profiles = get_active_profiles(project_path)
    profiles_to_unload = [p for p in prev_profiles if p not in needed_profiles and p != ESSENTIAL_PROFILE]
    profiles_to_load = [p for p in needed_profiles if p not in prev_profiles and p != ESSENTIAL_PROFILE]

    if not profiles_to_unload and not profiles_to_load:
        return [], []

    profile_mcp = str(Path.home() / ".claude" / "mcp-servers" / "profile-mcp" / "profile-mcp")

    # Unload old profiles
    for profile in profiles_to_unload:
        try:
            subprocess.run(
                [profile_mcp, "--unload", profile, project_path],
                capture_output=True, text=True, timeout=5
            )
        except Exception:
            pass

    # Load new profiles
    for profile in profiles_to_load:
        try:
            subprocess.run(
                [profile_mcp, "--load", profile, project_path],
                capture_output=True, text=True, timeout=5
            )
        except Exception:
            pass

    # Track active profiles
    new_active = [p for p in prev_profiles if p not in profiles_to_unload] + profiles_to_load
    save_active_profiles(project_path, new_active)

    return profiles_to_load, profiles_to_unload


def check_and_load_mcp_profiles(domains: List[Tuple[str, int]]) -> Tuple[List[str], List[str]]:
    """Check domains for needed MCP profiles. Rotates: unloads old, loads new.

    Returns (added_servers, removed_servers).
    """
    needed_profiles = []
    seen = set()

    for domain, score in domains:
        if score < 3:
            continue
        for profile in DOMAIN_MCP_PROFILES.get(domain, []):
            if profile not in seen:
                seen.add(profile)
                needed_profiles.append(profile)

    if not needed_profiles:
        return [], []

    return rotate_and_load_profiles(needed_profiles)


def build_context(prompt: str) -> str:
    """Analyze prompt and build additionalContext string.

    Returns empty string if no relevant context found.
    """
    scored = score_domains(prompt)
    if not scored:
        return ""

    # Get top domains (score > 0, max 3)
    top_domains = scored[:3]
    highest_score = top_domains[0][1] if top_domains else 0

    # Skip if confidence is too low (only contextual matches)
    if highest_score < 2:
        return ""

    # Compute complexity score
    complexity_score, tier = compute_complexity_score(prompt, scored)

    # Rotate and load domain-specific MCP profiles
    newly_added_servers, removed_servers = check_and_load_mcp_profiles(top_domains)

    parts = []
    parts.append("=" * 72)
    parts.append("WORKFLOW AUTOLOADER — Detected relevant context")
    parts.append("=" * 72)

    # Task tier guidance
    tier_guidance = {
        "Simple": "Execute directly. No ceremony needed.",
        "Standard": "State Goal/Result/Criteria before executing. Freeze criteria.",
        "Complex": "Use EnterPlanMode. Implicit team — spawn named teammates via the Agent tool.",
        "Critical": "EnterPlanMode, then spawn named teammates via the Agent tool (implicit team), then user approval before execution.",
    }
    parts.append("")
    parts.append(f"TASK TIER: {tier} (score: {complexity_score}/100) → {tier_guidance.get(tier, tier_guidance['Standard'])}")
    if tier not in ("Simple",):
        parts.append("  → Criteria freeze: don't change criteria to match output — iterate instead.")

    modules_to_load = []
    skills_to_suggest = []
    examples_to_show = []

    for domain, score in top_domains:
        if score < 2:
            continue

        config = DOMAIN_KEYWORDS[domain]

        # Collect modules
        for mod in config.get("modules", []):
            if mod not in modules_to_load:
                modules_to_load.append(mod)

        # Collect skills
        for skill in config.get("skills", []):
            if skill not in skills_to_suggest:
                skills_to_suggest.append(skill)

        # Collect examples
        ex_dir = config.get("examples", [""])[0] if config.get("examples") else ""
        if ex_dir and ex_dir not in [e[0] for e in examples_to_show]:
            examples = get_example_list(ex_dir)
            if examples:
                examples_to_show.append((ex_dir, examples))

    # Section 1: Modules
    if modules_to_load:
        parts.append("")
        parts.append("RELEVANT MODULES (load on demand):")
        for mod in modules_to_load[:4]:
            sections = get_module_sections(mod)
            parts.append(f"  - ~/.claude/modules/{mod}")
            if sections:
                parts.append(f"    {sections}")

    # Section 2: Skills
    if skills_to_suggest:
        parts.append("")
        parts.append("AVAILABLE SKILLS (invoke with /skill-name):")
        for skill in skills_to_suggest[:4]:
            desc = SKILL_DESCRIPTIONS.get(skill, skill)
            parts.append(f"  - {desc}")

    # Section 3: Examples
    if examples_to_show:
        parts.append("")
        parts.append("FEW-SHOT EXAMPLES (reference for approach):")
        for ex_dir, examples in examples_to_show[:3]:
            parts.append(f"  - ~/.claude/examples/{ex_dir}/: {', '.join(examples[:4])}")

    # Section 4: Domain-specific workflow hints
    top_domain = top_domains[0][0] if top_domains else ""
    workflow_hint = get_workflow_hint(top_domain)
    if workflow_hint:
        parts.append("")
        parts.append("SUGGESTED WORKFLOW:")
        parts.append(workflow_hint)

    # Section 5a: Missing parameter detection (actionable warnings)
    missing_warning = detect_missing_params(top_domain, prompt, tier, complexity_score)
    if missing_warning:
        parts.append("")
        parts.append(missing_warning)

    # Section 5b: Clarification questions based on domain (suggestions)
    questions = get_clarification_questions(top_domain, prompt)
    if questions:
        parts.append("")
        parts.append("CONSIDER ASKING:")
        for q in questions[:3]:
            parts.append(f"  - {q}")

    # Section 6: MCP rotation — session reopen required
    if newly_added_servers or removed_servers:
        parts.append("")
        parts.append("!" * 72)
        parts.append("MCP PROFILE ROTATED — SESSION REOPEN REQUIRED")
        parts.append("!" * 72)
        parts.append("")
        if newly_added_servers:
            parts.append(f"+ Added ({len(newly_added_servers)}): {', '.join(newly_added_servers)}")
        if removed_servers:
            parts.append(f"- Removed ({len(removed_servers)}): {', '.join(removed_servers)}")
        parts.append("")
        parts.append("Changes take effect after session restart.")
        parts.append("Claude Code loads MCP at session start — reopen to use new servers.")
        parts.append("")
        parts.append("ACTION: Inform user, recommend exit + reopen.")

    parts.append("")
    parts.append("=" * 72)

    return "\n".join(parts)


def get_workflow_hint(domain: str) -> str:
    """Return domain-specific workflow steps."""
    workflows = {
        "security": (
            "  1. Define scope and authorization\n"
            "  2. Reconnaissance (passive → active)\n"
            "  3. Vulnerability assessment\n"
            "  4. Exploitation (if authorized)\n"
            "  5. Report findings"
        ),
        "devops": (
            "  1. Analyze current infrastructure\n"
            "  2. Plan changes (IaC, dry-run)\n"
            "  3. Implement with rollback strategy\n"
            "  4. Deploy (canary/blue-green)\n"
            "  5. Monitor and validate"
        ),
        "dfir": (
            "  1. Classify incident (severity, type)\n"
            "  2. Contain (isolate affected systems)\n"
            "  3. Collect evidence (memory, disk, logs)\n"
            "  4. Analyze (timeline, IOCs, root cause)\n"
            "  5. Eradicate, recover, report"
        ),
        "planning": (
            "  1. Requirements gathering\n"
            "  2. WBS decomposition\n"
            "  3. PERT estimation (optimistic/likely/pessimistic)\n"
            "  4. Risk analysis\n"
            "  5. Timeline + resource allocation"
        ),
        "writing": (
            "  1. Literature review\n"
            "  2. Outline + structure\n"
            "  3. Draft sections\n"
            "  4. Peer review cycle\n"
            "  5. Final formatting + submission"
        ),
        "compliance": (
            "  1. Identify applicable standards\n"
            "  2. Gap analysis (current vs required)\n"
            "  3. Risk assessment\n"
            "  4. Remediation plan\n"
            "  5. Documentation + evidence"
        ),
        "procurement": (
            "  1. Requirements elicitation\n"
            "  2. Market research + vendor shortlist\n"
            "  3. Create TZ/RFP per 44-ФЗ/223-ФЗ\n"
            "  4. Evaluation criteria + TCO analysis\n"
            "  5. Review + compliance check"
        ),
        "network": (
            "  1. Inventory audit (NetBox/Snipe-IT)\n"
            "  2. Configuration review\n"
            "  3. Vulnerability assessment (VLANs, ACLs, VPN)\n"
            "  4. Compliance check (segmentation, ZTNA)\n"
            "  5. Report + remediation plan"
        ),
        "business_analysis": (
            "  1. Stakeholder analysis\n"
            "  2. AS-IS process modeling (BPMN)\n"
            "  3. Requirements elicitation (BABOK)\n"
            "  4. TO-BE design + gap analysis\n"
            "  5. Decision matrix + recommendation"
        ),
        "engineering": (
            "  1. Understand requirements\n"
            "  2. Write tests first (TDD)\n"
            "  3. Implement minimal code\n"
            "  4. Run tests + code review\n"
            "  5. Refactor + document"
        ),
        "education": (
            "  1. Assess learner level\n"
            "  2. Define learning objectives\n"
            "  3. Build from fundamentals\n"
            "  4. Provide practical exercises\n"
            "  5. Evaluate understanding"
        ),
        "reverse_engineering": (
            "  1. Static analysis (file type, strings, imports)\n"
            "  2. Disassembly / decompilation\n"
            "  3. Dynamic analysis (debugger, sandbox)\n"
            "  4. Document findings incrementally\n"
            "  5. Create IOCs if malware"
        ),
        "osint": (
            "  1. Define target scope\n"
            "  2. Passive reconnaissance\n"
            "  3. Social media + email analysis\n"
            "  4. Cross-reference findings\n"
            "  5. Document with sources"
        ),
        "lowlevel": (
            "  1. Identify target (kernel module, driver, firmware)\n"
            "  2. Static analysis (disassembly, strings, symbols)\n"
            "  3. Dynamic tracing (GDB, eBPF, strace)\n"
            "  4. Debug and patch\n"
            "  5. Document findings"
        ),
        "mcp": (
            "  1. Check existing MCP servers and profiles\n"
            "  2. Search registry for needed tools\n"
            "  3. Install and configure\n"
            "  4. Test connectivity\n"
            "  5. Document in profile manager"
        ),
        "orchestration": (
            "  1. Define requirements and constraints\n"
            "  2. Design architecture (pipelines, agents)\n"
            "  3. Implement components\n"
            "  4. Test end-to-end\n"
            "  5. Deploy and monitor"
        ),
        "prompting": (
            "  1. Define task and desired output\n"
            "  2. Choose technique (CoT, few-shot, etc.)\n"
            "  3. Iterate on prompt design\n"
            "  4. Evaluate against criteria\n"
            "  5. Document final prompt"
        ),
        "testing": (
            "  1. Analyze coverage gaps\n"
            "  2. Write test cases (unit, integration, e2e)\n"
            "  3. Run test suite\n"
            "  4. Fix failures and regressions\n"
            "  5. Report coverage metrics"
        ),
        "coding_agents": (
            "  1. Define agent requirements and scope\n"
            "  2. Create agent/skill definition\n"
            "  3. Implement agent logic\n"
            "  4. Test with sample inputs\n"
            "  5. Register and document"
        ),
        "general": (
            "  1. Clarify requirements and scope\n"
            "  2. Research: search codebase, docs, web as needed\n"
            "  3. Plan approach (EnterPlanMode if complex)\n"
            "  4. Execute: implement, test, iterate\n"
            "  5. Verify against requirements\n"
            "  6. Summarize results to user"
        ),
    }
    return workflows.get(domain, "")


def compose_workflows(w1: str, w2: str) -> str:
    """Merge two domain workflows: shared steps first, then domain-specific."""
    steps1 = [s.strip() for s in w1.strip().split('\n') if s.strip()]
    steps2 = [s.strip() for s in w2.strip().split('\n') if s.strip()]
    merged = []
    seen = set()
    for s in steps1 + steps2:
        clean = re.sub(r'^\s*\d+\.\s*', '', s).lower()
        if clean not in seen:
            seen.add(clean)
            merged.append(re.sub(r'^\s*\d+\.\s*', '', s))
    # Re-number
    result = []
    for i, step in enumerate(merged, 1):
        result.append(f"  {i}. {step}")
    return '\n'.join(result)


def get_clarification_questions(domain: str, prompt: str) -> List[str]:
    """Return domain-specific clarification questions."""
    questions: Dict[str, List[str]] = {
        "security": [
            "What is the authorized scope (IP range, domains)?",
            "What type of assessment (black-box, grey-box, white-box)?",
            "Is there written authorization for this test?",
        ],
        "devops": [
            "What is the target environment (dev/staging/prod)?",
            "What is the current infrastructure state?",
            "What is the rollback strategy?",
        ],
        "dfir": [
            "What is the incident severity (P1-P4)?",
            "Are affected systems isolated?",
            "What evidence has been preserved so far?",
        ],
        "compliance": [
            "Which standard(s) apply (ISO 27001, GDPR, ФЗ-152)?",
            "What is the current compliance level?",
            "Is there an existing risk register?",
        ],
        "procurement": [
            "Which law applies (44-ФЗ, 223-ФЗ, international)?",
            "What is the estimated budget?",
            "What are the key evaluation criteria?",
        ],
        "network": [
            "What network equipment is in scope?",
            "Is there a current network diagram?",
            "What are the segmentation requirements?",
        ],
        "writing": [
            "What is the target journal/conference?",
            "What citation style is required?",
            "What is the word/page limit?",
            "NOTE: For complex research tasks, use sequential-thinking MCP tool to break down multi-step reasoning before writing.",
        ],
        "planning": [
            "What is the project timeline?",
            "How many team members are available?",
            "What are the key risks/constraints?",
            "NOTE: For complex planning tasks, use sequential-thinking to map dependencies and critical path before estimating.",
        ],
        "business_analysis": [
            "Which methodology? (BABOK, TOGAF, C4, ArchiMate)",
            "Is there an existing AS-IS model or documentation?",
            "Who are the key stakeholders?",
            "NOTE: For complex requirements analysis, use sequential-thinking to trace stakeholder needs through to system constraints.",
        ],
        "engineering": [
            "What is the target language/framework?",
            "Are there existing tests or CI pipeline?",
            "What are the performance requirements?",
        ],
        "education": [
            "What is the learner's current level?",
            "What is the target learning outcome?",
            "What format? (tutorial, CTF, workshop, course)",
        ],
        "reverse_engineering": [
            "What is the target binary format (ELF, PE, firmware)?",
            "Is this malware analysis or software reverse engineering?",
            "What tools are available (Ghidra, IDA, radare2)?",
            "NOTE: For complex binaries, use sequential-thinking to plan analysis stages before diving into disassembly.",
        ],
        "lowlevel": [
            "What is the target architecture (x86-64, ARM, RISC-V)?",
            "What OS/kernel version?",
            "Is this debugging, tracing, or development?",
        ],
        "orchestration": [
            "Which framework? (LangChain, CrewAI, AutoGen, LlamaIndex)",
            "What is the use case (RAG, multi-agent, pipeline)?",
            "What LLM provider (Anthropic, OpenAI, local)?",
            "NOTE: For complex multi-agent designs, use sequential-thinking to reason through agent roles, handoffs, and failure modes.",
        ],
        "coding_agents": [
            "Which coding agent? (Claude Code, Cursor, Copilot, Aider)",
            "What is the task type (new feature, bug fix, refactor)?",
            "What language and framework?",
        ],
        "mcp": [
            "Which MCP server do you need?",
            "Is this about configuration, development, or usage?",
            "Do you have API keys configured?",
        ],
        "testing": [
            "What type of testing? (unit, integration, E2E, eval)",
            "What framework? (pytest, jest, promptfoo)",
            "What is being tested (code, agent, LLM output)?",
        ],
        "prompting": [
            "What is the task type? (reasoning, generation, extraction)",
            "What model? (Claude, GPT, local LLM)",
            "What are the quality requirements?",
            "NOTE: For complex prompting tasks, use sequential-thinking to reason through failure modes and edge cases before finalizing.",
        ],
        "osint": [
            "What is the investigation target (person, domain, org)?",
            "What OSINT sources are available?",
            "Is there legal authorization for this investigation?",
            "NOTE: For complex investigations with multiple leads, use sequential-thinking to prioritize collection threads.",
        ],
    }
    return questions.get(domain, [])


# ─────────────────────────────────────────────────────────────────
# MISSING PARAMETER DETECTION
# Checks if critical domain-specific parameters are present in prompt.
# Returns warning string if essential params missing, empty if OK.
# ─────────────────────────────────────────────────────────────────

# Required parameters per domain — each tuple: (param_name, detection_patterns, question)
DOMAIN_REQUIRED_PARAMS: Dict[str, List[Tuple[str, List[str], str]]] = {
    "security": [
        ("target", [
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",  # IP
            r"[a-z0-9][-a-z0-9]*\.[a-z]{2,}",         # domain
            r"https?://",                                # URL
            r"target\s*[:=]",
        ], "target (IP, домен или URL)"),
        ("scope", [
            r"scope\s*[:=]", r"скоуп", r"область", r"периметр",
            r"black.?box", r"grey.?box", r"white.?box",
            r"internal", r"external", r"recon",
        ], "scope (black/grey/white-box, internal/external)"),
    ],
    "osint": [
        ("target", [
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
            r"[a-z0-9][-a-z0-9]*\.[a-z]{2,}",
            r"@[a-z]", r"username", r"email",
            r"компани|организаци|персон|человек|домен",
        ], "target (person, org, domain, email)"),
    ],
    "devops": [
        ("environment", [
            r"dev\b", r"staging", r"prod", r"production",
            r"окружени", r"среда", r"кластер",
        ], "environment (dev/staging/prod)"),
    ],
    "dfir": [
        ("severity", [
            r"p[1-4]", r"sev\s*[1-4]", r"critical", r"high",
            r"severity", r"приоритет", r"инцидент",
        ], "severity (P1-P4)"),
    ],
    "network": [
        ("target", [
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
            r"[a-z0-9][-a-z0-9]*\.[a-z]{2,}",
            r"vlan", r"subnet", r"подсет", r"сегмент",
            r"mikrotik", r"cisco", r"juniper",
        ], "target (IP/subnet/устройство)"),
    ],
    "compliance": [
        ("standard", [
            r"iso\s*27001", r"gdpr", r"pci.?dss", r"нист", r"nist",
            r"152.?фз", r"фз.?152", r"187.?фз", r"фз.?187",
            r"гост", r"57580", r"cobit", r"sox", r"hipaa",
        ], "standard (ISO 27001, GDPR, PCI-DSS, ФЗ-152/187, ГОСТ)"),
    ],
    "engineering": [
        ("target_files", [
            r"\.\w{1,5}$", r"src/", r"lib/", r"app/",
            r"component", r"module", r"service",
            r"\.py$", r"\.ts$", r"\.go$", r"\.rs$",
        ], "target files or components"),
    ],
    "reverse_engineering": [
        ("target", [
            r"\.exe$", r"\.elf$", r"\.bin$", r"\.apk$",
            r"\.dll$", r"\.so$", r"\.dylib$", r"\.ko$",
            r"sample", r"malware", r"firmware", r"binary",
        ], "target (binary file or sample)"),
    ],
    "procurement": [
        ("budget", [
            r"\d+.*руб", r"\$\d+", r"нмцк", r"nmck",
            r"бюджет", r"budget", r"цена", r"price",
            r"44.?фз", r"223.?фз",
        ], "budget or НМЦК (сумма, ФЗ)"),
    ],
    "lowlevel": [
        ("target", [
            r"kernel", r"driver", r"module", r"\.ko$",
            r"ядро", r"драйвер", r"модуль",
            r"ebpf", r"bpf", r"kprobe", r"ftrace",
        ], "target (kernel module, driver, subsystem)"),
    ],
    "planning": [
        ("scope", [
            r"sprint", r"milestone", r"deadline", r"okr",
            r"roadmap", r"backlog", r"estimate",
            r"спринт", r"дедлайн", r"план",
        ], "scope (sprint, milestone, deadline)"),
    ],
    "business_analysis": [
        ("deliverable", [
            r"brd", r"srs", r"user.?stor", r"требовани",
            r"stakeholder", r"as.?is", r"to.?be", r"use.?case",
            r"бизнес.?требовани", r"тз", r"спецификаци",
        ], "deliverable (BRD, SRS, user stories, ТЗ)"),
    ],
}

# Domains that require NETWORK_ACTIVE confirmation — always check target
NETWORK_ACTIVE_DOMAINS = {"security", "osint", "network"}


def detect_missing_params(domain: str, prompt: str, tier: str, complexity_score: int) -> str:
    """Detect missing essential parameters for the domain and tier.

    Returns formatted warning string, or empty string if all OK.
    """
    # Simple tasks — don't check
    if tier == "Simple":
        return ""

    prompt_lower = prompt.lower()
    required = DOMAIN_REQUIRED_PARAMS.get(domain, [])
    if not required:
        return ""

    missing = []
    for param_name, patterns, description in required:
        found = any(re.search(p, prompt_lower) for p in patterns)
        if not found:
            missing.append(description)

    if not missing:
        return ""

    # Build warning
    severity = "CRITICAL" if domain in NETWORK_ACTIVE_DOMAINS else "RECOMMENDED"
    parts = []
    parts.append(f"CLARIFICATION {severity}:")
    for m in missing:
        parts.append(f"  - Не указан {m}")

    if domain in NETWORK_ACTIVE_DOMAINS:
        parts.append("  ⚠ NETWORK_ACTIVE домен — target и scope обязательны перед выполнением.")

    return "\n".join(parts)


def analyze_prompt(prompt: str) -> str:
    """Main entry point — analyze prompt and return context string."""
    return build_context(prompt)


if __name__ == "__main__":
    # CLI testing mode
    import sys
    if len(sys.argv) > 1:
        test_prompt = " ".join(sys.argv[1:])
    else:
        test_prompt = "Run nmap scan on 192.168.1.0/24 and create sigma rules for detections"
    result = analyze_prompt(test_prompt)
    if result:
        print(result)
    else:
        print("No relevant context detected.")
