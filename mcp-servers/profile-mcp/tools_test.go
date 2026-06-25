package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
)

// makeRequest creates a CallToolRequest from arguments.
func makeRequest(args map[string]any) mcp.CallToolRequest {
	return mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Arguments: args,
		},
	}
}

// extractText gets the text content from a CallToolResult.
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

// setupTestConfig creates a temp ~/.claude.json for testing.
// Returns cleanup function that restores real config path.
func setupTestConfig(t *testing.T) (string, func()) {
	t.Helper()
	dir := t.TempDir()

	// Create a fake claude.json
	configFile := filepath.Join(dir, ".claude.json")
	initial := map[string]any{
		"projects": map[string]any{
			"*": map[string]any{
				"mcpServers": map[string]any{},
			},
		},
		"mcpServers": map[string]any{
			"github": map[string]any{
				"env": map[string]any{
					"GITHUB_PERSONAL_ACCESS_TOKEN": "test-token-123",
				},
			},
			"censys-asm": map[string]any{
				"headers": map[string]any{
					"Authorization": "Bearer censys-token",
				},
			},
		},
	}
	data, _ := json.MarshalIndent(initial, "", "  ")
	if err := os.WriteFile(configFile, data, 0o644); err != nil {
		t.Fatalf("write test config: %v", err)
	}

	// Override configPath by setting HOME
	origHome := os.Getenv("HOME")
	os.Setenv("HOME", dir)

	return configFile, func() {
		os.Setenv("HOME", origHome)
	}
}

func TestHandleProfileList(t *testing.T) {
	ctx := context.Background()
	result, err := handleProfileList(ctx, makeRequest(nil))
	if err != nil {
		t.Fatalf("profile_list: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	profileCount := int(resp["total_profiles"].(float64))
	if profileCount != 11 {
		t.Errorf("total_profiles: got %d, want 11", profileCount)
	}

	serverCount := int(resp["total_servers"].(float64))
	if serverCount < 40 {
		t.Errorf("total_servers: got %d, want >= 40", serverCount)
	}
}

func TestHandleProfileShow(t *testing.T) {
	ctx := context.Background()

	// Valid profile
	result, err := handleProfileShow(ctx, makeRequest(map[string]any{
		"profile_name": "essential",
	}))
	if err != nil {
		t.Fatalf("profile_show: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp["profile"] != "essential" {
		t.Errorf("profile: got %v", resp["profile"])
	}
	serverCount := int(resp["server_count"].(float64))
	if serverCount != len(Profiles["essential"].Servers) {
		t.Errorf("server_count: got %d, want %d", serverCount, len(Profiles["essential"].Servers))
	}

	// Invalid profile
	result, err = handleProfileShow(ctx, makeRequest(map[string]any{
		"profile_name": "nonexistent",
	}))
	if err != nil {
		t.Fatalf("profile_show error: %v", err)
	}
	if !result.IsError {
		t.Error("expected error for nonexistent profile")
	}
}

func TestHandleProfileLoad(t *testing.T) {
	_, cleanup := setupTestConfig(t)
	defer cleanup()

	ctx := context.Background()
	result, err := handleProfileLoad(ctx, makeRequest(map[string]any{
		"profile_name": "security",
	}))
	if err != nil {
		t.Fatalf("profile_load: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp["status"] != "loaded" {
		t.Errorf("status: got %v", resp["status"])
	}
	addedCount := int(resp["added_count"].(float64))
	if addedCount != len(Profiles["security"].Servers) {
		t.Errorf("added_count: got %d, want %d", addedCount, len(Profiles["security"].Servers))
	}

	// Verify config was written
	cfg, err := LoadConfig()
	if err != nil {
		t.Fatalf("reload config: %v", err)
	}
	servers := cfg.GetLocalServers(resolveProjectPath(""))
	for name := range Profiles["security"].Servers {
		if _, exists := servers[name]; !exists {
			t.Errorf("server %q not found in config after load", name)
		}
	}
}

func TestHandleProfileUnload(t *testing.T) {
	_, cleanup := setupTestConfig(t)
	defer cleanup()

	ctx := context.Background()

	// First load security
	_, err := handleProfileLoad(ctx, makeRequest(map[string]any{
		"profile_name": "security",
	}))
	if err != nil {
		t.Fatalf("load: %v", err)
	}

	// Then unload
	result, err := handleProfileUnload(ctx, makeRequest(map[string]any{
		"profile_name": "security",
	}))
	if err != nil {
		t.Fatalf("unload: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp["status"] != "unloaded" {
		t.Errorf("status: got %v", resp["status"])
	}
	removedCount := int(resp["removed_count"].(float64))
	if removedCount != len(Profiles["security"].Servers) {
		t.Errorf("removed_count: got %d, want %d", removedCount, len(Profiles["security"].Servers))
	}

	// Verify servers removed
	cfg, err := LoadConfig()
	if err != nil {
		t.Fatalf("reload config: %v", err)
	}
	servers := cfg.GetLocalServers(resolveProjectPath(""))
	for name := range Profiles["security"].Servers {
		if _, exists := servers[name]; exists {
			t.Errorf("server %q still in config after unload", name)
		}
	}
}

func TestHandleProfileStatus(t *testing.T) {
	_, cleanup := setupTestConfig(t)
	defer cleanup()

	ctx := context.Background()

	// Load essential first
	_, err := handleProfileLoad(ctx, makeRequest(map[string]any{
		"profile_name": "essential",
	}))
	if err != nil {
		t.Fatalf("load: %v", err)
	}

	result, err := handleProfileStatus(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("status: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	totalServers := int(resp["total_servers"].(float64))
	if totalServers != len(Profiles["essential"].Servers) {
		t.Errorf("total_servers: got %d, want %d", totalServers, len(Profiles["essential"].Servers))
	}

	coverage, ok := resp["coverage"].([]any)
	if !ok || len(coverage) == 0 {
		t.Error("expected non-empty coverage")
	}
}

func TestHandleProfileLoadAll(t *testing.T) {
	_, cleanup := setupTestConfig(t)
	defer cleanup()

	ctx := context.Background()
	result, err := handleProfileLoadAll(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("load_all: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp["status"] != "loaded_all" {
		t.Errorf("status: got %v", resp["status"])
	}

	totalServers := int(resp["total_servers"].(float64))
	if totalServers < 40 {
		t.Errorf("total_servers: got %d, expected >= 40", totalServers)
	}
}

func TestHandleProfileReset(t *testing.T) {
	_, cleanup := setupTestConfig(t)
	defer cleanup()

	ctx := context.Background()

	// Load all first
	_, err := handleProfileLoadAll(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("load_all: %v", err)
	}

	// Then reset
	result, err := handleProfileReset(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("reset: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp["status"] != "reset" {
		t.Errorf("status: got %v", resp["status"])
	}

	totalServers := int(resp["total_servers"].(float64))
	if totalServers != len(Profiles["essential"].Servers) {
		t.Errorf("total_servers: got %d, want %d (essential only)", totalServers, len(Profiles["essential"].Servers))
	}
}

func TestHandleProfileEnsureEssential(t *testing.T) {
	_, cleanup := setupTestConfig(t)
	defer cleanup()

	ctx := context.Background()

	// First call: should add all essential servers
	result, err := handleProfileEnsureEssential(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("ensure_essential: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp["changed"] != true {
		t.Error("first call should show changed=true")
	}
	addedCount := int(resp["added_count"].(float64))
	if addedCount != len(Profiles["essential"].Servers) {
		t.Errorf("added_count: got %d, want %d", addedCount, len(Profiles["essential"].Servers))
	}

	// Second call: idempotent, nothing to add
	result, err = handleProfileEnsureEssential(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("ensure_essential 2nd: %v", err)
	}

	text = extractText(result)
	var resp2 map[string]any
	if err := json.Unmarshal([]byte(text), &resp2); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp2["changed"] != false {
		t.Error("second call should show changed=false")
	}
	if int(resp2["added_count"].(float64)) != 0 {
		t.Error("second call should add 0 servers")
	}
}

func TestHandleProfileLoadWithTokenInjection(t *testing.T) {
	_, cleanup := setupTestConfig(t)
	defer cleanup()

	ctx := context.Background()

	// Load essential - github should get token from user-scope
	result, err := handleProfileLoad(ctx, makeRequest(map[string]any{
		"profile_name": "essential",
	}))
	if err != nil {
		t.Fatalf("load: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	// Verify token was injected
	cfg, err := LoadConfig()
	if err != nil {
		t.Fatalf("reload: %v", err)
	}
	servers := cfg.GetLocalServers(resolveProjectPath(""))
	github, ok := servers["github"].(map[string]any)
	if !ok {
		t.Fatal("github server not found")
	}
	env, ok := github["env"].(map[string]any)
	if !ok {
		t.Fatal("github env not found")
	}
	if env["GITHUB_PERSONAL_ACCESS_TOKEN"] != "test-token-123" {
		t.Errorf("token not injected: got %v", env["GITHUB_PERSONAL_ACCESS_TOKEN"])
	}
}

func TestHandleProfileLoadWithProjectPath(t *testing.T) {
	_, cleanup := setupTestConfig(t)
	defer cleanup()

	ctx := context.Background()
	result, err := handleProfileLoad(ctx, makeRequest(map[string]any{
		"profile_name": "browser",
		"project_path": "/opt/myproject",
	}))
	if err != nil {
		t.Fatalf("load: %v", err)
	}

	text := extractText(result)
	var resp map[string]any
	if err := json.Unmarshal([]byte(text), &resp); err != nil {
		t.Fatalf("parse: %v", err)
	}

	if resp["project"] != "/opt/myproject" {
		t.Errorf("project: got %v", resp["project"])
	}

	// Verify it was saved under the project key
	cfg, err := LoadConfig()
	if err != nil {
		t.Fatalf("reload: %v", err)
	}
	servers := cfg.GetLocalServers("/opt/myproject")
	if len(servers) != len(Profiles["browser"].Servers) {
		t.Errorf("server count: got %d, want %d", len(servers), len(Profiles["browser"].Servers))
	}
}

func TestHandleProfileShowMissingParam(t *testing.T) {
	ctx := context.Background()
	result, err := handleProfileShow(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("profile_show: %v", err)
	}
	if !result.IsError {
		t.Error("expected error when profile_name is missing")
	}
}

func TestHandleProfileLoadMissingParam(t *testing.T) {
	ctx := context.Background()
	result, err := handleProfileLoad(ctx, makeRequest(map[string]any{}))
	if err != nil {
		t.Fatalf("profile_load: %v", err)
	}
	if !result.IsError {
		t.Error("expected error when profile_name is missing")
	}
}
