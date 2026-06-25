package main

import (
	"fmt"
	"strings"
)

// Format serializes a Backlog struct back to BACKLOG.md markdown.
func Format(b *Backlog) string {
	var sb strings.Builder

	sb.WriteString("# BACKLOG\n\n")

	sb.WriteString("## Active\n\n")
	for _, t := range b.Active {
		sb.WriteString(FormatTask(t))
		sb.WriteByte('\n')
	}
	if len(b.Active) == 0 {
		sb.WriteString("_No active tasks._\n")
	}

	sb.WriteString("\n## Completed Archive\n\n")
	for _, t := range b.Completed {
		sb.WriteString(FormatTask(t))
		sb.WriteByte('\n')
	}
	if len(b.Completed) == 0 {
		sb.WriteString("_No completed tasks._\n")
	}

	sb.WriteString("\n## Deferred\n\n")
	for _, t := range b.Deferred {
		sb.WriteString(FormatTask(t))
		sb.WriteByte('\n')
	}
	if len(b.Deferred) == 0 {
		sb.WriteString("_No deferred tasks._\n")
	}

	return sb.String()
}

// FormatTask serializes a single task to its markdown line representation.
func FormatTask(t Task) string {
	var sb strings.Builder

	// Checkbox
	if t.Completed {
		sb.WriteString("- [x] ")
	} else {
		sb.WriteString("- [ ] ")
	}

	// Optional wave
	if t.Wave != "" {
		fmt.Fprintf(&sb, "[%s] ", t.Wave)
	}

	// Description
	sb.WriteString(t.Description)

	// Priority
	fmt.Fprintf(&sb, " (%s)", t.Priority)

	// Optional agent hint
	if t.AgentHint != "" {
		fmt.Fprintf(&sb, " @%s", t.AgentHint)
	}

	// Em-dash + created date
	fmt.Fprintf(&sb, " — %s", t.CreatedDate.Format(dateFormat))

	// Optional completed date
	if t.CompletedDate != nil {
		fmt.Fprintf(&sb, " ✓ %s", t.CompletedDate.Format(dateFormat))
	}

	return sb.String()
}
