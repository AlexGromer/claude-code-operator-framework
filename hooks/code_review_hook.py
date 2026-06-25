#!/usr/bin/env python3
"""
Code Review & Auto-Fix Hook (PostToolUse on Write/Edit)

Automatically:
1. Runs code review to find issues
2. AUTO-FIXES safe issues (style,  is None, whitespace)
3. Reports CONFIRM_FIX issues for Claude to decide
4. Reports MANUAL_FIX/CRITICAL issues that must be addressed

Hook Type: PostToolUse (non-blocking, advisory)
Trigger: Write, Edit tools on code files (.py, .js, .ts, .sh, .go, .rs)
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone

# Add tools directory to path
tools_dir = Path.home() / ".claude" / "tools"
sys.path.insert(0, str(tools_dir))

try:
    from code_review_checks import analyze_code
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False

try:
    from code_auto_fixer import PythonAutoFixer, categorize_fixes, FixLevel
    FIXER_AVAILABLE = True
except ImportError:
    FIXER_AVAILABLE = False

# Code file extensions
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.sh', '.bash', '.go', '.rs', '.rb'}

# Minimum lines for review
MIN_LINES_FOR_REVIEW = 10


def should_review(file_path: str) -> bool:
    """Check if file should be reviewed."""
    if not file_path:
        return False
    path = Path(file_path)
    return path.suffix.lower() in CODE_EXTENSIONS


def get_file_content(file_path: str) -> str:
    """Read file content safely."""
    try:
        path = Path(file_path)
        if path.exists():
            return path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        pass
    return ""


def apply_auto_fixes(file_path: str, content: str) -> tuple:
    """
    Apply safe auto-fixes and return (new_content, fixes_applied, fixes_pending).
    """
    if not FIXER_AVAILABLE:
        return content, [], []

    path = Path(file_path)
    if path.suffix.lower() != '.py':
        return content, [], []

    fixer = PythonAutoFixer(content, file_path)
    all_fixes = fixer.analyze()

    if not all_fixes:
        return content, [], []

    categorized = categorize_fixes(all_fixes)

    # Apply AUTO_FIX automatically
    auto_fixes = categorized[FixLevel.AUTO_FIX]
    confirm_fixes = categorized[FixLevel.CONFIRM_FIX]

    if auto_fixes:
        new_content = fixer.apply_fixes(auto_fixes)

        # Write back to file
        try:
            path.write_text(new_content, encoding='utf-8')
        except Exception:
            return content, [], confirm_fixes

        return new_content, auto_fixes, confirm_fixes

    return content, [], confirm_fixes


def format_hook_output(file_path: str, review_result, auto_fixes, confirm_fixes) -> dict:
    """Format combined output for Claude."""
    lines = []
    has_critical = False

    # 1. Report auto-applied fixes
    if auto_fixes:
        lines.append(f"✅ AUTO-FIXED in {Path(file_path).name}:")
        for fix in auto_fixes[:5]:  # Limit to 5
            lines.append(f"   [{fix.code}] Line {fix.line}: {fix.description}")
        if len(auto_fixes) > 5:
            lines.append(f"   ... and {len(auto_fixes) - 5} more")
        lines.append("")

    # 2. Report issues needing confirmation
    if confirm_fixes:
        lines.append(f"⚠️  CONFIRM FIXES ({len(confirm_fixes)} suggestions):")
        for fix in confirm_fixes[:3]:  # Limit to 3
            lines.append(f"   [{fix.code}] Line {fix.line}: {fix.description}")
            lines.append(f"      Current:  {fix.original.strip()[:50]}")
            lines.append(f"      Proposed: {fix.fixed.strip()[:50]}")
        if len(confirm_fixes) > 3:
            lines.append(f"   ... and {len(confirm_fixes) - 3} more")
        lines.append("")
        lines.append("   Apply these? Edit the file to apply, or ignore if not needed.")
        lines.append("")

    # 3. Report critical review issues (undefined functions, security)
    if review_result and review_result.issues:
        critical_high = [i for i in review_result.issues if i.severity in ('CRITICAL', 'HIGH')]

        if critical_high:
            has_critical = True
            lines.append(f"🔴 CRITICAL/HIGH ISSUES ({len(critical_high)}):")
            for issue in critical_high[:5]:
                lines.append(f"   [{issue.code}] Line {issue.line}: {issue.message}")
                if issue.suggestion:
                    lines.append(f"      → {issue.suggestion}")
            if len(critical_high) > 5:
                lines.append(f"   ... and {len(critical_high) - 5} more")
            lines.append("")
            lines.append("   ❌ FIX THESE BEFORE DELIVERY")

    if not lines:
        return {}

    return {
        "message": "\n".join(lines),
        "severity": "error" if has_critical else "warning"
    }


def log_review(file_path: str, auto_fixes_count: int, confirm_fixes_count: int,
               critical_count: int, session_id: str):
    """Log review to metrics."""
    try:
        data_dir = Path.home() / ".claude" / "evaluation" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_file = data_dir / "code_reviews.jsonl"

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_path": file_path,
            "auto_fixes_applied": auto_fixes_count,
            "confirm_fixes_pending": confirm_fixes_count,
            "critical_issues": critical_count,
            "session_id": session_id
        }

        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass


def main():
    """Process Write/Edit and run review + auto-fix."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from hook_stdin import read_hook_stdin
        input_data = read_hook_stdin()

        tool_name = input_data.get("tool_name", "")
        if tool_name not in ("Write", "Edit"):
            print(json.dumps({}))
            return

        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if not should_review(file_path):
            print(json.dumps({}))
            return

        content = get_file_content(file_path)
        if not content or len(content.split('\n')) < MIN_LINES_FOR_REVIEW:
            print(json.dumps({}))
            return

        # Step 1: Apply auto-fixes
        new_content, auto_fixes, confirm_fixes = apply_auto_fixes(file_path, content)

        # Step 2: Run review on (possibly fixed) content
        review_result = None
        if ANALYZER_AVAILABLE:
            review_result = analyze_code(new_content, file_path)

        # Step 3: Format output
        output = format_hook_output(file_path, review_result, auto_fixes, confirm_fixes)

        # Step 4: Log
        session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
        critical_count = 0
        if review_result:
            critical_count = sum(1 for i in review_result.issues
                               if i.severity in ('CRITICAL', 'HIGH'))

        log_review(file_path, len(auto_fixes), len(confirm_fixes),
                  critical_count, session_id)

        print(json.dumps(output) if output else json.dumps({}))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        print(json.dumps({}))


if __name__ == "__main__":
    main()
