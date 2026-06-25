# Rule: Request Clarification
# Auto-loaded by Claude Code from ~/.claude/rules/

## Principle

Before executing Standard+ tasks — verify essential parameters are present.
Missing context → ask, don't assume. Wrong assumptions waste more time than a question.

## Required Parameters by Domain

| Domain | Must have | Ask if missing |
|--------|-----------|----------------|
| Security/Pentest | target (IP/domain/app), scope, authorization | "Какой target и scope? Есть ли авторизация?" |
| OSINT | target (person/org/domain), legal basis | "Кого/что исследуем? Есть ли основания?" |
| DevOps/Infra | environment (dev/staging/prod), target infra | "Какое окружение? Что меняем?" |
| Code/Development | repo/files, requirements, language/framework | "Какие файлы? Какие требования?" |
| Analysis/Research | data source, output format, depth | "Где данные? Какой формат результата?" |
| Compliance | standard (ISO/ГОСТ/ФЗ), current state, scope | "Какой стандарт? Текущий уровень?" |
| DFIR | incident severity, evidence status, containment | "Какой severity? Что изолировано?" |

## When to Clarify

- **Simple tasks (<20):** Don't ask. Just do it.
- **Standard tasks (20-65):** Ask only if critical parameter is missing (target, scope, or deliverable).
- **Complex+ tasks (65+):** verify completeness before PlanMode. Missing params = bad plan.
- **NETWORK_ACTIVE/CREDENTIAL domain:** always confirm target and authorization — no exceptions.

## How to Clarify (by execution context)

### Main process / PlanMode
Use `AskUserQuestion` directly. One question, 2-4 options including reasonable defaults.

### Teammate (implicit team)
```
SendMessage(lead): "NEEDS_CLARIFICATION: [вопрос]. Не могу продолжить без [параметр]."
```
Lead asks user via AskUserQuestion, sends answer back.

### Task() subagent
Cannot ask questions. Return result with clarification section:
```
## NEEDS_CLARIFICATION
The following parameters were not specified:
- [parameter 1]: assumed [value], but verify with user
- [parameter 2]: could not proceed without this
Recommendations: [what to ask user before re-running]
```
Never silently assume critical parameters (target, scope, credentials, environment).

## Anti-Pattern: Over-Asking

Don't ask about:
- Things obvious from context (e.g., language when file extension is .py)
- Things with safe defaults (e.g., output format — just use markdown)
- Things already in the prompt or recent conversation
- Simple tasks that don't need parameters

One focused question is better than three vague ones.
