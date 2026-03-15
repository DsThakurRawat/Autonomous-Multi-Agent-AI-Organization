package mcp

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

// MCP server instance
var MCPServer *server.MCPServer

// Base directory for allowed file operations
var allowedBasePath string

func InitServer(basePath string) *server.MCPServer {
	// create the server instance
	s := server.NewMCPServer(
		"Proximus-Nova-Local-Agent",
		"1.0.0",
	)

	allowedBasePath, _ = filepath.Abs(basePath)

	// Add tool: read_file
	readFileTool := mcp.NewTool("read_file",
		mcp.WithDescription("Read contents of a file from the local file system. Path must be relative to the allowed base path."),
		mcp.WithString("path",
			mcp.Required(),
			mcp.Description("Relative path to the file"),
		),
	)

	s.AddTool(readFileTool, handleReadFile)

	// Add tool: write_file
	writeFileTool := mcp.NewTool("write_file",
		mcp.WithDescription("Write contents to a file on the local file system. Path must be relative to the allowed base path."),
		mcp.WithString("path",
			mcp.Required(),
			mcp.Description("Relative path to the file"),
		),
		mcp.WithString("content",
			mcp.Required(),
			mcp.Description("The content to write"),
		),
	)

	s.AddTool(writeFileTool, handleWriteFile)

	// Add tool: list_files
	listFilesTool := mcp.NewTool("list_files",
		mcp.WithDescription("List files in a directory on the local file system."),
		mcp.WithString("directory",
			mcp.Description("Relative path to the directory (empty for base path)"),
		),
	)

	s.AddTool(listFilesTool, handleListFiles)

	MCPServer = s
	return s
}

// Security: ensures the target path is inside allowedBasePath
func getSecurePath(relPath string) (string, error) {
	target := filepath.Join(allowedBasePath, filepath.Clean(relPath))
	absTarget, err := filepath.Abs(target)
	if err != nil {
		return "", err
	}

	// Basic sandbox check
	if len(absTarget) < len(allowedBasePath) || absTarget[:len(allowedBasePath)] != allowedBasePath {
		return "", fmt.Errorf("path access denied (outside sandbox)")
	}

	return absTarget, nil
}

func handleReadFile(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	path, err := req.RequireString("path")
	if err != nil {
		return mcp.NewToolResultError("path is required"), nil
	}

	securePath, err := getSecurePath(path)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	data, err := os.ReadFile(securePath)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to read file: %v", err)), nil
	}

	return mcp.NewToolResultText(string(data)), nil
}

func handleWriteFile(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	path, err := req.RequireString("path")
	if err != nil {
		return mcp.NewToolResultError("path is required"), nil
	}
	content, err := req.RequireString("content")
	if err != nil {
		return mcp.NewToolResultError("content is required"), nil
	}

	securePath, err := getSecurePath(path)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	// Ensure directory exists
	err = os.MkdirAll(filepath.Dir(securePath), 0755)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to create directories: %v", err)), nil
	}

	err = os.WriteFile(securePath, []byte(content), 0644)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to write file: %v", err)), nil
	}

	return mcp.NewToolResultText(fmt.Sprintf("Successfully wrote to %s", path)), nil
}

func handleListFiles(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	dir := req.GetString("directory", "")

	securePath, err := getSecurePath(dir)
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}

	entries, err := os.ReadDir(securePath)
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("Failed to list directory: %v", err)), nil
	}

	result := ""
	for _, entry := range entries {
		info := ""
		if entry.IsDir() {
			info = "/"
		}
		result += fmt.Sprintf("- %s%s\n", entry.Name(), info)
	}

	if result == "" {
		result = "(empty directory)"
	}

	return mcp.NewToolResultText(result), nil
}
