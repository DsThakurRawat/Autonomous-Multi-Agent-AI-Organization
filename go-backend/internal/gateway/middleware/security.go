package middleware

import (
	"bytes"
	"encoding/json"
	"os/exec"
	"strings"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

type SecurityRequest struct {
	Task    string `json:"task"`
	Content string `json:"content"`
}

type SecurityResponse struct {
	Safe    bool   `json:"safe"`
	Result  string `json:"result"`
	Message string `json:"message"`
}

// SecurityScrubber applies the Rust-based PII scrubber to all outgoing JSON responses.
func SecurityScrubber(binPath string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Process the request first
		err := c.Next()
		if err != nil {
			return err
		}

		// Only scrub JSON responses
		ctype := string(c.Response().Header.Peek("Content-Type"))
		if !strings.Contains(ctype, "application/json") {
			return nil
		}

		body := c.Response().Body()
		if len(body) == 0 {
			return nil
		}

		// Call Rust security-check
		req := SecurityRequest{
			Task:    "scrub",
			Content: string(body),
		}
		reqData, _ := json.Marshal(req)

		cmd := exec.Command(binPath)
		cmd.Stdin = bytes.NewReader(reqData)
		var out bytes.Buffer
		cmd.Stdout = &out

		if err := cmd.Run(); err != nil {
			logger.L().Error("security-check failed", zap.Error(err))
			return nil // Fail safe (original body)
		}

		var resp SecurityResponse
		if err := json.Unmarshal(out.Bytes(), &resp); err != nil {
			logger.L().Error("security-check unmarshal failed", zap.Error(err))
			return nil
		}

		// Update response body
		c.Response().SetBody([]byte(resp.Result))
		return nil
	}
}
