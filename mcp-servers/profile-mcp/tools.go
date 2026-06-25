package main

import (
	"context"
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

func registerTools(s *server.MCPServer) {
	// profile_list
	s.AddTool(mcp.NewTool("profile_list",
		mcp.WithDescription("List all available profiles with server counts"),
	), handleProfileList)

	// profile_show
	s.AddTool(mcp.NewTool("profile_show",
		mcp.WithDescription("Show servers in a specific profile"),
		mcp.WithString("profile_name", mcp.Required(), mcp.Description("Profile name to show")),
	), handleProfileShow)

	// profile_load
	s.AddTool(mcp.NewTool("profile_load",
		mcp.WithDescription("Load a profile's servers into ~/.claude.json"),
		mcp.WithString("profile_name", mcp.Required(), mcp.Description("Profile name to load")),
		mcp.WithString("project_path", mcp.Description("Project path (default: wildcard '*')")),
	), handleProfileLoad)

	// profile_unload
	s.AddTool(mcp.NewTool("profile_unload",
		mcp.WithDescription("Unload a profile's servers from ~/.claude.json"),
		mcp.WithString("profile_name", mcp.Required(), mcp.Description("Profile name to unload")),
		mcp.WithString("project_path", mcp.Description("Project path (default: wildcard '*')")),
	), handleProfileUnload)

	// profile_status
	s.AddTool(mcp.NewTool("profile_status",
		mcp.WithDescription("Show currently loaded servers for a project"),
		mcp.WithString("project_path", mcp.Description("Project path (default: wildcard '*')")),
	), handleProfileStatus)

	// profile_load_all
	s.AddTool(mcp.NewTool("profile_load_all",
		mcp.WithDescription("Load all profiles"),
		mcp.WithString("project_path", mcp.Description("Project path (default: wildcard '*')")),
	), handleProfileLoadAll)

	// profile_reset
	s.AddTool(mcp.NewTool("profile_reset",
		mcp.WithDescription("Reset to essential servers only"),
		mcp.WithString("project_path", mcp.Description("Project path (default: wildcard '*')")),
	), handleProfileReset)

	// profile_ensure_essential
	s.AddTool(mcp.NewTool("profile_ensure_essential",
		mcp.WithDescription("Ensure essential servers are loaded, idempotent"),
		mcp.WithString("project_path", mcp.Description("Project path (default: wildcard '*')")),
	), handleProfileEnsureEssential)
}

// --- Helpers ---

func optStr(request mcp.CallToolRequest, key string) string {
	args := request.GetArguments()
	if v, ok := args[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func jsonResult(v any) (*mcp.CallToolResult, error) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("json: %v", err)), nil
	}
	return mcp.NewToolResultText(string(data)), nil
}

// --- Handlers ---

func handleProfileList(_ context.Context, _ mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	type profileInfo struct {
		Name        string `json:"name"`
		Description string `json:"description"`
		ServerCount int    `json:"server_count"`
	}

	profiles := make([]profileInfo, 0, len(Profiles))
	totalServers := 0

	for _, name := range ProfileNames() {
		p := Profiles[name]
		count := len(p.Servers)
		totalServers += count
		profiles = append(profiles, profileInfo{
			Name:        name,
			Description: p.Description,
			ServerCount: count,
		})
	}

	return jsonResult(map[string]any{
		"profiles":      profiles,
		"total_profiles": len(profiles),
		"total_servers":  totalServers,
	})
}

func handleProfileShow(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	name, err := request.RequireString("profile_name")
	if err != nil {
		return mcp.NewToolResultError("profile_name is required"), nil
	}

	profile, ok := Profiles[name]
	if !ok {
		return mcp.NewToolResultError(fmt.Sprintf("profile not found: %q", name)), nil
	}

	type serverInfo struct {
		Name    string `json:"name"`
		Type    string `json:"type"`
		Command string `json:"command,omitempty"`
		URL     string `json:"url,omitempty"`
		Args    string `json:"args,omitempty"`
	}

	servers := make([]serverInfo, 0, len(profile.Servers))
	// Sort server names for consistent output
	names := make([]string, 0, len(profile.Servers))
	for n := range profile.Servers {
		names = append(names, n)
	}
	sort.Strings(names)

	for _, n := range names {
		cfg := profile.Servers[n]
		si := serverInfo{
			Name: n,
			Type: cfg.Type,
		}
		if cfg.Type == "sse" {
			si.URL = cfg.URL
		} else {
			si.Command = cfg.Command
			if len(cfg.Args) > 0 {
				limit := len(cfg.Args)
				if limit > 3 {
					limit = 3
				}
				si.Args = strings.Join(cfg.Args[:limit], " ")
			}
		}
		servers = append(servers, si)
	}

	return jsonResult(map[string]any{
		"profile":      name,
		"description":  profile.Description,
		"server_count": len(servers),
		"servers":      servers,
	})
}

func handleProfileLoad(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	profileName, err := request.RequireString("profile_name")
	if err != nil {
		return mcp.NewToolResultError("profile_name is required"), nil
	}

	profile, ok := Profiles[profileName]
	if !ok {
		return mcp.NewToolResultError(fmt.Sprintf("profile not found: %q", profileName)), nil
	}

	projectKey := resolveProjectPath(optStr(request, "project_path"))

	cfg, err := LoadConfig()
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load config: %v", err)), nil
	}

	servers := cfg.GetLocalServers(projectKey)
	userServers := cfg.GetUserServers()
	added := make([]string, 0, len(profile.Servers))

	for name, serverCfg := range profile.Servers {
		enriched := InjectEnvTokens(serverCfg, name, userServers)
		servers[name] = serverConfigToMap(enriched, profileName)
		added = append(added, name)
	}
	sort.Strings(added)

	cfg.SetLocalServers(projectKey, servers)
	if err := SaveConfig(cfg); err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("save config: %v", err)), nil
	}

	return jsonResult(map[string]any{
		"status":        "loaded",
		"profile":       profileName,
		"project":       projectKey,
		"added":         added,
		"added_count":   len(added),
		"total_servers": len(servers),
		"message":       "Restart Claude Code session to use new servers.",
	})
}

func handleProfileUnload(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	profileName, err := request.RequireString("profile_name")
	if err != nil {
		return mcp.NewToolResultError("profile_name is required"), nil
	}

	profile, ok := Profiles[profileName]
	if !ok {
		return mcp.NewToolResultError(fmt.Sprintf("profile not found: %q", profileName)), nil
	}

	projectKey := resolveProjectPath(optStr(request, "project_path"))

	cfg, err := LoadConfig()
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load config: %v", err)), nil
	}

	servers := cfg.GetLocalServers(projectKey)
	removed := make([]string, 0)

	for name := range profile.Servers {
		if _, exists := servers[name]; exists {
			delete(servers, name)
			removed = append(removed, name)
		}
	}
	sort.Strings(removed)

	cfg.SetLocalServers(projectKey, servers)
	if err := SaveConfig(cfg); err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("save config: %v", err)), nil
	}

	return jsonResult(map[string]any{
		"status":            "unloaded",
		"profile":           profileName,
		"project":           projectKey,
		"removed":           removed,
		"removed_count":     len(removed),
		"remaining_servers": len(servers),
	})
}

func handleProfileStatus(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	projectKey := resolveProjectPath(optStr(request, "project_path"))

	cfg, err := LoadConfig()
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load config: %v", err)), nil
	}

	servers := cfg.GetLocalServers(projectKey)

	// Build server list
	type serverEntry struct {
		Name    string `json:"name"`
		Command string `json:"command,omitempty"`
		Type    string `json:"type,omitempty"`
	}

	entries := make([]serverEntry, 0, len(servers))
	names := make([]string, 0, len(servers))
	for n := range servers {
		names = append(names, n)
	}
	sort.Strings(names)

	for _, n := range names {
		s := servers[n]
		entry := serverEntry{Name: n}
		if sm, ok := s.(map[string]any); ok {
			if cmd, ok := sm["command"].(string); ok {
				entry.Command = cmd
			}
			if t, ok := sm["type"].(string); ok {
				entry.Type = t
			}
		}
		entries = append(entries, entry)
	}

	// Profile coverage
	type profileCoverage struct {
		Name   string `json:"name"`
		Loaded int    `json:"loaded"`
		Total  int    `json:"total"`
		Status string `json:"status"`
	}

	coverage := make([]profileCoverage, 0)
	for _, pname := range ProfileNames() {
		p := Profiles[pname]
		loaded := 0
		for sname := range p.Servers {
			if _, exists := servers[sname]; exists {
				loaded++
			}
		}
		if loaded > 0 {
			status := fmt.Sprintf("%d/%d", loaded, len(p.Servers))
			if loaded == len(p.Servers) {
				status = "FULL"
			}
			coverage = append(coverage, profileCoverage{
				Name:   pname,
				Loaded: loaded,
				Total:  len(p.Servers),
				Status: status,
			})
		}
	}

	return jsonResult(map[string]any{
		"project":       projectKey,
		"total_servers": len(servers),
		"servers":       entries,
		"coverage":      coverage,
	})
}

func handleProfileLoadAll(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	projectKey := resolveProjectPath(optStr(request, "project_path"))

	cfg, err := LoadConfig()
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load config: %v", err)), nil
	}

	servers := cfg.GetLocalServers(projectKey)
	userServers := cfg.GetUserServers()
	totalAdded := 0

	for _, profileName := range ProfileNames() {
		profile := Profiles[profileName]
		for name, serverCfg := range profile.Servers {
			enriched := InjectEnvTokens(serverCfg, name, userServers)
			servers[name] = serverConfigToMap(enriched, profileName)
			totalAdded++
		}
	}

	cfg.SetLocalServers(projectKey, servers)
	if err := SaveConfig(cfg); err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("save config: %v", err)), nil
	}

	return jsonResult(map[string]any{
		"status":        "loaded_all",
		"project":       projectKey,
		"profiles":      len(Profiles),
		"servers_added": totalAdded,
		"total_servers": len(servers),
		"message":       "Restart Claude Code session to use new servers.",
	})
}

func handleProfileReset(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	projectKey := resolveProjectPath(optStr(request, "project_path"))

	cfg, err := LoadConfig()
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load config: %v", err)), nil
	}

	userServers := cfg.GetUserServers()

	// Clear all servers, then load essential only
	newServers := map[string]any{}
	essential := Profiles["essential"]
	added := make([]string, 0, len(essential.Servers))

	for name, serverCfg := range essential.Servers {
		enriched := InjectEnvTokens(serverCfg, name, userServers)
		newServers[name] = serverConfigToMap(enriched, "essential")
		added = append(added, name)
	}
	sort.Strings(added)

	cfg.SetLocalServers(projectKey, newServers)
	if err := SaveConfig(cfg); err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("save config: %v", err)), nil
	}

	return jsonResult(map[string]any{
		"status":        "reset",
		"project":       projectKey,
		"essential":     added,
		"total_servers": len(newServers),
		"message":       "Reset to essential servers only. Restart Claude Code session.",
	})
}

func handleProfileEnsureEssential(_ context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	projectKey := resolveProjectPath(optStr(request, "project_path"))

	cfg, err := LoadConfig()
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("load config: %v", err)), nil
	}

	servers := cfg.GetLocalServers(projectKey)
	userServers := cfg.GetUserServers()
	essential := Profiles["essential"]
	missing := make([]string, 0)

	for name, serverCfg := range essential.Servers {
		if _, exists := servers[name]; !exists {
			enriched := InjectEnvTokens(serverCfg, name, userServers)
			servers[name] = serverConfigToMap(enriched, "essential")
			missing = append(missing, name)
		}
	}
	sort.Strings(missing)

	if len(missing) > 0 {
		cfg.SetLocalServers(projectKey, servers)
		if err := SaveConfig(cfg); err != nil {
			return mcp.NewToolResultError(fmt.Sprintf("save config: %v", err)), nil
		}
	}

	return jsonResult(map[string]any{
		"status":        "ok",
		"project":       projectKey,
		"added":         missing,
		"added_count":   len(missing),
		"total_servers": len(servers),
		"changed":       len(missing) > 0,
	})
}
