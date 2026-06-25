package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
)

// ScopeState tracks files modified and domains touched during a session.
type ScopeState struct {
	FilesModified    []string `json:"files_modified"`
	DomainsTouched   []string `json:"domains_touched"`
	LastWarningLevel int      `json:"last_warning_level"`
}

// pathDomainMap maps working directory prefixes to domains.
var pathDomainMap = map[string]string{
	"/opt/work/pentest/":    "security",
	"/opt/work/osint/":      "osint",
	"/opt/work/devops/":     "devops",
	"/opt/work/reverse/":    "reverse_engineering",
	"/opt/work/dfir/":       "dfir",
	"/opt/work/compliance/": "compliance",
	"/opt/work/business/":   "business_analysis",
	"/opt/work/ml/":         "orchestration",
	"/opt/go/":         "engineering",
	"/opt/cargo/":      "engineering",
	"/opt/templates/":  "engineering",
}

// extDomainMap maps file extensions to domains as a fallback.
var extDomainMap = map[string]string{
	".tf":         "devops",
	".yaml":       "devops",
	".yml":        "devops",
	".dockerfile": "devops",
	".yar":        "security",
	".yara":       "security",
	".sigma":      "security",
	".rule":       "security",
}

func scopeStatePath(sessionID string) string {
	return fmt.Sprintf("/tmp/claude_scope_%s.json", sessionID)
}

func loadScopeState(path string) *ScopeState {
	data, err := os.ReadFile(path)
	if err != nil {
		return &ScopeState{}
	}
	var state ScopeState
	if err := json.Unmarshal(data, &state); err != nil {
		return &ScopeState{}
	}
	return &state
}

func saveScopeState(path string, state *ScopeState) error {
	return atomicWriteJSON(path, state)
}

func detectDomain(filePath string) string {
	fp := strings.ToLower(filePath)
	for prefix, domain := range pathDomainMap {
		if strings.HasPrefix(fp, prefix) {
			return domain
		}
	}
	ext := strings.ToLower(filepath.Ext(filePath))
	if domain, ok := extDomainMap[ext]; ok {
		return domain
	}
	if strings.Contains(filePath, "/.claude/") {
		return "config"
	}
	return "unknown"
}

func contains(slice []string, item string) bool {
	for _, v := range slice {
		if v == item {
			return true
		}
	}
	return false
}

// handleScopeTrack records a file modification and returns escalation warning if thresholds are reached.
func handleScopeTrack(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	filePath, err := reqStr(request, "file_path")
	if err != nil {
		return errResult(err.Error()), nil
	}

	sessionID := resolveClaudeKey(request)
	statePath := scopeStatePath(sessionID)
	state := loadScopeState(statePath)

	// Track unique files
	if !contains(state.FilesModified, filePath) {
		state.FilesModified = append(state.FilesModified, filePath)
	}

	// Track unique domains (skip unknown/config)
	domain := detectDomain(filePath)
	if domain != "unknown" && domain != "config" && !contains(state.DomainsTouched, domain) {
		state.DomainsTouched = append(state.DomainsTouched, domain)
	}

	filesCount := len(state.FilesModified)
	domainsCount := len(state.DomainsTouched)

	// Calculate live score
	liveScore := filesCount * 12
	if ds := domainsCount * 25; ds > liveScore {
		liveScore = ds
	}

	// Determine warning level
	warningLevel := 0
	if filesCount >= 6 && domainsCount >= 2 {
		warningLevel = 2
	} else if filesCount >= 4 {
		warningLevel = 1
	}

	warning := ""
	if warningLevel > state.LastWarningLevel {
		state.LastWarningLevel = warningLevel
		switch warningLevel {
		case 2:
			warning = fmt.Sprintf(
				"SCOPE ESCALATION: %d files modified across %d domains (live_score=%d). TeamCreate recommended. Domains: %s",
				filesCount, domainsCount, liveScore, strings.Join(state.DomainsTouched, ", "),
			)
		case 1:
			warning = fmt.Sprintf(
				"SCOPE ESCALATION: %d files modified (live_score=%d). Consider Plan Mode.",
				filesCount, liveScore,
			)
		}
	}

	if err := saveScopeState(statePath, state); err != nil {
		return errResult(fmt.Sprintf("save state: %v", err)), nil
	}

	result := map[string]any{
		"status":         "ok",
		"files_modified": filesCount,
		"domains":        domainsCount,
		"live_score":     liveScore,
		"warning_level":  warningLevel,
		"domain":         domain,
	}
	if warning != "" {
		result["warning"] = warning
	}

	return jsonResult(result)
}

// handleScopeStatus returns current scope tracking state for the session.
func handleScopeStatus(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	sessionID := resolveClaudeKey(request)
	statePath := scopeStatePath(sessionID)
	state := loadScopeState(statePath)

	filesCount := len(state.FilesModified)
	domainsCount := len(state.DomainsTouched)

	liveScore := filesCount * 12
	if ds := domainsCount * 25; ds > liveScore {
		liveScore = ds
	}

	tier := "Simple"
	switch {
	case liveScore >= 65:
		tier = "Complex"
	case liveScore >= 20:
		tier = "Standard"
	}

	result := map[string]any{
		"session_id":      sessionID,
		"files_modified":  state.FilesModified,
		"domains_touched": state.DomainsTouched,
		"files_count":     filesCount,
		"domains_count":   domainsCount,
		"live_score":      liveScore,
		"tier":            tier,
		"warning_level":   state.LastWarningLevel,
	}

	return jsonResult(result)
}
