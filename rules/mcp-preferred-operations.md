# Rule: MCP Preferred Operations
# Auto-loaded by Claude Code from ~/.claude/rules/

## Принцип

Для операций где доступен **наш MCP tool** — используй его ВМЕСТО прямого редактирования
файлов или shell команд. MCP серверы (13 essential из `profile-mcp --list`)
валидируют формат, обновляют indexes, возвращают structured stats.

Ручные Edit/Bash — fallback когда MCP недоступен или не покрывает edge case.

## Правила по операциям

### BACKLOG.md

| Действие | Использовать | НЕ использовать |
|---|---|---|
| Добавить новую задачу | `mcp__backlog-mcp__backlog_add` | Edit tool + ручная строка |
| Отметить задачу как done | `mcp__backlog-mcp__backlog_complete` (автоматически перемещает в Completed Archive) | Ручное `[ ]` → `[x]` в секции Active |
| Посмотреть stats | `mcp__backlog-mcp__backlog_stats` | `grep -c` в Bash |
| Отфильтровать | `mcp__backlog-mcp__backlog_list` с filter (priority/wave/section/agent) | `awk` в Bash |
| Миграция (>30 Active) | `mcp__backlog-mcp__backlog_rotate` (раз в неделю) | Ручной мув строк |
| Удалить задачу | `mcp__backlog-mcp__backlog_delete` | Ручное удаление строки |
| Найти stale | `mcp__backlog-mcp__backlog_stale` | Bash по датам |

**Исключение**: массовое переписывание формата или cleanup корявых entries — допустим
Edit в одном проходе, потом recreate через MCP.

### Git remote операции (GitHub)

> **Precedence (разрешает конфликт с gh-CLI):** этот конфиг ПЕРЕОПРЕДЕЛЯЕТ дефолтную harness-инструкцию «use gh CLI». API-операции (PR/issue/review/repo/merge) → `mcp__github__*`; отправка локальных коммитов → `git push` (сохраняет SHA/GPG/Co-Authored-By). `gh` CLI — только fallback, если MCP github недоступен.

**Ключевое различие**:
- `git push` → отправляет УЖЕ сделанные local commits (сохраняет SHA, GPG signing, Co-Authored-By)
- `mcp__github__push_files` → создаёт НОВЫЙ commit через GitHub API с передачей content (другой SHA, author = token owner, нет GPG)

Выбор по сценарию:

| Действие | Использовать | Почему |
|---|---|---|
| Создать repo | `mcp__github__create_repository` | только через API |
| Создать/обновить **single file прямо на GitHub** (remote-first, без local edit) | `mcp__github__create_or_update_file` | не нужен local clone |
| **Massive remote-first batch** (несколько файлов без local commit) | `mcp__github__push_files` | один API commit без local clone |
| Создать branch на GitHub | `mcp__github__create_branch` | remote-only |
| **Push existing local commit(s)** | Bash `git push` | сохраняет SHA + GPG + Co-Authored-By |
| Open PR | `mcp__github__create_pull_request` | API workflow |
| PR review/comment | `mcp__github__add_issue_comment`, `create_pull_request_review` | API workflow |
| Search code | `mcp__github__search_code` | API |
| Списки issues/PRs | `mcp__github__list_issues`, `list_pull_requests` | API |
| Merge PR | `mcp__github__merge_pull_request` | API |

**Local git через Bash (MCP не нужен)**:
- `git init`, `git add`, `git commit` — local-only
- `git push` — sync local → remote (сохраняет local commit metadata)
- `git log`, `git status`, `git diff` — inspection
- `git reset`, `git checkout`, `git branch -d` — local mutations
- `git pull`, `git fetch` — sync remote → local

**Правило выбора**:
- Есть local edit → `git add && git commit && git push` (Bash)
- Нет local clone / one-off update на remote → `mcp__github__create_or_update_file`
- Нужен PR / issue / review → всегда MCP (API)

### Scope tracking (Standard+ задачи)

| Когда | Действие |
|---|---|
| Начало Standard+ (score ≥ 20) | `mcp__tools-mcp__scope_status` — проверить текущее state |
| После каждого Edit/Write | `mcp__tools-mcp__scope_track` с `file_path` — increment tracker |
| Warning level ≥ 2 | PAUSE, сообщить пользователю, пересмотреть scope |
| Конец Standard+ | `mcp__tools-mcp__scope_status` финально — зафиксировать |

Thresholds (из scope_track API):
- `files ≥ 4` → warning L1, предложить Plan Mode
- `files ≥ 6 AND domains ≥ 2` → warning L2, предложить implicit team (named teammates via Agent tool)
- `live_score ≥ 80` → tier Complex, требует EnterPlanMode

### Criteria freeze (Standard+)

| Когда | Действие |
|---|---|
| Goal/Result/Criteria определены | `mcp__tools-mcp__criteria_freeze({goal, result, criteria})` |
| Проверка что criteria актуальны | `mcp__tools-mcp__criteria_check` |
| Criteria нужно сменить (плохое планирование) | `mcp__tools-mcp__criteria_unfreeze` (явный сигнал) |

### Discovery scoring (ADR, research finds)

| Когда | Действие |
|---|---|
| Добавляю ADR (новое технологическое решение) | `mcp__score-mcp__score_discovery({title, category, description})` → сохранить impact score в ADR frontmatter |
| Research finding (новый tool/паттерн) | `score_discovery` → если ≥ 80 записать в GAPS.md с high priority |
| Batch scoring | `mcp__score-mcp__score_batch` |

### Сессии и usage

| Действие | Tool |
|---|---|
| Начало большой сессии | `mcp__tools-mcp__session_start` |
| Конец сессии | `mcp__tools-mcp__session_end` (генерирует summary) |
| Сбросить мусор | `mcp__tools-mcp__session_cleanup` |
| Top used tools | `mcp__tools-mcp__usage_top_tools` |
| Usage trends | `mcp__tools-mcp__usage_trends` |

### Health / diagnostics

| Симптом | Tool |
|---|---|
| Disk pressure | `mcp__gc-mcp__gc_status` → `gc_dry_run` → `gc_run` |
| MCP servers не отвечают | `mcp__doctor-mcp__doctor_check({category: "mcp"})` |
| Общий health check | `mcp__doctor-mcp__doctor_full` или `doctor_json` |
| Профиль MCP | `mcp__profile-mcp__profile_status` |

## Antipatterns (чего избегать)

1. **Ручной `Edit` BACKLOG.md для добавления/завершения задач** — MCP_backlog добавляет ID, валидирует формат, обновляет stats
2. **`Bash git push`** когда у нас MCP GitHub — push теряется в audit trail проекта
3. **Игнорирование scope_track для Standard+** — scope escalation не обнаруживается, задачи растут бесконтрольно
4. **Создавать ADR без score_discovery** — нет priority signal, prioritization теряется
5. **`grep -c` вместо `backlog_stats`** — теряется structured output, нет by_agent/by_priority

## Fallback policy

Если MCP tool недоступен в текущей сессии:
1. Проверить `mcp__profile-mcp__profile_status` — возможно профиль не загружен
2. Попробовать `mcp__profile-mcp__profile_load({name: "essential"})` для перезагрузки
3. Если всё ещё нет — использовать прямой инструмент (Edit/Bash) + записать в GAPS.md
   что MCP был недоступен (для фикса потом)
4. **Не блокироваться** — работа важнее process purity

## Recovery from manual state

Если в BACKLOG.md накопились `[x]` в Active section (ручное помечение):
```bash
python3 /tmp/uka-migrate-backlog.py /opt/uka_site/BACKLOG.md
```
Скрипт массово переносит `[x]` из `## Active` в `## Completed Archive`.
После — использовать `backlog_complete` по одной.
