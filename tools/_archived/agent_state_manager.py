#!/usr/bin/env python3
"""
Agent State Manager (GAP-AGENT-STATE-001)

Manages persistent state for agent conversations and workflows.
Supports checkpointing, state recovery, and cross-session persistence.

Usage:
    python agent_state_manager.py --save STATE_ID --data DATA
    python agent_state_manager.py --load STATE_ID
    python agent_state_manager.py --checkpoint SESSION_ID
    python agent_state_manager.py --list
    python agent_state_manager.py --verify
"""

import argparse
import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

DATA_DIR = Path.home() / ".claude" / "evaluation" / "data"
STATES_DIR = DATA_DIR / "agent_states"
CHECKPOINTS_DIR = DATA_DIR / "agent_checkpoints"
INDEX_FILE = DATA_DIR / "state_index.json"


@dataclass
class AgentState:
    """Represents agent state at a point in time."""
    state_id: str
    session_id: str
    created_at: str
    updated_at: str
    version: int
    data: Dict[str, Any]
    metadata: Dict = field(default_factory=dict)
    checksum: str = ""


@dataclass
class StateCheckpoint:
    """A checkpoint of agent state."""
    checkpoint_id: str
    state_id: str
    session_id: str
    created_at: str
    reason: str
    data_snapshot: Dict[str, Any]
    can_restore: bool = True


def generate_state_id(session_id: str, prefix: str = "state") -> str:
    """Generate unique state ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    hash_input = f"{session_id}:{timestamp}"
    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"{prefix}-{short_hash}"


def calculate_checksum(data: Dict) -> str:
    """Calculate checksum for state data."""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def load_index() -> Dict:
    """Load state index."""
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text())
    return {"states": {}, "checkpoints": {}, "sessions": {}}


def save_index(index: Dict):
    """Save state index."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def save_state(state: AgentState) -> bool:
    """Save agent state to disk."""
    STATES_DIR.mkdir(parents=True, exist_ok=True)

    # Calculate checksum
    state.checksum = calculate_checksum(state.data)

    # Save state file
    state_file = STATES_DIR / f"{state.state_id}.json"
    with open(state_file, "w") as f:
        json.dump(asdict(state), f, indent=2)

    # Update index
    index = load_index()
    index["states"][state.state_id] = {
        "session_id": state.session_id,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "version": state.version,
        "checksum": state.checksum,
    }
    if state.session_id not in index["sessions"]:
        index["sessions"][state.session_id] = []
    if state.state_id not in index["sessions"][state.session_id]:
        index["sessions"][state.session_id].append(state.state_id)
    save_index(index)

    return True


def load_state(state_id: str) -> Optional[AgentState]:
    """Load agent state from disk."""
    state_file = STATES_DIR / f"{state_id}.json"
    if not state_file.exists():
        return None

    data = json.loads(state_file.read_text())
    return AgentState(**data)


def create_checkpoint(session_id: str, reason: str = "manual") -> Optional[StateCheckpoint]:
    """Create a checkpoint of current session state."""
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

    # Find latest state for session
    index = load_index()
    session_states = index.get("sessions", {}).get(session_id, [])

    if not session_states:
        return None

    latest_state_id = session_states[-1]
    state = load_state(latest_state_id)
    if not state:
        return None

    checkpoint = StateCheckpoint(
        checkpoint_id=generate_state_id(session_id, "chkpt"),
        state_id=state.state_id,
        session_id=session_id,
        created_at=datetime.now().isoformat(),
        reason=reason,
        data_snapshot=state.data.copy(),
    )

    # Save checkpoint
    checkpoint_file = CHECKPOINTS_DIR / f"{checkpoint.checkpoint_id}.json"
    with open(checkpoint_file, "w") as f:
        json.dump(asdict(checkpoint), f, indent=2)

    # Update index
    if "checkpoints" not in index:
        index["checkpoints"] = {}
    index["checkpoints"][checkpoint.checkpoint_id] = {
        "session_id": session_id,
        "state_id": state.state_id,
        "created_at": checkpoint.created_at,
    }
    save_index(index)

    return checkpoint


def restore_checkpoint(checkpoint_id: str) -> Optional[AgentState]:
    """Restore state from a checkpoint."""
    checkpoint_file = CHECKPOINTS_DIR / f"{checkpoint_id}.json"
    if not checkpoint_file.exists():
        return None

    checkpoint_data = json.loads(checkpoint_file.read_text())
    checkpoint = StateCheckpoint(**checkpoint_data)

    if not checkpoint.can_restore:
        return None

    # Create new state from checkpoint
    new_state = AgentState(
        state_id=generate_state_id(checkpoint.session_id),
        session_id=checkpoint.session_id,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        version=1,
        data=checkpoint.data_snapshot,
        metadata={"restored_from": checkpoint_id},
    )

    save_state(new_state)
    return new_state


def verify_states() -> Dict:
    """Verify integrity of all states."""
    results = {
        "total": 0,
        "valid": 0,
        "corrupted": [],
        "orphaned": [],
    }

    index = load_index()

    for state_id in index.get("states", {}):
        results["total"] += 1
        state = load_state(state_id)

        if state is None:
            results["orphaned"].append(state_id)
            continue

        # Verify checksum
        current_checksum = calculate_checksum(state.data)
        if current_checksum != state.checksum:
            results["corrupted"].append(state_id)
        else:
            results["valid"] += 1

    return results


def cleanup_old_states(days: int = 30) -> int:
    """Clean up states older than specified days."""
    cutoff = datetime.now() - timedelta(days=days)
    index = load_index()
    removed = 0

    states_to_remove = []
    for state_id, info in index.get("states", {}).items():
        created = datetime.fromisoformat(info["created_at"])
        if created < cutoff:
            states_to_remove.append(state_id)

    for state_id in states_to_remove:
        state_file = STATES_DIR / f"{state_id}.json"
        if state_file.exists():
            state_file.unlink()
        del index["states"][state_id]
        removed += 1

    save_index(index)
    return removed


def list_states(session_id: str = None) -> List[Dict]:
    """List all states or states for a session."""
    index = load_index()
    states = []

    for state_id, info in index.get("states", {}).items():
        if session_id and info.get("session_id") != session_id:
            continue
        states.append({
            "state_id": state_id,
            **info,
        })

    return sorted(states, key=lambda x: x.get("created_at", ""), reverse=True)


def print_states(states: List[Dict]):
    """Print states list."""
    print("\n" + "="*60)
    print("AGENT STATES")
    print("="*60)

    if not states:
        print("\nNo states found")
    else:
        for state in states[:20]:
            created = state.get("created_at", "")[:19]
            print(f"\n📦 {state['state_id']}")
            print(f"   Session: {state.get('session_id', 'unknown')[:20]}...")
            print(f"   Created: {created}")
            print(f"   Version: {state.get('version', 1)}")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description="Agent State Manager")
    parser.add_argument("--save", help="Save state with ID")
    parser.add_argument("--data", help="State data (JSON)")
    parser.add_argument("--session", help="Session ID")
    parser.add_argument("--load", help="Load state by ID")
    parser.add_argument("--checkpoint", help="Create checkpoint for session")
    parser.add_argument("--restore", help="Restore from checkpoint ID")
    parser.add_argument("--list", "-l", action="store_true", help="List states")
    parser.add_argument("--verify", action="store_true", help="Verify state integrity")
    parser.add_argument("--cleanup", type=int, help="Cleanup states older than N days")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.save:
        if not args.data:
            print("❌ --data required for save")
            return 1

        try:
            data = json.loads(args.data)
        except Exception:
            data = {"raw": args.data}

        state = AgentState(
            state_id=args.save,
            session_id=args.session or "default",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            version=1,
            data=data,
        )

        if save_state(state):
            print(f"✅ State saved: {state.state_id}")
        return 0

    if args.load:
        state = load_state(args.load)
        if state:
            if args.json:
                print(json.dumps(asdict(state), indent=2))
            else:
                print(f"\n📦 State: {state.state_id}")
                print(f"   Session: {state.session_id}")
                print(f"   Version: {state.version}")
                print(f"   Data: {json.dumps(state.data)[:100]}...")
        else:
            print(f"❌ State not found: {args.load}")
        return 0

    if args.checkpoint:
        checkpoint = create_checkpoint(args.checkpoint, "manual")
        if checkpoint:
            print(f"✅ Checkpoint created: {checkpoint.checkpoint_id}")
        else:
            print("❌ No state found for session")
        return 0

    if args.restore:
        state = restore_checkpoint(args.restore)
        if state:
            print(f"✅ Restored to state: {state.state_id}")
        else:
            print("❌ Could not restore checkpoint")
        return 0

    if args.verify:
        results = verify_states()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n" + "="*50)
            print("STATE VERIFICATION")
            print("="*50)
            print(f"\nTotal: {results['total']}")
            print(f"Valid: {results['valid']}")
            print(f"Corrupted: {len(results['corrupted'])}")
            print(f"Orphaned: {len(results['orphaned'])}")
            if results['corrupted']:
                print(f"\n⚠️ Corrupted: {results['corrupted']}")
            print("\n" + "="*50)
        return 0

    if args.cleanup:
        removed = cleanup_old_states(args.cleanup)
        print(f"✅ Removed {removed} old states")
        return 0

    if args.list:
        states = list_states(args.session)
        if args.json:
            print(json.dumps(states, indent=2))
        else:
            print_states(states)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
