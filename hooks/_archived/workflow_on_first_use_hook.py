#!/usr/bin/env python3
"""
Workflow-on-First-Use Hook (PostToolUse on Bash)

Detects first use of a tool that lacks a documented workflow in modules.
Logs a gap and outputs a reminder to create the workflow.

Hook Type: PostToolUse (Bash only)
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
MODULES_DIR = Path.home() / ".claude" / "modules"
TRACKER_FILE = DATA_DIR / "workflow_tracker.json"
LOG_FILE = DATA_DIR / "workflow_gaps.jsonl"

# Tools we monitor for workflow existence
# Map: regex pattern on bash command → tool canonical name
TOOL_PATTERNS = {
    r'\bnmap\b': 'nmap',
    r'\bnuclei\b': 'nuclei',
    r'\btrivy\b': 'trivy',
    r'\bterraform\b': 'terraform',
    r'\bansible\b': 'ansible',
    r'\bkubectl\b': 'kubernetes',
    r'\bhelm\b': 'helm',
    r'\bdocker\b': 'docker',
    r'\bdocker-compose\b': 'docker-compose',
    r'\bprometheus\b': 'prometheus',
    r'\bgrafana\b': 'grafana',
    r'\bvault\b': 'vault',
    r'\bkeycloak\b': 'keycloak',
    r'\bsonarqube\b': 'sonarqube',
    r'\bwazuh\b': 'wazuh',
    r'\bsuricata\b': 'suricata',
    r'\bzeek\b': 'zeek',
    r'\bfalco\b': 'falco',
    r'\bcrowdsec\b': 'crowdsec',
    r'\bistio\b': 'istio',
    r'\blinkerd\b': 'linkerd',
    r'\bcilium\b': 'cilium',
    r'\bargocd\b': 'argocd',
    r'\bflux\b': 'flux',
    r'\bjenkins\b': 'jenkins',
    r'\bgitlab-ci\b': 'gitlab-ci',
    r'\bnginx\b': 'nginx',
    r'\bhaproxy\b': 'haproxy',
    r'\btraefik\b': 'traefik',
    r'\bpostgresql\b|\bpsql\b': 'postgresql',
    r'\bredis-cli\b|\bredis\b': 'redis',
    r'\bminio\b|\bmc\s': 'minio',
    r'\belasticsearch\b|\bcurl.*:9200\b': 'elasticsearch',
    r'\bloki\b': 'loki',
    r'\bjaeger\b': 'jaeger',
    r'\bzabbix\b': 'zabbix',
    r'\bopenvpn\b': 'openvpn',
    r'\bwireguard\b|\bwg\b': 'wireguard',
    r'\bfreeipa\b|\bipa\b': 'freeipa',
    r'\bmisp\b': 'misp',
    r'\bthehive\b': 'thehive',
    r'\bopenvas\b|\bgvm\b': 'openvas',
    r'\bcert-manager\b': 'cert-manager',
    r'\bmikrotik\b|\brouterOS\b': 'mikrotik',
    r'\bopnsense\b': 'opnsense',
    r'\bnetbox\b': 'netbox',
    r'\bsnipe-it\b': 'snipe-it',
    r'\bpacketfence\b': 'packetfence',
    r'\bpacker\b': 'packer',
    r'\bvagrant\b': 'vagrant',
    r'\bk3s\b': 'k3s',
    r'\bcrossplane\b': 'crossplane',
    r'\bceph\b': 'ceph',
    r'\bproxmox\b|\bpvesh\b': 'proxmox',
    r'\bn8n\b': 'n8n',
    r'\bvector\b': 'vector',
    r'\bvictoriametrics\b|\bvmselect\b': 'victoriametrics',
}

# Tools known to have full workflows (Deployment+Config+Operations)
TOOLS_WITH_WORKFLOWS = {
    'trivy', 'trivy-operator', 'defectdojo', 'dependency-track',
    'vault', 'keycloak', 'lynis', 'mega-linter', 'smallstep',
    'sonarqube', 'teleport',
    'ceph', 'crossplane', 'k3s', 'opencost', 'packer',
    'proxmox', 'pulp', 'tinkerbell', 'vector', 'victorialogs',
    'victoriametrics', 'n8n',
    'bunkerweb', 'netdisco', 'ntopng', 'safeline', 'stalwart',
}


def load_tracker() -> dict:
    """Load the workflow tracker (which tools have been used)."""
    if TRACKER_FILE.exists():
        try:
            with open(TRACKER_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"seen_tools": {}, "notified_tools": []}


def save_tracker(tracker: dict) -> None:
    """Save the workflow tracker."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2)


def log_gap(tool_name: str) -> None:
    """Log a workflow gap to JSONL."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool_name,
        "gap_type": "missing_workflow",
        "message": f"Tool '{tool_name}' used but has no documented workflow in modules",
        "suggested_action": f"Create workflow section for {tool_name} with: Purpose, Deployment, Configuration, Operations, Integration, Best Practices"
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def detect_tool(command: str) -> str | None:
    """Detect which tool is being used from a bash command."""
    for pattern, tool_name in TOOL_PATTERNS.items():
        if re.search(pattern, command, re.IGNORECASE):
            return tool_name
    return None


def has_workflow(tool_name: str) -> bool:
    """Check if a tool has a documented workflow in any module."""
    return tool_name in TOOLS_WITH_WORKFLOWS


def main():
    """Detect first use of tool without workflow, log gap."""
    try:
        input_data = json.load(sys.stdin)
        tool_input = input_data.get("tool_input", {})

        # Get the bash command
        command = ""
        if isinstance(tool_input, dict):
            command = tool_input.get("command", "")
        elif isinstance(tool_input, str):
            command = tool_input

        if not command:
            print(json.dumps({}))
            return

        # Detect tool
        detected_tool = detect_tool(command)
        if not detected_tool:
            print(json.dumps({}))
            return

        # Load tracker
        tracker = load_tracker()

        # Record usage
        if detected_tool not in tracker["seen_tools"]:
            tracker["seen_tools"][detected_tool] = {
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "count": 0
            }
        tracker["seen_tools"][detected_tool]["count"] = (
            tracker["seen_tools"][detected_tool].get("count", 0) + 1
        )

        # Check if workflow exists
        if not has_workflow(detected_tool):
            if detected_tool not in tracker.get("notified_tools", []):
                # First use without workflow — notify
                tracker.setdefault("notified_tools", []).append(detected_tool)
                log_gap(detected_tool)
                print(
                    f"📝 Workflow gap: '{detected_tool}' used for first time "
                    f"but has no documented workflow. "
                    f"Consider creating workflow in the appropriate module.",
                    file=sys.stderr,
                )

        save_tracker(tracker)
        print(json.dumps({}))

    except Exception as e:
        print(f"Workflow hook error: {e}", file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
