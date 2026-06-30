from pathlib import Path

# Fix saved Test Connection: probe once, preserve error, avoid nil .Error panic.
models = Path('web/backend/api/models.go')
s = models.read_text()
old = '''\tm := cfg.ModelList[idx]
\tstart := time.Now()
\tsummary := modelConfigurationStatus(m)
\tif providers.NormalizeProvider(modelProtocol(m)) == "antigravity" && summary.Available {
\t\tif err := probeAntigravityOAuthModelError(splitModelID(m)); err != nil {
\t\t\tsummary.Available = false
\t\t\tsummary.Status = modelStatusUnreachable
\t\t}
\t}
\tlatency := time.Since(start).Milliseconds()

\tresult := map[string]any{
\t\t"success":    summary.Available,
\t\t"latency_ms": latency,
\t\t"status":     summary.Status,
\t}

\tif !summary.Available {
\t\tif summary.Status == modelStatusUnconfigured {
\t\t\tresult["error"] = "OAuth credential not configured"
\t\t} else if providers.NormalizeProvider(modelProtocol(m)) == "antigravity" {
\t\t\tresult["error"] = probeAntigravityOAuthModelError(splitModelID(m)).Error()
\t\t} else {
\t\t\tresult["error"] = "Endpoint unreachable"
\t\t}
\t}
'''
new = '''\tm := cfg.ModelList[idx]
\tstart := time.Now()
\tsummary := modelConfigurationStatus(m)
\tvar probeErr error
\tif providers.NormalizeProvider(modelProtocol(m)) == "antigravity" && summary.Available {
\t\tprobeErr = probeAntigravityOAuthModelError(splitModelID(m))
\t\tif probeErr != nil {
\t\t\tsummary.Available = false
\t\t\tsummary.Status = modelStatusUnreachable
\t\t}
\t}
\tlatency := time.Since(start).Milliseconds()

\tresult := map[string]any{
\t\t"success":    summary.Available,
\t\t"latency_ms": latency,
\t\t"status":     summary.Status,
\t}

\tif !summary.Available {
\t\tif summary.Status == modelStatusUnconfigured {
\t\t\tresult["error"] = "OAuth credential not configured"
\t\t} else if probeErr != nil {
\t\t\tresult["error"] = probeErr.Error()
\t\t} else {
\t\t\tresult["error"] = "Endpoint unreachable"
\t\t}
\t}
'''
if old in s:
    s = s.replace(old, new, 1)
elif 'var probeErr error' not in s:
    raise SystemExit('saved test connection block not found')
models.write_text(s)

# Make Cloud Code Assist helper calls match 9router headers and onboarding tier.
provider = Path('pkg/providers/oauth/antigravity_provider.go')
s = provider.read_text()

# loadCodeAssist header must include Client-Metadata.
load_headers = '''\treq.Header.Set("User-Agent", antigravityLoadUserAgent)
\treq.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)
\treq.Header.Set(antigravityRequestSourceName, antigravityRequestSource)
'''
load_headers_final = '''\treq.Header.Set("User-Agent", antigravityLoadUserAgent)
\treq.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)
\treq.Header.Set("Client-Metadata", mustAntigravityClientMetadataJSON())
\treq.Header.Set(antigravityRequestSourceName, antigravityRequestSource)
'''
if load_headers in s:
    s = s.replace(load_headers, load_headers_final, 1)

# fetchAvailableModels also uses load-style headers if any codepath calls it.
s = s.replace('''\treq.Header.Set("User-Agent", antigravityUserAgent)
\treq.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)
''', '''\treq.Header.Set("User-Agent", antigravityLoadUserAgent)
\treq.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)
\treq.Header.Set("Client-Metadata", mustAntigravityClientMetadataJSON())
\treq.Header.Set(antigravityRequestSourceName, antigravityRequestSource)
''')

# Ensure onboarding uses default tier from loadCodeAssist, not hardcoded legacy-tier only.
old = '''func EnsureAntigravityProjectWithContext(ctx context.Context, accessToken string) (string, error) {
\tprojectID, err := fetchAntigravityProjectID(ctx, accessToken)
\tif err != nil {
\t\treturn "", err
\t}
\tif err := onboardAntigravityUser(ctx, accessToken); err != nil {
\t\tlogger.WarnCF("provider.antigravity", "Antigravity onboardUser warning", map[string]any{"error": err.Error()})
\t}
\treturn projectID, nil
}

func onboardAntigravityUser(ctx context.Context, accessToken string) error {
\treqBody, _ := json.Marshal(map[string]any{
\t\t"tierId":   "legacy-tier",
\t\t"metadata": antigravityClientMetadata(),
\t})
'''
new = '''func EnsureAntigravityProjectWithContext(ctx context.Context, accessToken string) (string, error) {
\tprojectID, tierID, err := fetchAntigravityProjectAndTier(ctx, accessToken)
\tif err != nil {
\t\treturn "", err
\t}
\tif err := onboardAntigravityUser(ctx, accessToken, tierID); err != nil {
\t\tlogger.WarnCF("provider.antigravity", "Antigravity onboardUser warning", map[string]any{"error": err.Error()})
\t}
\treturn projectID, nil
}

func onboardAntigravityUser(ctx context.Context, accessToken, tierID string) error {
\tif strings.TrimSpace(tierID) == "" {
\t\ttierID = "legacy-tier"
\t}
\treqBody, _ := json.Marshal(map[string]any{
\t\t"tierId":   tierID,
\t\t"metadata": antigravityClientMetadata(),
\t})
'''
if old in s:
    s = s.replace(old, new, 1)

old = '''func FetchAntigravityProjectIDWithContext(ctx context.Context, accessToken string) (string, error) {
\treturn fetchAntigravityProjectID(ctx, accessToken)
}
'''
new = '''func FetchAntigravityProjectIDWithContext(ctx context.Context, accessToken string) (string, error) {
\tprojectID, _, err := fetchAntigravityProjectAndTier(ctx, accessToken)
\treturn projectID, err
}
'''
if old in s:
    s = s.replace(old, new, 1)

old = '''func FetchAntigravityProjectID(accessToken string) (string, error) {
\treturn fetchAntigravityProjectID(context.Background(), accessToken)
}

func fetchAntigravityProjectID(ctx context.Context, accessToken string) (string, error) {
'''
new = '''func FetchAntigravityProjectID(accessToken string) (string, error) {
\tprojectID, _, err := fetchAntigravityProjectAndTier(context.Background(), accessToken)
\treturn projectID, err
}

func fetchAntigravityProjectAndTier(ctx context.Context, accessToken string) (string, string, error) {
'''
if old in s:
    s = s.replace(old, new, 1)

s = s.replace('''\tvar result struct {
\t\tCloudAICompanionProject any `json:"cloudaicompanionProject"`
\t}
''', '''\tvar result struct {
\t\tCloudAICompanionProject any `json:"cloudaicompanionProject"`
\t\tAllowedTiers             []struct {
\t\t\tID        string `json:"id"`
\t\t\tIsDefault bool   `json:"isDefault"`
\t\t} `json:"allowedTiers"`
\t}
''', 1)
s = s.replace('''\tswitch project := result.CloudAICompanionProject.(type) {
\tcase string:
\t\tproject = strings.TrimSpace(project)
\t\tif project != "" {
\t\t\treturn project, nil
\t\t}
\tcase map[string]any:
\t\tif id, ok := project["id"].(string); ok && strings.TrimSpace(id) != "" {
\t\t\treturn strings.TrimSpace(id), nil
\t\t}
\t}

\treturn "", fmt.Errorf("no project ID in loadCodeAssist response")
}
''', '''\ttierID := "legacy-tier"
\tfor _, tier := range result.AllowedTiers {
\t\tif tier.IsDefault && strings.TrimSpace(tier.ID) != "" {
\t\t\ttierID = strings.TrimSpace(tier.ID)
\t\t\tbreak
\t\t}
\t}

\tswitch project := result.CloudAICompanionProject.(type) {
\tcase string:
\t\tproject = strings.TrimSpace(project)
\t\tif project != "" {
\t\t\treturn project, tierID, nil
\t\t}
\tcase map[string]any:
\t\tif id, ok := project["id"].(string); ok && strings.TrimSpace(id) != "" {
\t\t\treturn strings.TrimSpace(id), tierID, nil
\t\t}
\t}

\treturn "", "", fmt.Errorf("no project ID in loadCodeAssist response")
}
''', 1)
provider.write_text(s)

# Adjust error returns after changing fetchAntigravityProjectAndTier signature.
provider = Path('pkg/providers/oauth/antigravity_provider.go')
s = provider.read_text()
start = s.find('func fetchAntigravityProjectAndTier(')
end = s.find('\n}\n\n// FetchAntigravityModels', start)
if start >= 0 and end >= 0:
    block = s[start:end]
    block = block.replace('return "", err', 'return "", "", err')
    block = block.replace('return "", fmt.Errorf(', 'return "", "", fmt.Errorf(')
    block = block.replace('return "", errors.New(', 'return "", "", errors.New(')
    s = s[:start] + block + s[end:]
provider.write_text(s)
