package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
)

// sessionSubdirs defines the standard subdirectories for each session.
var sessionSubdirs = []string{
	"scratchpad",
	"research",
	"research/web_search_cache",
	"artifacts",
}

func handleSessionStart(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := resolveSessionID(request)
	if sessionID == "unknown" {
		return errResult("no session ID provided or detected"), nil
	}

	sessionDir := filepath.Join(workDir, sessionID)
	var createdPaths []string

	// Create base work dir
	if err := os.MkdirAll(workDir, 0755); err != nil {
		return errResult(fmt.Sprintf("failed to create work directory: %v", err)), nil
	}

	// Create session dir
	if err := os.MkdirAll(sessionDir, 0755); err != nil {
		return errResult(fmt.Sprintf("failed to create session directory: %v", err)), nil
	}
	createdPaths = append(createdPaths, sessionDir)

	// Create subdirs
	for _, subdir := range sessionSubdirs {
		subdirPath := filepath.Join(sessionDir, subdir)
		if err := os.MkdirAll(subdirPath, 0755); err != nil {
			return errResult(fmt.Sprintf("failed to create subdirectory %s: %v", subdir, err)), nil
		}
		createdPaths = append(createdPaths, subdirPath)
	}

	return jsonResult(map[string]any{
		"status":        "success",
		"session_id":    sessionID,
		"path":          sessionDir,
		"created_paths": createdPaths,
	})
}

func handleSessionEnd(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := resolveSessionID(request)
	if sessionID == "unknown" {
		return errResult("no session ID provided or detected"), nil
	}

	sessionDir := filepath.Join(workDir, sessionID)
	if _, err := os.Stat(sessionDir); os.IsNotExist(err) {
		return errResult(fmt.Sprintf("session directory does not exist: %s", sessionDir)), nil
	}

	// Write .ended marker
	markerPath := filepath.Join(sessionDir, ".ended")
	content := fmt.Sprintf("ended_at: %s\n", time.Now().UTC().Format(time.RFC3339))
	if err := os.WriteFile(markerPath, []byte(content), 0644); err != nil {
		return errResult(fmt.Sprintf("failed to write .ended marker: %v", err)), nil
	}

	return jsonResult(map[string]any{
		"status":     "ended",
		"session_id": sessionID,
		"marker":     markerPath,
	})
}

func handleSessionStatus(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := resolveSessionID(request)
	if sessionID == "unknown" {
		return errResult("no session ID provided or detected"), nil
	}

	sessionDir := filepath.Join(workDir, sessionID)
	info, err := os.Stat(sessionDir)
	if err != nil {
		return errResult(fmt.Sprintf("session directory does not exist: %s", sessionDir)), nil
	}

	mtime := info.ModTime()
	ageDays := int(time.Since(mtime).Hours() / 24)

	// Build structure info
	structure := make(map[string]any)
	for _, subdir := range sessionSubdirs {
		subdirPath := filepath.Join(sessionDir, subdir)
		if _, err := os.Stat(subdirPath); err == nil {
			structure[subdir] = map[string]any{
				"exists":     true,
				"file_count": fileCount(subdirPath),
			}
		} else {
			structure[subdir] = map[string]any{
				"exists": false,
			}
		}
	}

	// Check for .ended marker
	_, endedErr := os.Stat(filepath.Join(sessionDir, ".ended"))
	hasEnded := endedErr == nil

	return jsonResult(map[string]any{
		"session_id": sessionID,
		"path":       sessionDir,
		"age_days":   ageDays,
		"size_human": formatSize(dirSize(sessionDir)),
		"file_count": fileCount(sessionDir),
		"structure":  structure,
		"has_ended":  hasEnded,
	})
}

func handleSessionList(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	entries, err := os.ReadDir(workDir)
	if err != nil {
		return jsonResult([]any{})
	}

	type sessionEntry struct {
		SessionID string `json:"session_id"`
		AgeDays   int    `json:"age_days"`
		SizeHuman string `json:"size_human"`
		FileCount int    `json:"file_count"`
		Ended     bool   `json:"ended"`
	}

	var sessions []sessionEntry

	for _, e := range entries {
		if !e.IsDir() || !isValidSessionID(e.Name()) {
			continue
		}

		sessionDir := filepath.Join(workDir, e.Name())
		info, err := e.Info()
		if err != nil {
			continue
		}

		mtime := info.ModTime()
		ageDays := int(time.Since(mtime).Hours() / 24)

		_, endedErr := os.Stat(filepath.Join(sessionDir, ".ended"))
		hasEnded := endedErr == nil

		sessions = append(sessions, sessionEntry{
			SessionID: e.Name(),
			AgeDays:   ageDays,
			SizeHuman: formatSize(dirSize(sessionDir)),
			FileCount: fileCount(sessionDir),
			Ended:     hasEnded,
		})
	}

	// Sort by age ascending (newest first)
	sort.Slice(sessions, func(i, j int) bool {
		return sessions[i].AgeDays < sessions[j].AgeDays
	})

	return jsonResult(sessions)
}

func handleSessionCleanup(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	days := optInt(request, "days", 7)
	cutoff := time.Now().Add(-time.Duration(days) * 24 * time.Hour)

	entries, err := os.ReadDir(workDir)
	if err != nil {
		return jsonResult(map[string]any{
			"status":  "success",
			"message": "Work directory does not exist or is empty",
			"summary": map[string]any{"removed": 0, "kept": 0, "errors": 0},
		})
	}

	removed := 0
	kept := 0
	errors := 0

	for _, e := range entries {
		if !e.IsDir() || !isValidSessionID(e.Name()) {
			continue
		}

		sessionDir := filepath.Join(workDir, e.Name())
		info, err := e.Info()
		if err != nil {
			errors++
			continue
		}

		if info.ModTime().Before(cutoff) {
			if err := os.RemoveAll(sessionDir); err != nil {
				errors++
			} else {
				removed++
			}
		} else {
			kept++
		}
	}

	return jsonResult(map[string]any{
		"status":      "success",
		"cutoff_days": days,
		"summary": map[string]any{
			"removed": removed,
			"kept":    kept,
			"errors":  errors,
		},
	})
}
