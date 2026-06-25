package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

var claudeDir = filepath.Join(os.Getenv("HOME"), ".claude")

type fileEntry struct {
	path  string
	mtime time.Time
}

// CleanupResult holds results for a single cleanup target.
type CleanupResult struct {
	Target  string `json:"target"`
	Cleaned int    `json:"cleaned"`
	Details string `json:"details,omitempty"`
}

// GCResults holds the full garbage collection report.
type GCResults struct {
	DryRun  bool            `json:"dry_run"`
	Results []CleanupResult `json:"results"`
	Total   int             `json:"total_cleaned"`
}

// StatusResult holds counts for gc_status.
type StatusResult struct {
	Target string `json:"target"`
	Stale  int    `json:"stale"`
}

func runAllCleanups(cwd string, dryRun bool) *GCResults {
	gr := &GCResults{DryRun: dryRun}

	gr.addResult(cleanTasks(dryRun))
	gr.addResult(cleanTeams(dryRun))
	gr.addResult(cleanSpendingArchive(dryRun))
	gr.addResult(cleanSpendingTracker(dryRun))
	gr.addResult(cleanBacklog(cwd, dryRun))
	gr.addResult(cleanPlans(dryRun))
	gr.addResult(cleanSessionEnv(dryRun))
	gr.addResult(cleanPythonCaches(dryRun))
	gr.addResult(cleanSecurityLog(dryRun))
	gr.addResult(cleanDebugFiles(dryRun))
	gr.addResult(cleanEmptyDirs(dryRun))
	gr.addResult(cleanGzArchives(dryRun))
	gr.addResult(cleanLogs(dryRun))
	gr.addResult(cleanTempFiles(cwd, dryRun))
	gr.addResult(cleanMcpProfiles(dryRun))
	gr.addResult(cleanEmptyJsonl(dryRun))

	return gr
}

func runQuickCleanups(cwd string, dryRun bool) *GCResults {
	gr := &GCResults{DryRun: dryRun}

	gr.addResult(cleanTasks(dryRun))
	gr.addResult(cleanTeams(dryRun))
	gr.addResult(cleanSessionEnv(dryRun))
	gr.addResult(cleanPythonCaches(dryRun))
	gr.addResult(cleanDebugFiles(dryRun))

	return gr
}

func (gr *GCResults) addResult(r CleanupResult) {
	gr.Results = append(gr.Results, r)
	gr.Total += r.Cleaned
}

func getStatus(cwd string) map[string]any {
	targets := []StatusResult{
		{Target: "tasks", Stale: countStaleDirs(filepath.Join(claudeDir, "tasks"), 24*time.Hour)},
		{Target: "teams", Stale: countStaleDirs(filepath.Join(claudeDir, "teams"), 24*time.Hour)},
		{Target: "spending_archive", Stale: countExcessFiles(filepath.Join(claudeDir, "evaluation", "data", "spending_archive"), "spending_*.jsonl", 30)},
		{Target: "spending_tracker", Stale: countExcessLines(filepath.Join(claudeDir, "evaluation", "data", "spending_tracker.jsonl"), 500)},
		{Target: "backlog", Stale: countCompletedInActive(filepath.Join(cwd, "BACKLOG.md"))},
		{Target: "plans", Stale: countStaleFiles(filepath.Join(claudeDir, "plans"), "*.md", 7*24*time.Hour)},
		{Target: "session_env", Stale: countStaleDirs(filepath.Join(claudeDir, "session-env"), 3*24*time.Hour)},
		{Target: "python_caches", Stale: countPythonCaches()},
		{Target: "security_log", Stale: countOversizedLog(filepath.Join(claudeDir, "security_audit.log"), 5*1024*1024)},
		{Target: "debug_files", Stale: countStaleDebugFiles(48 * time.Hour)},
		{Target: "empty_dirs", Stale: countEmptyDirs()},
		{Target: "gz_archives", Stale: countGzArchives()},
		{Target: "logs", Stale: countStaleLogs(30 * 24 * time.Hour)},
		{Target: "temp_files", Stale: countTempFiles(cwd)},
		{Target: "mcp_profiles", Stale: countStaleMcpProfiles()},
		{Target: "empty_jsonl", Stale: countEmptyJsonl()},
	}

	total := 0
	for _, t := range targets {
		total += t.Stale
	}

	return map[string]any{
		"targets":     targets,
		"total_stale": total,
	}
}

// --- Target 1: tasks ---

func cleanTasks(dryRun bool) CleanupResult {
	return cleanStaleDirs(filepath.Join(claudeDir, "tasks"), 24*time.Hour, dryRun, "tasks")
}

// --- Target 2: teams ---

func cleanTeams(dryRun bool) CleanupResult {
	return cleanStaleDirs(filepath.Join(claudeDir, "teams"), 24*time.Hour, dryRun, "teams")
}

// --- Target 3: spending_archive ---

func cleanSpendingArchive(dryRun bool) CleanupResult {
	dir := filepath.Join(claudeDir, "evaluation", "data", "spending_archive")
	pattern := "spending_*.jsonl"
	maxFiles := 30
	target := "spending_archive"

	matches, err := filepath.Glob(filepath.Join(dir, pattern))
	if err != nil || len(matches) <= maxFiles {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	// Sort by mtime (oldest first)
	entries := make([]fileEntry, 0, len(matches))
	for _, m := range matches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		entries = append(entries, fileEntry{path: m, mtime: info.ModTime()})
	}
	sortFileEntries(entries)

	toRemove := len(entries) - maxFiles
	if toRemove <= 0 {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	removed := 0
	for i := 0; i < toRemove; i++ {
		if !dryRun {
			if err := os.Remove(entries[i].path); err != nil {
				continue
			}
		}
		removed++
	}

	return CleanupResult{Target: target, Cleaned: removed}
}

// sortFileEntries sorts by mtime ascending (oldest first) using insertion sort.
func sortFileEntries(entries []fileEntry) {
	for i := 1; i < len(entries); i++ {
		key := entries[i]
		j := i - 1
		for j >= 0 && entries[j].mtime.After(key.mtime) {
			entries[j+1] = entries[j]
			j--
		}
		entries[j+1] = key
	}
}

// --- Target 4: spending_tracker ---

func cleanSpendingTracker(dryRun bool) CleanupResult {
	tracker := filepath.Join(claudeDir, "evaluation", "data", "spending_tracker.jsonl")
	maxEntries := 500
	target := "spending_tracker"

	data, err := os.ReadFile(tracker)
	if err != nil {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) <= maxEntries {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	trimmed := len(lines) - maxEntries
	if !dryRun {
		kept := lines[len(lines)-maxEntries:]
		if err := os.WriteFile(tracker, []byte(strings.Join(kept, "\n")+"\n"), 0o644); err != nil {
			return CleanupResult{Target: target, Cleaned: 0}
		}
	}

	return CleanupResult{Target: target, Cleaned: trimmed, Details: "lines trimmed"}
}

// --- Target 5: backlog ---

func cleanBacklog(cwd string, dryRun bool) CleanupResult {
	backlogPath := filepath.Join(cwd, "BACKLOG.md")
	result := rotateBacklog(backlogPath, dryRun)
	total := result.Moved + result.Pruned
	details := ""
	if result.Moved > 0 || result.Pruned > 0 {
		details = strings.TrimSpace(
			strings.Join([]string{
				func() string {
					if result.Moved > 0 {
						return fmt.Sprintf("%d moved to archive", result.Moved)
					}
					return ""
				}(),
				func() string {
					if result.Pruned > 0 {
						return fmt.Sprintf("%d pruned from archive", result.Pruned)
					}
					return ""
				}(),
			}, ", "),
		)
		// Clean leading comma
		details = strings.TrimPrefix(details, ", ")
	}
	return CleanupResult{Target: "backlog", Cleaned: total, Details: details}
}

// --- Target 6: plans ---

func cleanPlans(dryRun bool) CleanupResult {
	return cleanStaleFilesByAge(filepath.Join(claudeDir, "plans"), "*.md", 7*24*time.Hour, dryRun, "plans")
}

// --- Target 7: session_env ---

func cleanSessionEnv(dryRun bool) CleanupResult {
	return cleanStaleDirs(filepath.Join(claudeDir, "session-env"), 3*24*time.Hour, dryRun, "session_env")
}

// --- Target 8: python_caches ---

func cleanPythonCaches(dryRun bool) CleanupResult {
	target := "python_caches"
	removed := 0

	for _, pattern := range []string{"__pycache__", ".pytest_cache"} {
		removed += removeDirsRecursive(claudeDir, pattern, dryRun)
	}

	return CleanupResult{Target: target, Cleaned: removed}
}

func removeDirsRecursive(root, name string, dryRun bool) int {
	removed := 0
	filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if info.IsDir() && info.Name() == name {
			if !dryRun {
				os.RemoveAll(path)
			}
			removed++
			return filepath.SkipDir
		}
		return nil
	})
	return removed
}

// --- Target 9: security_log ---

func cleanSecurityLog(dryRun bool) CleanupResult {
	logFile := filepath.Join(claudeDir, "security_audit.log")
	target := "security_log"
	maxSize := int64(5 * 1024 * 1024) // 5MB
	maxLines := 1000

	info, err := os.Stat(logFile)
	if err != nil || info.Size() <= maxSize {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	data, err := os.ReadFile(logFile)
	if err != nil {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	lines := strings.Split(string(data), "\n")
	if len(lines) <= maxLines {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	if !dryRun {
		kept := lines[len(lines)-maxLines:]
		os.WriteFile(logFile, []byte(strings.Join(kept, "\n")), 0o644)
	}

	return CleanupResult{Target: target, Cleaned: 1, Details: "rotated"}
}

// --- Target 10: debug_files ---

func cleanDebugFiles(dryRun bool) CleanupResult {
	target := "debug_files"
	cutoff := time.Now().Add(-48 * time.Hour)
	removed := 0

	// Debug logs in ~/.claude/
	for _, pattern := range []string{"*_debug.log", "*_debug.txt"} {
		matches, _ := filepath.Glob(filepath.Join(claudeDir, pattern))
		for _, m := range matches {
			info, err := os.Stat(m)
			if err != nil {
				continue
			}
			if info.ModTime().Before(cutoff) {
				if !dryRun {
					os.Remove(m)
				}
				removed++
			}
		}
	}

	// Debug/session txt files in evaluation/data/
	evalData := filepath.Join(claudeDir, "evaluation", "data")
	matches, _ := filepath.Glob(filepath.Join(evalData, "*.txt"))
	for _, m := range matches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			if !dryRun {
				os.Remove(m)
			}
			removed++
		}
	}

	return CleanupResult{Target: target, Cleaned: removed}
}

// --- Target 11: empty_dirs (agent-memory, commands) ---

func cleanEmptyDirs(dryRun bool) CleanupResult {
	target := "empty_dirs"
	removed := 0

	dirs := []string{
		filepath.Join(claudeDir, "agent-memory"),
		filepath.Join(claudeDir, "commands"),
	}

	for _, dir := range dirs {
		removed += removeEmptyDirsRecursive(dir, dryRun)
	}

	return CleanupResult{Target: target, Cleaned: removed}
}

func removeEmptyDirsRecursive(root string, dryRun bool) int {
	removed := 0
	// Walk bottom-up: collect all dirs, then check emptiness in reverse
	var allDirs []string
	filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if info.IsDir() {
			allDirs = append(allDirs, path)
		}
		return nil
	})

	// Process deepest dirs first (reverse order ensures bottom-up)
	for i := len(allDirs) - 1; i >= 0; i-- {
		dir := allDirs[i]
		entries, err := os.ReadDir(dir)
		if err != nil {
			continue
		}
		if len(entries) == 0 {
			if !dryRun {
				os.Remove(dir)
			}
			removed++
		}
	}
	return removed
}

// --- Target 12: gz archives ---

func cleanGzArchives(dryRun bool) CleanupResult {
	target := "gz_archives"
	removed := 0
	evalData := filepath.Join(claudeDir, "evaluation", "data")

	// Collect all .gz and date-stamped backup files
	var entries []fileEntry
	for _, pattern := range []string{"*.gz", "*-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"} {
		matches, _ := filepath.Glob(filepath.Join(evalData, pattern))
		for _, m := range matches {
			info, err := os.Stat(m)
			if err != nil {
				continue
			}
			entries = append(entries, fileEntry{path: m, mtime: info.ModTime()})
		}
	}

	// Also check tool_chains/ for date-stamped copies
	toolChains := filepath.Join(evalData, "tool_chains")
	matches, _ := filepath.Glob(filepath.Join(toolChains, "*-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"))
	for _, m := range matches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		entries = append(entries, fileEntry{path: m, mtime: info.ModTime()})
	}

	maxFiles := 10
	if len(entries) <= maxFiles {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	sortFileEntries(entries)
	toRemove := len(entries) - maxFiles
	for i := 0; i < toRemove; i++ {
		if !dryRun {
			if err := os.Remove(entries[i].path); err != nil {
				continue
			}
		}
		removed++
	}

	return CleanupResult{Target: target, Cleaned: removed}
}

// --- Target 13: logs ---

func cleanLogs(dryRun bool) CleanupResult {
	target := "logs"
	logsDir := filepath.Join(claudeDir, "logs")
	cutoff := time.Now().Add(-30 * 24 * time.Hour) // 30 days
	removed := 0

	matches, err := filepath.Glob(filepath.Join(logsDir, "*.log"))
	if err != nil {
		return CleanupResult{Target: target, Cleaned: 0}
	}
	// Also include .md logs
	mdMatches, _ := filepath.Glob(filepath.Join(logsDir, "*.md"))
	matches = append(matches, mdMatches...)

	for _, m := range matches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			if !dryRun {
				os.Remove(m)
			}
			removed++
		}
	}

	return CleanupResult{Target: target, Cleaned: removed}
}

// --- Target 14: temp files ---

func cleanTempFiles(cwd string, dryRun bool) CleanupResult {
	target := "temp_files"
	removed := 0

	// /tmp/claude-* dirs older than 24h
	cutoff24h := time.Now().Add(-24 * time.Hour)
	matches, _ := filepath.Glob("/tmp/claude-*")
	for _, m := range matches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		if info.IsDir() && info.ModTime().Before(cutoff24h) {
			if !dryRun {
				os.RemoveAll(m)
			}
			removed++
		}
	}

	// .claude-init-attempted files older than 2h
	cutoff2h := time.Now().Add(-2 * time.Hour)
	initFile := filepath.Join(cwd, ".claude-init-attempted")
	if info, err := os.Stat(initFile); err == nil && info.ModTime().Before(cutoff2h) {
		if !dryRun {
			os.Remove(initFile)
		}
		removed++
	}

	// upgrade-log-*.md files older than 30d
	cutoff30d := time.Now().Add(-30 * 24 * time.Hour)
	upgradeMatches, _ := filepath.Glob(filepath.Join(cwd, "upgrade-log-*.md"))
	for _, m := range upgradeMatches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff30d) {
			if !dryRun {
				os.Remove(m)
			}
			removed++
		}
	}

	return CleanupResult{Target: target, Cleaned: removed}
}

func countTempFiles(cwd string) int {
	count := 0
	cutoff24h := time.Now().Add(-24 * time.Hour)
	matches, _ := filepath.Glob("/tmp/claude-*")
	for _, m := range matches {
		info, err := os.Stat(m)
		if err == nil && info.IsDir() && info.ModTime().Before(cutoff24h) {
			count++
		}
	}
	cutoff2h := time.Now().Add(-2 * time.Hour)
	if info, err := os.Stat(filepath.Join(cwd, ".claude-init-attempted")); err == nil && info.ModTime().Before(cutoff2h) {
		count++
	}
	cutoff30d := time.Now().Add(-30 * 24 * time.Hour)
	upgradeMatches, _ := filepath.Glob(filepath.Join(cwd, "upgrade-log-*.md"))
	for _, m := range upgradeMatches {
		info, err := os.Stat(m)
		if err == nil && info.ModTime().Before(cutoff30d) {
			count++
		}
	}
	return count
}

func countEmptyDirs() int {
	count := 0
	dirs := []string{
		filepath.Join(claudeDir, "agent-memory"),
		filepath.Join(claudeDir, "commands"),
	}
	for _, dir := range dirs {
		filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil
			}
			if info.IsDir() {
				entries, err := os.ReadDir(path)
				if err == nil && len(entries) == 0 {
					count++
				}
			}
			return nil
		})
	}
	return count
}

// --- Shared helpers ---

func cleanStaleDirs(dir string, maxAge time.Duration, dryRun bool, target string) CleanupResult {
	cutoff := time.Now().Add(-maxAge)
	removed := 0

	entries, err := os.ReadDir(dir)
	if err != nil {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		info, err := e.Info()
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			if !dryRun {
				os.RemoveAll(filepath.Join(dir, e.Name()))
			}
			removed++
		}
	}

	return CleanupResult{Target: target, Cleaned: removed}
}

func cleanStaleFilesByAge(dir, pattern string, maxAge time.Duration, dryRun bool, target string) CleanupResult {
	cutoff := time.Now().Add(-maxAge)
	removed := 0

	matches, err := filepath.Glob(filepath.Join(dir, pattern))
	if err != nil {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	for _, m := range matches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			if !dryRun {
				os.Remove(m)
			}
			removed++
		}
	}

	return CleanupResult{Target: target, Cleaned: removed}
}

// --- Status counting helpers ---

func countStaleDirs(dir string, maxAge time.Duration) int {
	cutoff := time.Now().Add(-maxAge)
	count := 0
	entries, err := os.ReadDir(dir)
	if err != nil {
		return 0
	}
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		info, err := e.Info()
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			count++
		}
	}
	return count
}

func countExcessFiles(dir, pattern string, max int) int {
	matches, err := filepath.Glob(filepath.Join(dir, pattern))
	if err != nil {
		return 0
	}
	excess := len(matches) - max
	if excess < 0 {
		return 0
	}
	return excess
}

func countExcessLines(filePath string, max int) int {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return 0
	}
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	excess := len(lines) - max
	if excess < 0 {
		return 0
	}
	return excess
}

func countCompletedInActive(backlogPath string) int {
	f, err := os.Open(backlogPath)
	if err != nil {
		return 0
	}
	defer f.Close()

	count := 0
	inActive := false
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := scanner.Text()
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
			count++
		}
	}
	return count
}

func countStaleFiles(dir, pattern string, maxAge time.Duration) int {
	cutoff := time.Now().Add(-maxAge)
	count := 0
	matches, _ := filepath.Glob(filepath.Join(dir, pattern))
	for _, m := range matches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			count++
		}
	}
	return count
}

func countPythonCaches() int {
	count := 0
	for _, pattern := range []string{"__pycache__", ".pytest_cache"} {
		filepath.Walk(claudeDir, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return nil
			}
			if info.IsDir() && info.Name() == pattern {
				count++
				return filepath.SkipDir
			}
			return nil
		})
	}
	return count
}

func countGzArchives() int {
	evalData := filepath.Join(claudeDir, "evaluation", "data")
	count := 0

	for _, pattern := range []string{"*.gz", "*-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"} {
		matches, _ := filepath.Glob(filepath.Join(evalData, pattern))
		count += len(matches)
	}

	toolChains := filepath.Join(evalData, "tool_chains")
	matches, _ := filepath.Glob(filepath.Join(toolChains, "*-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"))
	count += len(matches)

	excess := count - 10
	if excess < 0 {
		return 0
	}
	return excess
}

func countStaleLogs(maxAge time.Duration) int {
	logsDir := filepath.Join(claudeDir, "logs")
	cutoff := time.Now().Add(-maxAge)
	count := 0

	for _, pattern := range []string{"*.log", "*.md"} {
		matches, _ := filepath.Glob(filepath.Join(logsDir, pattern))
		for _, m := range matches {
			info, err := os.Stat(m)
			if err != nil {
				continue
			}
			if info.ModTime().Before(cutoff) {
				count++
			}
		}
	}
	return count
}

func countOversizedLog(path string, maxBytes int64) int {
	info, err := os.Stat(path)
	if err != nil {
		return 0
	}
	if info.Size() > maxBytes {
		return 1
	}
	return 0
}

func countStaleDebugFiles(maxAge time.Duration) int {
	cutoff := time.Now().Add(-maxAge)
	count := 0

	for _, pattern := range []string{"*_debug.log", "*_debug.txt"} {
		matches, _ := filepath.Glob(filepath.Join(claudeDir, pattern))
		for _, m := range matches {
			info, err := os.Stat(m)
			if err != nil {
				continue
			}
			if info.ModTime().Before(cutoff) {
				count++
			}
		}
	}

	evalData := filepath.Join(claudeDir, "evaluation", "data")
	matches, _ := filepath.Glob(filepath.Join(evalData, "*.txt"))
	for _, m := range matches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		if info.ModTime().Before(cutoff) {
			count++
		}
	}

	return count
}

// --- Target 15: mcp_profiles ---
// Cleans stale non-essential MCP server entries from ~/.claude.json.
// Removes servers with _loaded_at older than 2h (except essential profile).

var essentialServerNames = map[string]bool{
	"github": true, "fetch": true, "filesystem": true, "memory": true,
	"git": true, "sequential-thinking": true, "sqlite": true,
	"backlog-mcp": true, "profile-mcp": true, "doctor-mcp": true,
	"gc-mcp": true, "score-mcp": true, "tools-mcp": true,
}

func cleanMcpProfiles(dryRun bool) CleanupResult {
	target := "mcp_profiles"
	configPath := filepath.Join(os.Getenv("HOME"), ".claude.json")

	f, err := os.OpenFile(configPath, os.O_RDWR, 0o644)
	if err != nil {
		return CleanupResult{Target: target, Cleaned: 0}
	}
	defer f.Close()

	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX); err != nil {
		return CleanupResult{Target: target, Cleaned: 0}
	}
	defer syscall.Flock(int(f.Fd()), syscall.LOCK_UN)

	data, err := os.ReadFile(configPath)
	if err != nil {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	projects, ok := raw["projects"].(map[string]any)
	if !ok {
		return CleanupResult{Target: target, Cleaned: 0}
	}

	cutoff := time.Now().UTC().Add(-2 * time.Hour)
	totalRemoved := 0

	for _, projVal := range projects {
		proj, ok := projVal.(map[string]any)
		if !ok {
			continue
		}
		servers, ok := proj["mcpServers"].(map[string]any)
		if !ok {
			continue
		}

		var toRemove []string
		for name, srvVal := range servers {
			if essentialServerNames[name] {
				continue
			}
			srv, ok := srvVal.(map[string]any)
			if !ok {
				continue
			}
			loadedAt, ok := srv["_loaded_at"].(string)
			if !ok {
				// No metadata — stale legacy entry, remove
				toRemove = append(toRemove, name)
				continue
			}
			t, err := time.Parse(time.RFC3339, loadedAt)
			if err != nil {
				toRemove = append(toRemove, name)
				continue
			}
			if t.Before(cutoff) {
				toRemove = append(toRemove, name)
			}
		}

		if !dryRun {
			for _, name := range toRemove {
				delete(servers, name)
			}
		}
		totalRemoved += len(toRemove)
	}

	if !dryRun && totalRemoved > 0 {
		newData, err := json.MarshalIndent(raw, "", "  ")
		if err != nil {
			return CleanupResult{Target: target, Cleaned: 0}
		}
		if err := f.Truncate(0); err != nil {
			return CleanupResult{Target: target, Cleaned: 0}
		}
		if _, err := f.Seek(0, 0); err != nil {
			return CleanupResult{Target: target, Cleaned: 0}
		}
		f.Write(newData)
	}

	return CleanupResult{Target: target, Cleaned: totalRemoved}
}

func countStaleMcpProfiles() int {
	configPath := filepath.Join(os.Getenv("HOME"), ".claude.json")
	data, err := os.ReadFile(configPath)
	if err != nil {
		return 0
	}

	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return 0
	}

	projects, ok := raw["projects"].(map[string]any)
	if !ok {
		return 0
	}

	cutoff := time.Now().UTC().Add(-2 * time.Hour)
	count := 0

	for _, projVal := range projects {
		proj, ok := projVal.(map[string]any)
		if !ok {
			continue
		}
		servers, ok := proj["mcpServers"].(map[string]any)
		if !ok {
			continue
		}
		for name, srvVal := range servers {
			if essentialServerNames[name] {
				continue
			}
			srv, ok := srvVal.(map[string]any)
			if !ok {
				continue
			}
			loadedAt, ok := srv["_loaded_at"].(string)
			if !ok {
				count++
				continue
			}
			t, err := time.Parse(time.RFC3339, loadedAt)
			if err != nil {
				count++
				continue
			}
			if t.Before(cutoff) {
				count++
			}
		}
	}
	return count
}

// --- Target 16: empty_jsonl ---
// Removes zero-byte .jsonl files from evaluation/data/ and its subdirectories.
// Excludes spending_tracker.jsonl (active log file, may be legitimately empty at session start).

var protectedJsonl = map[string]bool{
	"spending_tracker.jsonl": true,
}

func cleanEmptyJsonl(dryRun bool) CleanupResult {
	target := "empty_jsonl"
	evalDataDir := filepath.Join(claudeDir, "evaluation", "data")
	removed := 0

	filepath.WalkDir(evalDataDir, func(path string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}
		if filepath.Ext(path) != ".jsonl" {
			return nil
		}
		if protectedJsonl[filepath.Base(path)] {
			return nil
		}
		info, err := d.Info()
		if err != nil || info.Size() != 0 {
			return nil
		}
		if !dryRun {
			os.Remove(path)
		}
		removed++
		return nil
	})

	return CleanupResult{Target: target, Cleaned: removed}
}

func countEmptyJsonl() int {
	evalDataDir := filepath.Join(claudeDir, "evaluation", "data")
	count := 0

	filepath.WalkDir(evalDataDir, func(path string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return nil
		}
		if filepath.Ext(path) != ".jsonl" {
			return nil
		}
		if protectedJsonl[filepath.Base(path)] {
			return nil
		}
		info, err := d.Info()
		if err == nil && info.Size() == 0 {
			count++
		}
		return nil
	})
	return count
}
