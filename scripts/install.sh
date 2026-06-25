#!/bin/bash
#===============================================================================
# Install Script - установка из репозитория
# 
# Использование:
#   git clone <url> /opt/claude-code-agent-addition
#   cd /opt/claude-code-agent-addition
#   ./scripts/install.sh
#
# Или полная установка с зависимостями:
#   ./scripts/install.sh --full
#===============================================================================

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "\n\033[1mClaude Code Agent Addition - Installer\033[0m\n"

# Если запрошена полная установка — вызываем setup-project.sh
if [[ "$1" == "--full" ]] || [[ "$1" == "-f" ]]; then
    echo -e "${CYAN}[i]${NC} Запуск полной установки..."
    exec "$SCRIPT_DIR/setup-project.sh" "$@"
fi

# Быстрая установка: только копирование конфигурации
CLAUDE_CONFIG_DIR="$HOME/.claude"

mkdir -p "$CLAUDE_CONFIG_DIR"/{modules,logs,skills,commands,agents}

# Бэкап если есть
if [ -f "$CLAUDE_CONFIG_DIR/CLAUDE.md" ]; then
    BACKUP="$CLAUDE_CONFIG_DIR/backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP"
    cp -r "$CLAUDE_CONFIG_DIR"/{CLAUDE.md,settings.json,modules} "$BACKUP/" 2>/dev/null || true
    echo -e "${YELLOW}[!]${NC} Бэкап: $BACKUP"
fi

# Копирование
for file in CLAUDE.md settings.json GAPS.md CHANGELOG.md TOOLS_REGISTRY.md GAP_DETECTION_PROTOCOL.md; do
    [ -f "$PROJECT_DIR/$file" ] && cp "$PROJECT_DIR/$file" "$CLAUDE_CONFIG_DIR/" && echo -e "${GREEN}[✓]${NC} $file"
done

[ -d "$PROJECT_DIR/modules" ] && cp -r "$PROJECT_DIR/modules/"* "$CLAUDE_CONFIG_DIR/modules/" && echo -e "${GREEN}[✓]${NC} modules/"

# Лог-файлы
touch "$CLAUDE_CONFIG_DIR/logs"/{security_audit,infra_audit,helm_audit,config_commit,chaos_audit}.log

echo -e "\n${GREEN}Быстрая установка завершена!${NC}"
echo -e "Конфигурация: $CLAUDE_CONFIG_DIR/"
echo ""
echo -e "${YELLOW}Для полной установки (зависимости, pass/keyring, git credentials):${NC}"
echo -e "  $SCRIPT_DIR/setup-project.sh"
echo ""
echo -e "Или:"
echo -e "  $SCRIPT_DIR/install.sh --full"
