package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const defaultTemplate = `# BACKLOG

## Active

_No active tasks._

## Completed Archive

_No completed tasks._

## Deferred

_No deferred tasks._
`

// Load reads and parses a BACKLOG.md file. Creates from template if missing.
func Load(path string) (*Backlog, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			if wErr := atomicWrite(path, defaultTemplate); wErr != nil {
				return nil, fmt.Errorf("create backlog: %w", wErr)
			}
			return Parse(defaultTemplate), nil
		}
		return nil, fmt.Errorf("read backlog: %w", err)
	}
	return Parse(string(data)), nil
}

// Save serializes and atomically writes the backlog to disk.
func Save(path string, b *Backlog) error {
	content := Format(b)
	return atomicWrite(path, content)
}

// atomicWrite writes content to a temp file, fsyncs, then renames.
func atomicWrite(path string, content string) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("mkdir: %w", err)
	}

	tmp, err := os.CreateTemp(dir, ".backlog-*.tmp")
	if err != nil {
		return fmt.Errorf("create temp: %w", err)
	}
	tmpName := tmp.Name()

	defer func() {
		// Clean up temp file on any error path
		tmp.Close()
		os.Remove(tmpName)
	}()

	if _, err := tmp.WriteString(content); err != nil {
		return fmt.Errorf("write temp: %w", err)
	}
	if err := tmp.Sync(); err != nil {
		return fmt.Errorf("fsync: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close temp: %w", err)
	}
	if err := os.Rename(tmpName, path); err != nil {
		return fmt.Errorf("rename: %w", err)
	}
	return nil
}

// FindTask searches for a task by ID prefix or description substring.
func FindTask(b *Backlog, query string) (*Task, Section, int) {
	query = strings.TrimSpace(query)
	if query == "" {
		return nil, "", -1
	}

	// First pass: ID prefix match
	for i := range b.Active {
		if strings.HasPrefix(b.Active[i].ID, query) {
			return &b.Active[i], SectionActive, i
		}
	}
	for i := range b.Completed {
		if strings.HasPrefix(b.Completed[i].ID, query) {
			return &b.Completed[i], SectionCompleted, i
		}
	}
	for i := range b.Deferred {
		if strings.HasPrefix(b.Deferred[i].ID, query) {
			return &b.Deferred[i], SectionDeferred, i
		}
	}

	// Second pass: description substring (case-insensitive)
	lowerQuery := strings.ToLower(query)
	for i := range b.Active {
		if strings.Contains(strings.ToLower(b.Active[i].Description), lowerQuery) {
			return &b.Active[i], SectionActive, i
		}
	}
	for i := range b.Completed {
		if strings.Contains(strings.ToLower(b.Completed[i].Description), lowerQuery) {
			return &b.Completed[i], SectionCompleted, i
		}
	}
	for i := range b.Deferred {
		if strings.Contains(strings.ToLower(b.Deferred[i].Description), lowerQuery) {
			return &b.Deferred[i], SectionDeferred, i
		}
	}

	return nil, "", -1
}

// RemoveTask removes a task from its section by index.
func RemoveTask(b *Backlog, section Section, index int) {
	switch section {
	case SectionActive:
		b.Active = append(b.Active[:index], b.Active[index+1:]...)
	case SectionCompleted:
		b.Completed = append(b.Completed[:index], b.Completed[index+1:]...)
	case SectionDeferred:
		b.Deferred = append(b.Deferred[:index], b.Deferred[index+1:]...)
	}
}
