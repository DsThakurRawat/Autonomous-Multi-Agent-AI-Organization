package main

import (
	"os"
	"strings"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/proxy"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

func main() {
	addr := os.Getenv("PROXY_ADDR")
	if addr == "" {
		addr = ":8080"
	}

	// Default allowlist for production-grade AI Organization
	defaultAllowlist := []string{
		"api.openai.com",
		"api.anthropic.com",
		"*.amazonaws.com", // For Bedrock and AWS services
		"generativelanguage.googleapis.com", // For Google Gemini
		"github.com",
		"api.github.com",
		"pypi.org",
		"files.pythonhosted.org",
		"registry.npmjs.org",
		"registry.terraform.io",
	}

	// Allow overriding via ENV
	envAllowlist := os.Getenv("PROXY_ALLOWLIST")
	if envAllowlist != "" {
		defaultAllowlist = append(defaultAllowlist, strings.Split(envAllowlist, ",")...)
	}

	p := proxy.NewEgressProxy(addr, defaultAllowlist)
	if err := p.Start(); err != nil {
		logger.L().Fatal("proxy server failed")
	}
}
