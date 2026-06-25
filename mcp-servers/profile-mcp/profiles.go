package main

import "os"

// ServerConfig represents a single MCP server configuration.
type ServerConfig struct {
	Type    string            `json:"type"`
	Command string            `json:"command,omitempty"`
	Args    []string          `json:"args,omitempty"`
	Env     map[string]string `json:"env,omitempty"`
	URL     string            `json:"url,omitempty"`
	Headers map[string]string `json:"headers,omitempty"`
}

// Profile represents an MCP server profile.
type Profile struct {
	Description string
	Servers     map[string]ServerConfig
}

func homeDir() string {
	h, _ := os.UserHomeDir()
	return h
}

// Profiles defines all available MCP server profiles.
var Profiles = map[string]Profile{
	"essential": {
		Description: "Core servers always loaded (auto-provisioned by SessionStart hook)",
		Servers: map[string]ServerConfig{
			"github": {
				Type:    "stdio",
				Command: "npx",
				Args:    []string{"-y", "@modelcontextprotocol/server-github"},
				Env:     map[string]string{},
			},
			"fetch": {
				Type:    "stdio",
				Command: "uvx",
				Args:    []string{"mcp-server-fetch"},
				Env:     map[string]string{},
			},
			"filesystem": {
				Type:    "stdio",
				Command: "/usr/local/bin/mcp-server-filesystem",
				Args:    []string{homeDir(), "/opt", "/tmp"},
				Env:     map[string]string{},
			},
			"memory": {
				Type:    "stdio",
				Command: "/usr/local/bin/mcp-server-memory",
				Args:    []string{},
				Env:     map[string]string{"MEMORY_FILE": homeDir() + "/.claude/mcp_data/memory.json"},
			},
			"git": {
				Type:    "stdio",
				Command: "uvx",
				Args:    []string{"mcp-server-git"},
				Env:     map[string]string{},
			},
			"sequential-thinking": {
				Type:    "stdio",
				Command: "npx",
				Args:    []string{"-y", "@modelcontextprotocol/server-sequential-thinking"},
				Env:     map[string]string{},
			},
			"sqlite": {
				Type:    "stdio",
				Command: "uvx",
				Args:    []string{"mcp-server-sqlite", "--db-path", homeDir() + "/.claude/mcp_data/claude.db"},
				Env:     map[string]string{},
			},
			"backlog-mcp": {
				Type:    "stdio",
				Command: homeDir() + "/.claude/mcp-servers/backlog-mcp/backlog-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"profile-mcp": {
				Type:    "stdio",
				Command: homeDir() + "/.claude/mcp-servers/profile-mcp/profile-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"doctor-mcp": {
				Type:    "stdio",
				Command: homeDir() + "/.claude/mcp-servers/doctor-mcp/doctor-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"gc-mcp": {
				Type:    "stdio",
				Command: homeDir() + "/.claude/mcp-servers/gc-mcp/gc-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"score-mcp": {
				Type:    "stdio",
				Command: homeDir() + "/.claude/mcp-servers/score-mcp/score-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"tools-mcp": {
				Type:    "stdio",
				Command: homeDir() + "/.claude/mcp-servers/tools-mcp/tools-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
		},
	},
	"security": {
		Description: "Security intelligence and scanning",
		Servers: map[string]ServerConfig{
			"shodan": {
				Type:    "stdio",
				Command: "/usr/local/bin/mcp-shodan",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"cve-intelligence": {
				Type:    "stdio",
				Command: "cve-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"security-detections": {
				Type:    "stdio",
				Command: "/usr/local/bin/security-detections-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"vulners": {
				Type:    "stdio",
				Command: "/opt/vulners-mcp/venv/bin/python",
				Args:    []string{"-m", "vulners_mcp"},
				Env:     map[string]string{},
			},
			"abusech": {
				Type:    "stdio",
				Command: "/opt/abusech-mcp/venv/bin/python",
				Args:    []string{"-m", "abusech_mcp"},
				Env:     map[string]string{},
			},
			"hexstrike": {
				Type:    "stdio",
				Command: "hexstrike_server",
				Args:    []string{},
				Env:     map[string]string{"PYTHONUNBUFFERED": "1"},
			},
		},
	},
	"osint": {
		Description: "OSINT and reconnaissance",
		Servers: map[string]ServerConfig{
			"brave-search": {
				Type:    "stdio",
				Command: "/usr/local/bin/mcp-server-brave-search",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"maigret": {
				Type:    "stdio",
				Command: "/usr/local/bin/mcp-maigret",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"spiderfoot-mcp": {
				Type:    "stdio",
				Command: "/opt/spiderfoot-mcp/venv/bin/python",
				Args:    []string{"-m", "spiderfoot_mcp"},
				Env:     map[string]string{},
			},
			"bbot": {
				Type:    "stdio",
				Command: homeDir() + "/.local/bin/bbot-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"censys-asm": {
				Type:    "sse",
				URL:     "https://mcp.asm.censys.io/asm/mcp/",
				Headers: map[string]string{},
			},
			"censys-platform": {
				Type:    "sse",
				URL:     "https://mcp.platform.censys.io/platform/mcp/",
				Headers: map[string]string{},
			},
			"wayback": {
				Type:    "stdio",
				Command: "npx",
				Args:    []string{"-y", "mcp-wayback-machine"},
				Env:     map[string]string{},
			},
		},
	},
	"pentest": {
		Description: "Penetration testing tools",
		Servers: map[string]ServerConfig{
			"pentest-mcp": {
				Type:    "stdio",
				Command: "/usr/local/bin/pentest-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"mcp-kali-server": {
				Type:    "stdio",
				Command: "/usr/bin/kali-server-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"PentestAgent": {
				Type:    "stdio",
				Command: "/opt/PentestAgent/venv/bin/python",
				Args:    []string{"/opt/PentestAgent/main.py"},
				Env:     map[string]string{"PYTHONUNBUFFERED": "1"},
			},
		},
	},
	"reverse": {
		Description: "Reverse engineering and forensics",
		Servers: map[string]ServerConfig{
			"ghidra-mcp": {
				Type:    "stdio",
				Command: "python3",
				Args:    []string{"-m", "ghidra_mcp"},
				Env:     map[string]string{},
			},
			"volatility-mcp": {
				Type:    "stdio",
				Command: "/opt/Volatility-MCP-Server/venv/bin/python",
				Args:    []string{"/opt/Volatility-MCP-Server/volatility_mcp_server.py"},
				Env:     map[string]string{"PYTHONPATH": "/opt/Volatility-MCP-Server/volatility3"},
			},
			"yaraflux": {
				Type:    "stdio",
				Command: "/opt/YaraFlux/venv/bin/python",
				Args:    []string{"-m", "yaraflux_mcp_server"},
				Env:     map[string]string{"PYTHONUNBUFFERED": "1"},
			},
		},
	},
	"devops": {
		Description: "Infrastructure and DevOps",
		Servers: map[string]ServerConfig{
			"kubernetes": {
				Type:    "stdio",
				Command: "/usr/local/bin/kubernetes-mcp-server",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"terraform": {
				Type:    "stdio",
				Command: "docker",
				Args:    []string{"run", "--rm", "-i", "--pull", "always", "hashicorp/terraform-mcp-server"},
				Env:     map[string]string{},
			},
			"mcp-grafana": {
				Type:    "stdio",
				Command: "/usr/local/bin/mcp-grafana",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"gitlab-mcp": {
				Type:    "stdio",
				Command: "/usr/local/bin/gitlab-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"pd-tools": {
				Type:    "stdio",
				Command: "node",
				Args:    []string{"/opt/pd-tools-mcp/build/index.js"},
				Env:     map[string]string{},
			},
		},
	},
	"browser": {
		Description: "Browser automation",
		Servers: map[string]ServerConfig{
			"playwright": {
				Type:    "stdio",
				Command: "/usr/local/bin/playwright-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"puppeteer": {
				Type:    "stdio",
				Command: "npx",
				Args:    []string{"-y", "@modelcontextprotocol/server-puppeteer"},
				Env:     map[string]string{},
			},
		},
	},
	"network": {
		Description: "Network infrastructure",
		Servers: map[string]ServerConfig{
			"mikrotik": {
				Type:    "stdio",
				Command: "/usr/local/bin/mikrotik-mcp-server",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"opnsense": {
				Type:    "stdio",
				Command: "/usr/local/bin/opnsense-mcp-server",
				Args:    []string{},
				Env:     map[string]string{},
			},
		},
	},
	"intel": {
		Description: "Threat intelligence and enrichment",
		Servers: map[string]ServerConfig{
			"virustotal": {
				Type:    "stdio",
				Command: "npx",
				Args:    []string{"-y", "mcp-virustotal"},
				Env:     map[string]string{},
			},
			"greynoise": {
				Type:    "stdio",
				Command: "npx",
				Args:    []string{"-y", "greynoise-mcp"},
				Env:     map[string]string{},
			},
			"ipinfo": {
				Type:    "stdio",
				Command: "uvx",
				Args:    []string{"mcp-server-ipinfo"},
				Env:     map[string]string{},
			},
			"threatintel": {
				Type:    "stdio",
				Command: "npx",
				Args:    []string{"-y", "mcp-threatintel-server"},
				Env:     map[string]string{},
			},
			"censys-threat-hunting": {
				Type:    "sse",
				URL:     "https://mcp.platform.censys.io/threat-hunting/mcp/",
				Headers: map[string]string{},
			},
		},
	},
	"dfir": {
		Description: "Digital forensics and incident response",
		Servers: map[string]ServerConfig{
			"velociraptor-mcp": {
				Type:    "stdio",
				Command: "/opt/velociraptor-mcp-server/venv/bin/python",
				Args:    []string{"-m", "velociraptor_mcp_server"},
				Env:     map[string]string{"PYTHONUNBUFFERED": "1"},
			},
			"WireMCP": {
				Type:    "stdio",
				Command: "node",
				Args:    []string{"/opt/WireMCP/index.js"},
				Env:     map[string]string{},
			},
			"suricata": {
				Type:    "stdio",
				Command: "/opt/SuricataMCP/venv/bin/python",
				Args:    []string{"/opt/SuricataMCP/suricata-mcp.py"},
				Env:     map[string]string{"PYTHONUNBUFFERED": "1"},
			},
			"wazuh-mcp": {
				Type:    "stdio",
				Command: "/opt/Wazuh-MCP-Server/venv/bin/python",
				Args:    []string{"-m", "wazuh_mcp_server"},
				Env:     map[string]string{"PYTHONUNBUFFERED": "1"},
			},
		},
	},
	"case-mgmt": {
		Description: "Case management and threat sharing",
		Servers: map[string]ServerConfig{
			"thehive-mcp": {
				Type:    "stdio",
				Command: "/opt/TheHiveMCP/thehive-mcp",
				Args:    []string{},
				Env:     map[string]string{},
			},
			"misp-mcp": {
				Type:    "stdio",
				Command: "/opt/MISP-MCP-SERVER/venv/bin/python",
				Args:    []string{"/opt/MISP-MCP-SERVER/misp_server.py"},
				Env:     map[string]string{"PYTHONUNBUFFERED": "1"},
			},
		},
	},
}

// ProfileNames returns sorted profile names for consistent output.
func ProfileNames() []string {
	return []string{
		"essential", "security", "osint", "pentest", "reverse",
		"devops", "browser", "network", "intel", "dfir", "case-mgmt",
	}
}

// EssentialServerNames returns the names of essential servers.
func EssentialServerNames() []string {
	names := make([]string, 0, len(Profiles["essential"].Servers))
	for name := range Profiles["essential"].Servers {
		names = append(names, name)
	}
	return names
}
