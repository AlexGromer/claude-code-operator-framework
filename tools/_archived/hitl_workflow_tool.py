#!/usr/bin/env python3
"""
HITL Workflow Tool (GAP-WORKFLOW-006)

Human-in-the-Loop workflow management for agent operations.
Defines approval checkpoints, escalation paths, and intervention points.

Usage:
    python hitl_workflow_tool.py --define-workflow WORKFLOW_NAME
    python hitl_workflow_tool.py --checkpoint CHECKPOINT_ID --action approve|reject
    python hitl_workflow_tool.py --status
    python hitl_workflow_tool.py --escalate TASK_ID --reason REASON
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
WORKFLOWS_FILE = DATA_DIR / "hitl_workflows.json"
CHECKPOINTS_FILE = DATA_DIR / "hitl_checkpoints.jsonl"
ESCALATIONS_FILE = DATA_DIR / "hitl_escalations.jsonl"


class CheckpointType(Enum):
    APPROVAL = "approval"          # Requires explicit human approval
    REVIEW = "review"              # Human review, can auto-proceed after timeout
    NOTIFICATION = "notification"  # Notify human, no blocking
    ESCALATION = "escalation"      # Auto-escalate to supervisor


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Checkpoint:
    """A checkpoint in the HITL workflow."""
    id: str
    workflow_id: str
    checkpoint_type: CheckpointType
    risk_level: RiskLevel
    description: str
    required_approvers: int = 1
    timeout_minutes: int = 60
    auto_approve_on_timeout: bool = False
    metadata: Dict = field(default_factory=dict)


@dataclass
class CheckpointStatus:
    """Status of a checkpoint execution."""
    checkpoint_id: str
    task_id: str
    status: str  # pending, approved, rejected, escalated, timed_out
    created_at: str
    resolved_at: Optional[str]
    resolved_by: Optional[str]
    approvals: List[str] = field(default_factory=list)
    rejections: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)


@dataclass
class HITLWorkflow:
    """Complete HITL workflow definition."""
    id: str
    name: str
    description: str
    checkpoints: List[Checkpoint]
    escalation_chain: List[str]
    default_timeout: int = 60
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# Predefined workflow templates
WORKFLOW_TEMPLATES = {
    "destructive_operations": HITLWorkflow(
        id="wf-destructive",
        name="Destructive Operations",
        description="Workflow for operations that delete data or modify infrastructure",
        checkpoints=[
            Checkpoint(
                id="cp-destructive-review",
                workflow_id="wf-destructive",
                checkpoint_type=CheckpointType.APPROVAL,
                risk_level=RiskLevel.CRITICAL,
                description="Review destructive operation before execution",
                required_approvers=1,
                timeout_minutes=15,
                auto_approve_on_timeout=False,
            ),
        ],
        escalation_chain=["user", "admin", "security"],
    ),
    "credential_access": HITLWorkflow(
        id="wf-credential",
        name="Credential Access",
        description="Workflow for accessing or modifying credentials",
        checkpoints=[
            Checkpoint(
                id="cp-credential-notify",
                workflow_id="wf-credential",
                checkpoint_type=CheckpointType.NOTIFICATION,
                risk_level=RiskLevel.HIGH,
                description="Notify about credential access attempt",
            ),
            Checkpoint(
                id="cp-credential-approve",
                workflow_id="wf-credential",
                checkpoint_type=CheckpointType.APPROVAL,
                risk_level=RiskLevel.HIGH,
                description="Approve credential access",
                timeout_minutes=30,
            ),
        ],
        escalation_chain=["user", "security"],
    ),
    "external_api": HITLWorkflow(
        id="wf-external-api",
        name="External API Calls",
        description="Workflow for making external API calls",
        checkpoints=[
            Checkpoint(
                id="cp-api-review",
                workflow_id="wf-external-api",
                checkpoint_type=CheckpointType.REVIEW,
                risk_level=RiskLevel.MEDIUM,
                description="Review external API call",
                timeout_minutes=60,
                auto_approve_on_timeout=True,
            ),
        ],
        escalation_chain=["user"],
    ),
}


def load_workflows() -> Dict[str, HITLWorkflow]:
    """Load workflows from file."""
    if WORKFLOWS_FILE.exists():
        data = json.loads(WORKFLOWS_FILE.read_text())
        workflows = {}
        for wf_id, wf_data in data.items():
            checkpoints = [
                Checkpoint(
                    **{**cp, "checkpoint_type": CheckpointType(cp["checkpoint_type"]),
                       "risk_level": RiskLevel(cp["risk_level"])}
                )
                for cp in wf_data.get("checkpoints", [])
            ]
            wf_data["checkpoints"] = checkpoints
            workflows[wf_id] = HITLWorkflow(**wf_data)
        return workflows
    return {}


def save_workflows(workflows: Dict[str, HITLWorkflow]):
    """Save workflows to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {}
    for wf_id, wf in workflows.items():
        wf_dict = asdict(wf)
        for cp in wf_dict["checkpoints"]:
            cp["checkpoint_type"] = cp["checkpoint_type"].value
            cp["risk_level"] = cp["risk_level"].value
        data[wf_id] = wf_dict
    with open(WORKFLOWS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def create_checkpoint_status(checkpoint: Checkpoint, task_id: str) -> CheckpointStatus:
    """Create a new checkpoint status."""
    return CheckpointStatus(
        checkpoint_id=checkpoint.id,
        task_id=task_id,
        status="pending",
        created_at=datetime.now().isoformat(),
        resolved_at=None,
        resolved_by=None,
    )


def log_checkpoint_status(status: CheckpointStatus):
    """Log checkpoint status."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINTS_FILE, "a") as f:
        f.write(json.dumps(asdict(status)) + "\n")


def get_pending_checkpoints() -> List[Dict]:
    """Get all pending checkpoints."""
    pending = []
    if CHECKPOINTS_FILE.exists():
        for line in CHECKPOINTS_FILE.read_text().splitlines():
            if line.strip():
                entry = json.loads(line)
                if entry.get("status") == "pending":
                    pending.append(entry)
    return pending


def resolve_checkpoint(checkpoint_id: str, task_id: str, action: str, by: str = "user"):
    """Resolve a pending checkpoint."""
    # Read all entries
    entries = []
    if CHECKPOINTS_FILE.exists():
        for line in CHECKPOINTS_FILE.read_text().splitlines():
            if line.strip():
                entries.append(json.loads(line))

    # Update matching entry
    for entry in entries:
        if entry["checkpoint_id"] == checkpoint_id and entry["task_id"] == task_id:
            if entry["status"] == "pending":
                entry["status"] = action
                entry["resolved_at"] = datetime.now().isoformat()
                entry["resolved_by"] = by
                if action == "approved":
                    entry["approvals"].append(by)
                elif action == "rejected":
                    entry["rejections"].append(by)

    # Write back
    with open(CHECKPOINTS_FILE, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def log_escalation(task_id: str, reason: str, escalated_to: str):
    """Log an escalation."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "task_id": task_id,
        "reason": reason,
        "escalated_to": escalated_to,
        "timestamp": datetime.now().isoformat(),
    }
    with open(ESCALATIONS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def print_workflows(workflows: Dict[str, HITLWorkflow]):
    """Print available workflows."""
    print("\n" + "="*60)
    print("HITL WORKFLOWS")
    print("="*60)

    for wf_id, wf in workflows.items():
        print(f"\n📋 {wf.name} ({wf_id})")
        print(f"   {wf.description}")
        print(f"   Checkpoints: {len(wf.checkpoints)}")
        print(f"   Escalation: {' → '.join(wf.escalation_chain)}")

        for cp in wf.checkpoints:
            risk_icons = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
            icon = risk_icons.get(cp.risk_level.value, "⚪")
            print(f"      {icon} {cp.id}: {cp.checkpoint_type.value} ({cp.timeout_minutes}min)")

    print("\n" + "="*60)


def print_status():
    """Print current checkpoint status."""
    pending = get_pending_checkpoints()

    print("\n" + "="*60)
    print("HITL CHECKPOINT STATUS")
    print("="*60)

    if not pending:
        print("\n✅ No pending checkpoints")
    else:
        print(f"\n⏳ {len(pending)} pending checkpoints:")
        for cp in pending:
            created = datetime.fromisoformat(cp["created_at"])
            age_mins = int((datetime.now() - created).total_seconds() / 60)
            print(f"\n   [{cp['checkpoint_id']}] Task: {cp['task_id']}")
            print(f"      Status: {cp['status']}")
            print(f"      Age: {age_mins} minutes")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="HITL Workflow Tool")
    parser.add_argument("--define-workflow", help="Define workflow from template")
    parser.add_argument("--list", "-l", action="store_true", help="List workflows")
    parser.add_argument("--status", "-s", action="store_true", help="Show checkpoint status")
    parser.add_argument("--checkpoint", help="Checkpoint ID to act on")
    parser.add_argument("--task", help="Task ID")
    parser.add_argument("--action", choices=["approve", "reject", "escalate"])
    parser.add_argument("--escalate", help="Task ID to escalate")
    parser.add_argument("--reason", help="Escalation reason")
    parser.add_argument("--init-templates", action="store_true", help="Initialize templates")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    workflows = load_workflows()

    if args.init_templates:
        for template_name, template in WORKFLOW_TEMPLATES.items():
            workflows[template.id] = template
        save_workflows(workflows)
        print(f"✅ Initialized {len(WORKFLOW_TEMPLATES)} workflow templates")
        return 0

    if args.define_workflow:
        if args.define_workflow in WORKFLOW_TEMPLATES:
            template = WORKFLOW_TEMPLATES[args.define_workflow]
            workflows[template.id] = template
            save_workflows(workflows)
            print(f"✅ Created workflow: {template.name}")
        else:
            print(f"❌ Template not found: {args.define_workflow}")
            print(f"   Available: {', '.join(WORKFLOW_TEMPLATES.keys())}")
            return 1
        return 0

    if args.checkpoint and args.action:
        if args.action in ["approve", "reject"]:
            resolve_checkpoint(args.checkpoint, args.task or "unknown",
                             "approved" if args.action == "approve" else "rejected")
            print(f"✅ Checkpoint {args.checkpoint}: {args.action}d")
        return 0

    if args.escalate:
        if not args.reason:
            print("❌ --reason required for escalation")
            return 1
        log_escalation(args.escalate, args.reason, "admin")
        print(f"✅ Task {args.escalate} escalated")
        return 0

    if args.status:
        if args.json:
            print(json.dumps(get_pending_checkpoints(), indent=2))
        else:
            print_status()
        return 0

    if args.list or not any([args.define_workflow, args.checkpoint, args.escalate]):
        # Merge templates with saved workflows
        all_workflows = {**{t.id: t for t in WORKFLOW_TEMPLATES.values()}, **workflows}
        if args.json:
            print(json.dumps({k: asdict(v) for k, v in all_workflows.items()}, indent=2, default=str))
        else:
            print_workflows(all_workflows)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
