package main

import (
	"bufio"
	"regexp"
	"strings"
	"time"
)

// Backlog is the parsed representation of a BACKLOG.md file.
type Backlog struct {
	Active    []Task
	Completed []Task
	Deferred  []Task
}

// AllTasks returns all tasks across all sections.
func (b *Backlog) AllTasks() []Task {
	all := make([]Task, 0, len(b.Active)+len(b.Completed)+len(b.Deferred))
	all = append(all, b.Active...)
	all = append(all, b.Completed...)
	all = append(all, b.Deferred...)
	return all
}

var taskRe = regexp.MustCompile(
	`^- \[([ xX])\]\s+` + // checkbox
		`(?:\[([^\]]+)\]\s+)?` + // optional [W1]
		`(.+?)\s+` + // description (non-greedy)
		`\((P[123])\)` + // (P1)
		`(?:\s+@(\S+))?` + // optional @agent-hint
		`\s+—\s+` + // em-dash separator
		`(\d{4}-\d{2}-\d{2})` + // created date
		`(?:\s+✓\s+(\d{4}-\d{2}-\d{2}))?` + // optional completed date
		`\s*$`,
)

var sectionRe = regexp.MustCompile(`^##\s+(.+)$`)

const dateFormat = "2006-01-02"

// Parse parses a BACKLOG.md content string into a Backlog struct.
func Parse(content string) *Backlog {
	b := &Backlog{}
	currentSection := SectionActive

	scanner := bufio.NewScanner(strings.NewReader(content))
	for scanner.Scan() {
		line := scanner.Text()

		// Check for section header
		if m := sectionRe.FindStringSubmatch(line); m != nil {
			name := strings.TrimSpace(m[1])
			switch {
			case strings.Contains(name, "Active"):
				currentSection = SectionActive
			case strings.Contains(name, "Completed"):
				currentSection = SectionCompleted
			case strings.Contains(name, "Deferred"):
				currentSection = SectionDeferred
			}
			continue
		}

		// Check for task line
		if m := taskRe.FindStringSubmatch(line); m != nil {
			task := parseMatch(m, currentSection)
			switch currentSection {
			case SectionActive:
				b.Active = append(b.Active, task)
			case SectionCompleted:
				b.Completed = append(b.Completed, task)
			case SectionDeferred:
				b.Deferred = append(b.Deferred, task)
			}
		}
		// Unknown lines are silently skipped (tolerant parser)
	}

	return b
}

func parseMatch(m []string, section Section) Task {
	completed := m[1] == "x" || m[1] == "X"
	description := strings.TrimSpace(m[3])

	t := Task{
		ID:          TaskID(description),
		Description: description,
		Priority:    ParsePriority(m[4]),
		Wave:        m[2], // may be empty
		AgentHint:   m[5], // may be empty
		Completed:   completed,
		Section:     section,
	}

	if d, err := time.Parse(dateFormat, m[6]); err == nil {
		t.CreatedDate = d
	}

	if m[7] != "" {
		if d, err := time.Parse(dateFormat, m[7]); err == nil {
			t.CompletedDate = &d
		}
	}

	return t
}
