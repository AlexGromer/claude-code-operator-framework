package main

import (
	"fmt"
	"os"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

const version = "0.1.0"

func main() {
	s := server.NewMCPServer(
		"backlog-mcp",
		version,
		server.WithToolCapabilities(false),
	)

	registerTools(s)

	if os.Getenv("BACKLOG_MCP_DEBUG") != "" {
		fmt.Fprintf(os.Stderr, "backlog-mcp %s started (tools: %d)\n", version, 8)
	}

	if err := server.ServeStdio(s); err != nil {
		fmt.Fprintf(os.Stderr, "fatal: %v\n", err)
		os.Exit(1)
	}
}

// ServerInfo returns the MCP server info for testing.
func ServerInfo() mcp.Implementation {
	return mcp.Implementation{
		Name:    "backlog-mcp",
		Version: version,
	}
}
