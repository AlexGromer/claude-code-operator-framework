package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"syscall"
	"time"
)

const defaultProjectKey = "*"

// ClaudeConfig represents the top-level ~/.claude.json structure.
type ClaudeConfig struct {
	raw map[string]any
}

// configPath returns the path to ~/.claude.json.
func configPath() string {
	return filepath.Join(homeDir(), ".claude.json")
}

// LoadConfig reads and parses ~/.claude.json.
func LoadConfig() (*ClaudeConfig, error) {
	data, err := os.ReadFile(configPath())
	if err != nil {
		if os.IsNotExist(err) {
			return &ClaudeConfig{raw: map[string]any{}}, nil
		}
		return nil, fmt.Errorf("read config: %w", err)
	}

	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}

	return &ClaudeConfig{raw: raw}, nil
}

// SaveConfig atomically writes ~/.claude.json with file locking.
func SaveConfig(cfg *ClaudeConfig) error {
	path := configPath()

	f, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE, 0o644)
	if err != nil {
		return fmt.Errorf("open config: %w", err)
	}
	defer f.Close()

	// Exclusive lock
	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX); err != nil {
		return fmt.Errorf("flock: %w", err)
	}
	defer syscall.Flock(int(f.Fd()), syscall.LOCK_UN)

	data, err := json.MarshalIndent(cfg.raw, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal config: %w", err)
	}

	if err := f.Truncate(0); err != nil {
		return fmt.Errorf("truncate: %w", err)
	}
	if _, err := f.Seek(0, 0); err != nil {
		return fmt.Errorf("seek: %w", err)
	}
	if _, err := f.Write(data); err != nil {
		return fmt.Errorf("write config: %w", err)
	}

	return nil
}

// resolveProjectPath returns the project key for ~/.claude.json.
// With no path it defaults to the process cwd — the per-project key Claude Code uses
// for LOCAL-scope MCP injection. Invariant: a fresh profile-mcp process runs per
// project session with cwd = the project dir; if that ever changes this default breaks.
// Falls back to "*" only if cwd is unavailable or root. An explicit path is absolutized.
func resolveProjectPath(projectPath string) string {
	if projectPath == "" {
		// Servers are injected per-project — the SessionStart hook writes them into
		// projects[cwd], NOT under the "*" wildcard. Default to cwd so tools operate
		// on the real per-project scope; fall back to "*" if cwd is unavailable or "/".
		if cwd, err := os.Getwd(); err == nil && cwd != "" && cwd != "/" {
			return cwd
		}
		return defaultProjectKey
	}
	// Resolve to absolute path
	abs, err := filepath.Abs(projectPath)
	if err != nil {
		return projectPath
	}
	return abs
}

// GetLocalServers returns the mcpServers map for a project key.
func (c *ClaudeConfig) GetLocalServers(projectKey string) map[string]any {
	projects, ok := c.raw["projects"].(map[string]any)
	if !ok {
		return map[string]any{}
	}
	proj, ok := projects[projectKey].(map[string]any)
	if !ok {
		return map[string]any{}
	}
	servers, ok := proj["mcpServers"].(map[string]any)
	if !ok {
		return map[string]any{}
	}
	return servers
}

// SetLocalServers sets the mcpServers map for a project key.
func (c *ClaudeConfig) SetLocalServers(projectKey string, servers map[string]any) {
	projects, ok := c.raw["projects"].(map[string]any)
	if !ok {
		projects = map[string]any{}
		c.raw["projects"] = projects
	}
	proj, ok := projects[projectKey].(map[string]any)
	if !ok {
		proj = map[string]any{}
		projects[projectKey] = proj
	}
	proj["mcpServers"] = servers
}

// GetUserServers returns the top-level mcpServers (user-scope) for token injection.
func (c *ClaudeConfig) GetUserServers() map[string]any {
	servers, ok := c.raw["mcpServers"].(map[string]any)
	if !ok {
		return map[string]any{}
	}
	return servers
}

// serverConfigToMap converts a ServerConfig to a map[string]any for JSON storage.
// profileName is stored as "_profile" metadata; "_loaded_at" is set to current UTC time.
func serverConfigToMap(cfg ServerConfig, profileName string) map[string]any {
	m := map[string]any{
		"type":       cfg.Type,
		"_profile":   profileName,
		"_loaded_at": time.Now().UTC().Format(time.RFC3339),
	}
	if cfg.Type == "sse" {
		m["url"] = cfg.URL
		if cfg.Headers != nil {
			h := map[string]any{}
			for k, v := range cfg.Headers {
				h[k] = v
			}
			m["headers"] = h
		}
	} else {
		m["command"] = cfg.Command
		if cfg.Args != nil {
			args := make([]any, len(cfg.Args))
			for i, a := range cfg.Args {
				args[i] = a
			}
			m["args"] = args
		}
		if cfg.Env != nil {
			env := map[string]any{}
			for k, v := range cfg.Env {
				env[k] = v
			}
			m["env"] = env
		}
	}
	return m
}

// InjectEnvTokens enriches a server config with tokens from user-scope config and env vars.
func InjectEnvTokens(cfg ServerConfig, name string, userServers map[string]any) ServerConfig {
	out := cfg

	// Check user-scope config for existing tokens
	if userCfg, ok := userServers[name].(map[string]any); ok {
		if cfg.Type == "sse" {
			// SSE: inject headers
			if userHeaders, ok := userCfg["headers"].(map[string]any); ok {
				if out.Headers == nil {
					out.Headers = map[string]string{}
				}
				for k, v := range userHeaders {
					if s, ok := v.(string); ok && s != "" {
						if _, exists := out.Headers[k]; !exists {
							out.Headers[k] = s
						}
					}
				}
			}
		} else {
			// stdio: inject env vars
			if userEnv, ok := userCfg["env"].(map[string]any); ok {
				if out.Env == nil {
					out.Env = map[string]string{}
				}
				for k, v := range userEnv {
					if s, ok := v.(string); ok && s != "" {
						if _, exists := out.Env[k]; !exists {
							out.Env[k] = s
						}
					}
				}
			}
		}
	}

	// Also check environment variables for common tokens
	if cfg.Type != "sse" {
		tokenMap := map[string]string{
			"github":       "GITHUB_PERSONAL_ACCESS_TOKEN",
			"shodan":       "SHODAN_API_KEY",
			"brave-search": "BRAVE_API_KEY",
		}
		if envVar, ok := tokenMap[name]; ok {
			token := os.Getenv(envVar)
			if token != "" {
				if out.Env == nil {
					out.Env = map[string]string{}
				}
				if _, exists := out.Env[envVar]; !exists {
					out.Env[envVar] = token
				}
			}
		}
	}

	return out
}
