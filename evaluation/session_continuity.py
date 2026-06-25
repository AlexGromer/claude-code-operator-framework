#!/usr/bin/env python3
"""
Generate session continuity summary for reopening Claude Code sessions.
Produces markdown summary with: task context, work completed, files modified,
key decisions, and next steps for seamless session transitions.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import Counter


def find_latest_session_file(project_path: Path) -> Path:
    """Find the most recently modified session JSONL file."""
    session_files = list(project_path.glob("*.jsonl"))

    if not session_files:
        raise FileNotFoundError(f"No session files found in {project_path}")

    return max(session_files, key=lambda f: f.stat().st_mtime)


def extract_task_description(session_file: Path) -> str:
    """Extract initial task/goal from first user messages."""
    with open(session_file, 'r', encoding='utf-8') as f:
        user_messages = []
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get('type') == 'user' and 'message' in entry:
                    msg = entry['message']
                    if 'content' in msg:
                        content = msg['content']

                        # Handle both string and array content formats
                        if isinstance(content, str):
                            # Old API format: content is a string
                            user_messages.append(content)
                        elif isinstance(content, list):
                            # New API format: content is array of blocks
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text = item.get('text', '')
                                    # Skip system reminders
                                    if not text.strip().startswith('<system-reminder>'):
                                        user_messages.append(text)
                                elif isinstance(item, str):
                                    # Fallback for simple strings
                                    if not item.strip().startswith('<system-reminder>'):
                                        user_messages.append(item)

                # Stop after first 5 meaningful user messages
                if len(user_messages) >= 5:
                    break

            except (json.JSONDecodeError, KeyError):
                continue

    if not user_messages:
        return "Task description not available (no user messages found)"

    # Join first messages and truncate if too long
    task_desc = " ".join(user_messages[:5]).strip()

    # Clean up excessive whitespace
    task_desc = " ".join(task_desc.split())

    if len(task_desc) > 800:
        task_desc = task_desc[:797] + "..."

    return task_desc if task_desc else "Task description not available"


def extract_files_modified(session_file: Path) -> List[str]:
    """Extract files that were modified (Edit/Write operations)."""
    files_modified = set()

    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())

                # Look for tool calls (Edit, Write)
                if entry.get('type') == 'assistant' and 'message' in entry:
                    msg = entry['message']
                    if 'content' in msg:
                        for item in msg.get('content', []):
                            if isinstance(item, dict) and item.get('type') == 'tool_use':
                                tool_name = item.get('name', '')
                                tool_input = item.get('input', {})

                                if tool_name in ('Edit', 'Write') and 'file_path' in tool_input:
                                    files_modified.add(tool_input['file_path'])

            except (json.JSONDecodeError, KeyError):
                continue

    return sorted(list(files_modified))


def extract_tools_used(session_file: Path) -> Dict[str, int]:
    """Extract tool usage statistics."""
    tool_counts = Counter()

    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())

                if entry.get('type') == 'assistant' and 'message' in entry:
                    msg = entry['message']
                    if 'content' in msg:
                        for item in msg.get('content', []):
                            if isinstance(item, dict) and item.get('type') == 'tool_use':
                                tool_name = item.get('name', 'unknown')
                                tool_counts[tool_name] += 1

            except (json.JSONDecodeError, KeyError):
                continue

    return dict(tool_counts.most_common(10))  # Top 10 tools


def extract_key_decisions(session_file: Path) -> List[str]:
    """Extract key decisions from assistant messages (look for decision markers)."""
    decisions = []

    decision_markers = [
        "DECISION:",
        "Decision:",
        "Chosen approach:",
        "Selected:",
        "Implemented:",
        "Strategy:",
        "Priority:",
        "Solution:",
        "Approach:",
        "Used:",
        "Created:",
        "Fixed:",
        "Enhanced:",
        "Updated:",
        "Gap Resolved:",
        "Status:",
        "Verdict:",
    ]

    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())

                if entry.get('type') == 'assistant' and 'message' in entry:
                    msg = entry['message']
                    if 'content' in msg:
                        content = msg['content']

                        # Handle both string and array content
                        text_blocks = []
                        if isinstance(content, str):
                            text_blocks = [content]
                        elif isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text_blocks.append(item.get('text', ''))

                        for text in text_blocks:
                            # Look for decision markers
                            for marker in decision_markers:
                                if marker in text:
                                    # Extract sentence containing marker
                                    lines = text.split('\n')
                                    for l in lines:
                                        if marker in l:
                                            decision = l.strip()
                                            # Keep decisions that are concise and meaningful
                                            if 20 < len(decision) < 250:
                                                decisions.append(decision)
                                            break

            except (json.JSONDecodeError, KeyError):
                continue

    # Deduplicate and limit
    unique_decisions = list(dict.fromkeys(decisions))

    # Filter out noise
    filtered = [
        d for d in unique_decisions
        if not any(noise in d.lower() for noise in ["see below", "as follows", "click here"])
    ]

    return filtered[:10]  # Top 10 unique decisions (increased from 5)


def extract_next_steps(session_file: Path) -> List[str]:
    """Extract pending tasks/next steps from last messages."""
    next_steps = []

    next_step_markers = [
        "Next steps:",
        "Next step:",
        "TODO:",
        "Pending:",
        "Next:",
        "Remaining:",
        "Still need to:",
        "To be implemented:",
        "Future:",
        "Phase 2",
        "Phase 3",
        "Not implemented:",
        "Not yet implemented:",
        "Pending tasks:",
        "Outstanding:",
        "GAP-",  # Gap IDs
        "Task ",  # Task references
        "выполни",  # Russian "execute"
        "реализ",  # Russian "implement"
    ]

    with open(session_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

        # Look at last 100 entries for next steps (increased from 50)
        for line in lines[-100:]:
            try:
                entry = json.loads(line.strip())

                # Check both assistant and user messages for pending tasks
                if entry.get('type') in ('assistant', 'user') and 'message' in entry:
                    msg = entry['message']
                    if 'content' in msg:
                        content = msg['content']

                        # Handle both string and array content
                        text_blocks = []
                        if isinstance(content, str):
                            text_blocks = [content]
                        elif isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text_blocks.append(item.get('text', ''))

                        for text in text_blocks:
                            # Look for next step markers
                            for marker in next_step_markers:
                                if marker.lower() in text.lower():
                                    # Extract content after marker
                                    idx = text.lower().find(marker.lower())
                                    if idx != -1:
                                        next_text = text[idx + len(marker):].strip()

                                        # Extract bullet list or numbered list
                                        for line_text in next_text.split('\n'):
                                            line_text = line_text.strip()

                                            # Check if it's a bullet point or numbered item
                                            if line_text and any(line_text.startswith(prefix) for prefix in ['-', '*', '•', '1.', '2.', '3.', '4.', '5.']):
                                                # Remove bullet/number prefix
                                                clean_text = line_text.lstrip('-*•0123456789. ')
                                                if clean_text and len(clean_text) < 300:
                                                    next_steps.append(clean_text)
                                            # Or take first substantial line
                                            elif line_text and len(line_text) > 10 and len(line_text) < 300:
                                                next_steps.append(line_text)
                                                break  # Only first line if no bullets

            except (json.JSONDecodeError, KeyError):
                continue

    # Deduplicate and limit
    unique_steps = list(dict.fromkeys(next_steps))

    # Filter out noise (very short items, markers themselves)
    filtered_steps = [
        step for step in unique_steps
        if len(step) > 15 and not any(m.lower() in step.lower() for m in ["click here", "see below", "as follows"])
    ]

    return filtered_steps[:10]  # Top 10 unique next steps (increased from 5)


def parse_session_metadata(session_file: Path) -> Dict[str, Any]:
    """Parse basic session metadata."""
    session_id = None
    session_start = None
    session_end = None
    api_calls = 0

    with open(session_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())

                if session_id is None and 'sessionId' in entry:
                    session_id = entry['sessionId']

                if 'timestamp' in entry:
                    ts = entry['timestamp']
                    if session_start is None:
                        session_start = ts
                    session_end = ts

                if entry.get('type') == 'assistant' and 'message' in entry:
                    if 'usage' in entry['message']:
                        api_calls += 1

            except (json.JSONDecodeError, KeyError):
                continue

    # Calculate duration
    duration_minutes = 0
    if session_start and session_end:
        try:
            start_dt = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(session_end.replace('Z', '+00:00'))
            duration_minutes = (end_dt - start_dt).total_seconds() / 60
        except:
            pass

    return {
        'session_id': session_id or 'unknown',
        'duration_minutes': duration_minutes,
        'api_calls': api_calls,
        'start_time': session_start,
        'end_time': session_end,
    }


def generate_continuity_summary(project_path: Path) -> str:
    """Generate complete continuity summary as markdown."""

    # Find session file
    session_file = find_latest_session_file(project_path)

    # Extract all data
    metadata = parse_session_metadata(session_file)
    task_desc = extract_task_description(session_file)
    files_modified = extract_files_modified(session_file)
    tools_used = extract_tools_used(session_file)
    decisions = extract_key_decisions(session_file)
    next_steps = extract_next_steps(session_file)

    # Build markdown summary
    summary = f"""# Session Continuity Summary

**Session ID:** `{metadata['session_id']}`
**Duration:** {metadata['duration_minutes']:.1f} minutes
**API Calls:** {metadata['api_calls']} requests
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## Task Context

{task_desc}

---

## Work Completed

### Files Modified ({len(files_modified)} files)

"""

    if files_modified:
        for file in files_modified[:10]:  # Limit to 10 files
            summary += f"- `{file}`\n"
        if len(files_modified) > 10:
            summary += f"\n_...and {len(files_modified) - 10} more files_\n"
    else:
        summary += "_No files modified in this session._\n"

    summary += f"""
### Tools Used

"""

    if tools_used:
        for tool, count in list(tools_used.items())[:10]:
            summary += f"- **{tool}**: {count} calls\n"
    else:
        summary += "_No tool usage data available._\n"

    summary += """
---

## Key Decisions

"""

    if decisions:
        for decision in decisions:
            summary += f"- {decision}\n"
    else:
        summary += "_No explicit decisions recorded._\n"

    summary += """
---

## Next Steps

"""

    if next_steps:
        for step in next_steps:
            summary += f"- [ ] {step}\n"
    else:
        summary += "_No pending tasks identified. Check last conversation messages for context._\n"

    summary += """
---

## How to Use This Summary

1. **Copy this entire summary** when reopening the session
2. **Paste into first message** of new session with: "Continue from this summary: [paste]"
3. **Add any updates** to Next Steps if priorities changed
4. **Verify Files Modified** are still relevant (some may have been committed/reverted)

---

_Generated by session_continuity.py - Claude Code Evaluation Framework_
"""

    return summary


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        # Try to detect current project
        cwd = Path.cwd()
        encoded_path = str(cwd).replace('/', '-').replace('_', '-')
        project_path = Path.home() / '.claude' / 'projects' / encoded_path

    try:
        if not project_path.exists():
            print(f"⚠️  Project path not found: {project_path}", file=sys.stderr)
            print("   No session data available for this directory.", file=sys.stderr)
            sys.exit(1)

        summary = generate_continuity_summary(project_path)
        print(summary)

    except FileNotFoundError as e:
        print(f"⚠️  {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating continuity summary: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
