package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestCleanTasks(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	tasksDir := filepath.Join(tmpHome, "tasks")
	os.MkdirAll(tasksDir, 0o755)

	// Create old dir (>24h)
	oldDir := filepath.Join(tasksDir, "old-session")
	os.MkdirAll(oldDir, 0o755)
	oldTime := time.Now().Add(-48 * time.Hour)
	os.Chtimes(oldDir, oldTime, oldTime)

	// Create recent dir (<24h)
	newDir := filepath.Join(tasksDir, "new-session")
	os.MkdirAll(newDir, 0o755)

	result := cleanTasks(false)
	if result.Cleaned != 1 {
		t.Errorf("cleaned: got %d, want 1", result.Cleaned)
	}
	if result.Target != "tasks" {
		t.Errorf("target: got %q, want tasks", result.Target)
	}

	// Old should be gone, new should remain
	if _, err := os.Stat(oldDir); !os.IsNotExist(err) {
		t.Error("old dir should be removed")
	}
	if _, err := os.Stat(newDir); err != nil {
		t.Error("new dir should remain")
	}
}

func TestCleanTasksDryRun(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	tasksDir := filepath.Join(tmpHome, "tasks")
	os.MkdirAll(tasksDir, 0o755)

	oldDir := filepath.Join(tasksDir, "old-session")
	os.MkdirAll(oldDir, 0o755)
	oldTime := time.Now().Add(-48 * time.Hour)
	os.Chtimes(oldDir, oldTime, oldTime)

	result := cleanTasks(true)
	if result.Cleaned != 1 {
		t.Errorf("dry run cleaned: got %d, want 1", result.Cleaned)
	}

	// Should still exist in dry run
	if _, err := os.Stat(oldDir); err != nil {
		t.Error("dir should still exist in dry run")
	}
}

func TestCleanTeams(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	teamsDir := filepath.Join(tmpHome, "teams")
	os.MkdirAll(teamsDir, 0o755)

	oldDir := filepath.Join(teamsDir, "team-abc")
	os.MkdirAll(oldDir, 0o755)
	oldTime := time.Now().Add(-48 * time.Hour)
	os.Chtimes(oldDir, oldTime, oldTime)

	newDir := filepath.Join(teamsDir, "team-xyz")
	os.MkdirAll(newDir, 0o755)

	result := cleanTeams(false)
	if result.Cleaned != 1 {
		t.Errorf("cleaned: got %d, want 1", result.Cleaned)
	}

	if _, err := os.Stat(oldDir); !os.IsNotExist(err) {
		t.Error("old dir should be removed")
	}
	if _, err := os.Stat(newDir); err != nil {
		t.Error("new dir should remain")
	}
}

func TestCleanSpendingArchive(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	archiveDir := filepath.Join(tmpHome, "evaluation", "data", "spending_archive")
	os.MkdirAll(archiveDir, 0o755)

	// Create 35 files (exceeds max 30)
	for i := 0; i < 35; i++ {
		name := filepath.Join(archiveDir, strings.Replace(
			"spending_2026-02-XX.jsonl", "XX",
			strings.Replace(string(rune('A'+i)), "", "", 0),
			1,
		))
		// Use unique names
		name = filepath.Join(archiveDir, "spending_"+string(rune('A'+i))+".jsonl")
		os.WriteFile(name, []byte("{}"), 0o644)
		// Stagger mtimes so sort is deterministic
		mtime := time.Now().Add(-time.Duration(35-i) * time.Hour)
		os.Chtimes(name, mtime, mtime)
	}

	result := cleanSpendingArchive(false)
	if result.Cleaned != 5 {
		t.Errorf("cleaned: got %d, want 5", result.Cleaned)
	}

	// Should have 30 files remaining
	remaining, _ := filepath.Glob(filepath.Join(archiveDir, "spending_*.jsonl"))
	if len(remaining) != 30 {
		t.Errorf("remaining: got %d, want 30", len(remaining))
	}
}

func TestCleanSpendingTracker(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	trackerDir := filepath.Join(tmpHome, "evaluation", "data")
	os.MkdirAll(trackerDir, 0o755)
	trackerFile := filepath.Join(trackerDir, "spending_tracker.jsonl")

	// Create 600 lines (exceeds 500)
	var lines []string
	for i := 0; i < 600; i++ {
		lines = append(lines, "{}")
	}
	os.WriteFile(trackerFile, []byte(strings.Join(lines, "\n")+"\n"), 0o644)

	result := cleanSpendingTracker(false)
	if result.Cleaned != 100 {
		t.Errorf("cleaned: got %d, want 100", result.Cleaned)
	}

	// Verify 500 lines remain
	data, _ := os.ReadFile(trackerFile)
	remaining := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(remaining) != 500 {
		t.Errorf("remaining lines: got %d, want 500", len(remaining))
	}
}

func TestCleanPlans(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	plansDir := filepath.Join(tmpHome, "plans")
	os.MkdirAll(plansDir, 0o755)

	// Old plan (>7d)
	oldPlan := filepath.Join(plansDir, "old-plan.md")
	os.WriteFile(oldPlan, []byte("# old"), 0o644)
	oldTime := time.Now().Add(-10 * 24 * time.Hour)
	os.Chtimes(oldPlan, oldTime, oldTime)

	// Recent plan (<7d)
	newPlan := filepath.Join(plansDir, "new-plan.md")
	os.WriteFile(newPlan, []byte("# new"), 0o644)

	result := cleanPlans(false)
	if result.Cleaned != 1 {
		t.Errorf("cleaned: got %d, want 1", result.Cleaned)
	}

	if _, err := os.Stat(oldPlan); !os.IsNotExist(err) {
		t.Error("old plan should be removed")
	}
	if _, err := os.Stat(newPlan); err != nil {
		t.Error("new plan should remain")
	}
}

func TestCleanSessionEnv(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	sessionDir := filepath.Join(tmpHome, "session-env")
	os.MkdirAll(sessionDir, 0o755)

	oldDir := filepath.Join(sessionDir, "sess-old")
	os.MkdirAll(oldDir, 0o755)
	oldTime := time.Now().Add(-5 * 24 * time.Hour)
	os.Chtimes(oldDir, oldTime, oldTime)

	newDir := filepath.Join(sessionDir, "sess-new")
	os.MkdirAll(newDir, 0o755)

	result := cleanSessionEnv(false)
	if result.Cleaned != 1 {
		t.Errorf("cleaned: got %d, want 1", result.Cleaned)
	}

	if _, err := os.Stat(oldDir); !os.IsNotExist(err) {
		t.Error("old session dir should be removed")
	}
	if _, err := os.Stat(newDir); err != nil {
		t.Error("new session dir should remain")
	}
}

func TestCleanPythonCaches(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	// Create nested __pycache__ and .pytest_cache
	cache1 := filepath.Join(tmpHome, "hooks", "__pycache__")
	os.MkdirAll(cache1, 0o755)
	os.WriteFile(filepath.Join(cache1, "test.pyc"), []byte(""), 0o644)

	cache2 := filepath.Join(tmpHome, "tools", ".pytest_cache")
	os.MkdirAll(cache2, 0o755)

	cache3 := filepath.Join(tmpHome, "hooks", "sub", "__pycache__")
	os.MkdirAll(cache3, 0o755)

	result := cleanPythonCaches(false)
	if result.Cleaned != 3 {
		t.Errorf("cleaned: got %d, want 3", result.Cleaned)
	}

	if _, err := os.Stat(cache1); !os.IsNotExist(err) {
		t.Error("__pycache__ should be removed")
	}
	if _, err := os.Stat(cache2); !os.IsNotExist(err) {
		t.Error(".pytest_cache should be removed")
	}
}

func TestCleanSecurityLog(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	logFile := filepath.Join(tmpHome, "security_audit.log")

	// Create a >5MB log file
	var lines []string
	line := strings.Repeat("A", 1000)
	for i := 0; i < 6000; i++ {
		lines = append(lines, line)
	}
	os.WriteFile(logFile, []byte(strings.Join(lines, "\n")), 0o644)

	info, _ := os.Stat(logFile)
	if info.Size() < 5*1024*1024 {
		t.Skipf("file too small: %d bytes", info.Size())
	}

	result := cleanSecurityLog(false)
	if result.Cleaned != 1 {
		t.Errorf("cleaned: got %d, want 1", result.Cleaned)
	}

	// Verify trimmed to ~1000 lines
	data, _ := os.ReadFile(logFile)
	remaining := strings.Split(strings.TrimRight(string(data), "\n"), "\n")
	if len(remaining) != 1000 {
		t.Errorf("remaining lines: got %d, want 1000", len(remaining))
	}
}

func TestCleanDebugFiles(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	// Old debug file
	oldFile := filepath.Join(tmpHome, "test_debug.log")
	os.WriteFile(oldFile, []byte("debug"), 0o644)
	oldTime := time.Now().Add(-72 * time.Hour)
	os.Chtimes(oldFile, oldTime, oldTime)

	// Recent debug file
	newFile := filepath.Join(tmpHome, "recent_debug.txt")
	os.WriteFile(newFile, []byte("debug"), 0o644)

	// Old txt in evaluation/data/
	evalDir := filepath.Join(tmpHome, "evaluation", "data")
	os.MkdirAll(evalDir, 0o755)
	oldEval := filepath.Join(evalDir, "session.txt")
	os.WriteFile(oldEval, []byte("old"), 0o644)
	os.Chtimes(oldEval, oldTime, oldTime)

	result := cleanDebugFiles(false)
	if result.Cleaned != 2 {
		t.Errorf("cleaned: got %d, want 2", result.Cleaned)
	}

	if _, err := os.Stat(oldFile); !os.IsNotExist(err) {
		t.Error("old debug file should be removed")
	}
	if _, err := os.Stat(newFile); err != nil {
		t.Error("recent debug file should remain")
	}
	if _, err := os.Stat(oldEval); !os.IsNotExist(err) {
		t.Error("old eval txt should be removed")
	}
}

func TestRunAllCleanups(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	// Create some stale artifacts
	tasksDir := filepath.Join(tmpHome, "tasks")
	os.MkdirAll(tasksDir, 0o755)
	old := filepath.Join(tasksDir, "stale")
	os.MkdirAll(old, 0o755)
	oldTime := time.Now().Add(-48 * time.Hour)
	os.Chtimes(old, oldTime, oldTime)

	results := runAllCleanups(t.TempDir(), false)
	if results == nil {
		t.Fatal("results should not be nil")
	}
	if len(results.Results) != 16 {
		t.Errorf("result count: got %d, want 16", len(results.Results))
	}

	// At least tasks should be cleaned
	if results.Results[0].Target != "tasks" {
		t.Errorf("first target: got %q, want tasks", results.Results[0].Target)
	}
	if results.Results[0].Cleaned != 1 {
		t.Errorf("tasks cleaned: got %d, want 1", results.Results[0].Cleaned)
	}
}

func TestRunAllCleanupsDryRun(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	tasksDir := filepath.Join(tmpHome, "tasks")
	os.MkdirAll(tasksDir, 0o755)
	old := filepath.Join(tasksDir, "stale")
	os.MkdirAll(old, 0o755)
	oldTime := time.Now().Add(-48 * time.Hour)
	os.Chtimes(old, oldTime, oldTime)

	results := runAllCleanups(t.TempDir(), true)
	if !results.DryRun {
		t.Error("should be dry run")
	}
	if results.Results[0].Cleaned != 1 {
		t.Errorf("dry run should count: got %d", results.Results[0].Cleaned)
	}

	// Dir should still exist
	if _, err := os.Stat(old); err != nil {
		t.Error("dir should still exist in dry run")
	}
}

func TestGetStatus(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	status := getStatus(t.TempDir())
	targets, ok := status["targets"].([]StatusResult)
	if !ok {
		t.Fatal("targets should be []StatusResult")
	}
	if len(targets) != 16 {
		t.Errorf("target count: got %d, want 16", len(targets))
	}
}

func TestCleanNonexistentDir(t *testing.T) {
	origDir := claudeDir
	tmpHome := t.TempDir()
	claudeDir = tmpHome
	defer func() { claudeDir = origDir }()

	// All should return 0 when dirs don't exist
	r := cleanTasks(false)
	if r.Cleaned != 0 {
		t.Errorf("tasks: got %d, want 0", r.Cleaned)
	}
	r = cleanTeams(false)
	if r.Cleaned != 0 {
		t.Errorf("teams: got %d, want 0", r.Cleaned)
	}
	r = cleanPlans(false)
	if r.Cleaned != 0 {
		t.Errorf("plans: got %d, want 0", r.Cleaned)
	}
	r = cleanSessionEnv(false)
	if r.Cleaned != 0 {
		t.Errorf("session_env: got %d, want 0", r.Cleaned)
	}
}
