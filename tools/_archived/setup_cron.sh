#!/usr/bin/env bash
#
# Cron Setup Helper for Research Monitoring
# Installs cron job for weekly research digest generation
#
# Usage:
#     bash setup_cron.sh [--uninstall]
#
# Version: 1.0.0
# Created: 2026-01-27
#

set -euo pipefail

SCRIPT_DIR="$HOME/.claude/tools"
OUTPUT_DIR="$HOME/.claude/evaluation/data/research_digests"
CRON_MARKER="# Claude Code Research Monitor"

function install_cron() {
    echo "Installing cron job for research monitoring..."

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    # Prepare cron entry
    CRON_ENTRY="$CRON_MARKER
0 9 * * 1 cd $SCRIPT_DIR && python3 research_monitor.py --output $OUTPUT_DIR/digest_\$(date +\\%Y-\\%m-\\%d).md 2>&1 | logger -t research_monitor"

    # Check if already installed
    if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        echo "❌ Cron job already installed. Uninstall first with: bash setup_cron.sh --uninstall"
        return 1
    fi

    # Install cron job
    (crontab -l 2>/dev/null || true; echo "$CRON_ENTRY") | crontab -

    echo "✅ Cron job installed successfully!"
    echo ""
    echo "Schedule: Every Monday at 09:00"
    echo "Output: $OUTPUT_DIR/digest_YYYY-MM-DD.md"
    echo ""
    echo "To verify: crontab -l | grep research_monitor"
    echo "To test manually: cd $SCRIPT_DIR && python3 research_monitor.py"
}

function uninstall_cron() {
    echo "Uninstalling cron job for research monitoring..."

    if ! crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        echo "❌ Cron job not found"
        return 1
    fi

    # Remove cron job (remove marker line + following line)
    crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | grep -v "research_monitor.py" | crontab -

    echo "✅ Cron job uninstalled successfully!"
}

function show_status() {
    echo "Research Monitor Cron Status"
    echo "=============================="
    echo ""

    if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        echo "Status: ✅ INSTALLED"
        echo ""
        echo "Current cron entry:"
        crontab -l | grep -A1 "$CRON_MARKER"
        echo ""
        echo "Recent digests:"
        ls -lh "$OUTPUT_DIR"/*.md 2>/dev/null | tail -5 || echo "  No digests generated yet"
    else
        echo "Status: ❌ NOT INSTALLED"
        echo ""
        echo "To install: bash setup_cron.sh"
    fi
}

# Main
case "${1:-}" in
    --uninstall)
        uninstall_cron
        ;;
    --status)
        show_status
        ;;
    "")
        install_cron
        ;;
    *)
        echo "Usage: bash setup_cron.sh [--uninstall|--status]"
        exit 1
        ;;
esac
