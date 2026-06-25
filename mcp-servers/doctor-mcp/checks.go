package main

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
)

// Issue represents a single diagnostic finding.
type Issue struct {
	Level   string // PASS, WARN, FAIL
	Message string
	Fix     string
}

// CheckResult holds the outcome of a single category check.
type CheckResult struct {
	Name     string
	Passed   int
	Failed   int
	Warnings int
	Issues   []Issue
	Details  map[string]any
}

// Status returns the overall status string for this check.
func (r *CheckResult) Status() string {
	if r.Failed > 0 {
		return "FAIL"
	}
	if r.Warnings > 0 {
		return "WARN"
	}
	return "OK"
}

// SummaryLine returns a brief text summary of pass/warn/fail counts.
func (r *CheckResult) SummaryLine() string {
	var parts []string
	if r.Passed > 0 {
		parts = append(parts, fmt.Sprintf("%d passed", r.Passed))
	}
	if r.Warnings > 0 {
		parts = append(parts, fmt.Sprintf("%d warnings", r.Warnings))
	}
	if r.Failed > 0 {
		parts = append(parts, fmt.Sprintf("%d failed", r.Failed))
	}
	if len(parts) == 0 {
		return "no checks"
	}
	return strings.Join(parts, ", ")
}

func (r *CheckResult) addPass(msg string) {
	r.Passed++
	if msg != "" {
		r.Issues = append(r.Issues, Issue{Level: "PASS", Message: msg})
	}
}

func (r *CheckResult) addFail(msg, fix string) {
	r.Failed++
	r.Issues = append(r.Issues, Issue{Level: "FAIL", Message: msg, Fix: fix})
}

func (r *CheckResult) addWarn(msg, fix string) {
	r.Warnings++
	r.Issues = append(r.Issues, Issue{Level: "WARN", Message: msg, Fix: fix})
}

// --- Paths ---

func homeDir() string {
	h, _ := os.UserHomeDir()
	return h
}

func claudeDir() string  { return filepath.Join(homeDir(), ".claude") }
func evalDir() string    { return filepath.Join(claudeDir(), "evaluation") }
func dataDir() string    { return filepath.Join(evalDir(), "data") }
func hooksDir() string   { return filepath.Join(claudeDir(), "hooks") }
func skillsDir() string  { return filepath.Join(claudeDir(), "skills") }
func toolsDir() string   { return filepath.Join(claudeDir(), "tools") }
func rulesDir() string   { return filepath.Join(claudeDir(), "rules") }
func modulesDir() string { return filepath.Join(claudeDir(), "modules") }

// --- Check runners ---

func runCheck(category string) CheckResult {
	switch category {
	case "hooks":
		return checkHooks()
	case "skills":
		return checkSkills()
	case "tools":
		return checkTools()
	case "mcp":
		return checkMCP()
	case "budget":
		return checkBudget()
	case "rules":
		return checkRules()
	case "modules":
		return checkModules()
	case "tests":
		return checkTests()
	case "logs":
		return checkLogs()
	case "anacron":
		return checkAnacron()
	default:
		r := CheckResult{Name: category, Details: map[string]any{}}
		r.addFail(fmt.Sprintf("unknown category: %s", category), "")
		return r
	}
}

func runAllChecks() []CheckResult {
	categories := []string{
		"hooks", "skills", "tools", "mcp", "budget",
		"rules", "modules", "tests", "logs", "anacron",
	}
	results := make([]CheckResult, 0, len(categories))
	for _, cat := range categories {
		results = append(results, runCheck(cat))
	}
	return results
}

// --- Utility ---

func checkPythonSyntax(path string) (bool, string) {
	cmd := exec.Command("python3", "-c", fmt.Sprintf("import ast; ast.parse(open(%q).read())", path))
	out, err := cmd.CombinedOutput()
	if err != nil {
		return false, strings.TrimSpace(string(out))
	}
	return true, ""
}

func listFiles(dir, pattern string) []string {
	matches, _ := filepath.Glob(filepath.Join(dir, pattern))
	sort.Strings(matches)
	return matches
}

func listDirs(dir string) []string {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}
	var dirs []string
	for _, e := range entries {
		if e.IsDir() {
			dirs = append(dirs, filepath.Join(dir, e.Name()))
		}
	}
	sort.Strings(dirs)
	return dirs
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func readJSON(path string, v any) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(data, v)
}

func dirSize(dir string) int64 {
	var total int64
	filepath.WalkDir(dir, func(_ string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}
		info, err := d.Info()
		if err != nil {
			return nil
		}
		total += info.Size()
		return nil
	})
	return total
}

// --- 10 Check Functions ---

func checkHooks() CheckResult {
	r := CheckResult{Name: "Hooks", Details: map[string]any{}}

	dir := hooksDir()
	if !fileExists(dir) {
		r.addFail("Hooks directory not found", fmt.Sprintf("mkdir -p %s", dir))
		return r
	}

	hookFiles := listFiles(dir, "*.py")
	// Exclude __init__.py
	filtered := hookFiles[:0]
	for _, f := range hookFiles {
		base := filepath.Base(f)
		if base != "__init__.py" && base != "__pycache__" {
			filtered = append(filtered, f)
		}
	}
	hookFiles = filtered
	r.Details["files_on_disk"] = len(hookFiles)

	// Check syntax
	for _, hf := range hookFiles {
		ok, errMsg := checkPythonSyntax(hf)
		if ok {
			r.addPass("")
		} else {
			r.addFail(fmt.Sprintf("Syntax error in %s: %s", filepath.Base(hf), errMsg), fmt.Sprintf("Fix syntax in %s", filepath.Base(hf)))
		}
	}

	// Check registrations in settings.json
	settingsPath := filepath.Join(claudeDir(), "settings.json")
	registered := map[string]bool{}
	if fileExists(settingsPath) {
		var settings map[string]any
		if err := readJSON(settingsPath, &settings); err == nil {
			if hooksConfig, ok := settings["hooks"].(map[string]any); ok {
				for _, matchers := range hooksConfig {
					if matcherList, ok := matchers.([]any); ok {
						for _, m := range matcherList {
							if matcher, ok := m.(map[string]any); ok {
								if hookList, ok := matcher["hooks"].([]any); ok {
									for _, h := range hookList {
										if hook, ok := h.(map[string]any); ok {
											cmd, _ := hook["command"].(string)
											for _, hf := range hookFiles {
												base := filepath.Base(hf)
												stem := strings.TrimSuffix(base, ".py")
												if strings.Contains(cmd, base) || strings.Contains(cmd, stem) {
													registered[base] = true
												}
											}
										}
									}
								}
							}
						}
					}
				}
			}
		} else {
			r.addFail("settings.json parse error", "Fix JSON syntax in settings.json")
		}
	}
	r.Details["registered"] = len(registered)

	// Check for orphaned hooks
	skipNames := map[string]bool{"__init__.py": true, "workflow_autoloader.py": true}
	var orphaned []string
	for _, hf := range hookFiles {
		base := filepath.Base(hf)
		if !registered[base] && !skipNames[base] {
			orphaned = append(orphaned, base)
		}
	}
	if len(orphaned) > 0 {
		shown := orphaned
		if len(shown) > 5 {
			shown = shown[:5]
		}
		r.addWarn(
			fmt.Sprintf("%d hook(s) on disk but not registered: %s", len(orphaned), strings.Join(shown, ", ")),
			"Register in settings.json or archive",
		)
	} else {
		r.addPass("All hooks registered")
	}

	return r
}

func checkSkills() CheckResult {
	r := CheckResult{Name: "Skills", Details: map[string]any{}}

	dir := skillsDir()
	if !fileExists(dir) {
		r.addFail("Skills directory not found", fmt.Sprintf("mkdir -p %s", dir))
		return r
	}

	skillDirs := listDirs(dir)
	r.Details["total"] = len(skillDirs)

	valid := 0
	for _, sd := range skillDirs {
		skillMD := filepath.Join(sd, "SKILL.md")
		if !fileExists(skillMD) {
			r.addFail(fmt.Sprintf("Missing SKILL.md in %s", filepath.Base(sd)), fmt.Sprintf("Create %s", skillMD))
			continue
		}

		data, err := os.ReadFile(skillMD)
		if err != nil {
			r.addWarn(fmt.Sprintf("Cannot read %s/SKILL.md", filepath.Base(sd)), "")
			continue
		}
		content := string(data)

		if strings.HasPrefix(content, "---") {
			parts := strings.SplitN(content, "---", 3)
			if len(parts) >= 3 {
				fm := parts[1]
				hasName := strings.Contains(fm, "name:")
				hasDesc := strings.Contains(fm, "description:")
				if hasName && hasDesc {
					valid++
					r.addPass("")
				} else {
					var missing []string
					if !hasName {
						missing = append(missing, "name")
					}
					if !hasDesc {
						missing = append(missing, "description")
					}
					r.addWarn(
						fmt.Sprintf("%s: missing frontmatter fields: %s", filepath.Base(sd), strings.Join(missing, ", ")),
						fmt.Sprintf("Add %s to %s", strings.Join(missing, ", "), skillMD),
					)
				}
			} else {
				r.addWarn(fmt.Sprintf("%s: malformed frontmatter", filepath.Base(sd)), fmt.Sprintf("Fix frontmatter in %s", skillMD))
			}
		} else {
			r.addWarn(fmt.Sprintf("%s: no frontmatter (missing ---)", filepath.Base(sd)), fmt.Sprintf("Add YAML frontmatter to %s", skillMD))
		}
	}

	r.Details["valid"] = valid
	return r
}

func checkTools() CheckResult {
	r := CheckResult{Name: "Tools", Details: map[string]any{}}

	dir := toolsDir()
	if !fileExists(dir) {
		r.addFail("Tools directory not found", fmt.Sprintf("mkdir -p %s", dir))
		return r
	}

	toolFiles := listFiles(dir, "*.py")
	// Exclude __init__.py
	filtered := toolFiles[:0]
	for _, f := range toolFiles {
		if filepath.Base(f) != "__init__.py" {
			filtered = append(filtered, f)
		}
	}
	toolFiles = filtered
	r.Details["total"] = len(toolFiles)

	syntaxOK := 0
	for _, tf := range toolFiles {
		ok, errMsg := checkPythonSyntax(tf)
		if ok {
			syntaxOK++
			r.addPass("")
		} else {
			r.addFail(fmt.Sprintf("Syntax error in %s: %s", filepath.Base(tf), errMsg), fmt.Sprintf("Fix %s", tf))
		}
	}
	r.Details["syntax_ok"] = syntaxOK

	return r
}

func checkMCP() CheckResult {
	r := CheckResult{Name: "MCP Servers", Details: map[string]any{}}

	// Check ~/.claude.json (LOCAL scope)
	mcpFile := filepath.Join(homeDir(), ".claude.json")
	if !fileExists(mcpFile) {
		// Fallback: project-level .mcp.json
		mcpFile = filepath.Join(claudeDir(), ".mcp.json")
	}
	if !fileExists(mcpFile) {
		mcpFile = "/opt/project/.mcp.json"
	}

	if !fileExists(mcpFile) {
		r.addWarn("No MCP config found", "Create MCP configuration")
		return r
	}

	data, err := os.ReadFile(mcpFile)
	if err != nil {
		r.addFail(fmt.Sprintf("Cannot read MCP config: %v", err), "")
		return r
	}

	var config map[string]any
	if err := json.Unmarshal(data, &config); err != nil {
		r.addFail("MCP config parse error", "Fix JSON syntax")
		return r
	}

	// Navigate to mcpServers — top-level, or per-project under projects.
	// Servers are injected per-project (into projects[cwd]), not under "*", so try
	// cwd FIRST (authoritative) and fall back to "*" only for legacy/manual configs.
	servers := map[string]any{}
	if s, ok := config["mcpServers"].(map[string]any); ok {
		servers = s
	} else if projects, ok := config["projects"].(map[string]any); ok {
		cwd, _ := os.Getwd()
		for _, key := range []string{cwd, "*"} {
			if key == "" {
				continue
			}
			if proj, ok := projects[key].(map[string]any); ok {
				if s, ok := proj["mcpServers"].(map[string]any); ok && len(s) > 0 {
					servers = s
					break
				}
			}
		}
	}

	r.Details["configured"] = len(servers)

	active := 0
	for name, cfg := range servers {
		if cfgMap, ok := cfg.(map[string]any); ok {
			cmd, _ := cfgMap["command"].(string)
			if cmd != "" {
				active++
				r.addPass("")
			} else {
				r.addWarn(fmt.Sprintf("MCP server '%s': no command defined", name), "")
			}
		}
	}
	r.Details["active"] = active

	return r
}

func checkBudget() CheckResult {
	r := CheckResult{Name: "Budget System", Details: map[string]any{}}

	configPath := filepath.Join(dataDir(), "budget_config.json")
	if fileExists(configPath) {
		var config map[string]any
		if err := readJSON(configPath, &config); err == nil {
			required := map[string]bool{"session": true, "daily": true, "monthly": true}
			present := 0
			var missing []string
			for k := range required {
				if _, ok := config[k]; ok {
					present++
				} else {
					missing = append(missing, k)
				}
			}
			if present == len(required) {
				r.addPass("Config valid")
			} else {
				r.addWarn(fmt.Sprintf("Budget config missing sections: %s", strings.Join(missing, ", ")), "")
			}
			r.Details["config"] = "valid"
		} else {
			r.addFail("budget_config.json parse error -- risk of lockout!", "Fix JSON manually")
			r.Details["config"] = "invalid"
		}
	} else {
		r.addWarn("No budget_config.json found", "")
		r.Details["config"] = "missing"
	}

	// Check spending log
	spendingLog := filepath.Join(dataDir(), "budget_spending.jsonl")
	if fileExists(spendingLog) {
		info, err := os.Stat(spendingLog)
		if err == nil {
			sizeKB := float64(info.Size()) / 1024
			r.Details["spending_log_kb"] = fmt.Sprintf("%.1f", sizeKB)
			if sizeKB > 10240 { // >10MB
				r.addWarn(fmt.Sprintf("Spending log large: %.1f MB", sizeKB/1024), "Run log rotation")
			} else {
				r.addPass(fmt.Sprintf("Spending log: %.0f KB", sizeKB))
			}
		}
	} else {
		r.addWarn("No spending log found", "")
	}

	// Check budget manager syntax
	budgetMgr := filepath.Join(evalDir(), "costs", "budget_manager.py")
	if fileExists(budgetMgr) {
		ok, errMsg := checkPythonSyntax(budgetMgr)
		if ok {
			r.addPass("Budget manager syntax OK")
		} else {
			r.addFail(fmt.Sprintf("Budget manager syntax error: %s", errMsg), "")
		}
	} else {
		r.addWarn("budget_manager.py not found", "")
	}

	return r
}

func checkRules() CheckResult {
	r := CheckResult{Name: "Rules", Details: map[string]any{}}

	dir := rulesDir()
	if !fileExists(dir) {
		r.addFail("Rules directory not found", fmt.Sprintf("mkdir -p %s", dir))
		return r
	}

	ruleFiles := listFiles(dir, "*.md")
	r.Details["total"] = len(ruleFiles)

	expected := map[string]bool{
		"anti-hallucination.md":    true,
		"authorization-levels.md":  true,
		"code-before-write.md":     true,
		"mandatory-checks.md":      true,
		"mcp-rules.md":             true,
		"task-execution.md":        true,
		"working-directories.md":   true,
	}

	present := map[string]bool{}
	for _, f := range ruleFiles {
		present[filepath.Base(f)] = true
	}

	var missing []string
	for e := range expected {
		if !present[e] {
			missing = append(missing, e)
		}
	}
	sort.Strings(missing)

	if len(missing) > 0 {
		for _, m := range missing {
			r.addFail(fmt.Sprintf("Missing rule: %s", m), "")
		}
	} else {
		r.addPass(fmt.Sprintf("All %d expected rules present", len(expected)))
	}

	// Count extra rules
	extra := 0
	for _, f := range ruleFiles {
		if !expected[filepath.Base(f)] {
			extra++
		}
	}
	if extra > 0 {
		r.addPass(fmt.Sprintf("+%d additional rules", extra))
	}

	return r
}

func checkModules() CheckResult {
	r := CheckResult{Name: "Modules", Details: map[string]any{}}

	dir := modulesDir()
	if !fileExists(dir) {
		r.addFail("Modules directory not found", fmt.Sprintf("mkdir -p %s", dir))
		return r
	}

	moduleFiles := listFiles(dir, "*.md")
	r.Details["total"] = len(moduleFiles)

	if len(moduleFiles) >= 20 {
		r.addPass(fmt.Sprintf("%d modules present", len(moduleFiles)))
	} else if len(moduleFiles) >= 10 {
		r.addWarn(fmt.Sprintf("Only %d modules (expected 20+)", len(moduleFiles)), "")
	} else {
		r.addFail(fmt.Sprintf("Only %d modules (expected 20+)", len(moduleFiles)), "")
	}

	return r
}

func checkTests() CheckResult {
	r := CheckResult{Name: "Tests", Details: map[string]any{}}

	testDir := filepath.Join(evalDir(), "tests")
	if !fileExists(testDir) {
		r.addWarn("No test directory found", "")
		return r
	}

	testFiles := listFiles(testDir, "test_*.py")
	r.Details["test_files"] = len(testFiles)

	syntaxOK := 0
	for _, tf := range testFiles {
		ok, errMsg := checkPythonSyntax(tf)
		if ok {
			syntaxOK++
		} else {
			r.addWarn(fmt.Sprintf("Test file syntax error: %s: %s", filepath.Base(tf), errMsg), "")
		}
	}

	r.Details["syntax_ok"] = syntaxOK
	if syntaxOK == len(testFiles) {
		r.addPass(fmt.Sprintf("All %d test files have valid syntax", len(testFiles)))
	} else {
		r.addWarn(fmt.Sprintf("%d/%d test files have valid syntax", syntaxOK, len(testFiles)), "")
	}

	return r
}

func checkLogs() CheckResult {
	r := CheckResult{Name: "Logs & Data", Details: map[string]any{}}

	var totalSize int64

	// Check evaluation data
	dd := dataDir()
	if fileExists(dd) {
		totalSize += dirSize(dd)
	}

	// Check logs directory
	logsDir := filepath.Join(claudeDir(), "logs")
	if fileExists(logsDir) {
		totalSize += dirSize(logsDir)
	}

	totalMB := float64(totalSize) / (1024 * 1024)
	r.Details["total_mb"] = fmt.Sprintf("%.1f", totalMB)

	if totalSize < 100*1024*1024 { // <100MB
		r.addPass(fmt.Sprintf("Total data: %.1f MB", totalMB))
	} else if totalSize < 500*1024*1024 {
		r.addWarn(fmt.Sprintf("Data growing: %.1f MB", totalMB), "Consider log rotation")
	} else {
		r.addFail(fmt.Sprintf("Data too large: %.1f MB", totalMB), "Run data_cleanup.py")
	}

	// Check for large individual files
	checkLargeFiles := func(dir string) {
		entries, err := os.ReadDir(dir)
		if err != nil {
			return
		}
		for _, e := range entries {
			if e.IsDir() {
				continue
			}
			info, err := e.Info()
			if err != nil {
				continue
			}
			if info.Size() > 10*1024*1024 { // >10MB
				sizeMB := float64(info.Size()) / (1024 * 1024)
				r.addWarn(fmt.Sprintf("Large file: %s (%.1f MB)", e.Name(), sizeMB), "Rotate or archive")
			}
		}
	}

	if fileExists(dd) {
		checkLargeFiles(dd)
	}
	logsDir2 := filepath.Join(claudeDir(), "logs")
	if fileExists(logsDir2) {
		checkLargeFiles(logsDir2)
	}

	return r
}

func checkAnacron() CheckResult {
	r := CheckResult{Name: "Anacron Jobs", Details: map[string]any{}}

	anacronTab := filepath.Join(homeDir(), ".anacron", "anacrontab")
	if !fileExists(anacronTab) {
		r.addWarn("No anacrontab found", fmt.Sprintf("Create %s", anacronTab))
		return r
	}

	data, err := os.ReadFile(anacronTab)
	if err != nil {
		r.addFail(fmt.Sprintf("Cannot read anacrontab: %v", err), "")
		return r
	}

	lines := strings.Split(string(data), "\n")
	var jobs int
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line != "" && !strings.HasPrefix(line, "#") {
			jobs++
		}
	}
	r.Details["jobs"] = jobs

	if jobs > 0 {
		r.addPass(fmt.Sprintf("%d jobs configured", jobs))
	} else {
		r.addWarn("No anacron jobs configured", "")
	}

	// Check spool directory
	spoolDir := filepath.Join(homeDir(), ".anacron", "spool")
	if fileExists(spoolDir) {
		r.addPass("Spool directory exists")
	} else {
		r.addWarn("Spool directory missing", fmt.Sprintf("mkdir -p %s", spoolDir))
	}

	return r
}
