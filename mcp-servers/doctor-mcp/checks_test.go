package main

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

// TestCheckHooksWithFixture sets up a temp hooks dir and verifies check logic.
func TestCheckHooksWithFixture(t *testing.T) {
	dir := t.TempDir()

	// Override paths for testing
	origHome := os.Getenv("HOME")
	t.Setenv("HOME", dir)
	defer os.Setenv("HOME", origHome)

	// Create .claude/hooks dir with test files
	hooksDir := filepath.Join(dir, ".claude", "hooks")
	if err := os.MkdirAll(hooksDir, 0o755); err != nil {
		t.Fatal(err)
	}

	// Create a valid Python hook
	if err := os.WriteFile(filepath.Join(hooksDir, "test_hook.py"), []byte("print('ok')\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Create settings.json with hook registration
	settingsDir := filepath.Join(dir, ".claude")
	settings := `{
		"hooks": {
			"UserPromptSubmit": [{
				"matcher": "",
				"hooks": [{"type": "command", "command": "python3 test_hook.py"}]
			}]
		}
	}`
	if err := os.WriteFile(filepath.Join(settingsDir, "settings.json"), []byte(settings), 0o644); err != nil {
		t.Fatal(err)
	}

	result := checkHooks()
	if result.Name != "Hooks" {
		t.Errorf("name: got %q, want Hooks", result.Name)
	}
	if result.Failed > 0 {
		t.Errorf("unexpected failures: %d, issues: %v", result.Failed, result.Issues)
	}
	filesOnDisk, ok := result.Details["files_on_disk"].(int)
	if !ok || filesOnDisk != 1 {
		t.Errorf("files_on_disk: got %v, want 1", result.Details["files_on_disk"])
	}
}

// TestCheckSkillsWithFixture creates temp skill dirs and checks validation.
func TestCheckSkillsWithFixture(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	skillsBase := filepath.Join(dir, ".claude", "skills")

	// Create a valid skill
	validDir := filepath.Join(skillsBase, "test-skill")
	if err := os.MkdirAll(validDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(validDir, "SKILL.md"), []byte("---\nname: test\ndescription: A test skill\n---\nBody\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Create a skill missing SKILL.md
	missingDir := filepath.Join(skillsBase, "bad-skill")
	if err := os.MkdirAll(missingDir, 0o755); err != nil {
		t.Fatal(err)
	}

	result := checkSkills()
	if result.Name != "Skills" {
		t.Errorf("name: got %q, want Skills", result.Name)
	}
	total, _ := result.Details["total"].(int)
	if total != 2 {
		t.Errorf("total: got %d, want 2", total)
	}
	valid, _ := result.Details["valid"].(int)
	if valid != 1 {
		t.Errorf("valid: got %d, want 1", valid)
	}
	if result.Failed != 1 {
		t.Errorf("failed: got %d, want 1", result.Failed)
	}
}

// TestCheckToolsWithFixture creates temp tool files.
func TestCheckToolsWithFixture(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	toolsBase := filepath.Join(dir, ".claude", "tools")
	if err := os.MkdirAll(toolsBase, 0o755); err != nil {
		t.Fatal(err)
	}

	// Valid Python file
	if err := os.WriteFile(filepath.Join(toolsBase, "helper.py"), []byte("x = 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Invalid Python file
	if err := os.WriteFile(filepath.Join(toolsBase, "broken.py"), []byte("def f(\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	result := checkTools()
	if result.Name != "Tools" {
		t.Errorf("name: got %q, want Tools", result.Name)
	}
	total, _ := result.Details["total"].(int)
	if total != 2 {
		t.Errorf("total: got %d, want 2", total)
	}
	syntaxOK, _ := result.Details["syntax_ok"].(int)
	if syntaxOK != 1 {
		t.Errorf("syntax_ok: got %d, want 1", syntaxOK)
	}
	if result.Failed != 1 {
		t.Errorf("failed: got %d, want 1 (broken.py)", result.Failed)
	}
}

// TestCheckRulesWithFixture creates temp rule files.
func TestCheckRulesWithFixture(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	rulesBase := filepath.Join(dir, ".claude", "rules")
	if err := os.MkdirAll(rulesBase, 0o755); err != nil {
		t.Fatal(err)
	}

	expected := []string{
		"anti-hallucination.md", "authorization-levels.md", "code-before-write.md",
		"mandatory-checks.md", "mcp-rules.md", "task-execution.md", "working-directories.md",
	}
	for _, name := range expected {
		if err := os.WriteFile(filepath.Join(rulesBase, name), []byte("# rule\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	// Add an extra rule
	if err := os.WriteFile(filepath.Join(rulesBase, "custom.md"), []byte("# custom\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	result := checkRules()
	if result.Status() != "OK" {
		t.Errorf("status: got %q, want OK; issues: %v", result.Status(), result.Issues)
	}
	total, _ := result.Details["total"].(int)
	if total != 8 {
		t.Errorf("total: got %d, want 8", total)
	}
}

// TestCheckModulesWithFixture creates temp module files.
func TestCheckModulesWithFixture(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	modulesBase := filepath.Join(dir, ".claude", "modules")
	if err := os.MkdirAll(modulesBase, 0o755); err != nil {
		t.Fatal(err)
	}

	// Create 15 modules (less than 20 — should warn)
	for i := 0; i < 15; i++ {
		name := filepath.Join(modulesBase, fmt.Sprintf("%02d-mod-%d.md", i, i))
		if err := os.WriteFile(name, []byte("# mod\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}

	result := checkModules()
	if result.Status() != "WARN" {
		t.Errorf("status: got %q, want WARN", result.Status())
	}
	total, _ := result.Details["total"].(int)
	if total != 15 {
		t.Errorf("total: got %d, want 15", total)
	}
}

// TestCheckBudgetMissing tests budget check when nothing exists.
func TestCheckBudgetMissing(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	result := checkBudget()
	if result.Name != "Budget System" {
		t.Errorf("name: got %q", result.Name)
	}
	// Should have warnings for missing config and log
	if result.Warnings < 2 {
		t.Errorf("warnings: got %d, want >= 2", result.Warnings)
	}
}

// TestCheckAnacronMissing tests anacron check when no anacrontab.
func TestCheckAnacronMissing(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	result := checkAnacron()
	if result.Name != "Anacron Jobs" {
		t.Errorf("name: got %q", result.Name)
	}
	if result.Warnings < 1 {
		t.Errorf("warnings: got %d, want >= 1", result.Warnings)
	}
}

// TestCheckAnacronPresent tests with a valid anacrontab.
func TestCheckAnacronPresent(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	anacronDir := filepath.Join(dir, ".anacron")
	if err := os.MkdirAll(filepath.Join(anacronDir, "spool"), 0o755); err != nil {
		t.Fatal(err)
	}
	content := "# anacrontab\n1 5 daily-job /usr/bin/true\n7 10 weekly-job /usr/bin/true\n"
	if err := os.WriteFile(filepath.Join(anacronDir, "anacrontab"), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}

	result := checkAnacron()
	jobs, _ := result.Details["jobs"].(int)
	if jobs != 2 {
		t.Errorf("jobs: got %d, want 2", jobs)
	}
	if result.Status() != "OK" {
		t.Errorf("status: got %q, want OK", result.Status())
	}
}

// TestCheckLogsTiny tests logs check with minimal data.
func TestCheckLogsTiny(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	dataBase := filepath.Join(dir, ".claude", "evaluation", "data")
	if err := os.MkdirAll(dataBase, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dataBase, "small.json"), []byte("{}"), 0o644); err != nil {
		t.Fatal(err)
	}

	result := checkLogs()
	if result.Status() != "OK" {
		t.Errorf("status: got %q, want OK", result.Status())
	}
}

// TestRunAllChecksCount verifies that runAllChecks produces 10 results.
func TestRunAllChecksCount(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("HOME", dir)

	results := runAllChecks()
	if len(results) != 10 {
		t.Errorf("runAllChecks: got %d results, want 10", len(results))
	}
}

// TestCheckResultStatus tests Status() logic.
func TestCheckResultStatus(t *testing.T) {
	r := CheckResult{Name: "test", Details: map[string]any{}}
	if r.Status() != "OK" {
		t.Errorf("empty result: got %q, want OK", r.Status())
	}

	r.addWarn("w", "")
	if r.Status() != "WARN" {
		t.Errorf("with warning: got %q, want WARN", r.Status())
	}

	r.addFail("f", "")
	if r.Status() != "FAIL" {
		t.Errorf("with fail: got %q, want FAIL", r.Status())
	}
}

// TestSummaryLine tests the SummaryLine formatting.
func TestSummaryLine(t *testing.T) {
	r := CheckResult{Name: "test", Details: map[string]any{}}
	if r.SummaryLine() != "no checks" {
		t.Errorf("empty: got %q", r.SummaryLine())
	}

	r.addPass("")
	r.addPass("")
	r.addWarn("w", "")
	if got := r.SummaryLine(); got != "2 passed, 1 warnings" {
		t.Errorf("got %q", got)
	}
}
