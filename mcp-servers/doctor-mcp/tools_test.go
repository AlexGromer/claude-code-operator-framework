package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

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

// setupMinimalEnv creates a minimal ~/.claude structure for integration tests.
func setupMinimalEnv(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	// Create minimal directory structure
	dirs := []string{
		filepath.Join(dir, ".claude", "hooks"),
		filepath.Join(dir, ".claude", "skills"),
		filepath.Join(dir, ".claude", "tools"),
		filepath.Join(dir, ".claude", "rules"),
		filepath.Join(dir, ".claude", "modules"),
		filepath.Join(dir, ".claude", "evaluation", "data"),
		filepath.Join(dir, ".claude", "evaluation", "tests"),
	}
	for _, d := range dirs {
		if err := os.MkdirAll(d, 0o755); err != nil {
			t.Fatal(err)
		}
	}

	// Create a few rule files
	rules := []string{"anti-hallucination.md", "authorization-levels.md", "code-before-write.md",
		"mandatory-checks.md", "mcp-rules.md", "task-execution.md", "working-directories.md"}
	for _, r := range rules {
		os.WriteFile(filepath.Join(dir, ".claude", "rules", r), []byte("# rule\n"), 0o644)
	}

	return dir
}

func TestHandleCheckValid(t *testing.T) {
	setupMinimalEnv(t)
	ctx := context.Background()

	result, err := handleCheck(ctx, makeRequest(map[string]any{
		"category": "rules",
	}))
	if err != nil {
		t.Fatalf("handleCheck: %v", err)
	}

	text := extractText(result)
	if text == "" {
		t.Fatal("empty result")
	}

	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}
	if resp["name"] != "Rules" {
		t.Errorf("name: got %v, want Rules", resp["name"])
	}
	if resp["status"] != "OK" {
		t.Errorf("status: got %v, want OK", resp["status"])
	}
}

func TestHandleCheckInvalid(t *testing.T) {
	ctx := context.Background()

	result, err := handleCheck(ctx, makeRequest(map[string]any{
		"category": "nonexistent",
	}))
	if err != nil {
		t.Fatalf("handleCheck: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "invalid category") {
		t.Errorf("expected error about invalid category, got: %s", text)
	}
}

func TestHandleCheckMissing(t *testing.T) {
	ctx := context.Background()

	result, err := handleCheck(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("handleCheck: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "required") {
		t.Errorf("expected 'required' error, got: %s", text)
	}
}

func TestHandleFull(t *testing.T) {
	setupMinimalEnv(t)
	ctx := context.Background()

	result, err := handleFull(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("handleFull: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "CLAUDE CODE DOCTOR") {
		t.Error("dashboard missing header")
	}
	if !strings.Contains(text, "Overall:") {
		t.Error("dashboard missing overall status")
	}
	// Should contain all 10 category names
	for _, cat := range []string{"Hooks", "Skills", "Tools", "MCP Servers", "Budget System", "Rules", "Modules", "Tests", "Logs & Data", "Anacron Jobs"} {
		if !strings.Contains(text, cat) {
			t.Errorf("dashboard missing category: %s", cat)
		}
	}
}

func TestHandleJSON(t *testing.T) {
	setupMinimalEnv(t)
	ctx := context.Background()

	result, err := handleJSON(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("handleJSON: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	checks, ok := resp["checks"].([]any)
	if !ok {
		t.Fatal("missing checks array")
	}
	if len(checks) != 10 {
		t.Errorf("checks count: got %d, want 10", len(checks))
	}

	summary, ok := resp["summary"].(map[string]any)
	if !ok {
		t.Fatal("missing summary")
	}
	if summary["categories_total"].(float64) != 10 {
		t.Errorf("categories_total: got %v, want 10", summary["categories_total"])
	}
}

func TestServerInfo(t *testing.T) {
	info := ServerInfo()
	if info.Name != "doctor-mcp" {
		t.Errorf("name: got %q, want doctor-mcp", info.Name)
	}
	if info.Version != "0.1.0" {
		t.Errorf("version: got %q, want 0.1.0", info.Version)
	}
}
