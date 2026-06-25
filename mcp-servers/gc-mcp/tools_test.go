package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
)

func makeRequest(args map[string]any) mcp.CallToolRequest {
	return mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Arguments: args,
		},
	}
}

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

func TestHandleGCRun(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	// Create stale task dir
	tasksDir := filepath.Join(tmpHome, "tasks")
	os.MkdirAll(tasksDir, 0o755)
	old := filepath.Join(tasksDir, "stale-session")
	os.MkdirAll(old, 0o755)
	oldTime := time.Now().Add(-48 * time.Hour)
	os.Chtimes(old, oldTime, oldTime)

	ctx := context.Background()
	result, err := handleGCRun(ctx, makeRequest(map[string]any{
		"cwd": t.TempDir(),
	}))
	if err != nil {
		t.Fatalf("gc_run: %v", err)
	}

	text := extractText(result)
	var resp GCResults
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp.DryRun {
		t.Error("should not be dry run")
	}
	if resp.Total < 1 {
		t.Errorf("total: got %d, want >= 1", resp.Total)
	}
	if len(resp.Results) != 16 {
		t.Errorf("results count: got %d, want 16", len(resp.Results))
	}

	// Verify the dir was actually removed
	if _, err := os.Stat(old); !os.IsNotExist(err) {
		t.Error("stale dir should be removed")
	}
}

func TestHandleGCDryRun(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	// Create stale artifacts
	tasksDir := filepath.Join(tmpHome, "tasks")
	os.MkdirAll(tasksDir, 0o755)
	old := filepath.Join(tasksDir, "stale")
	os.MkdirAll(old, 0o755)
	oldTime := time.Now().Add(-48 * time.Hour)
	os.Chtimes(old, oldTime, oldTime)

	ctx := context.Background()
	result, err := handleGCDryRun(ctx, makeRequest(map[string]any{
		"cwd": t.TempDir(),
	}))
	if err != nil {
		t.Fatalf("gc_dry_run: %v", err)
	}

	text := extractText(result)
	var resp GCResults
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if !resp.DryRun {
		t.Error("should be dry run")
	}
	if resp.Total < 1 {
		t.Errorf("total: got %d, want >= 1", resp.Total)
	}

	// Dir should still exist
	if _, err := os.Stat(old); err != nil {
		t.Error("dir should still exist in dry run")
	}
}

func TestHandleGCStatus(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	// Create stale artifacts
	teamsDir := filepath.Join(tmpHome, "teams")
	os.MkdirAll(teamsDir, 0o755)
	old := filepath.Join(teamsDir, "team-old")
	os.MkdirAll(old, 0o755)
	oldTime := time.Now().Add(-48 * time.Hour)
	os.Chtimes(old, oldTime, oldTime)

	ctx := context.Background()
	result, err := handleGCStatus(ctx, makeRequest(map[string]any{
		"cwd": t.TempDir(),
	}))
	if err != nil {
		t.Fatalf("gc_status: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	totalStale := int(resp["total_stale"].(float64))
	if totalStale < 1 {
		t.Errorf("total_stale: got %d, want >= 1", totalStale)
	}

	targets, ok := resp["targets"].([]any)
	if !ok {
		t.Fatal("targets should be array")
	}
	if len(targets) != 16 {
		t.Errorf("targets count: got %d, want 16", len(targets))
	}
}

func TestBacklogRotation(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	cwd := t.TempDir()
	backlogPath := filepath.Join(cwd, "BACKLOG.md")
	content := `# BACKLOG — test

## Active
- [x] Completed task one (P1) — 2026-02-20
- [ ] Open task two (P2) — 2026-02-21
- [x] Completed task three (P2) — 2026-02-22

## Completed Archive
- [x] Old completed (P1) — 2026-01-01 ✓ 2026-01-02

## Deferred
- [ ] Deferred task (P3) — 2026-02-15
`
	os.WriteFile(backlogPath, []byte(content), 0o644)

	ctx := context.Background()
	result, err := handleGCRun(ctx, makeRequest(map[string]any{
		"cwd": cwd,
	}))
	if err != nil {
		t.Fatalf("gc_run: %v", err)
	}

	text := extractText(result)
	var resp GCResults
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	// Find backlog result
	var backlogResult *CleanupResult
	for i := range resp.Results {
		if resp.Results[i].Target == "backlog" {
			backlogResult = &resp.Results[i]
			break
		}
	}
	if backlogResult == nil {
		t.Fatal("backlog result not found")
	}
	if backlogResult.Cleaned != 2 {
		t.Errorf("backlog cleaned: got %d, want 2 (2 moved)", backlogResult.Cleaned)
	}

	// Verify file content
	data, err := os.ReadFile(backlogPath)
	if err != nil {
		t.Fatalf("read backlog: %v", err)
	}
	fileContent := string(data)

	// Active should not have completed items
	lines := strings.Split(fileContent, "\n")
	inActive := false
	for _, line := range lines {
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
			t.Errorf("completed task still in Active: %s", trimmed)
		}
	}

	// Archive should contain moved tasks
	if !strings.Contains(fileContent, "Completed task one") {
		t.Error("moved task should be in archive")
	}
}

func TestServerInfo(t *testing.T) {
	info := ServerInfo()
	if info.Name != "gc-mcp" {
		t.Errorf("name: got %q, want gc-mcp", info.Name)
	}
	if info.Version != "0.1.0" {
		t.Errorf("version: got %q, want 0.1.0", info.Version)
	}
}
