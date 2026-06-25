#!/usr/bin/env python3
"""
Zettelkasten Knowledge Manager

CLI tool for creating and exporting knowledge notes in Zettelkasten format.
Supports creating atomic notes, linking them, and exporting to multiple formats
(Obsidian, JSON, Moodle GIFT, Anki flashcards).

Storage: /opt/agent_work_directory/shared/knowledge/notes/

Usage:
    zettelkasten_manager.py create-note --title "Note title" --type literature --tags security,osint
    zettelkasten_manager.py list-notes --tag security
    zettelkasten_manager.py export --format obsidian --output ~/knowledge_export
    zettelkasten_manager.py flashcards --output flashcards.csv --format anki-csv

Version: 2.0.0
Restored: 2026-02-10 (from archived zettelkasten_export.py, renamed)
"""

import argparse
import json
import hashlib
import fcntl
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Constants
KNOWLEDGE_BASE = Path("/opt/agent_work_directory/shared/knowledge/notes")
NOTE_TYPES = ["fleeting", "literature", "permanent"]
EXPORT_FORMATS = ["obsidian", "json", "moodle"]
FLASHCARD_FORMATS = ["anki-csv", "json"]


class ZettelkastenError(Exception):
    """Base exception for Zettelkasten operations."""
    pass


def generate_note_id(title: str, timestamp: datetime) -> str:
    """Generate unique note ID: YYYYMMDD-HHMMSS-{short_hash}."""
    timestamp_str = timestamp.strftime("%Y%m%d-%H%M%S")
    hash_input = f"{title}{timestamp_str}".encode('utf-8')
    short_hash = hashlib.sha256(hash_input).hexdigest()[:6]
    return f"{timestamp_str}-{short_hash}"


def atomic_write_json(file_path: Path, data: Dict[str, Any]) -> None:
    """Atomically write JSON data to file with locking."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = file_path.with_suffix('.tmp')
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.replace(tmp_path, file_path)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise ZettelkastenError(f"Failed to write {file_path}: {e}") from e


def atomic_write_text(file_path: Path, content: str) -> None:
    """Atomically write text content to file with locking."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = file_path.with_suffix('.tmp')
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.replace(tmp_path, file_path)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise ZettelkastenError(f"Failed to write {file_path}: {e}") from e


def sanitize_filename(name: str) -> str:
    """Sanitize string for use in filename."""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '_', name)
    return name[:50]


def format_note_markdown(note: Dict[str, Any]) -> str:
    """Format note as Markdown with YAML frontmatter."""
    frontmatter = [
        "---",
        f"id: {note['id']}",
        f"title: {note['title']}",
        f"type: {note['type']}",
        f"tags: {json.dumps(note['tags'])}",
        f"source: {json.dumps(note['source'])}",
        f"links: {json.dumps(note['links'])}",
        f"created: {note['created']}",
        "---",
        ""
    ]
    content_lines = [note['content'], ""]
    if note.get('questions'):
        content_lines.extend(["## Questions", *[f"- {q}" for q in note['questions']], ""])
    return "\n".join(frontmatter + content_lines)


def create_note(args: argparse.Namespace) -> Dict[str, Any]:
    """Create a new atomic note."""
    timestamp = datetime.now(timezone.utc)
    note_id = generate_note_id(args.title, timestamp)

    content = args.content or ""
    if args.content_file:
        content_path = Path(args.content_file)
        if not content_path.exists():
            raise ZettelkastenError(f"Content file not found: {args.content_file}")
        content = content_path.read_text(encoding='utf-8')

    tags = [tag.strip() for tag in args.tags.split(',')] if args.tags else []
    links = [link.strip() for link in args.links.split(',')] if args.links else []
    questions = [q.strip() for q in args.questions.split(',')] if args.questions else []

    note = {
        "id": note_id,
        "title": args.title,
        "type": args.type,
        "tags": tags,
        "source": args.source or "",
        "links": links,
        "created": timestamp.isoformat(),
        "content": content,
        "questions": questions
    }

    json_path = KNOWLEDGE_BASE / f"{note_id}.json"
    atomic_write_json(json_path, note)

    md_path = KNOWLEDGE_BASE / f"{note_id}.md"
    atomic_write_text(md_path, format_note_markdown(note))

    return {"status": "success", "note_id": note_id, "json_path": str(json_path), "md_path": str(md_path)}


def list_notes(args: argparse.Namespace) -> List[Dict[str, Any]]:
    """List all notes with optional filtering."""
    if not KNOWLEDGE_BASE.exists():
        return []

    notes = []
    for json_file in KNOWLEDGE_BASE.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                note = json.load(f)
            if args.type and note.get('type') != args.type:
                continue
            if args.tag and args.tag not in note.get('tags', []):
                continue
            if args.since:
                if datetime.fromisoformat(note['created']) < datetime.fromisoformat(args.since):
                    continue
            notes.append({
                "id": note['id'], "title": note['title'], "type": note['type'],
                "tags": note.get('tags', []), "created": note['created']
            })
        except Exception as e:
            print(f"Warning: Failed to read {json_file}: {e}", file=sys.stderr)

    notes.sort(key=lambda n: n['created'], reverse=True)
    return notes


def export_obsidian(output_dir: Path, notes: List[Dict[str, Any]]) -> None:
    """Export notes to Obsidian format."""
    notes_dir = output_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    id_to_title = {note['id']: note['title'] for note in notes}

    for note in notes:
        frontmatter = ["---", f"id: {note['id']}", f"type: {note['type']}", "tags:"]
        frontmatter.extend([f"  - {tag}" for tag in note.get('tags', [])])
        if note.get('source'):
            frontmatter.append(f"source: {json.dumps(note['source'])}")
        frontmatter.extend([f"created: {note['created']}", "---", ""])

        content_lines = [note['content'], ""]
        if note.get('links'):
            content_lines.append("## Links")
            for link_id in note['links']:
                content_lines.append(f"- [[{id_to_title.get(link_id, link_id)}]]")
            content_lines.append("")
        if note.get('questions'):
            content_lines.extend(["## Questions", *[f"- {q}" for q in note['questions']], ""])

        filename = f"{note['id']}_{sanitize_filename(note['title'])}.md"
        atomic_write_text(notes_dir / filename, "\n".join(frontmatter + content_lines))


def export_json(output_dir: Path, notes: List[Dict[str, Any]]) -> None:
    """Export notes to JSON format."""
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output_dir / "notes.json", {
        "exported": datetime.now(timezone.utc).isoformat(),
        "count": len(notes), "notes": notes
    })


def export_moodle(output_dir: Path, notes: List[Dict[str, Any]]) -> None:
    """Export notes to Moodle GIFT format."""
    output_dir.mkdir(parents=True, exist_ok=True)
    gift_lines = []
    for note in notes:
        if not note.get('questions'):
            continue
        category = "_".join(note.get('tags', ['general']))
        gift_lines.append(f"$CATEGORY: {category}\n")
        for question in note['questions']:
            gift_lines.extend([
                f"// Note: {note['title']}",
                f"::{note['id']}_{question[:30]}::",
                f"{question} {{",
                f"#### Answer based on: {note['title']}",
                f"{note['content'][:200]}...", "}\n"
            ])
    atomic_write_text(output_dir / "quiz.gift", "\n".join(gift_lines))


def export_notes(args: argparse.Namespace) -> Dict[str, Any]:
    """Export notes to target format."""
    output_dir = Path(args.output)
    if not KNOWLEDGE_BASE.exists():
        return {"status": "error", "message": "Knowledge base directory does not exist"}

    all_notes = []
    for json_file in KNOWLEDGE_BASE.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                note = json.load(f)
            if args.tag and args.tag not in note.get('tags', []):
                continue
            if args.type and note.get('type') != args.type:
                continue
            all_notes.append(note)
        except Exception as e:
            print(f"Warning: {e}", file=sys.stderr)

    if not all_notes:
        return {"status": "error", "message": "No notes found"}

    try:
        exporters = {"obsidian": export_obsidian, "json": export_json, "moodle": export_moodle}
        exporters[args.format](output_dir, all_notes)
        return {"status": "success", "format": args.format, "notes_exported": len(all_notes)}
    except Exception as e:
        return {"status": "error", "message": f"Export failed: {e}"}


def generate_flashcards(args: argparse.Namespace) -> Dict[str, Any]:
    """Generate spaced repetition flashcards from notes."""
    output_path = Path(args.output)
    if not KNOWLEDGE_BASE.exists():
        return {"status": "error", "message": "Knowledge base does not exist"}

    flashcards = []
    for json_file in KNOWLEDGE_BASE.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                note = json.load(f)
            if args.tag and args.tag not in note.get('tags', []):
                continue
            for question in note.get('questions', []):
                flashcards.append({
                    "front": question, "back": f"{note['content'][:300]}...",
                    "tags": note.get('tags', []), "source": note['title']
                })
            if note.get('content') and len(note['content']) > 100:
                flashcards.append({
                    "front": f"What is the main idea of: {note['title']}?",
                    "back": note['content'], "tags": note.get('tags', []), "source": note['title']
                })
        except Exception as e:
            print(f"Warning: {e}", file=sys.stderr)

    if not flashcards:
        return {"status": "error", "message": "No flashcards generated"}

    try:
        if args.format == "anki-csv":
            lines = [f"{c['front'].replace(chr(10),' ').replace(chr(9),' ')}\t{c['back'].replace(chr(10),' ').replace(chr(9),' ')}" for c in flashcards]
            atomic_write_text(output_path, "\n".join(lines))
        elif args.format == "json":
            atomic_write_json(output_path, {"exported": datetime.now(timezone.utc).isoformat(), "flashcards": flashcards})
        return {"status": "success", "format": args.format, "flashcards_generated": len(flashcards)}
    except Exception as e:
        return {"status": "error", "message": f"Failed: {e}"}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Zettelkasten knowledge management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    cp = subparsers.add_parser('create-note', help='Create a new atomic note')
    cp.add_argument('--title', required=True, help='Note title')
    cp.add_argument('--type', required=True, choices=NOTE_TYPES, help='Note type')
    cp.add_argument('--tags', help='Comma-separated tags')
    cp.add_argument('--source', help='Source citation')
    cp.add_argument('--content', help='Note content (inline)')
    cp.add_argument('--content-file', help='Read content from file')
    cp.add_argument('--links', help='Comma-separated linked note IDs')
    cp.add_argument('--questions', help='Comma-separated review questions')

    lp = subparsers.add_parser('list-notes', help='List all notes')
    lp.add_argument('--type', choices=NOTE_TYPES, help='Filter by type')
    lp.add_argument('--tag', help='Filter by tag')
    lp.add_argument('--since', help='Filter by date (ISO format)')

    ep = subparsers.add_parser('export', help='Export notes')
    ep.add_argument('--format', required=True, choices=EXPORT_FORMATS, help='Export format')
    ep.add_argument('--output', required=True, help='Output directory')
    ep.add_argument('--tag', help='Filter by tag')
    ep.add_argument('--type', choices=NOTE_TYPES, help='Filter by type')

    fp = subparsers.add_parser('flashcards', help='Generate flashcards')
    fp.add_argument('--output', required=True, help='Output file')
    fp.add_argument('--format', default='anki-csv', choices=FLASHCARD_FORMATS, help='Format')
    fp.add_argument('--tag', help='Filter by tag')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == 'create-note':
            print(json.dumps(create_note(args), indent=2))
        elif args.command == 'list-notes':
            print(json.dumps(list_notes(args), indent=2))
        elif args.command == 'export':
            print(json.dumps(export_notes(args), indent=2))
        elif args.command == 'flashcards':
            print(json.dumps(generate_flashcards(args), indent=2))
    except ZettelkastenError as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Unexpected: {e}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
