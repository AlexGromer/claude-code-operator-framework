#!/usr/bin/env python3
"""
HITL Queue Monitor (GAP-HITL-*)

Monitors Human-in-the-Loop approval queue for high-risk operations.
Ensures CREDENTIAL and DESTRUCTIVE operations get timely review.

Usage:
    python hitl_queue_monitor.py --status
    python hitl_queue_monitor.py --pending
    python hitl_queue_monitor.py --approve REQ-001
    python hitl_queue_monitor.py --stats
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
QUEUE_FILE = DATA_DIR / "hitl_queue.json"
HISTORY_FILE = DATA_DIR / "hitl_history.jsonl"

# Operation risk levels
RISK_LEVELS = {
    "CRITICAL": {"timeout_minutes": 5, "auto_reject": True, "requires_explicit": True},
    "HIGH": {"timeout_minutes": 15, "auto_reject": False, "requires_explicit": True},
    "MEDIUM": {"timeout_minutes": 60, "auto_reject": False, "requires_explicit": False},
}

# Operations requiring HITL
HITL_OPERATIONS = {
    "rm -rf": "CRITICAL",
    "DROP DATABASE": "CRITICAL",
    "DROP TABLE": "CRITICAL",
    "terraform destroy": "CRITICAL",
    "kubectl delete": "HIGH",
    "git reset --hard": "HIGH",
    "git push --force": "HIGH",
    "chmod 777": "HIGH",
    "sudo": "HIGH",
    "password": "MEDIUM",
    "credential": "MEDIUM",
    "api_key": "MEDIUM",
    "secret": "MEDIUM",
}


@dataclass
class HITLRequest:
    """A HITL approval request."""
    id: str
    operation: str
    command: str
    risk_level: str
    requested_at: str
    expires_at: str
    status: str  # PENDING, APPROVED, REJECTED, EXPIRED
    context: str
    decision_at: Optional[str]
    decided_by: Optional[str]


def generate_request_id() -> str:
    """Generate unique request ID."""
    now = datetime.now()
    return f"REQ-{now.strftime('%Y%m%d%H%M%S%f')[:17]}"


def load_queue() -> Dict:
    """Load queue from file."""
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text())
    return {"requests": [], "last_updated": None}


def save_queue(data: Dict):
    """Save queue to file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    with open(QUEUE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def save_to_history(request: Dict):
    """Save completed request to history."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(request) + "\n")


def detect_risk_level(command: str) -> str:
    """Detect risk level of a command."""
    command_lower = command.lower()

    for pattern, level in HITL_OPERATIONS.items():
        if pattern.lower() in command_lower:
            return level

    return "MEDIUM"


def create_request(
    operation: str,
    command: str,
    context: str = "",
    risk_level: str = None
) -> HITLRequest:
    """Create a new HITL request."""
    if risk_level is None:
        risk_level = detect_risk_level(command)

    now = datetime.now()
    timeout = RISK_LEVELS[risk_level]["timeout_minutes"]
    expires = now + timedelta(minutes=timeout)

    request = HITLRequest(
        id=generate_request_id(),
        operation=operation,
        command=command[:500],  # Truncate long commands
        risk_level=risk_level,
        requested_at=now.isoformat(),
        expires_at=expires.isoformat(),
        status="PENDING",
        context=context,
        decision_at=None,
        decided_by=None,
    )

    # Add to queue
    queue = load_queue()
    queue["requests"].append(asdict(request))
    save_queue(queue)

    return request


def get_pending_requests() -> List[Dict]:
    """Get all pending requests."""
    queue = load_queue()
    now = datetime.now()
    pending = []

    for req in queue["requests"]:
        if req["status"] != "PENDING":
            continue

        # Check if expired
        expires = datetime.fromisoformat(req["expires_at"])
        if now > expires:
            req["status"] = "EXPIRED"
            save_to_history(req)
        else:
            pending.append(req)

    # Update queue with only pending
    queue["requests"] = [r for r in queue["requests"] if r["status"] == "PENDING"]
    save_queue(queue)

    return pending


def approve_request(request_id: str, decided_by: str = "user") -> bool:
    """Approve a request."""
    queue = load_queue()

    for req in queue["requests"]:
        if req["id"] == request_id and req["status"] == "PENDING":
            req["status"] = "APPROVED"
            req["decision_at"] = datetime.now().isoformat()
            req["decided_by"] = decided_by

            # Move to history
            save_to_history(req)
            queue["requests"] = [r for r in queue["requests"] if r["id"] != request_id]
            save_queue(queue)
            return True

    return False


def reject_request(request_id: str, decided_by: str = "user") -> bool:
    """Reject a request."""
    queue = load_queue()

    for req in queue["requests"]:
        if req["id"] == request_id and req["status"] == "PENDING":
            req["status"] = "REJECTED"
            req["decision_at"] = datetime.now().isoformat()
            req["decided_by"] = decided_by

            # Move to history
            save_to_history(req)
            queue["requests"] = [r for r in queue["requests"] if r["id"] != request_id]
            save_queue(queue)
            return True

    return False


def expire_old_requests():
    """Expire old requests and handle auto-reject."""
    queue = load_queue()
    now = datetime.now()

    for req in queue["requests"]:
        if req["status"] != "PENDING":
            continue

        expires = datetime.fromisoformat(req["expires_at"])
        if now > expires:
            risk_config = RISK_LEVELS.get(req["risk_level"], {})
            if risk_config.get("auto_reject"):
                req["status"] = "REJECTED"
                req["decided_by"] = "auto_timeout"
            else:
                req["status"] = "EXPIRED"

            req["decision_at"] = now.isoformat()
            save_to_history(req)

    queue["requests"] = [r for r in queue["requests"] if r["status"] == "PENDING"]
    save_queue(queue)


def get_statistics() -> Dict:
    """Get queue statistics."""
    queue = load_queue()
    pending = get_pending_requests()

    stats = {
        "timestamp": datetime.now().isoformat(),
        "pending_count": len(pending),
        "by_risk_level": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0},
        "oldest_pending_minutes": 0,
        "history": {"approved": 0, "rejected": 0, "expired": 0},
    }

    # Count by risk level
    for req in pending:
        level = req.get("risk_level", "MEDIUM")
        if level in stats["by_risk_level"]:
            stats["by_risk_level"][level] += 1

    # Find oldest
    if pending:
        oldest = min(pending, key=lambda x: x["requested_at"])
        requested = datetime.fromisoformat(oldest["requested_at"])
        stats["oldest_pending_minutes"] = int((datetime.now() - requested).total_seconds() / 60)

    # Load history stats
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    status = entry.get("status", "").lower()
                    if status in stats["history"]:
                        stats["history"][status] += 1

    return stats


def check_request_status(request_id: str) -> Optional[Dict]:
    """Check status of a specific request."""
    queue = load_queue()

    for req in queue["requests"]:
        if req["id"] == request_id:
            return req

    # Check history
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("id") == request_id:
                        return entry

    return None


def print_pending(pending: List[Dict]):
    """Print pending requests."""
    print("\n" + "="*60)
    print("HITL PENDING APPROVALS")
    print("="*60)

    if not pending:
        print("\n✅ No pending requests")
    else:
        now = datetime.now()
        for req in pending:
            level_icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}
            icon = level_icons.get(req["risk_level"], "⚪")

            expires = datetime.fromisoformat(req["expires_at"])
            remaining = int((expires - now).total_seconds() / 60)

            print(f"\n{icon} [{req['id']}] {req['risk_level']}")
            print(f"   Operation: {req['operation']}")
            print(f"   Command: {req['command'][:60]}...")
            print(f"   Requested: {req['requested_at'][:19]}")
            print(f"   Expires in: {remaining} minutes")
            if req.get("context"):
                print(f"   Context: {req['context'][:50]}")

    print("\n" + "="*60)


def print_stats(stats: Dict):
    """Print statistics."""
    print("\n" + "="*60)
    print("HITL QUEUE STATISTICS")
    print("="*60)

    print(f"\nPending: {stats['pending_count']}")
    print(f"Oldest pending: {stats['oldest_pending_minutes']} minutes")

    print(f"\nBy Risk Level:")
    for level, count in stats["by_risk_level"].items():
        print(f"  {level}: {count}")

    print(f"\nHistory:")
    for status, count in stats["history"].items():
        print(f"  {status.capitalize()}: {count}")

    # Alert if critical pending
    if stats["by_risk_level"]["CRITICAL"] > 0:
        print(f"\n⚠️  ALERT: {stats['by_risk_level']['CRITICAL']} CRITICAL requests pending!")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="HITL Queue Monitor")
    parser.add_argument("--status", "-s", action="store_true", help="Show queue status")
    parser.add_argument("--pending", "-p", action="store_true", help="Show pending requests")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--approve", "-a", help="Approve request ID")
    parser.add_argument("--reject", "-r", help="Reject request ID")
    parser.add_argument("--check", "-c", help="Check specific request status")
    parser.add_argument("--create", help="Create test request (operation)")
    parser.add_argument("--command", help="Command for test request")
    parser.add_argument("--expire-old", action="store_true", help="Expire old requests")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Always expire old requests first
    expire_old_requests()

    if args.status or args.pending:
        pending = get_pending_requests()
        if args.json:
            print(json.dumps(pending, indent=2))
        else:
            print_pending(pending)
        return 0

    if args.stats:
        stats = get_statistics()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print_stats(stats)
        return 0

    if args.approve:
        if approve_request(args.approve):
            print(f"✅ Request {args.approve} approved")
        else:
            print(f"❌ Request {args.approve} not found or already processed")
        return 0

    if args.reject:
        if reject_request(args.reject):
            print(f"✅ Request {args.reject} rejected")
        else:
            print(f"❌ Request {args.reject} not found or already processed")
        return 0

    if args.check:
        result = check_request_status(args.check)
        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Status: {result['status']}")
        else:
            print(f"Request not found: {args.check}")
        return 0

    if args.create:
        command = args.command or args.create
        request = create_request(args.create, command)
        if args.json:
            print(json.dumps(asdict(request), indent=2))
        else:
            print(f"✅ Created request: {request.id}")
        return 0

    if args.expire_old:
        expire_old_requests()
        print("✅ Expired old requests processed")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
