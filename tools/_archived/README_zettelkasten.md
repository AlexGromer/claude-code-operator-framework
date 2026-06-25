# Zettelkasten Export Tool

CLI tool for creating and managing knowledge notes in Zettelkasten format with multi-format export capabilities.

## Overview

**Zettelkasten** (German: "slip box") is a knowledge management method based on atomic, linked notes. This tool implements:

- **Atomic notes**: Each note contains one idea
- **Unique IDs**: Timestamp-based with collision-resistant hash
- **Linking**: Notes reference each other by ID
- **Tagging**: Organize by multiple tags
- **Types**: Fleeting (temporary), Literature (from sources), Permanent (synthesized)
- **Export**: Obsidian, JSON, Moodle GIFT, Anki flashcards

## Installation

```bash
# Make executable
chmod +x ~/.claude/tools/zettelkasten_export.py

# Create knowledge base directory
mkdir -p /opt/agent_work_directory/shared/knowledge/notes

# Optionally create alias
alias zk='python3 ~/.claude/tools/zettelkasten_export.py'
```

## Usage

### 1. Create Notes

**Create note with inline content:**
```bash
python3 zettelkasten_export.py create-note \
    --title "OSINT Methodology Overview" \
    --type literature \
    --tags "osint,methodology" \
    --source "Smith (2025). OSINT Handbook. https://example.com" \
    --content "OSINT follows a 6-phase cycle: requirements, collection, processing, analysis, dissemination, feedback." \
    --questions "What are the 6 phases of OSINT?,Why is feedback important?"
```

**Create note from file:**
```bash
echo "Detailed content here..." > /tmp/note_content.md

python3 zettelkasten_export.py create-note \
    --title "Advanced OSINT Techniques" \
    --type permanent \
    --tags "osint,advanced" \
    --content-file /tmp/note_content.md \
    --links "20260210-143000-a1b2c3"
```

**Output:**
```json
{
  "status": "success",
  "note_id": "20260210-143000-a1b2c3",
  "json_path": "/opt/agent_work_directory/shared/knowledge/notes/20260210-143000-a1b2c3.json",
  "md_path": "/opt/agent_work_directory/shared/knowledge/notes/20260210-143000-a1b2c3.md",
  "note": { ... }
}
```

### 2. List Notes

**List all notes:**
```bash
python3 zettelkasten_export.py list-notes
```

**Filter by type:**
```bash
python3 zettelkasten_export.py list-notes --type literature
```

**Filter by tag:**
```bash
python3 zettelkasten_export.py list-notes --tag osint
```

**Filter by date:**
```bash
python3 zettelkasten_export.py list-notes --since "2026-02-01T00:00:00Z"
```

**Output:**
```json
[
  {
    "id": "20260210-143000-a1b2c3",
    "title": "OSINT Methodology Overview",
    "type": "literature",
    "tags": ["osint", "methodology"],
    "created": "2026-02-10T14:30:00Z",
    "has_questions": true
  }
]
```

### 3. Export Notes

**Export to Obsidian:**
```bash
python3 zettelkasten_export.py export \
    --format obsidian \
    --output ~/obsidian_vault/my_notes

# Filter by tag
python3 zettelkasten_export.py export \
    --format obsidian \
    --output ~/obsidian_vault/security_notes \
    --tag security
```

**Obsidian output structure:**
```
~/obsidian_vault/my_notes/
└── notes/
    ├── 20260210-143000-a1b2c3_OSINT_Methodology_Overview.md
    └── 20260210-143500-d4e5f6_Advanced_OSINT_Techniques.md
```

**Export to JSON:**
```bash
python3 zettelkasten_export.py export \
    --format json \
    --output /tmp/knowledge_backup
```

**JSON output:**
```json
{
  "exported": "2026-02-10T15:00:00Z",
  "count": 42,
  "notes": [...]
}
```

**Export to Moodle GIFT:**
```bash
python3 zettelkasten_export.py export \
    --format moodle \
    --output ~/moodle_course/quizzes
```

**GIFT output:**
```
$CATEGORY: osint_methodology

// Note: OSINT Methodology Overview
// ID: 20260210-143000-a1b2c3
::20260210-143000-a1b2c3_What are the 6 phases of OSINT?::
What are the 6 phases of OSINT? {
#### Answer based on: OSINT Methodology Overview
OSINT follows a 6-phase cycle: requirements, collection, processing, analysis, dissemination, feedback.
}
```

### 4. Generate Flashcards

**Anki CSV format:**
```bash
python3 zettelkasten_export.py flashcards \
    --output ~/anki_import.csv \
    --format anki-csv

# Filter by tag
python3 zettelkasten_export.py flashcards \
    --output ~/security_flashcards.csv \
    --format anki-csv \
    --tag security
```

**Anki CSV output:**
```
What are the 6 phases of OSINT?	OSINT follows a 6-phase cycle: requirements, collection, processing, analysis, dissemination, feedback.
What is the main idea of: OSINT Methodology Overview?	OSINT follows a 6-phase cycle: requirements, collection, processing...
```

**JSON format:**
```bash
python3 zettelkasten_export.py flashcards \
    --output ~/flashcards.json \
    --format json
```

**JSON output:**
```json
{
  "exported": "2026-02-10T15:00:00Z",
  "count": 84,
  "flashcards": [
    {
      "front": "What are the 6 phases of OSINT?",
      "back": "OSINT follows a 6-phase cycle: requirements, collection...",
      "tags": ["osint", "methodology"],
      "source": "OSINT Methodology Overview",
      "note_id": "20260210-143000-a1b2c3"
    }
  ]
}
```

## Note Structure

### JSON Format

```json
{
  "id": "20260210-143000-a1b2c3",
  "title": "Note title",
  "type": "literature",
  "tags": ["tag1", "tag2"],
  "source": "Author (Year). Title. URL",
  "links": ["20260210-142000-d4e5f6"],
  "created": "2026-02-10T14:30:00Z",
  "content": "Main content.\nSupports markdown.",
  "questions": ["Question 1?", "Question 2?"]
}
```

### Markdown Format

```markdown
---
id: 20260210-143000-a1b2c3
title: Note title
type: literature
tags: ["tag1", "tag2"]
source: "Author (Year). Title. URL"
links: ["20260210-142000-d4e5f6"]
created: 2026-02-10T14:30:00Z
---

Main content.
Supports markdown.

## Questions
- Question 1?
- Question 2?
```

### Obsidian Export Format

```markdown
---
id: 20260210-143000-a1b2c3
type: literature
tags:
  - tag1
  - tag2
source: "Author (Year). Title. URL"
created: 2026-02-10T14:30:00Z
---

Main content.

## Links
- [[Other Note Title]]

## Questions
- Question 1?
```

## Note Types

| Type | Purpose | When to Use |
|------|---------|-------------|
| **fleeting** | Temporary notes, quick captures | During reading, meetings, brainstorming |
| **literature** | Notes from external sources | Books, papers, articles, videos |
| **permanent** | Synthesized knowledge | After processing fleeting/literature notes |

## Workflow Examples

### 1. Research Paper Processing

```bash
# 1. Create literature note while reading
zk create-note \
    --title "Smith 2025 - OSINT Automation" \
    --type literature \
    --tags "osint,automation,research" \
    --source "Smith, J. (2025). Automating OSINT Workflows. Journal of InfoSec, 12(3), 45-67." \
    --content-file /tmp/smith2025_notes.md \
    --questions "What automation approaches does Smith recommend?,What are the limitations?"

# 2. Create permanent note synthesizing insights
NOTE1_ID="20260210-143000-a1b2c3"  # From step 1

zk create-note \
    --title "OSINT Automation Best Practices" \
    --type permanent \
    --tags "osint,automation,synthesis" \
    --links "$NOTE1_ID" \
    --content "Synthesis of automation approaches from Smith (2025)..."
```

### 2. Meeting Notes to Knowledge

```bash
# 1. Capture fleeting notes during meeting
zk create-note \
    --title "Security Review Meeting 2026-02-10" \
    --type fleeting \
    --tags "meeting,security" \
    --content "Discussed new vulnerability management process. Key points: ..."

# 2. Process into permanent note later
zk create-note \
    --title "Vulnerability Management Process" \
    --type permanent \
    --tags "security,process" \
    --links "20260210-150000-xyz123" \
    --content "Refined process based on meeting discussion..."
```

### 3. Course Creation

```bash
# 1. Create notes for each topic
zk create-note --title "Topic 1: OSINT Basics" --type permanent --tags "course,osint,basics" --content "..." --questions "What is OSINT?,Name 3 OSINT sources"
zk create-note --title "Topic 2: OSINT Tools" --type permanent --tags "course,osint,tools" --content "..." --questions "What is Shodan?,How to use theHarvester?"

# 2. Export to Moodle for quiz
zk export --format moodle --output ~/course/week1 --tag course

# 3. Generate flashcards for students
zk flashcards --format anki-csv --output ~/course/flashcards.csv --tag course
```

## Integration

### With Obsidian

1. Export notes to Obsidian vault:
```bash
zk export --format obsidian --output ~/obsidian_vault/zettelkasten
```

2. In Obsidian:
   - Notes appear with full metadata
   - Wikilinks work: [[Note Title]]
   - Tags searchable: #osint #security
   - Graph view shows connections

### With Anki

1. Generate flashcards:
```bash
zk flashcards --format anki-csv --output ~/flashcards.csv
```

2. In Anki:
   - File → Import
   - Select `flashcards.csv`
   - Fields separated by: Tab
   - Field 1 → Front, Field 2 → Back

### With Moodle

1. Export quiz:
```bash
zk export --format moodle --output ~/moodle_quiz
```

2. In Moodle:
   - Course → Question Bank → Import
   - Format: GIFT
   - Upload `quiz.gift`

## Automation

### Hook for Automatic Note Capture

Create `~/.claude/hooks/knowledge_capture_hook.py`:

```python
#!/usr/bin/env python3
import subprocess
import sys

# Detect when Claude provides learning content
if "claude_learns:" in sys.stdin.read():
    # Extract and create note automatically
    subprocess.run([
        "python3",
        "/home/user/.claude/tools/zettelkasten_export.py",
        "create-note",
        "--title", "Auto-captured Learning",
        "--type", "fleeting",
        "--tags", "auto",
        "--content", "..."
    ])
```

### Anacron Job for Weekly Review

```bash
# ~/.anacron/anacrontab
7 15 knowledge_review cd ~/.claude && python3 tools/knowledge_review.py
```

## Best Practices

### Writing Atomic Notes

✅ **Good** (atomic):
```
Title: "Shodan Search Syntax"
Content: "Shodan uses filters: port:, hostname:, org:, country:.
Example: hostname:*.example.com port:443"
```

❌ **Bad** (not atomic):
```
Title: "OSINT Tools Overview"
Content: "Shodan is a search engine. TheHarvester finds emails.
Maltego does link analysis. Recon-ng is a framework..."
```

### Linking Strategy

- Link when notes have **direct relationship**
- Create "hub notes" for related concepts
- Use tags for loose groupings
- Review connections periodically

### Tag Taxonomy

```
# Domain
osint, security, devops, reverse

# Type
tool, technique, concept, workflow

# Status
draft, reviewed, validated

# Priority
critical, important, reference
```

## Troubleshooting

### Permission Denied

```bash
chmod +x ~/.claude/tools/zettelkasten_export.py
```

### Directory Not Found

```bash
mkdir -p /opt/agent_work_directory/shared/knowledge/notes
```

### Duplicate Note IDs (Collision)

Extremely unlikely (6-char SHA256 hash collision). If occurs:
- Tool will overwrite existing note
- Manually rename one note ID

### Obsidian Links Not Working

- Ensure note titles are unique
- Check wikilink format: `[[Title]]` not `[[id]]`
- Verify notes exported to same vault

### Anki Import Issues

- Ensure CSV uses **tab separator** (not comma)
- Check for special characters (escape quotes)
- Use `--format anki-csv` not generic CSV

## Files and Paths

| Path | Purpose |
|------|---------|
| `/home/user/.claude/tools/zettelkasten_export.py` | Main tool |
| `/opt/agent_work_directory/shared/knowledge/notes/` | Knowledge base (JSON + MD) |
| `~/.claude/evaluation/data/zettelkasten_stats.json` | Usage statistics (future) |

## Performance

- **Create note**: ~50ms (includes JSON + MD write)
- **List notes**: ~5ms per 100 notes
- **Export 1000 notes**: ~2-3 seconds
- **Flashcard generation**: ~1ms per card

## Limitations

- No full-text search (use external tools: grep, ripgrep)
- No automatic bidirectional links (manual)
- No built-in graph visualization (use Obsidian)
- No collaborative features (single-user)

## Roadmap

- [ ] Full-text search with indexing
- [ ] Automatic link suggestions
- [ ] Note templates
- [ ] Statistics dashboard
- [ ] Web interface
- [ ] Git integration for versioning

## References

- Ahrens, S. (2017). *How to Take Smart Notes*. Sönke Ahrens.
- [Zettelkasten Method Overview](https://zettelkasten.de/)
- [Obsidian Documentation](https://help.obsidian.md/)
- [GIFT Format Specification](https://docs.moodle.org/en/GIFT_format)

## License

MIT License - Use freely for personal or commercial projects.

## Support

For issues or questions:
- Check this README
- Test with `test_zettelkasten.sh`
- Review source code (well-documented)
- Open issue in project repo
