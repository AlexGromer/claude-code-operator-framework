package main

import (
	"testing"
)

func TestProfileNamesMatchProfiles(t *testing.T) {
	names := ProfileNames()
	if len(names) != len(Profiles) {
		t.Errorf("ProfileNames() length %d != Profiles length %d", len(names), len(Profiles))
	}
	for _, name := range names {
		if _, ok := Profiles[name]; !ok {
			t.Errorf("ProfileNames() contains %q but Profiles does not", name)
		}
	}
}

func TestAllProfilesHaveServers(t *testing.T) {
	for name, profile := range Profiles {
		if len(profile.Servers) == 0 {
			t.Errorf("profile %q has no servers", name)
		}
		if profile.Description == "" {
			t.Errorf("profile %q has no description", name)
		}
	}
}

func TestEssentialProfileExists(t *testing.T) {
	essential, ok := Profiles["essential"]
	if !ok {
		t.Fatal("essential profile not found")
	}
	// Must have these core servers
	required := []string{"github", "fetch", "filesystem", "memory", "git"}
	for _, name := range required {
		if _, ok := essential.Servers[name]; !ok {
			t.Errorf("essential profile missing server: %q", name)
		}
	}
}

func TestProfileCount(t *testing.T) {
	if len(Profiles) != 11 {
		t.Errorf("expected 11 profiles, got %d", len(Profiles))
	}
}

func TestServerConfigTypes(t *testing.T) {
	for pname, profile := range Profiles {
		for sname, cfg := range profile.Servers {
			if cfg.Type != "stdio" && cfg.Type != "sse" {
				t.Errorf("%s/%s: invalid type %q", pname, sname, cfg.Type)
			}
			if cfg.Type == "stdio" && cfg.Command == "" {
				t.Errorf("%s/%s: stdio server missing command", pname, sname)
			}
			if cfg.Type == "sse" && cfg.URL == "" {
				t.Errorf("%s/%s: sse server missing url", pname, sname)
			}
		}
	}
}

func TestServerConfigToMap(t *testing.T) {
	// Test stdio server
	cfg := ServerConfig{
		Type:    "stdio",
		Command: "/usr/bin/test",
		Args:    []string{"-a", "-b"},
		Env:     map[string]string{"FOO": "bar"},
	}
	m := serverConfigToMap(cfg, "test-profile")
	if m["type"] != "stdio" {
		t.Errorf("type: got %v", m["type"])
	}
	if m["command"] != "/usr/bin/test" {
		t.Errorf("command: got %v", m["command"])
	}
	args, ok := m["args"].([]any)
	if !ok || len(args) != 2 {
		t.Errorf("args: got %v", m["args"])
	}
	// Verify TTL metadata
	if m["_profile"] != "test-profile" {
		t.Errorf("_profile: expected 'test-profile', got %v", m["_profile"])
	}
	if _, ok := m["_loaded_at"].(string); !ok || m["_loaded_at"] == "" {
		t.Errorf("_loaded_at: expected non-empty RFC3339 string, got %v", m["_loaded_at"])
	}

	// Test SSE server
	sseConfig := ServerConfig{
		Type:    "sse",
		URL:     "https://example.com/mcp/",
		Headers: map[string]string{"Authorization": "Bearer token"},
	}
	m2 := serverConfigToMap(sseConfig, "sse-profile")
	if m2["type"] != "sse" {
		t.Errorf("type: got %v", m2["type"])
	}
	if m2["url"] != "https://example.com/mcp/" {
		t.Errorf("url: got %v", m2["url"])
	}
	headers, ok := m2["headers"].(map[string]any)
	if !ok {
		t.Fatal("headers not a map")
	}
	if headers["Authorization"] != "Bearer token" {
		t.Errorf("header: got %v", headers["Authorization"])
	}
}

func TestInjectEnvTokensFromUserScope(t *testing.T) {
	cfg := ServerConfig{
		Type:    "stdio",
		Command: "test",
		Env:     map[string]string{},
	}

	userServers := map[string]any{
		"myserver": map[string]any{
			"env": map[string]any{
				"API_KEY": "secret123",
			},
		},
	}

	result := InjectEnvTokens(cfg, "myserver", userServers)
	if result.Env["API_KEY"] != "secret123" {
		t.Errorf("expected API_KEY=secret123, got %v", result.Env["API_KEY"])
	}
}

func TestInjectEnvTokensSSE(t *testing.T) {
	cfg := ServerConfig{
		Type:    "sse",
		URL:     "https://example.com",
		Headers: map[string]string{},
	}

	userServers := map[string]any{
		"mysse": map[string]any{
			"headers": map[string]any{
				"Authorization": "Bearer token123",
			},
		},
	}

	result := InjectEnvTokens(cfg, "mysse", userServers)
	if result.Headers["Authorization"] != "Bearer token123" {
		t.Errorf("expected Authorization header, got %v", result.Headers["Authorization"])
	}
}

func TestInjectEnvTokensNoOverwrite(t *testing.T) {
	cfg := ServerConfig{
		Type:    "stdio",
		Command: "test",
		Env:     map[string]string{"API_KEY": "original"},
	}

	userServers := map[string]any{
		"myserver": map[string]any{
			"env": map[string]any{
				"API_KEY": "should-not-overwrite",
			},
		},
	}

	result := InjectEnvTokens(cfg, "myserver", userServers)
	if result.Env["API_KEY"] != "original" {
		t.Errorf("should not overwrite existing key, got %v", result.Env["API_KEY"])
	}
}

func TestEssentialServerNames(t *testing.T) {
	names := EssentialServerNames()
	if len(names) != len(Profiles["essential"].Servers) {
		t.Errorf("EssentialServerNames() length mismatch: %d vs %d",
			len(names), len(Profiles["essential"].Servers))
	}
}

func TestResolveProjectPath(t *testing.T) {
	// Empty -> current working directory (servers are injected per-project, not "*")
	if got := resolveProjectPath(""); got == "*" {
		t.Errorf("empty should resolve to cwd, not wildcard, got %q", got)
	}
	// Absolute path stays absolute
	result := resolveProjectPath("/opt/test")
	if result != "/opt/test" {
		t.Errorf("absolute path should stay, got %q", result)
	}
}
