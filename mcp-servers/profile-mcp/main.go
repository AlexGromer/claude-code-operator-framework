package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

const version = "0.1.0"

func main() {
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "--ensure-essential":
			projectPath := getCwdFromArgs()
			result := cliEnsureEssential(projectPath)
			printJSON(result)
			return
		case "--load":
			// --load <profile_name> [project_path]
			if len(os.Args) < 3 {
				fmt.Fprintln(os.Stderr, "usage: profile-mcp --load <profile_name> [project_path]")
				os.Exit(1)
			}
			profileName := os.Args[2]
			projectPath := ""
			if len(os.Args) > 3 {
				projectPath = os.Args[3]
			}
			result := cliLoad(profileName, projectPath)
			printJSON(result)
			return
		case "--unload":
			// --unload <profile_name> [project_path]
			if len(os.Args) < 3 {
				fmt.Fprintln(os.Stderr, "usage: profile-mcp --unload <profile_name> [project_path]")
				os.Exit(1)
			}
			profileName := os.Args[2]
			projectPath := ""
			if len(os.Args) > 3 {
				projectPath = os.Args[3]
			}
			result := cliUnload(profileName, projectPath)
			printJSON(result)
			return
		case "--version":
			fmt.Println("profile-mcp", version)
			return
		}
	}

	s := server.NewMCPServer(
		"profile-mcp",
		version,
		server.WithToolCapabilities(false),
	)

	registerTools(s)

	if os.Getenv("PROFILE_MCP_DEBUG") != "" {
		fmt.Fprintf(os.Stderr, "profile-mcp %s started (tools: %d)\n", version, 8)
	}

	if err := server.ServeStdio(s); err != nil {
		fmt.Fprintf(os.Stderr, "fatal: %v\n", err)
		os.Exit(1)
	}
}

func getCwdFromArgs() string {
	if len(os.Args) > 2 {
		return os.Args[2]
	}
	cwd, _ := os.Getwd()
	return cwd
}

func printJSON(v map[string]any) {
	data, _ := json.MarshalIndent(v, "", "  ")
	fmt.Println(string(data))
}

func cliLoad(profileName, projectPath string) map[string]any {
	profile, ok := Profiles[profileName]
	if !ok {
		return map[string]any{"status": "error", "error": fmt.Sprintf("profile not found: %q", profileName)}
	}

	projectKey := resolveProjectPath(projectPath)

	cfg, err := LoadConfig()
	if err != nil {
		return map[string]any{"status": "error", "error": err.Error()}
	}

	servers := cfg.GetLocalServers(projectKey)
	userServers := cfg.GetUserServers()
	added := make([]string, 0, len(profile.Servers))

	for name, serverCfg := range profile.Servers {
		enriched := InjectEnvTokens(serverCfg, name, userServers)
		servers[name] = serverConfigToMap(enriched, profileName)
		added = append(added, name)
	}

	cfg.SetLocalServers(projectKey, servers)
	if err := SaveConfig(cfg); err != nil {
		return map[string]any{"status": "error", "error": err.Error()}
	}

	return map[string]any{
		"status":        "loaded",
		"profile":       profileName,
		"project":       projectKey,
		"added":         added,
		"added_count":   len(added),
		"total_servers": len(servers),
	}
}

func cliUnload(profileName, projectPath string) map[string]any {
	profile, ok := Profiles[profileName]
	if !ok {
		return map[string]any{"status": "error", "error": fmt.Sprintf("profile not found: %q", profileName)}
	}

	projectKey := resolveProjectPath(projectPath)

	cfg, err := LoadConfig()
	if err != nil {
		return map[string]any{"status": "error", "error": err.Error()}
	}

	servers := cfg.GetLocalServers(projectKey)
	removed := make([]string, 0)

	for name := range profile.Servers {
		if _, exists := servers[name]; exists {
			delete(servers, name)
			removed = append(removed, name)
		}
	}

	cfg.SetLocalServers(projectKey, servers)
	if err := SaveConfig(cfg); err != nil {
		return map[string]any{"status": "error", "error": err.Error()}
	}

	return map[string]any{
		"status":            "unloaded",
		"profile":           profileName,
		"project":           projectKey,
		"removed":           removed,
		"removed_count":     len(removed),
		"remaining_servers": len(servers),
	}
}

func cliEnsureEssential(projectPath string) map[string]any {
	projectKey := resolveProjectPath(projectPath)

	cfg, err := LoadConfig()
	if err != nil {
		return map[string]any{"status": "error", "error": err.Error()}
	}

	servers := cfg.GetLocalServers(projectKey)
	userServers := cfg.GetUserServers()
	essential := Profiles["essential"]
	added := make([]string, 0)

	for name, serverCfg := range essential.Servers {
		if _, exists := servers[name]; !exists {
			enriched := InjectEnvTokens(serverCfg, name, userServers)
			servers[name] = serverConfigToMap(enriched, "essential")
			added = append(added, name)
		}
	}

	if len(added) > 0 {
		cfg.SetLocalServers(projectKey, servers)
		if err := SaveConfig(cfg); err != nil {
			return map[string]any{"status": "error", "error": err.Error()}
		}
	}

	return map[string]any{
		"status":        "ok",
		"project":       projectKey,
		"added":         added,
		"added_count":   len(added),
		"total_servers": len(servers),
		"changed":       len(added) > 0,
	}
}

// ServerInfo returns the MCP server info for testing.
func ServerInfo() mcp.Implementation {
	return mcp.Implementation{
		Name:    "profile-mcp",
		Version: version,
	}
}
