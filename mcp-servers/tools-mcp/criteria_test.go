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

// makeRequest creates a CallToolRequest with the given arguments.
func makeRequest(args map[string]any) mcp.CallToolRequest {
	return mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Arguments: args,
		},
	}
}

// extractText extracts text content from a tool result.
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

// TestCriteriaFreeze verifies that freezing criteria creates a file with correct data.
func TestCriteriaFreeze(t *testing.T) {
	// Override workDir to temp directory
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "12345678-1234-1234-1234-123456789012"

	ctx := context.Background()
	result, err := handleCriteriaFreeze(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
		"goal":       "Implement feature X",
		"result":     "Feature X works as specified",
		"criteria":   "Passes unit tests, No regression, Code reviewed",
	}))
	if err != nil {
		t.Fatalf("handleCriteriaFreeze: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if status, ok := resp["status"].(string); !ok || status != "frozen" {
		t.Errorf("status: got %v, want frozen", resp["status"])
	}

	// Verify file was created
	freezePath := freezeFilePath(sessionID)
	data, err := os.ReadFile(freezePath)
	if err != nil {
		t.Fatalf("read freeze file: %v", err)
	}

	var freeze FreezeData
	if err := json.Unmarshal(data, &freeze); err != nil {
		t.Fatalf("parse freeze data: %v", err)
	}

	if !freeze.IsFrozen {
		t.Error("IsFrozen should be true")
	}
	if freeze.Goal != "Implement feature X" {
		t.Errorf("goal: got %q, want %q", freeze.Goal, "Implement feature X")
	}
	if freeze.ExpectedResult != "Feature X works as specified" {
		t.Errorf("expected_result: got %q, want %q", freeze.ExpectedResult, "Feature X works as specified")
	}
	if len(freeze.Criteria) != 3 {
		t.Errorf("criteria count: got %d, want 3", len(freeze.Criteria))
	}
	if freeze.Criteria[0] != "Passes unit tests" {
		t.Errorf("first criterion: got %q", freeze.Criteria[0])
	}

	// Verify TTL is 24 hours from now
	expires, err := parseTimestamp(freeze.ExpiresAt)
	if err != nil {
		t.Fatalf("parse ExpiresAt: %v", err)
	}
	now := time.Now().UTC()
	expectedExpires := now.Add(freezeTTLHours * time.Hour)
	diff := expires.Sub(expectedExpires)
	// Allow 5 second tolerance
	if diff < -5*time.Second || diff > 5*time.Second {
		t.Errorf("ExpiresAt: diff %v, want < 5s", diff)
	}
}

// TestCriteriaCheck verifies that checking frozen criteria returns the correct data.
func TestCriteriaCheck(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "87654321-4321-4321-4321-210987654321"

	// First freeze
	ctx := context.Background()
	_, err := handleCriteriaFreeze(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
		"goal":       "Test goal",
		"result":     "Test result",
		"criteria":   "Criterion A, Criterion B",
	}))
	if err != nil {
		t.Fatalf("freeze: %v", err)
	}

	// Then check
	result, err := handleCriteriaCheck(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleCriteriaCheck: %v", err)
	}

	text := extractText(result)
	var freeze FreezeData
	if err := json.Unmarshal([]byte(text), &freeze); err != nil {
		t.Fatalf("parse freeze: %v", err)
	}

	if !freeze.IsFrozen {
		t.Error("IsFrozen should be true")
	}
	if len(freeze.Criteria) != 2 {
		t.Errorf("criteria count: got %d, want 2", len(freeze.Criteria))
	}
}

// TestCriteriaCheckExpired verifies that expired criteria are auto-removed and reported as unfrozen.
func TestCriteriaCheckExpired(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "11111111-1111-1111-1111-111111111111"

	// Manually create an expired freeze file
	freezePath := freezeFilePath(sessionID)
	os.MkdirAll(filepath.Dir(freezePath), 0755)

	now := time.Now().UTC()
	expired := now.Add(-1 * time.Hour) // 1 hour ago, past the 24h TTL

	freeze := FreezeData{
		FrozenAt:       now.Format(time.RFC3339),
		ExpiresAt:      expired.Format(time.RFC3339),
		SessionID:      sessionID,
		Goal:           "Old goal",
		ExpectedResult: "Old result",
		Criteria:       []string{"Old criterion"},
		IsFrozen:       true,
	}

	data, _ := json.MarshalIndent(freeze, "", "  ")
	data = append(data, '\n')
	os.WriteFile(freezePath, data, 0644)

	// Check should auto-expire
	ctx := context.Background()
	result, err := handleCriteriaCheck(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleCriteriaCheck: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if frozen, ok := resp["is_frozen"].(bool); !ok || frozen {
		t.Errorf("is_frozen: got %v, want false", resp["is_frozen"])
	}
	if msg, ok := resp["message"].(string); !ok || !strings.Contains(msg, "expired") {
		t.Errorf("message should mention expiry: %v", resp["message"])
	}

	// File should be removed
	if _, err := os.Stat(freezePath); !os.IsNotExist(err) {
		t.Error("freeze file should be removed after expiry")
	}
}

// TestCriteriaUnfreeze verifies that unfreezing removes the freeze file.
func TestCriteriaUnfreeze(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "22222222-2222-2222-2222-222222222222"

	ctx := context.Background()

	// Freeze first
	_, err := handleCriteriaFreeze(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
		"goal":       "To freeze",
		"result":     "Frozen",
		"criteria":   "Frozen criterion",
	}))
	if err != nil {
		t.Fatalf("freeze: %v", err)
	}

	freezePath := freezeFilePath(sessionID)
	if _, err := os.Stat(freezePath); err != nil {
		t.Fatalf("freeze file not created: %v", err)
	}

	// Unfreeze
	result, err := handleCriteriaUnfreeze(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleCriteriaUnfreeze: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if status, ok := resp["status"].(string); !ok || status != "unfrozen" {
		t.Errorf("status: got %v, want unfrozen", resp["status"])
	}

	// File should be removed
	if _, err := os.Stat(freezePath); !os.IsNotExist(err) {
		t.Error("freeze file should be removed after unfreeze")
	}
}

// TestCriteriaUnfreezeNotFrozen verifies unfreezing when no freeze exists.
func TestCriteriaUnfreezeNotFrozen(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "33333333-3333-3333-3333-333333333333"

	ctx := context.Background()
	result, err := handleCriteriaUnfreeze(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleCriteriaUnfreeze: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if status, ok := resp["status"].(string); !ok || status != "not_frozen" {
		t.Errorf("status: got %v, want not_frozen", resp["status"])
	}
}

// TestCriteriaList verifies listing returns frozen data or empty when not frozen.
func TestCriteriaList(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "44444444-4444-4444-4444-444444444444"

	ctx := context.Background()

	// List when not frozen
	result, err := handleCriteriaList(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleCriteriaList (not frozen): %v", err)
	}

	text := extractText(result)
	var freeze FreezeData
	if err := json.Unmarshal([]byte(text), &freeze); err != nil {
		t.Fatalf("parse freeze: %v", err)
	}

	if freeze.IsFrozen {
		t.Error("should not be frozen initially")
	}

	// Freeze
	_, err = handleCriteriaFreeze(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
		"goal":       "Goal for list",
		"result":     "Result for list",
		"criteria":   "Criterion for list",
	}))
	if err != nil {
		t.Fatalf("freeze: %v", err)
	}

	// List when frozen
	result, err = handleCriteriaList(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleCriteriaList (frozen): %v", err)
	}

	text = extractText(result)
	if err := json.Unmarshal([]byte(text), &freeze); err != nil {
		t.Fatalf("parse freeze: %v", err)
	}

	if !freeze.IsFrozen {
		t.Error("should be frozen")
	}
	if freeze.Goal != "Goal for list" {
		t.Errorf("goal: got %q", freeze.Goal)
	}
}

// TestCriteriaFreezeEmptyCriteria verifies error when no valid criteria provided.
func TestCriteriaFreezeEmptyCriteria(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "55555555-5555-5555-5555-555555555555"

	ctx := context.Background()
	result, err := handleCriteriaFreeze(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
		"goal":       "Goal",
		"result":     "Result",
		"criteria":   "   ,  , ",  // Only whitespace and commas
	}))
	if err != nil {
		t.Fatalf("handleCriteriaFreeze: %v", err)
	}

	text := extractText(result)
	// Should contain error message
	if !strings.Contains(text, "no valid criteria") {
		t.Errorf("should contain error about no valid criteria: %s", text)
	}
}

// TestCriteriaFreezeMissingRequired verifies error when required parameters are missing.
func TestCriteriaFreezeMissingRequired(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "66666666-6666-6666-6666-666666666666"

	tests := []struct {
		name    string
		args    map[string]any
		wantErr string
	}{
		{
			name: "missing_goal",
			args: map[string]any{
				"session_id": sessionID,
				"result":     "Result",
				"criteria":   "Criterion",
			},
			wantErr: "goal",
		},
		{
			name: "missing_result",
			args: map[string]any{
				"session_id": sessionID,
				"goal":       "Goal",
				"criteria":   "Criterion",
			},
			wantErr: "result",
		},
		{
			name: "missing_criteria",
			args: map[string]any{
				"session_id": sessionID,
				"goal":       "Goal",
				"result":     "Result",
			},
			wantErr: "criteria",
		},
	}

	ctx := context.Background()
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := handleCriteriaFreeze(ctx, makeRequest(tt.args))
			if err != nil {
				t.Fatalf("handleCriteriaFreeze: %v", err)
			}
			text := extractText(result)
			if !strings.Contains(text, tt.wantErr) {
				t.Errorf("should contain error about %s: %s", tt.wantErr, text)
			}
		})
	}
}
