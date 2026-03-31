package middleware

import (
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gofiber/fiber/v2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ---------- LocalMode() ----------

func TestLocalMode_Enabled(t *testing.T) {
	os.Setenv("AUTH_DISABLED", "true")
	defer os.Unsetenv("AUTH_DISABLED")
	assert.True(t, LocalMode())
}

func TestLocalMode_CaseInsensitive(t *testing.T) {
	os.Setenv("AUTH_DISABLED", "TRUE")
	defer os.Unsetenv("AUTH_DISABLED")
	assert.True(t, LocalMode())
}

func TestLocalMode_Disabled(t *testing.T) {
	os.Setenv("AUTH_DISABLED", "false")
	defer os.Unsetenv("AUTH_DISABLED")
	assert.False(t, LocalMode())
}

func TestLocalMode_Unset(t *testing.T) {
	os.Unsetenv("AUTH_DISABLED")
	assert.False(t, LocalMode())
}

// ---------- LocalAuth ----------

func TestLocalAuth_InjectsLocals(t *testing.T) {
	app := fiber.New()
	app.Use(LocalAuth())
	app.Get("/test", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"user_id":   c.Locals("user_id"),
			"tenant_id": c.Locals("tenant_id"),
			"role":      c.Locals("role"),
		})
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
}

// ---------- RequireRole ----------

func TestRequireRole_OwnerAccessesAll(t *testing.T) {
	app := fiber.New()
	app.Use(func(c *fiber.Ctx) error {
		c.Locals("role", "owner")
		return c.Next()
	})
	app.Get("/admin", RequireRole("admin"), func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	req := httptest.NewRequest(http.MethodGet, "/admin", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
}

func TestRequireRole_ViewerBlockedFromAdmin(t *testing.T) {
	app := fiber.New()
	app.Use(func(c *fiber.Ctx) error {
		c.Locals("role", "viewer")
		return c.Next()
	})
	app.Get("/admin", RequireRole("admin"), func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	req := httptest.NewRequest(http.MethodGet, "/admin", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusForbidden, resp.StatusCode)
}

func TestRequireRole_MemberAccessesMember(t *testing.T) {
	app := fiber.New()
	app.Use(func(c *fiber.Ctx) error {
		c.Locals("role", "member")
		return c.Next()
	})
	app.Get("/data", RequireRole("member"), func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	req := httptest.NewRequest(http.MethodGet, "/data", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
}

func TestRequireRole_NoRoleIsForbidden(t *testing.T) {
	app := fiber.New()
	// No role set in locals
	app.Get("/admin", RequireRole("admin"), func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	req := httptest.NewRequest(http.MethodGet, "/admin", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusForbidden, resp.StatusCode)
}

// ---------- CORS ----------

func TestCORS_SetsHeaders(t *testing.T) {
	app := fiber.New()
	app.Use(CORS())
	app.Get("/test", func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, "*", resp.Header.Get("Access-Control-Allow-Origin"))
	assert.Contains(t, resp.Header.Get("Access-Control-Allow-Methods"), "GET")
	assert.Contains(t, resp.Header.Get("Access-Control-Allow-Headers"), "Authorization")
}

func TestCORS_OptionsReturnsNoContent(t *testing.T) {
	app := fiber.New()
	app.Use(CORS())
	app.Options("/test", func(c *fiber.Ctx) error {
		return c.SendString("should not reach")
	})

	req := httptest.NewRequest(http.MethodOptions, "/test", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusNoContent, resp.StatusCode)
}

// ---------- RequestLogger ----------

func TestRequestLogger_InjectsTraceID(t *testing.T) {
	app := fiber.New()
	app.Use(RequestLogger())
	app.Get("/test", func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
	// Should get a trace ID back in response headers
	assert.NotEmpty(t, resp.Header.Get("X-Trace-ID"))
}

func TestRequestLogger_UsesProvidedTraceID(t *testing.T) {
	app := fiber.New()
	app.Use(RequestLogger())
	app.Get("/test", func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	customID := "custom-trace-12345"
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("X-Trace-ID", customID)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, customID, resp.Header.Get("X-Trace-ID"))
}
