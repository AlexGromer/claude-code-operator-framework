package main

import (
	"context"
	"fmt"
	"os"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

const version = "1.0.0"

func main() {
	// CLI mode: --scope-track <file_path> or --scope-status
	if len(os.Args) >= 2 {
		switch os.Args[1] {
		case "--scope-track":
			if len(os.Args) < 3 {
				fmt.Fprintf(os.Stderr, "usage: tools-mcp --scope-track <file_path>\n")
				os.Exit(1)
			}
			req := mcp.CallToolRequest{}
			req.Params.Arguments = map[string]any{"file_path": os.Args[2]}
			result, _ := handleScopeTrack(context.Background(), req)
			if result != nil && len(result.Content) > 0 {
				if tc, ok := result.Content[0].(mcp.TextContent); ok {
					fmt.Print(tc.Text)
				}
			}
			return
		case "--scope-status":
			req := mcp.CallToolRequest{}
			req.Params.Arguments = map[string]any{}
			result, _ := handleScopeStatus(context.Background(), req)
			if result != nil && len(result.Content) > 0 {
				if tc, ok := result.Content[0].(mcp.TextContent); ok {
					fmt.Print(tc.Text)
				}
			}
			return
		}
	}

	// MCP server mode (default)
	s := server.NewMCPServer(
		"tools-mcp",
		version,
		server.WithToolCapabilities(false),
	)

	registerTools(s)

	if os.Getenv("TOOLS_MCP_DEBUG") != "" {
		fmt.Fprintf(os.Stderr, "tools-mcp %s started (tools: %d)\n", version, 15)
	}

	if err := server.ServeStdio(s); err != nil {
		fmt.Fprintf(os.Stderr, "fatal: %v\n", err)
		os.Exit(1)
	}
}

// ServerInfo returns the MCP server info for testing.
func ServerInfo() mcp.Implementation {
	return mcp.Implementation{
		Name:    "tools-mcp",
		Version: version,
	}
}
