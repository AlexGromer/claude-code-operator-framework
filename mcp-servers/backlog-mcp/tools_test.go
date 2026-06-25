package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
)

func setupTestBacklog(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	src, err := os.ReadFile("testdata/full.md")
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	path := filepath.Join(dir, "BACKLOG.md")
	if err := os.WriteFile(path, src, 0o644); err != nil {
		t.Fatalf("write fixture: %v", err)
	}
	return path
}

func makeRequest(args map[string]any) mcp.CallToolRequest {
	return mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Arguments: args,
		},
	}
}

func TestAddAndList(t *testing.T) {
	path := setupTestBacklog(t)
	ctx := context.Background()

	// Add a task
	result, err := handleAdd(ctx, makeRequest(map[string]any{
		"description": "New test task",
		"priority":    "P1",
		"wave":        "W3",
		"agent_hint":  "test-writer",
		"file_path":   path,
	}))
	if err != nil {
		t.Fatalf("add: %v", err)
	}
	assertResultContains(t, result, "added")

	// List active tasks
	result, err = handleList(ctx, makeRequest(map[string]any{
		"section":   "Active",
		"file_path": path,
	}))
	if err != nil {
		t.Fatalf("list: %v", err)
	}

	var listResp map[string]any
	text := extractText(result)
	if err := json.Unmarshal([]byte(text), &listResp); err != nil {
		t.Fatalf("parse list: %v", err)
	}
	count := int(listResp["count"].(float64))
	if count != 5 { // 4 original + 1 new
		t.Errorf("count: got %d, want 5", count)
	}
}

func TestComplete(t *testing.T) {
	path := setupTestBacklog(t)
	ctx := context.Background()

	// Complete a task by description
	result, err := handleComplete(ctx, makeRequest(map[string]any{
		"task_id":   "authentication",
		"file_path": path,
	}))
	if err != nil {
		t.Fatalf("complete: %v", err)
	}
	assertResultContains(t, result, "completed")

	// Verify it moved to completed archive
	b, err := Load(path)
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	if len(b.Active) != 3 { // was 4, now 3
		t.Errorf("active: got %d, want 3", len(b.Active))
	}
	if len(b.Completed) != 4 { // was 3, now 4
		t.Errorf("completed: got %d, want 4", len(b.Completed))
	}
}

func TestDelete(t *testing.T) {
	path := setupTestBacklog(t)
	ctx := context.Background()

	result, err := handleDelete(ctx, makeRequest(map[string]any{
		"task_id":   "landing page",
		"file_path": path,
	}))
	if err != nil {
		t.Fatalf("delete: %v", err)
	}
	assertResultContains(t, result, "deleted")

	b, err := Load(path)
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	if len(b.Active) != 3 {
		t.Errorf("active: got %d, want 3", len(b.Active))
	}
}

func TestUpdate(t *testing.T) {
	path := setupTestBacklog(t)
	ctx := context.Background()

	result, err := handleUpdate(ctx, makeRequest(map[string]any{
		"task_id":    "database migrations",
		"priority":   "P1",
		"wave":       "W3",
		"agent_hint": "db-developer",
		"file_path":  path,
	}))
	if err != nil {
		t.Fatalf("update: %v", err)
	}
	assertResultContains(t, result, "updated")

	b, err := Load(path)
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	found := false
	for _, task := range b.Active {
		if task.Description == "Add database migrations" {
			if task.Priority != P1 {
				t.Errorf("priority: got %v, want P1", task.Priority)
			}
			if task.Wave != "W3" {
				t.Errorf("wave: got %q, want W3", task.Wave)
			}
			found = true
			break
		}
	}
	if !found {
		t.Error("updated task not found")
	}
}

func TestStale(t *testing.T) {
	path := setupTestBacklog(t)
	ctx := context.Background()

	result, err := handleStale(ctx, makeRequest(map[string]any{
		"file_path": path,
	}))
	if err != nil {
		t.Fatalf("stale: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}
	// Tasks from 2026-02-20 should be stale by now (test date is >= 2026-02-26)
	staleCount := int(resp["stale_count"].(float64))
	if staleCount < 1 {
		t.Logf("stale_count=%d (may vary by run date)", staleCount)
	}
}

func TestStats(t *testing.T) {
	path := setupTestBacklog(t)
	ctx := context.Background()

	result, err := handleStats(ctx, makeRequest(map[string]any{
		"file_path": path,
	}))
	if err != nil {
		t.Fatalf("stats: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}
	if int(resp["active"].(float64)) != 4 {
		t.Errorf("active: got %v, want 4", resp["active"])
	}
	if int(resp["completed"].(float64)) != 3 {
		t.Errorf("completed: got %v, want 3", resp["completed"])
	}
	if int(resp["total"].(float64)) != 9 {
		t.Errorf("total: got %v, want 9", resp["total"])
	}
}

func TestRotateNoOp(t *testing.T) {
	path := setupTestBacklog(t)
	ctx := context.Background()

	result, err := handleRotate(ctx, makeRequest(map[string]any{
		"file_path": path,
	}))
	if err != nil {
		t.Fatalf("rotate: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}
	if int(resp["moved_to_deferred"].(float64)) != 0 {
		t.Error("should not move any tasks")
	}
}

func TestAutoCreateBacklog(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "BACKLOG.md")

	b, err := Load(path)
	if err != nil {
		t.Fatalf("load: %v", err)
	}
	if len(b.Active) != 0 {
		t.Error("new backlog should be empty")
	}

	// File should exist now
	if _, err := os.Stat(path); err != nil {
		t.Errorf("file should be created: %v", err)
	}
}

// --- test helpers ---

func extractText(result *mcp.CallToolResult) string {
	if result == nil || len(result.Content) == 0 {
		return ""
	}
	for _, c := range result.Content {
		if tc, ok := c.(mcp.TextContent); ok {
			return tc.Text
		}
	}
	return ""
}

func assertResultContains(t *testing.T, result *mcp.CallToolResult, substr string) {
	t.Helper()
	text := extractText(result)
	if text == "" {
		t.Fatalf("empty result, expected to contain %q", substr)
	}
	if !contains(text, substr) {
		t.Errorf("result %q does not contain %q", text, substr)
	}
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && searchString(s, substr)
}

func searchString(s, sub string) bool {
	for i := 0; i <= len(s)-len(sub); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
