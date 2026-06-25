package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// TestSessionStart verifies that session start creates the directory structure.
func TestSessionStart(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

	ctx := context.Background()
	result, err := handleSessionStart(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionStart: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if status, ok := resp["status"].(string); !ok || status != "success" {
		t.Errorf("status: got %v, want success", resp["status"])
	}

	// Verify directory structure
	sessionDir := filepath.Join(workDir, sessionID)
	if _, err := os.Stat(sessionDir); err != nil {
		t.Fatalf("session dir not created: %v", err)
	}

	// Verify subdirectories exist
	for _, subdir := range []string{"scratchpad", "research", "research/web_search_cache", "artifacts"} {
		subdirPath := filepath.Join(sessionDir, subdir)
		if _, err := os.Stat(subdirPath); err != nil {
			t.Errorf("subdir not created: %s", subdir)
		}
	}

	// Verify created_paths returned
	if createdPaths, ok := resp["created_paths"].([]any); !ok || len(createdPaths) == 0 {
		t.Error("created_paths should be non-empty array")
	}
}

// TestSessionStartNoSessionID verifies error when session ID is unknown.
func TestSessionStartNoSessionID(t *testing.T) {
	origWorkDir := workDir
	origSessionIDFile := sessionIDFile
	tmpDir := t.TempDir()
	workDir = tmpDir
	// Override sessionIDFile to a path that doesn't exist and won't get auto-detected
	sessionIDFile = filepath.Join(tmpDir, "nonexistent_dir", "session_id_file")
	defer func() {
		workDir = origWorkDir
		sessionIDFile = origSessionIDFile
	}()

	// Make sure CLAUDE_SESSION_ID env var is not set
	origEnv := os.Getenv("CLAUDE_SESSION_ID")
	os.Unsetenv("CLAUDE_SESSION_ID")
	defer os.Setenv("CLAUDE_SESSION_ID", origEnv)

	ctx := context.Background()
	result, err := handleSessionStart(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("handleSessionStart: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "no session ID") {
		t.Errorf("should contain error about no session ID: %s", text)
	}
}

// TestSessionEnd verifies that session end creates the .ended marker.
func TestSessionEnd(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

	ctx := context.Background()

	// Start session first
	_, err := handleSessionStart(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionStart: %v", err)
	}

	// End session
	result, err := handleSessionEnd(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionEnd: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if status, ok := resp["status"].(string); !ok || status != "ended" {
		t.Errorf("status: got %v, want ended", resp["status"])
	}

	// Verify .ended marker exists
	markerPath := filepath.Join(workDir, sessionID, ".ended")
	if _, err := os.Stat(markerPath); err != nil {
		t.Fatalf(".ended marker not created: %v", err)
	}

	// Verify content contains timestamp
	data, err := os.ReadFile(markerPath)
	if err != nil {
		t.Fatalf("read marker: %v", err)
	}
	if !strings.Contains(string(data), "ended_at:") {
		t.Error("marker should contain ended_at")
	}
}

// TestSessionEndNonexistent verifies error when session directory doesn't exist.
func TestSessionEndNonexistent(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "cccccccc-cccc-cccc-cccc-cccccccccccc"

	ctx := context.Background()
	result, err := handleSessionEnd(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionEnd: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "does not exist") {
		t.Errorf("should contain error about nonexistent dir: %s", text)
	}
}

// TestSessionStatus verifies that status returns correct information.
func TestSessionStatus(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "dddddddd-dddd-dddd-dddd-dddddddddddd"

	ctx := context.Background()

	// Start session
	_, err := handleSessionStart(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionStart: %v", err)
	}

	// Add some files to verify file count
	scraPath := filepath.Join(workDir, sessionID, "scratchpad", "test.txt")
	os.WriteFile(scraPath, []byte("test content"), 0644)

	// Get status
	result, err := handleSessionStatus(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionStatus: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if id, ok := resp["session_id"].(string); !ok || id != sessionID {
		t.Errorf("session_id: got %v, want %v", resp["session_id"], sessionID)
	}

	if _, ok := resp["path"].(string); !ok {
		t.Error("path should be string")
	}

	if ageDays, ok := resp["age_days"].(float64); !ok || ageDays > 1 {
		t.Errorf("age_days: got %v, want ~0", ageDays)
	}

	if fileCount, ok := resp["file_count"].(float64); !ok || fileCount < 1 {
		t.Errorf("file_count: got %v, want >= 1", fileCount)
	}

	if hasEnded, ok := resp["has_ended"].(bool); !ok || hasEnded {
		t.Errorf("has_ended: got %v, want false", hasEnded)
	}

	// Verify structure field
	if structure, ok := resp["structure"].(map[string]any); ok {
		if scratchpad, ok := structure["scratchpad"].(map[string]any); ok {
			if exists, ok := scratchpad["exists"].(bool); !ok || !exists {
				t.Error("scratchpad should exist")
			}
		} else {
			t.Error("scratchpad structure missing")
		}
	} else {
		t.Error("structure should be object")
	}
}

// TestSessionStatusNonexistent verifies error when session doesn't exist.
func TestSessionStatusNonexistent(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	sessionID := "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"

	ctx := context.Background()
	result, err := handleSessionStatus(ctx, makeRequest(map[string]any{
		"session_id": sessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionStatus: %v", err)
	}

	text := extractText(result)
	if !strings.Contains(text, "does not exist") {
		t.Errorf("should contain error about nonexistent dir: %s", text)
	}
}

// TestSessionList verifies listing multiple sessions, sorted by age.
func TestSessionList(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	ctx := context.Background()

	// Create three sessions
	sessionIDs := []string{
		"ffffffff-ffff-ffff-ffff-ffffffffffff",
		"10101010-1010-1010-1010-101010101010",
		"20202020-2020-2020-2020-202020202020",
	}

	for _, sid := range sessionIDs {
		_, err := handleSessionStart(ctx, makeRequest(map[string]any{
			"session_id": sid,
		}))
		if err != nil {
			t.Fatalf("handleSessionStart(%s): %v", sid, err)
		}
		// Add some time between sessions
		time.Sleep(10 * time.Millisecond)
	}

	// List sessions
	result, err := handleSessionList(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("handleSessionList: %v", err)
	}

	text := extractText(result)
	var sessions []map[string]any
	if err := json.Unmarshal([]byte(text), &sessions); err != nil {
		t.Fatalf("parse sessions: %v", err)
	}

	if len(sessions) < 3 {
		t.Errorf("session count: got %d, want >= 3", len(sessions))
	}

	// Verify fields in first session
	if len(sessions) > 0 {
		s := sessions[0]
		if _, ok := s["session_id"].(string); !ok {
			t.Error("session_id should be string")
		}
		if _, ok := s["age_days"].(float64); !ok {
			t.Error("age_days should be number")
		}
		if _, ok := s["size_human"].(string); !ok {
			t.Error("size_human should be string")
		}
		if _, ok := s["file_count"].(float64); !ok {
			t.Error("file_count should be number")
		}
		if _, ok := s["ended"].(bool); !ok {
			t.Error("ended should be boolean")
		}
	}

	// Verify sorting by age (newest first = lowest age_days)
	if len(sessions) >= 2 {
		age0 := sessions[0]["age_days"].(float64)
		age1 := sessions[1]["age_days"].(float64)
		if age0 > age1 {
			t.Error("sessions should be sorted by age ascending (newest first)")
		}
	}
}

// TestSessionListEmpty verifies empty list when no sessions exist.
func TestSessionListEmpty(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	ctx := context.Background()
	result, err := handleSessionList(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("handleSessionList: %v", err)
	}

	text := extractText(result)
	var sessions []map[string]any
	if err := json.Unmarshal([]byte(text), &sessions); err != nil {
		t.Fatalf("parse sessions: %v", err)
	}

	if len(sessions) != 0 {
		t.Errorf("session count: got %d, want 0", len(sessions))
	}
}

// TestSessionCleanup verifies removal of old sessions and preservation of recent ones.
func TestSessionCleanup(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	ctx := context.Background()

	// Create two sessions: one old, one recent
	oldSessionID := "30303030-3030-3030-3030-303030303030"
	newSessionID := "40404040-4040-4040-4040-404040404040"

	_, err := handleSessionStart(ctx, makeRequest(map[string]any{
		"session_id": oldSessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionStart(old): %v", err)
	}

	// Set old session time to 10 days ago
	oldDir := filepath.Join(workDir, oldSessionID)
	oldTime := time.Now().Add(-10 * 24 * time.Hour)
	os.Chtimes(oldDir, oldTime, oldTime)

	_, err = handleSessionStart(ctx, makeRequest(map[string]any{
		"session_id": newSessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionStart(new): %v", err)
	}

	// Cleanup sessions older than 7 days
	result, err := handleSessionCleanup(ctx, makeRequest(map[string]any{
		"days": "7",
	}))
	if err != nil {
		t.Fatalf("handleSessionCleanup: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if status, ok := resp["status"].(string); !ok || status != "success" {
		t.Errorf("status: got %v, want success", resp["status"])
	}

	// Verify summary
	if summary, ok := resp["summary"].(map[string]any); ok {
		if removed, ok := summary["removed"].(float64); !ok || removed < 1 {
			t.Errorf("removed: got %v, want >= 1", summary["removed"])
		}
		if kept, ok := summary["kept"].(float64); !ok || kept < 1 {
			t.Errorf("kept: got %v, want >= 1", summary["kept"])
		}
	}

	// Verify old dir was removed
	if _, err := os.Stat(oldDir); !os.IsNotExist(err) {
		t.Error("old session dir should be removed")
	}

	// Verify new dir still exists
	newDir := filepath.Join(workDir, newSessionID)
	if _, err := os.Stat(newDir); err != nil {
		t.Error("new session dir should still exist")
	}
}

// TestSessionCleanupDefaultDays verifies default cleanup is 7 days.
func TestSessionCleanupDefaultDays(t *testing.T) {
	origWorkDir := workDir
	tmpDir := t.TempDir()
	workDir = tmpDir
	defer func() { workDir = origWorkDir }()

	ctx := context.Background()

	// Create one session 8 days ago
	oldSessionID := "50505050-5050-5050-5050-505050505050"
	_, err := handleSessionStart(ctx, makeRequest(map[string]any{
		"session_id": oldSessionID,
	}))
	if err != nil {
		t.Fatalf("handleSessionStart: %v", err)
	}

	oldDir := filepath.Join(workDir, oldSessionID)
	oldTime := time.Now().Add(-8 * 24 * time.Hour)
	os.Chtimes(oldDir, oldTime, oldTime)

	// Cleanup with default (7 days) - should remove 8 day old session
	result, err := handleSessionCleanup(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("handleSessionCleanup: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse response: %v", err)
	}

	if summary, ok := resp["summary"].(map[string]any); ok {
		if removed, ok := summary["removed"].(float64); !ok || removed < 1 {
			t.Errorf("should have removed 8-day-old session with default cleanup, got removed=%v", summary["removed"])
		}
	}
}
