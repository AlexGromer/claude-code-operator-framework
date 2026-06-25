#!/usr/bin/env bash
#
# Anacron Setup for Research Monitoring
# Ensures weekly digest runs even if computer was off on Monday 09:00
#
# Usage:
#     bash setup_anacron.sh [--uninstall]
#
# Version: 1.0.0
# Created: 2026-01-27
#

set -euo pipefail

SCRIPT_DIR="$HOME/.claude/tools"
OUTPUT_DIR="$HOME/.claude/evaluation/data/research_digests"
ANACRON_DIR="$HOME/.anacron"
SPOOL_DIR="$ANACRON_DIR/spool"
ANACRONTAB="$ANACRON_DIR/anacrontab"
SYSTEMD_TIMER="$HOME/.config/systemd/user/anacron-research.timer"
SYSTEMD_SERVICE="$HOME/.config/systemd/user/anacron-research.service"

function install_anacron() {
    echo "Installing anacron-based research monitoring..."

    # Create directories
    mkdir -p "$ANACRON_DIR" "$SPOOL_DIR" "$OUTPUT_DIR"
    mkdir -p "$HOME/.config/systemd/user"

    # Create anacrontab
    cat > "$ANACRONTAB" <<EOF
# Anacron configuration for Claude Code Research Monitor
# Format: period delay job-identifier command

# Weekly research digest (runs once per week)
7  5  research_weekly  cd $SCRIPT_DIR && python3 research_monitor.py --output $OUTPUT_DIR/digest_\$(date +\\%Y-\\%m-\\%d).md 2>&1 | logger -t research_monitor
EOF

    echo "✅ Created anacrontab: $ANACRONTAB"

    # Create systemd timer (runs anacron daily to check for missed jobs)
    cat > "$SYSTEMD_TIMER" <<EOF
[Unit]
Description=Anacron Research Monitor Timer
Documentation=man:anacron(8)

[Timer]
# Run daily at 10:00 (checks if weekly job needs to run)
OnCalendar=daily
OnCalendar=*-*-* 10:00:00

# Also run 5 minutes after boot (catches missed jobs)
OnBootSec=5min

Persistent=true

[Install]
WantedBy=timers.target
EOF

    echo "✅ Created systemd timer: $SYSTEMD_TIMER"

    # Create systemd service
    cat > "$SYSTEMD_SERVICE" <<EOF
[Unit]
Description=Anacron Research Monitor Service
Documentation=man:anacron(8)

[Service]
Type=oneshot
ExecStart=/usr/sbin/anacron -s -t $ANACRONTAB -S $SPOOL_DIR
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    echo "✅ Created systemd service: $SYSTEMD_SERVICE"

    # Enable and start systemd timer
    systemctl --user daemon-reload
    systemctl --user enable anacron-research.timer
    systemctl --user start anacron-research.timer

    echo ""
    echo "✅ Anacron-based research monitoring installed successfully!"
    echo ""
    echo "How it works:"
    echo "  - Weekly job runs once per 7 days (not tied to specific time)"
    echo "  - If computer was off, job runs 5 minutes after next boot"
    echo "  - Systemd timer checks daily at 10:00 for missed jobs"
    echo ""
    echo "To verify:"
    echo "  systemctl --user status anacron-research.timer"
    echo "  journalctl --user -u anacron-research -n 20"
    echo ""
    echo "Output location: $OUTPUT_DIR/"
}

function uninstall_anacron() {
    echo "Uninstalling anacron research monitoring..."

    # Stop and disable systemd timer
    systemctl --user stop anacron-research.timer 2>/dev/null || true
    systemctl --user disable anacron-research.timer 2>/dev/null || true

    # Remove files
    rm -f "$SYSTEMD_TIMER" "$SYSTEMD_SERVICE"
    rm -rf "$ANACRON_DIR"

    systemctl --user daemon-reload

    echo "✅ Anacron research monitoring uninstalled!"
}

function show_status() {
    echo "Anacron Research Monitor Status"
    echo "================================"
    echo ""

    if systemctl --user is-active anacron-research.timer >/dev/null 2>&1; then
        echo "Status: ✅ ACTIVE"
        echo ""
        echo "Timer status:"
        systemctl --user status anacron-research.timer --no-pager
        echo ""
        echo "Last digest:"
        ls -lht "$OUTPUT_DIR"/*.md 2>/dev/null | head -1 || echo "  No digests yet"
        echo ""
        echo "Anacron spool (last run timestamps):"
        ls -lh "$SPOOL_DIR" 2>/dev/null || echo "  No jobs run yet"
    else
        echo "Status: ❌ NOT INSTALLED"
        echo ""
        echo "To install: bash setup_anacron.sh"
    fi
}

# Main
case "${1:-}" in
    --uninstall)
        uninstall_anacron
        ;;
    --status)
        show_status
        ;;
    "")
        install_anacron
        ;;
    *)
        echo "Usage: bash setup_anacron.sh [--uninstall|--status]"
        exit 1
        ;;
esac
