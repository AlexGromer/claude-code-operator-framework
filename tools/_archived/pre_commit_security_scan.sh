#!/bin/bash
#
# Pre-Commit Security Scan Hook
# OWASP LLM02 Automation: Scan for secrets/PII before git commit
#
# Version: 1.0.0
# Task: Tasks 20-28 Automation (Task 25 - LLM02)
#
# Installation:
#   1. Copy to your project: cp ~/.claude/hooks/pre_commit_security_scan.sh .git/hooks/pre-commit
#   2. Or use symlink: ln -sf ~/.claude/hooks/pre_commit_security_scan.sh .git/hooks/pre-commit
#   3. Make executable: chmod +x .git/hooks/pre-commit
#
# Dependencies:
#   - gitleaks (https://github.com/gitleaks/gitleaks)
#   - Optional: trufflehog for additional detection
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[PRE-COMMIT SECURITY SCAN]${NC}"

# Check for gitleaks
if ! command -v gitleaks &> /dev/null; then
    echo -e "${YELLOW}Warning: gitleaks not installed. Install with: brew install gitleaks${NC}"
    echo -e "${YELLOW}Skipping secrets scan...${NC}"
    exit 0
fi

# 1. Scan staged files for secrets
echo "Scanning staged files for secrets..."

# Create temp file with staged content
STAGED_FILES=$(git diff --cached --name-only)

if [ -z "$STAGED_FILES" ]; then
    echo -e "${GREEN}No files staged for commit${NC}"
    exit 0
fi

# Run gitleaks on staged changes
if ! gitleaks protect --staged --no-banner --redact 2>/dev/null; then
    echo -e "${RED}==========================================${NC}"
    echo -e "${RED}  SECRETS DETECTED - COMMIT BLOCKED${NC}"
    echo -e "${RED}==========================================${NC}"
    echo ""
    echo "Found potential secrets in staged files."
    echo "Please remove secrets before committing:"
    echo ""
    echo "1. Remove the secret from the file"
    echo "2. If already committed historically, use BFG or git-filter-branch"
    echo "3. Rotate any exposed credentials immediately"
    echo ""
    echo "To bypass (NOT RECOMMENDED):"
    echo "  git commit --no-verify"
    echo ""
    exit 1
fi

echo -e "${GREEN}[PASS] No secrets detected in staged files${NC}"

# 2. Check for .claude/ directory (should never be committed)
if echo "$STAGED_FILES" | grep -q "^\.claude/"; then
    echo -e "${RED}==========================================${NC}"
    echo -e "${RED}  .claude/ DIRECTORY STAGED - BLOCKED${NC}"
    echo -e "${RED}==========================================${NC}"
    echo ""
    echo "The .claude/ directory contains local settings and should never be committed."
    echo ""
    echo "To fix:"
    echo "  1. git reset HEAD .claude/"
    echo "  2. Add to .gitignore: echo '.claude/' >> .gitignore"
    echo ""
    exit 1
fi

# 3. Check for common sensitive files
SENSITIVE_PATTERNS=(
    "\.env$"
    "\.env\."
    "credentials\.json"
    "secrets\.yaml"
    "secrets\.yml"
    "\.pem$"
    "\.key$"
    "id_rsa"
    "id_dsa"
    "id_ecdsa"
    "id_ed25519"
    "\.htpasswd"
)

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if echo "$STAGED_FILES" | grep -qE "$pattern"; then
        echo -e "${YELLOW}==========================================${NC}"
        echo -e "${YELLOW}  WARNING: Potentially sensitive file staged${NC}"
        echo -e "${YELLOW}==========================================${NC}"
        echo ""
        echo "Found file matching pattern: $pattern"
        echo "Please verify this file should be committed."
        echo ""
        echo "If intentional, you can bypass with: git commit --no-verify"
        echo ""
        # Warning only, not blocking
    fi
done

# 4. Log successful scan (for audit trail)
LOG_FILE="${HOME}/.claude/security_audit.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "[$(date -Iseconds)] PRE-COMMIT SCAN: PASS - $(pwd) - Files: $(echo "$STAGED_FILES" | wc -l | tr -d ' ')" >> "$LOG_FILE"

echo -e "${GREEN}[PRE-COMMIT SCAN COMPLETE]${NC}"
exit 0
