#!/bin/bash
#
# Activate Claude Wrapper with Cache Analytics
# This script adds the wrapper to your shell configuration
#

set -e

echo "🔧 Activating Claude wrapper with cache analytics..."

# Detect shell
SHELL_CONFIG=""
if [[ -n "$ZSH_VERSION" ]] || [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_CONFIG="$HOME/.zshrc"
    echo "Detected: Zsh"
elif [[ -n "$BASH_VERSION" ]] || [[ "$SHELL" == *"bash"* ]]; then
    SHELL_CONFIG="$HOME/.bashrc"
    echo "Detected: Bash"
else
    echo "⚠️  Unknown shell. Please add manually to your shell config."
    echo "Current SHELL: $SHELL"
    exit 1
fi

# Check if already activated
if grep -q "claude_wrapper.sh" "$SHELL_CONFIG" 2>/dev/null; then
    echo "✅ Wrapper already activated in $SHELL_CONFIG"
    echo "   To apply changes, run: source $SHELL_CONFIG"
    exit 0
fi

# Add to shell config
echo "" >> "$SHELL_CONFIG"
echo "# Claude Code wrapper with cache analytics (added $(date '+%Y-%m-%d'))" >> "$SHELL_CONFIG"
echo "if [[ -f ~/.claude/evaluation/claude_wrapper.sh ]]; then" >> "$SHELL_CONFIG"
echo "    source ~/.claude/evaluation/claude_wrapper.sh" >> "$SHELL_CONFIG"
echo "fi" >> "$SHELL_CONFIG"

echo "✅ Wrapper activated!"
echo ""
echo "Next steps:"
echo "  1. Reload shell config: source $SHELL_CONFIG"
echo "  2. Or open a new terminal"
echo "  3. Use 'claude' as normal - dashboard will show on exit"
echo ""
echo "To test now: source $SHELL_CONFIG && echo 'Wrapper ready!'"
