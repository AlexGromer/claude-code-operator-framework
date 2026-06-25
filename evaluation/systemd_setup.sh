#!/bin/bash
# Claude Metrics Systemd Setup Script
# Version: 1.0.0

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"
LOG_DIR="$HOME/.claude/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}        Claude Metrics Systemd Timer Setup                     ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Create log directory
mkdir -p "$LOG_DIR"

# Function to show status
show_status() {
    echo -e "\n${YELLOW}Current Timer Status:${NC}"
    systemctl --user list-timers --all | grep -E "claude|NEXT|UNIT" || echo "No claude timers found"
}

# Function to install unit files
install_units() {
    echo -e "${GREEN}Installing systemd unit files...${NC}"

    mkdir -p "$USER_SYSTEMD_DIR"

    # Copy all service and timer files
    for f in "$SCRIPT_DIR/systemd/"*.service "$SCRIPT_DIR/systemd/"*.timer; do
        if [ -f "$f" ]; then
            cp "$f" "$USER_SYSTEMD_DIR/"
            echo -e "  ${GREEN}✓${NC} Installed $(basename "$f")"
        fi
    done

    systemctl --user daemon-reload
    echo -e "${GREEN}Unit files installed and daemon reloaded${NC}"
}

# Function to enable timers
enable_timers() {
    echo -e "${GREEN}Enabling Claude Metrics timers...${NC}"

    # Install units first
    install_units

    # Enable and start weekly report timer
    if [ -f "$USER_SYSTEMD_DIR/claude-metrics.timer" ]; then
        systemctl --user enable claude-metrics.timer
        systemctl --user start claude-metrics.timer
        echo -e "  ${GREEN}✓${NC} claude-metrics.timer (Weekly reports - Friday 17:00)"
    fi

    # Enable and start daily reminder timer
    if [ -f "$USER_SYSTEMD_DIR/claude-metrics-reminder.timer" ]; then
        systemctl --user enable claude-metrics-reminder.timer
        systemctl --user start claude-metrics-reminder.timer
        echo -e "  ${GREEN}✓${NC} claude-metrics-reminder.timer (Daily reminders - 18:00)"
    fi

    # Enable and start weekly cleanup timer
    if [ -f "$USER_SYSTEMD_DIR/claude-metrics-cleanup.timer" ]; then
        systemctl --user enable claude-metrics-cleanup.timer
        systemctl --user start claude-metrics-cleanup.timer
        echo -e "  ${GREEN}✓${NC} claude-metrics-cleanup.timer (Weekly cleanup - Sunday 03:00)"
    fi

    show_status
}

# Function to disable timers
disable_timers() {
    echo -e "${YELLOW}Disabling Claude Metrics timers...${NC}"

    systemctl --user stop claude-metrics.timer 2>/dev/null || true
    systemctl --user disable claude-metrics.timer 2>/dev/null || true
    echo -e "  ${YELLOW}○${NC} claude-metrics.timer disabled"

    systemctl --user stop claude-metrics-reminder.timer 2>/dev/null || true
    systemctl --user disable claude-metrics-reminder.timer 2>/dev/null || true
    echo -e "  ${YELLOW}○${NC} claude-metrics-reminder.timer disabled"

    systemctl --user stop claude-metrics-cleanup.timer 2>/dev/null || true
    systemctl --user disable claude-metrics-cleanup.timer 2>/dev/null || true
    echo -e "  ${YELLOW}○${NC} claude-metrics-cleanup.timer disabled"

    show_status
}

# Function to test run
test_run() {
    echo -e "${BLUE}Running metrics report manually...${NC}"
    systemctl --user start claude-metrics.service
    echo ""
    echo -e "${GREEN}Check the report at:${NC}"
    ls -la "$SCRIPT_DIR/reports/" | tail -5
}

# Function to show logs
show_logs() {
    echo -e "${BLUE}Recent logs:${NC}"
    journalctl --user -u claude-metrics.service --no-pager -n 20 2>/dev/null || \
        echo "No systemd logs available yet"

    echo ""
    echo -e "${BLUE}Service log file:${NC}"
    tail -20 "$LOG_DIR/metrics_service.log" 2>/dev/null || \
        echo "No log file yet"
}

# Function to show next runs
show_next_runs() {
    echo -e "${BLUE}Upcoming scheduled runs:${NC}"
    systemctl --user list-timers claude-metrics.timer claude-metrics-reminder.timer 2>/dev/null || \
        echo "Timers not enabled yet"
}

# Parse command line arguments
case "$1" in
    enable)
        enable_timers
        ;;
    disable)
        disable_timers
        ;;
    status)
        show_status
        ;;
    test)
        test_run
        ;;
    logs)
        show_logs
        ;;
    next)
        show_next_runs
        ;;
    reload)
        echo -e "${BLUE}Reloading systemd daemon...${NC}"
        systemctl --user daemon-reload
        echo -e "${GREEN}Done${NC}"
        ;;
    *)
        echo "Usage: $0 {enable|disable|status|test|logs|next|reload}"
        echo ""
        echo "Commands:"
        echo "  enable  - Enable and start all timers"
        echo "  disable - Stop and disable all timers"
        echo "  status  - Show current timer status"
        echo "  test    - Manually run metrics report now"
        echo "  logs    - Show recent logs"
        echo "  next    - Show next scheduled runs"
        echo "  reload  - Reload systemd daemon"
        echo ""
        echo "Examples:"
        echo "  $0 enable   # Start automatic metrics collection"
        echo "  $0 status   # Check if timers are running"
        echo "  $0 test     # Generate report immediately"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                         Done!                                  ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
