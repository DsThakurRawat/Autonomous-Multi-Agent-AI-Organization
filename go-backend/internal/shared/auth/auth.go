// Package auth provides JWT signing/verification and Google OAuth2 helpers.
// Uses RS256 asymmetric signing — private key is never exposed to clients.
package auth

import (
	"context"
	"crypto/rsa"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/config"
)

// Claims is the JWT payload embedded in every access token.
type Claims struct {
	UserID    string `json:"uid"`
	TenantID  string `json:"tid"`
	Email     string `json:"email"`
	Role      string `json:"role"`
	TokenType string `json:"typ"` // "access" or "refresh"
	jwt.RegisteredClaims
}

// Service handles JWT and Google OAuth operations.
type Service struct {
	privateKey    *rsa.PrivateKey
	publicKey     *rsa.PublicKey
	accessExpiry  time.Duration
	refreshExpiry time.Duration
	oauthConfig   *oauth2.Config
}

// New loads RSA keys from disk and builds the auth service.
func New(cfg *config.AuthConfig) (*Service, error) {
	// Load private key
	privBytes, err := os.ReadFile(cfg.JWTPrivateKeyPath)
	if err != nil {
		return nil, fmt.Errorf("auth: read private key: %w", err)
	}
	privKey, err := jwt.ParseRSAPrivateKeyFromPEM(privBytes)
	if err != nil {
		return nil, fmt.Errorf("auth: parse private key: %w", err)
	}

	// Load public key
	pubBytes, err := os.ReadFile(cfg.JWTPublicKeyPath)
	if err != nil {
		return nil, fmt.Errorf("auth: read public key: %w", err)
	}
	pubKey, err := jwt.ParseRSAPublicKeyFromPEM(pubBytes)
	if err != nil {
		return nil, fmt.Errorf("auth: parse public key: %w", err)
	}

	oauthCfg := &oauth2.Config{
		ClientID:     cfg.GoogleClientID,
		ClientSecret: cfg.GoogleClientSecret,
		RedirectURL:  cfg.GoogleRedirectURL,
		Scopes: []string{
			"openid",
			"https://www.googleapis.com/auth/userinfo.email",
			"https://www.googleapis.com/auth/userinfo.profile",
		},
		Endpoint: google.Endpoint,
	}

	return &Service{
		privateKey:    privKey,
		publicKey:     pubKey,
		accessExpiry:  cfg.JWTAccessExpiry,
		refreshExpiry: cfg.JWTRefreshExpiry,
		oauthConfig:   oauthCfg,
	}, nil
}

// IssueTokens creates and signs an access and refresh JWT for the given user.
func (s *Service) IssueTokens(userID, tenantID, email, role string) (string, string, error) {
	now := time.Now()
	
	createToken := func(typ string, exp time.Duration) (string, error) {
		claims := Claims{
			UserID:    userID,
			TenantID:  tenantID,
			Email:     email,
			Role:      role,
			TokenType: typ,
			RegisteredClaims: jwt.RegisteredClaims{
				Subject:   userID,
				IssuedAt:  jwt.NewNumericDate(now),
				ExpiresAt: jwt.NewNumericDate(now.Add(exp)),
				Issuer:    "autonomous-org",
			},
		}

		token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
		return token.SignedString(s.privateKey)
	}

	accessToken, err := createToken("access", s.accessExpiry)
	if err != nil {
		return "", "", fmt.Errorf("auth: sign access token: %w", err)
	}

	refreshToken, err := createToken("refresh", s.refreshExpiry)
	if err != nil {
		return "", "", fmt.Errorf("auth: sign refresh token: %w", err)
	}

	return accessToken, refreshToken, nil
}

// ValidateToken parses and validates a JWT string.
// Returns Claims on success, error if expired/invalid.
func (s *Service) ValidateToken(tokenStr string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenStr, &Claims{}, func(t *jwt.Token) (any, error) {
		if _, ok := t.Method.(*jwt.SigningMethodRSA); !ok {
			return nil, fmt.Errorf("auth: unexpected signing method: %v", t.Header["alg"])
		}
		return s.publicKey, nil
	}, jwt.WithExpirationRequired())

	if err != nil {
		return nil, fmt.Errorf("auth: invalid token: %w", err)
	}

	claims, ok := token.Claims.(*Claims)
	if !ok {
		return nil, fmt.Errorf("auth: invalid claims type")
	}
	return claims, nil
}

// GoogleAuthURL returns the OAuth2 redirect URL with a state token.
func (s *Service) GoogleAuthURL(state string) string {
	return s.oauthConfig.AuthCodeURL(state, oauth2.AccessTypeOffline)
}

// GoogleUserInfo exchanges an OAuth2 code for user info.
// Returns (googleSub, email, displayName, error).
func (s *Service) GoogleUserInfo(ctx context.Context, code string) (sub, email, name string, err error) {
	token, err := s.oauthConfig.Exchange(ctx, code)
	if err != nil {
		return "", "", "", fmt.Errorf("auth: exchange code: %w", err)
	}

	client := s.oauthConfig.Client(ctx, token)
	resp, err := client.Get("https://www.googleapis.com/oauth2/v3/userinfo")
	if err != nil {
		return "", "", "", fmt.Errorf("auth: get userinfo: %w", err)
	}
	defer resp.Body.Close()

	var info struct {
		Sub   string `json:"sub"`
		Email string `json:"email"`
		Name  string `json:"name"`
	}
	if err := parseJSON(resp.Body, &info); err != nil {
		return "", "", "", fmt.Errorf("auth: parse userinfo: %w", err)
	}

	return info.Sub, info.Email, info.Name, nil
}

func parseJSON(r io.Reader, v any) error {
	return json.NewDecoder(r).Decode(v)
}
