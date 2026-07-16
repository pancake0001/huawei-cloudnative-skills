package main

import (
	"net/http"
	"testing"
)

func TestCanonicalURIAddsTrailingSlash(t *testing.T) {
	got := canonicalURI("/v1/project-id/vpcs")
	want := "/v1/project-id/vpcs/"
	if got != want {
		t.Fatalf("canonicalURI() = %q, want %q", got, want)
	}
}

func TestAKSKSignedHeadersMatchHuaweiGoSDKShape(t *testing.T) {
	req, err := http.NewRequest(http.MethodGet, "https://service.region.example.com/v1/project-id/vpcs?limit=2&marker=abc", nil)
	if err != nil {
		t.Fatal(err)
	}
	req.Host = "service.region.example.com"
	req.Header.Set("Host", "service.region.example.com")
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Sdk-Date", "20191115T033655Z")

	signedHeaders := signedHeaders(req.Header)
	canonicalHeaders := canonicalHeaders(req, signedHeaders)
	if signedHeaders != "host;x-sdk-date" {
		t.Fatalf("signedHeaders = %q", signedHeaders)
	}
	wantHeaders := "host:service.region.example.com\nx-sdk-date:20191115T033655Z\n"
	if canonicalHeaders != wantHeaders {
		t.Fatalf("canonicalHeaders = %q, want %q", canonicalHeaders, wantHeaders)
	}
}

func TestCleanEnvValueRemovesSmartQuotes(t *testing.T) {
	got := cleanEnvValue(" ‘6feaa266-79e4-11f1-946d-0255ac100260’ ")
	want := "6feaa266-79e4-11f1-946d-0255ac100260"
	if got != want {
		t.Fatalf("cleanEnvValue() = %q, want %q", got, want)
	}
}

func TestApplyCLIOverrides(t *testing.T) {
	cfg := config{
		clusterID: "env-cluster",
		region:    "cn-north-4",
		endpoint:  "",
		projectID: "env-project",
	}
	cfg.applyCLIOverrides(" cli-cluster ", "cn-east-3", " ‘example.com’ ", "cli-project")

	if cfg.clusterID != "cli-cluster" {
		t.Fatalf("clusterID = %q", cfg.clusterID)
	}
	if cfg.region != "cn-east-3" {
		t.Fatalf("region = %q", cfg.region)
	}
	if cfg.endpoint != "example.com" {
		t.Fatalf("endpoint = %q", cfg.endpoint)
	}
	if cfg.projectID != "cli-project" {
		t.Fatalf("projectID = %q", cfg.projectID)
	}
}

func TestExecIsBlocked(t *testing.T) {
	if command := findUnsupportedStreamingCommand([]string{"exec", "pod/nginx", "--", "date"}); command != "exec" {
		t.Fatalf("findUnsupportedStreamingCommand() = %q, want exec", command)
	}
}

func TestCanonicalQuerySortsKeysAndValues(t *testing.T) {
	req, err := http.NewRequest(http.MethodGet, "https://example.com/path?b=2&a=z&a=x", nil)
	if err != nil {
		t.Fatal(err)
	}
	got := canonicalQuery(req.URL.Query())
	want := "a=x&a=z&b=2"
	if got != want {
		t.Fatalf("canonicalQuery() = %q, want %q", got, want)
	}
}
