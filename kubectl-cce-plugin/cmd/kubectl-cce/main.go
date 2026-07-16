package main

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"crypto/tls"
	"encoding/hex"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"os/signal"
	"sort"
	"strings"
	"syscall"
	"time"
)

const (
	defaultRegion = "cn-north-4"
)

var unsupportedStreamingCommands = map[string]bool{
	"attach":       true,
	"exec":         true,
	"port-forward": true,
}

type config struct {
	clusterID     string
	region        string
	endpoint      string
	ak            string
	sk            string
	securityToken string
	iamToken      string
	kubectl       string
	insecureTLS   bool
	debug         bool
}

func main() {
	if err := run(os.Args[1:]); err != nil {
		var exitErr kubectlExitError
		if errors.As(err, &exitErr) {
			os.Exit(exitErr.code)
		}
		fmt.Fprintf(os.Stderr, "kubectl-cce: %v\n", err)
		os.Exit(2)
	}
}

func run(args []string) error {
	fs := flag.NewFlagSet("kubectl cce", flag.ContinueOnError)
	fs.SetOutput(os.Stderr)
	printProxyURL := fs.Bool("print-proxy-url", false, "print a temporary local proxy URL and exit")
	insecureTLS := fs.Bool("cce-insecure-upstream-tls", false, "skip TLS verification for the upstream CCE endpoint")
	if err := fs.Parse(args); err != nil {
		return err
	}

	cfg := loadConfig()
	cfg.insecureTLS = *insecureTLS
	if err := cfg.validate(); err != nil {
		return err
	}

	proxy, err := newProxy(cfg)
	if err != nil {
		return err
	}
	defer proxy.close(context.Background())

	if *printProxyURL {
		fmt.Println(proxy.url())
		return nil
	}

	kubectlArgs := fs.Args()
	if len(kubectlArgs) == 0 {
		return errors.New("pass a kubectl command, for example: kubectl cce get pods -n default")
	}
	if command := findUnsupportedStreamingCommand(kubectlArgs); command != "" {
		return fmt.Errorf("kubectl %s is not supported in this MVP because it needs a streaming connection", command)
	}

	return runKubectlThroughProxy(proxy, cfg, kubectlArgs)
}

func loadConfig() config {
	cfg := config{
		clusterID:     os.Getenv("CCE_CLUSTER_ID"),
		region:        envDefault("CCE_REGION", defaultRegion),
		endpoint:      os.Getenv("CCE_ENDPOINT"),
		ak:            firstEnv("HUAWEICLOUD_SDK_AK", "HUAWEI_CLOUD_AK", "HW_ACCESS_KEY"),
		sk:            firstEnv("HUAWEICLOUD_SDK_SK", "HUAWEI_CLOUD_SK", "HW_SECRET_KEY"),
		securityToken: firstEnv("HUAWEICLOUD_SECURITY_TOKEN", "HUAWEI_CLOUD_SECURITY_TOKEN", "HW_SECURITY_TOKEN"),
		iamToken:      os.Getenv("HUAWEI_IAM_TOKEN"),
		kubectl:       envDefault("KUBECTL_BIN", "kubectl"),
		debug:         os.Getenv("CCE_PROXY_DEBUG") != "",
	}
	if path, err := exec.LookPath(cfg.kubectl); err == nil {
		cfg.kubectl = path
	}
	return cfg
}

func (c config) validate() error {
	if c.endpoint == "" && c.clusterID == "" {
		return errors.New("CCE_CLUSTER_ID is required unless CCE_ENDPOINT is set")
	}
	if c.ak != "" && c.sk != "" {
		return nil
	}
	if c.iamToken != "" {
		return nil
	}
	return errors.New("set HUAWEICLOUD_SDK_AK and HUAWEICLOUD_SDK_SK, or set HUAWEI_IAM_TOKEN")
}

func (c config) upstreamHost() string {
	if c.endpoint != "" {
		host := strings.TrimSuffix(c.endpoint, "/")
		host = strings.TrimPrefix(host, "https://")
		host = strings.TrimPrefix(host, "http://")
		return host
	}
	return fmt.Sprintf("%s.cce.%s.myhuaweicloud.com", c.clusterID, c.region)
}

func (c config) useAKSK() bool {
	return c.ak != "" && c.sk != ""
}

type localProxy struct {
	server   *http.Server
	listener net.Listener
}

type kubectlExitError struct {
	code int
}

func (e kubectlExitError) Error() string {
	return fmt.Sprintf("kubectl exited with status %d", e.code)
}

func newProxy(cfg config) (*localProxy, error) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return nil, err
	}
	p := &localProxy{listener: listener}
	p.server = &http.Server{
		Handler:           proxyHandler(cfg),
		ReadHeaderTimeout: 30 * time.Second,
	}
	go func() {
		if err := p.server.Serve(listener); err != nil && !errors.Is(err, http.ErrServerClosed) {
			fmt.Fprintf(os.Stderr, "kubectl-cce: proxy stopped unexpectedly: %v\n", err)
		}
	}()
	return p, nil
}

func (p *localProxy) url() string {
	return "http://" + p.listener.Addr().String()
}

func (p *localProxy) close(ctx context.Context) error {
	shutdownCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	return p.server.Shutdown(shutdownCtx)
}

func proxyHandler(cfg config) http.Handler {
	upstreamHost := cfg.upstreamHost()
	client := &http.Client{
		Timeout: 0,
		Transport: &http.Transport{
			Proxy: http.ProxyFromEnvironment,
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: cfg.insecureTLS, //nolint:gosec
			},
		},
	}

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		defer r.Body.Close()

		upstreamURL := url.URL{
			Scheme:   "https",
			Host:     upstreamHost,
			Path:     r.URL.Path,
			RawQuery: r.URL.RawQuery,
		}
		req, err := http.NewRequestWithContext(r.Context(), r.Method, upstreamURL.String(), bytes.NewReader(body))
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadGateway)
			return
		}
		copyHeaders(req.Header, r.Header)
		removeHopByHopHeaders(req.Header)
		req.Host = upstreamHost
		req.Header.Set("Host", upstreamHost)

		if cfg.useAKSK() {
			applyAKSKSignature(req, body, cfg)
		} else {
			req.Header.Set("X-Auth-Token", cfg.iamToken)
			req.Header.Del("Authorization")
		}

		if cfg.debug {
			fmt.Fprintf(os.Stderr, "kubectl-cce proxy: %s %s\n", r.Method, upstreamURL.RequestURI())
		}

		resp, err := client.Do(req)
		if err != nil {
			http.Error(w, "upstream request failed: "+err.Error(), http.StatusBadGateway)
			return
		}
		defer resp.Body.Close()

		copyHeaders(w.Header(), resp.Header)
		removeHopByHopHeaders(w.Header())
		w.WriteHeader(resp.StatusCode)
		if _, err := io.Copy(w, resp.Body); err != nil && cfg.debug {
			fmt.Fprintf(os.Stderr, "kubectl-cce proxy: failed to write response: %v\n", err)
		}
	})
}

func applyAKSKSignature(req *http.Request, body []byte, cfg config) {
	req.Header.Del("Authorization")
	req.Header.Del("X-Auth-Token")
	req.Header.Set("X-Sdk-Date", time.Now().UTC().Format("20060102T150405Z"))
	req.Header.Set("Content-Sha256", hexSHA256(body))
	if cfg.securityToken != "" {
		req.Header.Set("X-Security-Token", cfg.securityToken)
	}
	if req.Header.Get("Content-Type") == "" && len(body) > 0 {
		req.Header.Set("Content-Type", "application/json")
	}

	signedHeaders, canonicalHeaders := canonicalHeaders(req)
	canonicalRequest := strings.Join([]string{
		req.Method,
		canonicalURI(req.URL.EscapedPath()),
		canonicalQuery(req.URL.Query()),
		canonicalHeaders,
		signedHeaders,
		hexSHA256(body),
	}, "\n")

	stringToSign := strings.Join([]string{
		"SDK-HMAC-SHA256",
		req.Header.Get("X-Sdk-Date"),
		hexSHA256([]byte(canonicalRequest)),
	}, "\n")
	signature := hmacSHA256Hex([]byte(cfg.sk), []byte(stringToSign))
	req.Header.Set("Authorization", fmt.Sprintf(
		"SDK-HMAC-SHA256 Access=%s, SignedHeaders=%s, Signature=%s",
		cfg.ak,
		signedHeaders,
		signature,
	))
}

func canonicalURI(path string) string {
	if path == "" {
		return "/"
	}
	if !strings.HasPrefix(path, "/") {
		path = "/" + path
	}
	segments := strings.Split(path, "/")
	for i, segment := range segments {
		decoded, err := url.PathUnescape(segment)
		if err == nil {
			segment = decoded
		}
		segments[i] = strings.ReplaceAll(url.PathEscape(segment), "+", "%20")
	}
	result := strings.Join(segments, "/")
	if strings.HasSuffix(path, "/") && !strings.HasSuffix(result, "/") {
		result += "/"
	}
	return result
}

func canonicalQuery(values url.Values) string {
	if len(values) == 0 {
		return ""
	}
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)

	parts := make([]string, 0)
	for _, key := range keys {
		escapedKey := escapeQuery(key)
		vals := append([]string(nil), values[key]...)
		sort.Strings(vals)
		for _, value := range vals {
			parts = append(parts, escapedKey+"="+escapeQuery(value))
		}
	}
	return strings.Join(parts, "&")
}

func canonicalHeaders(req *http.Request) (string, string) {
	headers := map[string][]string{}
	headers["host"] = []string{req.Host}
	for key, values := range req.Header {
		lowerKey := strings.ToLower(strings.TrimSpace(key))
		if lowerKey == "" || shouldSkipSignedHeader(lowerKey) {
			continue
		}
		headers[lowerKey] = append(headers[lowerKey], values...)
	}

	names := make([]string, 0, len(headers))
	for name := range headers {
		names = append(names, name)
	}
	sort.Strings(names)

	var b strings.Builder
	for _, name := range names {
		normalizedValues := make([]string, 0, len(headers[name]))
		for _, value := range headers[name] {
			normalizedValues = append(normalizedValues, strings.Join(strings.Fields(value), " "))
		}
		b.WriteString(name)
		b.WriteByte(':')
		b.WriteString(strings.Join(normalizedValues, ","))
		b.WriteByte('\n')
	}
	return strings.Join(names, ";"), b.String()
}

func shouldSkipSignedHeader(name string) bool {
	switch name {
	case "authorization", "connection", "content-length", "expect", "transfer-encoding":
		return true
	default:
		return false
	}
}

func runKubectlThroughProxy(proxy *localProxy, cfg config, kubectlArgs []string) error {
	args := append([]string{
		"--server=" + proxy.url(),
		"--insecure-skip-tls-verify=true",
		"--kubeconfig=/dev/null",
	}, kubectlArgs...)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	cmd := exec.CommandContext(ctx, cfg.kubectl, args...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			return kubectlExitError{code: exitErr.ExitCode()}
		}
		return err
	}
	return nil
}

func findUnsupportedStreamingCommand(args []string) string {
	for _, arg := range args {
		if unsupportedStreamingCommands[arg] {
			return arg
		}
	}
	return ""
}

func copyHeaders(dst, src http.Header) {
	for key, values := range src {
		for _, value := range values {
			dst.Add(key, value)
		}
	}
}

func removeHopByHopHeaders(header http.Header) {
	for _, h := range strings.Split(header.Get("Connection"), ",") {
		if h = strings.TrimSpace(h); h != "" {
			header.Del(h)
		}
	}
	for _, key := range []string{
		"Connection",
		"Keep-Alive",
		"Proxy-Authenticate",
		"Proxy-Authorization",
		"Te",
		"Trailer",
		"Transfer-Encoding",
		"Upgrade",
	} {
		header.Del(key)
	}
}

func envDefault(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func firstEnv(keys ...string) string {
	for _, key := range keys {
		if value := os.Getenv(key); value != "" {
			return value
		}
	}
	return ""
}

func escapeQuery(value string) string {
	return strings.ReplaceAll(url.QueryEscape(value), "+", "%20")
}

func hexSHA256(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func hmacSHA256Hex(key, data []byte) string {
	mac := hmac.New(sha256.New, key)
	mac.Write(data)
	return hex.EncodeToString(mac.Sum(nil))
}
