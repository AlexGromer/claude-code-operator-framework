package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
)

// FreezeData holds frozen acceptance criteria for a task.
type FreezeData struct {
	FrozenAt       string   `json:"frozen_at"`
	ExpiresAt      string   `json:"expires_at"`
	SessionID      string   `json:"session_id"`
	Goal           string   `json:"goal"`
	ExpectedResult string   `json:"expected_result"`
	Criteria       []string `json:"acceptance_criteria"`
	IsFrozen       bool     `json:"is_frozen"`
}

const freezeTTLHours = 24

// freezeFilePath returns the path to the frozen criteria file for a session.
func freezeFilePath(sessionID string) string {
	return filepath.Join(workDir, sessionID, "scratchpad", "frozen_criteria.json")
}

func handleCriteriaFreeze(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	goal, err := reqStr(request, "goal")
	if err != nil {
		return errResult(err.Error()), nil
	}

	result, err := reqStr(request, "result")
	if err != nil {
		return errResult(err.Error()), nil
	}

	criteriaStr, err := reqStr(request, "criteria")
	if err != nil {
		return errResult(err.Error()), nil
	}

	// Parse comma-separated criteria
	var criteria []string
	for _, c := range strings.Split(criteriaStr, ",") {
		c = strings.TrimSpace(c)
		if c != "" {
			criteria = append(criteria, c)
		}
	}

	if len(criteria) == 0 {
		return errResult("no valid criteria provided after parsing"), nil
	}

	sessionID := resolveClaudeKey(request)
	now := time.Now().UTC()
	expires := now.Add(freezeTTLHours * time.Hour)

	data := FreezeData{
		FrozenAt:       now.Format(time.RFC3339),
		ExpiresAt:      expires.Format(time.RFC3339),
		SessionID:      sessionID,
		Goal:           goal,
		ExpectedResult: result,
		Criteria:       criteria,
		IsFrozen:       true,
	}

	freezePath := freezeFilePath(sessionID)

	// Ensure directory exists
	if err := os.MkdirAll(filepath.Dir(freezePath), 0755); err != nil {
		return errResult(fmt.Sprintf("failed to create directory: %v", err)), nil
	}

	if err := atomicWriteJSON(freezePath, data); err != nil {
		return errResult(fmt.Sprintf("failed to write freeze file: %v", err)), nil
	}

	return jsonResult(map[string]any{
		"status":         "frozen",
		"file":           freezePath,
		"criteria_count": len(criteria),
		"expires_at":     data.ExpiresAt,
		"message":        "Criteria frozen. Do NOT change criteria to match output — iterate instead.",
	})
}

func handleCriteriaUnfreeze(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := resolveClaudeKey(request)
	freezePath := freezeFilePath(sessionID)

	if _, err := os.Stat(freezePath); os.IsNotExist(err) {
		return jsonResult(map[string]any{
			"status":  "not_frozen",
			"message": "No frozen criteria to remove",
		})
	}

	if err := os.Remove(freezePath); err != nil {
		return errResult(fmt.Sprintf("failed to remove freeze file: %v", err)), nil
	}

	return jsonResult(map[string]any{
		"status":  "unfrozen",
		"message": "Criteria unfrozen. You may now redefine criteria.",
	})
}

func handleCriteriaCheck(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := resolveClaudeKey(request)
	freezePath := freezeFilePath(sessionID)

	data, err := os.ReadFile(freezePath)
	if err != nil {
		return jsonResult(map[string]any{
			"is_frozen": false,
			"message":   "No frozen criteria",
		})
	}

	var freeze FreezeData
	if err := json.Unmarshal(data, &freeze); err != nil {
		return jsonResult(map[string]any{
			"is_frozen": false,
			"error":     "Failed to read freeze file",
		})
	}

	// Check expiration
	if freeze.ExpiresAt != "" {
		expires, err := parseTimestamp(freeze.ExpiresAt)
		if err == nil && time.Now().UTC().After(expires) {
			// Auto-expire
			os.Remove(freezePath)
			return jsonResult(map[string]any{
				"is_frozen": false,
				"message":   fmt.Sprintf("Criteria expired (%dh TTL). Auto-removed.", freezeTTLHours),
				"was":       freeze,
			})
		}
	}

	return jsonResult(freeze)
}

func handleCriteriaList(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := resolveClaudeKey(request)
	freezePath := freezeFilePath(sessionID)

	data, err := os.ReadFile(freezePath)
	if err != nil {
		return jsonResult(FreezeData{
			IsFrozen: false,
		})
	}

	var freeze FreezeData
	if err := json.Unmarshal(data, &freeze); err != nil {
		return jsonResult(FreezeData{
			IsFrozen: false,
		})
	}

	// Check expiration for list too
	if freeze.ExpiresAt != "" {
		expires, err := parseTimestamp(freeze.ExpiresAt)
		if err == nil && time.Now().UTC().After(expires) {
			os.Remove(freezePath)
			freeze.IsFrozen = false
			return jsonResult(freeze)
		}
	}

	return jsonResult(freeze)
}

