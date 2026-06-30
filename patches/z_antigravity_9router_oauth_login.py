from pathlib import Path

provider = Path('pkg/providers/oauth/antigravity_provider.go')
s = provider.read_text()
if 'func EnsureAntigravityProjectWithContext(' not in s:
    marker = 'func FetchAntigravityProjectIDWithContext(ctx context.Context, accessToken string) (string, error) {\n\treturn fetchAntigravityProjectID(ctx, accessToken)\n}\n'
    if marker not in s:
        raise SystemExit('FetchAntigravityProjectIDWithContext anchor not found')
    helper = r'''
func EnsureAntigravityProjectWithContext(ctx context.Context, accessToken string) (string, error) {
	projectID, err := fetchAntigravityProjectID(ctx, accessToken)
	if err != nil {
		return "", err
	}
	if err := onboardAntigravityUser(ctx, accessToken); err != nil {
		logger.WarnCF("provider.antigravity", "Antigravity onboardUser warning", map[string]any{"error": err.Error()})
	}
	return projectID, nil
}

func onboardAntigravityUser(ctx context.Context, accessToken string) error {
	reqBody, _ := json.Marshal(map[string]any{
		"tierId":   "legacy-tier",
		"metadata": antigravityClientMetadata(),
	})
	for attempt := 0; attempt < 10; attempt++ {
		req, err := http.NewRequestWithContext(ctx, "POST", antigravityAssistBaseURL+"/v1internal:onboardUser", bytes.NewReader(reqBody))
		if err != nil {
			return err
		}
		req.Header.Set("Authorization", "Bearer "+accessToken)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("User-Agent", antigravityLoadUserAgent)
		req.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)
		req.Header.Set("Client-Metadata", mustAntigravityClientMetadataJSON())
		req.Header.Set(antigravityRequestSourceName, antigravityRequestSource)

		resp, err := (&http.Client{Timeout: 30 * time.Second}).Do(req)
		if err != nil {
			return err
		}
		body, _ := io.ReadAll(resp.Body)
		_ = resp.Body.Close()
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			return fmt.Errorf("onboardUser failed: HTTP %d %s", resp.StatusCode, truncateString(string(body), 300))
		}
		var out struct{ Done bool `json:"done"` }
		if err := json.Unmarshal(body, &out); err == nil && out.Done {
			return nil
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(5 * time.Second):
		}
	}
	return nil
}

func mustAntigravityClientMetadataJSON() string {
	b, _ := json.Marshal(antigravityClientMetadata())
	return string(b)
}

'''
    s = s.replace(marker, marker + helper, 1)
provider.write_text(s)

facade = Path('pkg/providers/oauth_facade.go')
f = facade.read_text()
if 'EnsureAntigravityProjectWithContext' not in f:
    f += '''
func EnsureAntigravityProjectWithContext(ctx context.Context, accessToken string) (string, error) {
	return oauthprovider.EnsureAntigravityProjectWithContext(ctx, accessToken)
}
'''
facade.write_text(f)

oauth = Path('web/backend/api/oauth.go')
s = oauth.read_text()
if '\t"context"\n' not in s:
    s = s.replace('import (\n', 'import (\n\t"context"\n', 1)
s = s.replace('oauthFetchAntigravityProject  = providers.FetchAntigravityProjectID', 'oauthFetchAntigravityProject  = providers.EnsureAntigravityProjectWithContext')
s = s.replace('projectID, err := oauthFetchAntigravityProject(cp.AccessToken)', 'projectID, err := oauthFetchAntigravityProject(context.Background(), cp.AccessToken)')
s = s.replace('ModelName:  "gemini-flash",\n\t\t\tProvider:   "antigravity",\n\t\t\tModel:      "gemini-3-flash",', 'ModelName:  "gemini-3-flash-agent",\n\t\t\tProvider:   "antigravity",\n\t\t\tModel:      "gemini-3-flash-agent",')
oauth.write_text(s)
