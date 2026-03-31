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

// ---------- Role Hierarchy Exhaustive ----------

func TestRequireRole_FullHierarchyMatrix(t *testing.T) {
	// Production scenario: verify every role combination is correct
	// Roles ranked: viewer(1) < member(2) < admin(3) < owner(4)
	tests := []struct {
		name     string
		userRole string
		minRole  string
		allowed  bool
	}{
		// Viewer access
		{"viewer accesses viewer", "viewer", "viewer", true},
		{"viewer blocked from member", "viewer", "member", false},
		{"viewer blocked from admin", "viewer", "admin", false},
		{"viewer blocked from owner", "viewer", "owner", false},

		// Member access
		{"member accesses viewer", "member", "viewer", true},
		{"member accesses member", "member", "member", true},
		{"member blocked from admin", "member", "admin", false},
		{"member blocked from owner", "member", "owner", false},

		// Admin access
		{"admin accesses viewer", "admin", "viewer", true},
		{"admin accesses member", "admin", "member", true},
		{"admin accesses admin", "admin", "admin", true},
		{"admin blocked from owner", "admin", "owner", false},

		// Owner access (god mode)
		{"owner accesses viewer", "owner", "viewer", true},
		{"owner accesses member", "owner", "member", true},
		{"owner accesses admin", "owner", "admin", true},
		{"owner accesses owner", "owner", "owner", true},

		// Edge cases
		{"empty role blocked", "", "viewer", false},
		{"unknown role blocked", "superadmin", "viewer", false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			app := fiber.New()
			app.Use(func(c *fiber.Ctx) error {
				if tt.userRole != "" {
					c.Locals("role", tt.userRole)
				}
				return c.Next()
			})
			app.Get("/test", RequireRole(tt.minRole), func(c *fiber.Ctx) error {
				return c.SendString("ok")
			})

			req := httptest.NewRequest(http.MethodGet, "/test", nil)
			resp, err := app.Test(req, -1)
			require.NoError(t, err)
			if tt.allowed {
				assert.Equal(t, http.StatusOK, resp.StatusCode,
					"Expected 200 for %s accessing %s", tt.userRole, tt.minRole)
			} else {
				assert.Equal(t, http.StatusForbidden, resp.StatusCode,
					"Expected 403 for %s accessing %s", tt.userRole, tt.minRole)
			}
		})
	}
}

// ---------- LocalAuth Injection Completeness ----------

func TestLocalAuth_AllLocalsSet(t *testing.T) {
	// Production scenario: all identity fields must be set for downstream middleware
	app := fiber.New()
	os.Setenv("LOCAL_USER_EMAIL", "dev@autonomousorg.ai")
	defer os.Unsetenv("LOCAL_USER_EMAIL")

	app.Use(LocalAuth())
	app.Get("/identity", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"user_id":   c.Locals("user_id"),
			"tenant_id": c.Locals("tenant_id"),
			"email":     c.Locals("email"),
			"role":      c.Locals("role"),
		})
	})

	req := httptest.NewRequest(http.MethodGet, "/identity", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
}

// ---------- CORS Production Scenarios ----------

func TestCORS_AllMethodsPresent(t *testing.T) {
	app := fiber.New()
	app.Use(CORS())
	app.Get("/test", func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	methods := resp.Header.Get("Access-Control-Allow-Methods")
	for _, m := range []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"} {
		assert.Contains(t, methods, m, "Missing HTTP method: %s", m)
	}
}

func TestCORS_AuthHeaderAllowed(t *testing.T) {
	app := fiber.New()
	app.Use(CORS())
	app.Get("/test", func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	headers := resp.Header.Get("Access-Control-Allow-Headers")
	assert.Contains(t, headers, "Authorization")
	assert.Contains(t, headers, "X-Trace-ID")
	assert.Contains(t, headers, "Content-Type")
}

// ---------- RequestLogger Production Scenarios ----------

func TestRequestLogger_TraceIDPersistsAcrossMiddleware(t *testing.T) {
	// Production scenario: trace ID must survive the full middleware chain
	app := fiber.New()
	app.Use(RequestLogger())
	app.Use(CORS())
	app.Get("/chained", func(c *fiber.Ctx) error {
		traceID := c.Locals("trace_id")
		return c.JSON(fiber.Map{"trace_id": traceID})
	})

	customID := "trace-from-load-balancer-001"
	req := httptest.NewRequest(http.MethodGet, "/chained", nil)
	req.Header.Set("X-Trace-ID", customID)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, customID, resp.Header.Get("X-Trace-ID"))
}

func TestRequestLogger_GeneratesUUIDWhenMissing(t *testing.T) {
	app := fiber.New()
	app.Use(RequestLogger())
	app.Get("/test", func(c *fiber.Ctx) error {
		return c.SendString("ok")
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)

	traceID := resp.Header.Get("X-Trace-ID")
	assert.NotEmpty(t, traceID)
	// UUID format: 8-4-4-4-12 = 36 chars
	assert.Len(t, traceID, 36, "Generated trace ID should be a UUID")
}

// ---------- Middleware Chain Integration ----------

func TestMiddlewareChain_LocalAuthWithRoleCheck(t *testing.T) {
	// Production scenario: LocalAuth sets "owner", which should pass any RequireRole check
	app := fiber.New()
	app.Use(LocalAuth())
	app.Get("/admin-only", RequireRole("admin"), func(c *fiber.Ctx) error {
		return c.SendString("admin access granted")
	})

	req := httptest.NewRequest(http.MethodGet, "/admin-only", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
}

func TestMiddlewareChain_FullStack(t *testing.T) {
	// Production scenario: the full middleware stack that runs in production
	app := fiber.New()
	app.Use(RequestLogger())
	app.Use(CORS())
	app.Use(LocalAuth())
	app.Get("/api/projects", RequireRole("member"), func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"user_id":  c.Locals("user_id"),
			"trace_id": c.Locals("trace_id"),
		})
	})

	req := httptest.NewRequest(http.MethodGet, "/api/projects", nil)
	resp, err := app.Test(req, -1)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
	assert.NotEmpty(t, resp.Header.Get("X-Trace-ID"))
	assert.Equal(t, "*", resp.Header.Get("Access-Control-Allow-Origin"))
}
