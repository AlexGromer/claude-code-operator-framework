#!/usr/bin/env bash
#
# .zshrc Hook for Claude Code Project Entry
# Shows research digest reminder when entering Claude Code projects
#
# Installation:
#     Add to ~/.zshrc:
#     source ~/.claude/tools/zshrc_project_hook.sh
#
# Version: 1.0.0
# Created: 2026-01-27
#

# Override cd command to add project entry detection
function cd() {
    builtin cd "$@"

    # Check if this is a Claude Code project
    if [[ -f ".claude/project.json" ]] || [[ -f "UNIFIED_IMPLEMENTATION_ROADMAP.md" ]]; then
        # Check for new research digest
        local digest_dir="$HOME/.claude/evaluation/data/research_digests"
        local latest_digest=$(ls -t "$digest_dir"/digest_*.md 2>/dev/null | head -1)

        if [[ -n "$latest_digest" ]]; then
            # Check digest age (show if < 7 days old)
            local digest_age=$(( ($(date +%s) - $(stat -c %Y "$latest_digest" 2>/dev/null || stat -f %m "$latest_digest")) / 86400 ))

            if (( digest_age <= 7 )); then
                # Check if marked as read
                local read_tracker="$HOME/.claude/evaluation/data/.digest_read"
                if [[ -f "$read_tracker" ]] && grep -q "$latest_digest" "$read_tracker" 2>/dev/null; then
                    # Already read, don't show
                    :
                else
                    # Show compact reminder
                    echo ""
                    echo "📊 New research digest available (${digest_age}d ago)"
                    echo "   Quick start: python ~/.claude/tools/research_workflow_agent.py"
                    echo "   Mark as read: echo \"$latest_digest\" >> $read_tracker"
                    echo ""
                fi
            fi
        fi
    fi
}

# Export the function so it's available in shell
typeset -f cd > /dev/null
