package proxy

import (
	"io"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"go.uber.org/zap"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// EgressProxy implements a simple HTTP/HTTPS proxy with hostname allowlisting.
type EgressProxy struct {
	addr      string
	allowlist map[string]bool
	mu        sync.RWMutex
	server    *http.Server
}

// NewEgressProxy creates a new proxy instance.
func NewEgressProxy(addr string, initialAllowlist []string) *EgressProxy {
	proxy := &EgressProxy{
		addr:      addr,
		allowlist: make(map[string]bool),
	}
	for _, host := range initialAllowlist {
		proxy.allowlist[strings.ToLower(host)] = true
	}
	return proxy
}

// Start runs the proxy server.
func (p *EgressProxy) Start() error {
	p.server = &http.Server{
		Addr:    p.addr,
		Handler: http.HandlerFunc(p.ServeHTTP),
		// Timeouts to prevent resource exhaustion
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  30 * time.Second,
	}

	logger.L().Info("egress proxy starting", zap.String("addr", p.addr), zap.Int("allowed_hosts", len(p.allowlist)))
	return p.server.ListenAndServe()
}

// ServeHTTP handles both normal HTTP proxy requests and HTTPS CONNECT tunnels.
func (p *EgressProxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	host := r.Host
	if strings.Contains(host, ":") {
		h, _, _ := net.SplitHostPort(host)
		host = h
	}

	if !p.isAllowed(host) {
		logger.L().Warn("egress blocked", zap.String("host", host), zap.String("method", r.Method), zap.String("url", r.URL.String()))
		http.Error(w, "Access blocked by AI Org Egress Proxy", http.StatusForbidden)
		return
	}

	if r.Method == http.MethodConnect {
		p.handleConnect(w, r)
	} else {
		p.handleHTTP(w, r)
	}
}

func (p *EgressProxy) isAllowed(host string) bool {
	p.mu.RLock()
	defer p.mu.RUnlock()
	
	host = strings.ToLower(host)
	// Check exact match
	if p.allowlist[host] {
		return true
	}
	
	// Check wildcard/suffix (e.g., .amazonaws.com)
	for allowed := range p.allowlist {
		if strings.HasPrefix(allowed, "*.") {
			suffix := allowed[1:]
			if strings.HasSuffix(host, suffix) {
				return true
			}
		}
	}
	
	return false
}

func (p *EgressProxy) handleConnect(w http.ResponseWriter, r *http.Request) {
	destConn, err := net.DialTimeout("tcp", r.Host, 10*time.Second)
	if err != nil {
		http.Error(w, err.Error(), http.StatusServiceUnavailable)
		return
	}
	defer destConn.Close()

	w.WriteHeader(http.StatusOK)
	
	hijacker, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "Hijacking not supported", http.StatusInternalServerError)
		return
	}
	
	clientConn, _, err := hijacker.Hijack()
	if err != nil {
		http.Error(w, err.Error(), http.StatusServiceUnavailable)
		return
	}
	defer clientConn.Close()

	// Bidirectional pipe
	var wg sync.WaitGroup
	wg.Add(2)
	
	go func() {
		defer wg.Done()
		_, _ = io.Copy(destConn, clientConn)
	}()
	
	go func() {
		defer wg.Done()
		_, _ = io.Copy(clientConn, destConn)
	}()
	
	wg.Wait()
}

func (p *EgressProxy) handleHTTP(w http.ResponseWriter, r *http.Request) {
	// Simple transparent proxying for HTTP
	transport := http.DefaultTransport
	
	// Prepare the request for forwarding
	outReq := new(http.Request)
	*outReq = *r
	outReq.RequestURI = "" // Must be empty for client requests

	resp, err := transport.RoundTrip(outReq)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	// Copy response headers
	for k, vv := range resp.Header {
		for _, v := range vv {
			w.Header().Add(k, v)
		}
	}
	
	w.WriteHeader(resp.StatusCode)
	_, _ = io.Copy(w, resp.Body)
}
