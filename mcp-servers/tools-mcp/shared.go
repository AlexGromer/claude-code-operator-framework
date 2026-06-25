package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
)

var (
	sessionIDFile  = filepath.Join(os.Getenv("HOME"), ".claude", "evaluation", "data", "current_session_id")
	sessionIDRegex = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)
	workDir        = "/opt/agent_work_directory"
)

// resolveSessionID gets the current session ID from file, env, or request param.
//
// LEGACY (ADR-007): kept for session_start/end/list/cleanup operations that
// manage UUID-keyed session directories created historically. New per-session
// state (criteria, scope) MUST use resolveClaudeKey to avoid the global
// current_session_id leak between parallel Claude Code windows.
func resolveSessionID(request mcp.CallToolRequest) string {
	// Check explicit param first
	if v := optStr(request, "session_id"); v != "" && isValidSessionID(v) {
		return v
	}

	// Check file
	if data, err := os.ReadFile(sessionIDFile); err == nil {
		id := strings.TrimSpace(string(data))
		if isValidSessionID(id) {
			return id
		}
	}

	// Check env
	if id := strings.TrimSpace(os.Getenv("CLAUDE_SESSION_ID")); isValidSessionID(id) {
		return id
	}

	return "unknown"
}

// isValidSessionID checks if a string matches UUID format.
func isValidSessionID(id string) bool {
	return sessionIDRegex.MatchString(id)
}

// claudeKeyRegex matches keys produced by resolveClaudeKey: "claude-<PID>-<STARTTIME>".
var claudeKeyRegex = regexp.MustCompile(`^claude-\d+-\d+$`)

// isValidSessionKey accepts both legacy UUID and ADR-007 PPID-based keys.
// Use this for directory listings that may contain either format.
func isValidSessionKey(id string) bool {
	return sessionIDRegex.MatchString(id) || claudeKeyRegex.MatchString(id)
}

// resolveClaudeKey returns a stable per-session storage key derived from the
// parent (Claude Code) process. Format: "claude-<PPID>-<STARTTIME>" where
// STARTTIME is field 22 of /proc/<PPID>/stat (clock ticks since boot) — this
// defeats PID reuse across reboots and within-boot rollover.
//
// Properties:
//   - Same value for every child of the same Claude Code process: this MCP
//     server, UserPromptSubmit hook, Task() subagents, TeamCreate teammates.
//   - Different across separate Claude Code windows (different PPIDs).
//   - No dependency on env, no shared file, no SessionStart hook coordination.
//
// session_id parameter override is honored (mostly for tests / explicit override).
//
// See: ADR-007 + /opt/project/poc/adr-007-ppid-isolation/.
func resolveClaudeKey(request mcp.CallToolRequest) string {
	if v := optStr(request, "session_id"); v != "" {
		return v
	}
	ppid := os.Getppid()
	return fmt.Sprintf("claude-%d-%s", ppid, readStartTime(ppid))
}

// readStartTime reads field 22 of /proc/<pid>/stat (process start time in
// clock ticks since boot). Returns "0" on any error — still deterministic,
// just less unique (only collides with the same caller's previous incarnation,
// not with arbitrary other sessions).
//
// Linux-only. For macOS/Windows portability, replace with gopsutil's
// process.Process.CreateTime() — out of scope for ADR-007 v1.
func readStartTime(pid int) string {
	data, err := os.ReadFile(fmt.Sprintf("/proc/%d/stat", pid))
	if err != nil {
		return "0"
	}
	// /proc/<pid>/stat format: pid (comm) state ppid ... starttime(field 22 ...)
	// comm may itself contain spaces — locate the LAST ')' to safely split.
	s := string(data)
	rparen := strings.LastIndex(s, ")")
	if rparen < 0 || rparen+2 > len(s) {
		return "0"
	}
	rest := strings.Fields(s[rparen+2:])
	// after rparen-space: state ppid pgrp session tty_nr tpgid flags
	// minflt cminflt majflt cmajflt utime stime cutime cstime
	// priority nice num_threads itrealvalue starttime(idx 19)
	if len(rest) < 20 {
		return "0"
	}
	return rest[19]
}

// optStr extracts an optional string parameter from request arguments.
func optStr(request mcp.CallToolRequest, key string) string {
	args := request.GetArguments()
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

// reqStr extracts a required string parameter, returning error if missing.
func reqStr(request mcp.CallToolRequest, key string) (string, error) {
	v := optStr(request, key)
	if v == "" {
		return "", fmt.Errorf("required parameter missing: %s", key)
	}
	return v, nil
}

// optInt extracts an optional int parameter with a default value.
func optInt(request mcp.CallToolRequest, key string, defaultVal int) int {
	s := optStr(request, key)
	if s == "" {
		return defaultVal
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return defaultVal
	}
	return n
}

// jsonResult marshals a value to indented JSON and returns it as a tool result.
func jsonResult(v any) (*mcp.CallToolResult, error) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("json: %v", err)), nil
	}
	return mcp.NewToolResultText(string(data)), nil
}

// errResult returns a tool error result.
func errResult(msg string) *mcp.CallToolResult {
	return mcp.NewToolResultError(msg)
}

// formatSize formats bytes as human-readable B/KB/MB/GB.
func formatSize(bytes int64) string {
	const (
		kb = 1024
		mb = kb * 1024
		gb = mb * 1024
	)
	switch {
	case bytes >= gb:
		return fmt.Sprintf("%.1fGB", float64(bytes)/float64(gb))
	case bytes >= mb:
		return fmt.Sprintf("%.1fMB", float64(bytes)/float64(mb))
	case bytes >= kb:
		return fmt.Sprintf("%.1fKB", float64(bytes)/float64(kb))
	default:
		return fmt.Sprintf("%dB", bytes)
	}
}

// atomicWriteJSON writes JSON data to a file atomically via tmp+rename.
//
// Uses os.CreateTemp so each concurrent call gets a unique temp file name,
// preventing two sessions from clobbering each other's in-flight write.
// The rename(2) syscall is atomic on the same filesystem (Linux ext4/tmpfs).
func atomicWriteJSON(path string, v any) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("mkdir: %w", err)
	}

	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal: %w", err)
	}
	data = append(data, '\n')

	// CreateTemp gives a unique name (e.g. claude_scope_XYZ.json.tmp123456)
	// so two concurrent writers for the same path don't share a tmp file.
	tmp, err := os.CreateTemp(dir, filepath.Base(path)+".tmp*")
	if err != nil {
		return fmt.Errorf("create tmp: %w", err)
	}
	tmpPath := tmp.Name()

	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		os.Remove(tmpPath)
		return fmt.Errorf("write tmp: %w", err)
	}
	if err := tmp.Close(); err != nil {
		os.Remove(tmpPath)
		return fmt.Errorf("close tmp: %w", err)
	}

	if err := os.Rename(tmpPath, path); err != nil {
		os.Remove(tmpPath)
		return fmt.Errorf("rename: %w", err)
	}

	return nil
}

// parseTimestamp parses an ISO8601 timestamp string to time.Time.
func parseTimestamp(s string) (time.Time, error) {
	// Handle Z suffix
	s = strings.Replace(s, "Z", "+00:00", 1)

	// Try standard formats
	formats := []string{
		time.RFC3339,
		"2006-01-02T15:04:05-07:00",
		"2006-01-02T15:04:05",
		"2006-01-02 15:04:05",
		"2006-01-02",
	}

	for _, fmt := range formats {
		if t, err := time.Parse(fmt, s); err == nil {
			if t.Location() == time.UTC || t.Location() == nil {
				return t.UTC(), nil
			}
			return t.UTC(), nil
		}
	}

	return time.Time{}, fmt.Errorf("cannot parse timestamp: %s", s)
}

// dirSize returns the total size of all files in a directory recursively.
func dirSize(path string) int64 {
	var total int64
	filepath.Walk(path, func(_ string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if !info.IsDir() {
			total += info.Size()
		}
		return nil
	})
	return total
}

// fileCount returns the total number of files in a directory recursively.
func fileCount(path string) int {
	count := 0
	filepath.Walk(path, func(_ string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if !info.IsDir() {
			count++
		}
		return nil
	})
	return count
}
