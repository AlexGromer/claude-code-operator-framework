package main

import (
	"os"
	"strings"
	"testing"
	"time"
)

func TestParseFullBacklog(t *testing.T) {
	data, err := os.ReadFile("testdata/full.md")
	if err != nil {
		t.Fatalf("read testdata: %v", err)
	}

	b := Parse(string(data))

	if len(b.Active) != 4 {
		t.Errorf("active tasks: got %d, want 4", len(b.Active))
	}
	if len(b.Completed) != 3 {
		t.Errorf("completed tasks: got %d, want 3", len(b.Completed))
	}
	if len(b.Deferred) != 2 {
		t.Errorf("deferred tasks: got %d, want 2", len(b.Deferred))
	}
}

func TestParseTaskFields(t *testing.T) {
	data, err := os.ReadFile("testdata/full.md")
	if err != nil {
		t.Fatalf("read testdata: %v", err)
	}
	b := Parse(string(data))

	// First active task: "- [ ] [W1] Implement user authentication (P1) @web-developer — 2026-02-20"
	task := b.Active[0]
	if task.Description != "Implement user authentication" {
		t.Errorf("description: got %q", task.Description)
	}
	if task.Priority != P1 {
		t.Errorf("priority: got %v, want P1", task.Priority)
	}
	if task.Wave != "W1" {
		t.Errorf("wave: got %q, want W1", task.Wave)
	}
	if task.AgentHint != "web-developer" {
		t.Errorf("agent: got %q, want web-developer", task.AgentHint)
	}
	if task.Completed {
		t.Error("should not be completed")
	}
	expectedDate := time.Date(2026, 2, 20, 0, 0, 0, 0, time.UTC)
	if !task.CreatedDate.Equal(expectedDate) {
		t.Errorf("date: got %v, want %v", task.CreatedDate, expectedDate)
	}
	if task.CompletedDate != nil {
		t.Error("should have no completed date")
	}

	// Task without wave and agent: "- [ ] Design landing page mockup (P3) — 2026-02-22"
	task4 := b.Active[3]
	if task4.Wave != "" {
		t.Errorf("task4 wave: got %q, want empty", task4.Wave)
	}
	if task4.AgentHint != "" {
		t.Errorf("task4 agent: got %q, want empty", task4.AgentHint)
	}
	if task4.Priority != P3 {
		t.Errorf("task4 priority: got %v, want P3", task4.Priority)
	}
}

func TestParseCompletedTask(t *testing.T) {
	data, err := os.ReadFile("testdata/full.md")
	if err != nil {
		t.Fatalf("read testdata: %v", err)
	}
	b := Parse(string(data))

	// "- [x] Set up CI/CD pipeline (P1) @ci-cd-engineer — 2026-02-10 ✓ 2026-02-12"
	task := b.Completed[0]
	if !task.Completed {
		t.Error("should be completed")
	}
	if task.CompletedDate == nil {
		t.Fatal("should have completed date")
	}
	expected := time.Date(2026, 2, 12, 0, 0, 0, 0, time.UTC)
	if !task.CompletedDate.Equal(expected) {
		t.Errorf("completed date: got %v, want %v", task.CompletedDate, expected)
	}
}

func TestParseEmptyBacklog(t *testing.T) {
	data, err := os.ReadFile("testdata/empty.md")
	if err != nil {
		t.Fatalf("read testdata: %v", err)
	}

	b := Parse(string(data))

	if len(b.Active) != 0 {
		t.Errorf("active: got %d, want 0", len(b.Active))
	}
	if len(b.Completed) != 0 {
		t.Errorf("completed: got %d, want 0", len(b.Completed))
	}
	if len(b.Deferred) != 0 {
		t.Errorf("deferred: got %d, want 0", len(b.Deferred))
	}
}

func TestTaskID(t *testing.T) {
	id := TaskID("Implement user authentication")
	if len(id) != 8 {
		t.Errorf("ID length: got %d, want 8", len(id))
	}
	// Same description → same ID (stable)
	id2 := TaskID("Implement user authentication")
	if id != id2 {
		t.Errorf("unstable ID: %q != %q", id, id2)
	}
	// Different description → different ID
	id3 := TaskID("Something else")
	if id == id3 {
		t.Errorf("collision: %q == %q", id, id3)
	}
}

func TestRoundtrip(t *testing.T) {
	data, err := os.ReadFile("testdata/full.md")
	if err != nil {
		t.Fatalf("read testdata: %v", err)
	}

	b := Parse(string(data))
	output := Format(b)
	b2 := Parse(output)

	// Verify task counts preserved
	if len(b2.Active) != len(b.Active) {
		t.Errorf("active: %d != %d", len(b2.Active), len(b.Active))
	}
	if len(b2.Completed) != len(b.Completed) {
		t.Errorf("completed: %d != %d", len(b2.Completed), len(b.Completed))
	}
	if len(b2.Deferred) != len(b.Deferred) {
		t.Errorf("deferred: %d != %d", len(b2.Deferred), len(b.Deferred))
	}

	// Verify specific fields survive roundtrip
	for i, orig := range b.Active {
		rt := b2.Active[i]
		if orig.Description != rt.Description {
			t.Errorf("active[%d] desc: %q != %q", i, orig.Description, rt.Description)
		}
		if orig.Priority != rt.Priority {
			t.Errorf("active[%d] priority: %v != %v", i, orig.Priority, rt.Priority)
		}
		if orig.Wave != rt.Wave {
			t.Errorf("active[%d] wave: %q != %q", i, orig.Wave, rt.Wave)
		}
		if orig.AgentHint != rt.AgentHint {
			t.Errorf("active[%d] agent: %q != %q", i, orig.AgentHint, rt.AgentHint)
		}
	}
}

func TestFormatTask(t *testing.T) {
	task := Task{
		Description: "Build REST API",
		Priority:    P1,
		Wave:        "W2",
		AgentHint:   "api-developer",
		CreatedDate: time.Date(2026, 2, 25, 0, 0, 0, 0, time.UTC),
	}
	line := FormatTask(task)
	expected := "- [ ] [W2] Build REST API (P1) @api-developer — 2026-02-25"
	if line != expected {
		t.Errorf("format:\ngot:  %q\nwant: %q", line, expected)
	}
}

func TestFormatCompletedTask(t *testing.T) {
	completed := time.Date(2026, 2, 26, 0, 0, 0, 0, time.UTC)
	task := Task{
		Description:   "Fix login bug",
		Priority:      P2,
		CreatedDate:   time.Date(2026, 2, 24, 0, 0, 0, 0, time.UTC),
		Completed:     true,
		CompletedDate: &completed,
	}
	line := FormatTask(task)
	if !strings.Contains(line, "[x]") {
		t.Error("should contain [x]")
	}
	if !strings.Contains(line, "✓ 2026-02-26") {
		t.Error("should contain completed date")
	}
}

func TestFindTask(t *testing.T) {
	data, err := os.ReadFile("testdata/full.md")
	if err != nil {
		t.Fatalf("read testdata: %v", err)
	}
	b := Parse(string(data))

	// Find by description substring
	task, section, idx := FindTask(b, "authentication")
	if task == nil {
		t.Fatal("should find task")
	}
	if section != SectionActive {
		t.Errorf("section: got %v, want Active", section)
	}
	if idx != 0 {
		t.Errorf("index: got %d, want 0", idx)
	}

	// Find by ID
	id := TaskID("Implement user authentication")
	task2, _, _ := FindTask(b, id)
	if task2 == nil {
		t.Fatal("should find by ID")
	}
	if task2.Description != task.Description {
		t.Error("ID and substring should find same task")
	}

	// Not found
	task3, _, _ := FindTask(b, "nonexistent-xyz-123")
	if task3 != nil {
		t.Error("should not find nonexistent task")
	}
}
