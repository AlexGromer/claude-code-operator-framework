package main

import (
	"crypto/sha256"
	"fmt"
	"time"
)

// Priority levels for backlog tasks.
type Priority int

const (
	P1 Priority = iota + 1
	P2
	P3
)

func (p Priority) String() string {
	switch p {
	case P1:
		return "P1"
	case P2:
		return "P2"
	case P3:
		return "P3"
	default:
		return "P2"
	}
}

func ParsePriority(s string) Priority {
	switch s {
	case "P1":
		return P1
	case "P3":
		return P3
	default:
		return P2
	}
}

// Section of BACKLOG.md where the task resides.
type Section string

const (
	SectionActive    Section = "Active"
	SectionCompleted Section = "Completed Archive"
	SectionDeferred  Section = "Deferred"
)

// Task represents a single backlog item.
type Task struct {
	ID            string
	Description   string
	Priority      Priority
	Wave          string // "W1", "W2", etc. Empty if none.
	AgentHint     string // "general-purpose", etc. Without @ prefix.
	CreatedDate   time.Time
	CompletedDate *time.Time
	Completed     bool
	Section       Section
}

// TaskID generates a stable 8-char hex ID from the task description.
func TaskID(description string) string {
	h := sha256.Sum256([]byte(description))
	return fmt.Sprintf("%x", h[:4])
}

// StaleThreshold returns the staleness threshold for a given priority.
func StaleThreshold(p Priority) time.Duration {
	switch p {
	case P1:
		return 3 * 24 * time.Hour
	case P2:
		return 7 * 24 * time.Hour
	default:
		return 14 * 24 * time.Hour
	}
}
