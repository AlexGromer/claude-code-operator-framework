package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// BacklogRotateResult holds the results of a BACKLOG.md rotation.
type BacklogRotateResult struct {
	Moved  int `json:"moved"`
	Pruned int `json:"pruned"`
}

// rotateBacklog moves completed items from Active to Completed Archive and prunes archive to 50.
func rotateBacklog(path string, dryRun bool) BacklogRotateResult {
	data, err := os.ReadFile(path)
	if err != nil {
		return BacklogRotateResult{}
	}

	content := string(data)
	lines := strings.Split(content, "\n")

	var activeLines []string
	var archiveLines []string
	var deferredLines []string
	var otherBefore []string // lines before Active section
	currentSection := ""

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "## Active") {
			currentSection = "active"
			continue
		} else if strings.HasPrefix(trimmed, "## Completed Archive") {
			currentSection = "archive"
			continue
		} else if strings.HasPrefix(trimmed, "## Deferred") {
			currentSection = "deferred"
			continue
		} else if strings.HasPrefix(trimmed, "## ") {
			currentSection = "other"
		}

		switch currentSection {
		case "active":
			activeLines = append(activeLines, line)
		case "archive":
			archiveLines = append(archiveLines, line)
		case "deferred":
			deferredLines = append(deferredLines, line)
		default:
			otherBefore = append(otherBefore, line)
		}
	}

	// Move completed from Active to Archive
	moved := 0
	var newActive []string
	var movedToArchive []string
	for _, line := range activeLines {
		if strings.HasPrefix(strings.TrimSpace(line), "- [x]") {
			movedToArchive = append(movedToArchive, line)
			moved++
		} else {
			newActive = append(newActive, line)
		}
	}

	// Split archive into task lines and other lines
	var archiveItems []string
	var archiveOther []string
	for _, line := range archiveLines {
		if strings.HasPrefix(strings.TrimSpace(line), "- [") {
			archiveItems = append(archiveItems, line)
		} else {
			archiveOther = append(archiveOther, line)
		}
	}

	// Add moved items to archive
	archiveItems = append(archiveItems, movedToArchive...)

	// Prune archive to last 50
	pruned := 0
	if len(archiveItems) > 50 {
		pruned = len(archiveItems) - 50
		archiveItems = archiveItems[len(archiveItems)-50:]
	}

	if moved == 0 && pruned == 0 {
		return BacklogRotateResult{}
	}

	if dryRun {
		return BacklogRotateResult{Moved: moved, Pruned: pruned}
	}

	// Rebuild the file
	// Find the project name from the first heading if present
	projectName := ""
	for _, line := range otherBefore {
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "# BACKLOG") {
			projectName = strings.TrimPrefix(trimmed, "# BACKLOG")
			projectName = strings.TrimSpace(strings.TrimPrefix(projectName, "—"))
			break
		}
	}

	var sb strings.Builder
	if projectName != "" {
		fmt.Fprintf(&sb, "# BACKLOG — %s\n\n", projectName)
	} else {
		sb.WriteString("# BACKLOG\n\n")
	}

	sb.WriteString("## Active\n")
	writeSection(&sb, newActive)

	sb.WriteString("\n## Deferred\n")
	writeSection(&sb, deferredLines)

	sb.WriteString("\n## Completed Archive\n")
	// Write non-task archive lines first
	for _, line := range archiveOther {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" {
			sb.WriteString(line)
			sb.WriteByte('\n')
		}
	}
	for _, line := range archiveItems {
		sb.WriteString(line)
		sb.WriteByte('\n')
	}
	if len(archiveOther) == 0 && len(archiveItems) == 0 {
		sb.WriteString("\n")
	}

	if err := os.WriteFile(path, []byte(sb.String()), 0o644); err != nil {
		return BacklogRotateResult{}
	}

	return BacklogRotateResult{Moved: moved, Pruned: pruned}
}

// countCompletedInActiveSection counts completed tasks in the Active section (for status).
// This is a scanner-based approach used by the status function in cleanup.go
// (countCompletedInActive). This file contains the write-capable version.
func countCompletedActive(path string) int {
	f, err := os.Open(path)
	if err != nil {
		return 0
	}
	defer f.Close()

	count := 0
	inActive := false
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
		trimmed := strings.TrimSpace(line)
		if strings.HasPrefix(trimmed, "## Active") {
			inActive = true
			continue
		}
		if strings.HasPrefix(trimmed, "## ") {
			inActive = false
			continue
		}
		if inActive && strings.HasPrefix(trimmed, "- [x]") {
			count++
		}
	}
	return count
}

func writeSection(sb *strings.Builder, lines []string) {
	written := false
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" && !strings.HasPrefix(trimmed, "_No ") {
			sb.WriteString(line)
			sb.WriteByte('\n')
			written = true
		}
	}
	if !written {
		sb.WriteByte('\n')
	}
}
