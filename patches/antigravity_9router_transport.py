from pathlib import Path

path = Path('pkg/providers/oauth/antigravity_provider.go')
s = path.read_text()

s = s.replace('antigravityBaseURL      = "https://cloudcode-pa.googleapis.com"', 'antigravityBaseURL      = "https://daily-cloudcode-pa.googleapis.com"')
s = s.replace('antigravityDefaultModel = "gemini-3-flash"', 'antigravityDefaultModel = "gemini-3-flash-agent"')
const_extra = '''	antigravityAssistBaseURL     = "https://cloudcode-pa.googleapis.com"
	antigravityChatUserAgent     = "antigravity/1.107.0 darwin/arm64"
	antigravityLoadUserAgent     = "google-api-nodejs-client/9.15.1"
	antigravityRequestSourceName = "x-request-source"
	antigravityRequestSource     = "local"
'''
if 'antigravityAssistBaseURL' not in s:
    s = s.replace('\tantigravityXGoogClient  = "google-cloud-sdk vscode_cloudshelleditor/0.1"\n', '\tantigravityXGoogClient  = "google-cloud-sdk vscode_cloudshelleditor/0.1"\n' + const_extra, 1)

s = s.replace('''	clientMetadata, _ := json.Marshal(map[string]string{
		"ideType":    "IDE_UNSPECIFIED",
		"platform":   "PLATFORM_UNSPECIFIED",
		"pluginType": "GEMINI",
	})
''', '''	clientMetadata, _ := json.Marshal(antigravityClientMetadata())
''')

for old in [
    'req.Header.Set("User-Agent", fmt.Sprintf("antigravity/cli/%s (%s; os_type=darwin; arch=arm64)", antigravityVersion, antigravityClientName))',
    'req.Header.Set("User-Agent", antigravityUserAgent)',
]:
    if old in s:
        s = s.replace(old, 'req.Header.Set("User-Agent", antigravityChatUserAgent)', 1)

chat_anchor = '''	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("User-Agent", antigravityChatUserAgent)
	req.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)
	req.Header.Set("Client-Metadata", string(clientMetadata))
'''
chat_new = '''	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("User-Agent", antigravityChatUserAgent)
	req.Header.Set(antigravityRequestSourceName, antigravityRequestSource)
	req.Header.Set("X-Machine-Session-Id", antigravitySessionID())
	req.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)
	req.Header.Set("Client-Metadata", string(clientMetadata))
'''
if chat_anchor in s:
    s = s.replace(chat_anchor, chat_new, 1)

s = s.replace('''	reqBody, _ := json.Marshal(map[string]any{
		"metadata": map[string]any{
			"ideType":    "IDE_UNSPECIFIED",
			"platform":   "PLATFORM_UNSPECIFIED",
			"pluginType": "GEMINI",
		},
	})
''', '''	reqBody, _ := json.Marshal(map[string]any{
		"metadata": antigravityClientMetadata(),
	})
''')
s = s.replace('antigravityBaseURL+"/v1internal:loadCodeAssist"', 'antigravityAssistBaseURL+"/v1internal:loadCodeAssist"')
s = s.replace('antigravityBaseURL+"/v1internal:fetchAvailableModels"', 'antigravityAssistBaseURL+"/v1internal:fetchAvailableModels"')

# loadCodeAssist/fetchAvailableModels headers: use 9router load headers, not chat UA.
s = s.replace('req.Header.Set("User-Agent", antigravityChatUserAgent)\n\treq.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)\n', 'req.Header.Set("User-Agent", antigravityLoadUserAgent)\n\treq.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)\n\treq.Header.Set(antigravityRequestSourceName, antigravityRequestSource)\n', 2)

insert = r'''
func antigravityClientMetadata() map[string]any {
	return map[string]any{
		"ideType":    9,
		"platform":   4,
		"pluginType": 2,
	}
}

func antigravitySessionID() string {
	return fmt.Sprintf("%d%s", time.Now().UnixNano(), randomString(12))
}

'''
if 'func antigravityClientMetadata()' not in s:
    marker = '// FetchAntigravityProjectID retrieves the Google Cloud project ID from the loadCodeAssist endpoint.\n'
    if marker not in s:
        raise SystemExit('FetchAntigravityProjectID marker not found')
    s = s.replace(marker, insert + marker, 1)

# Add context-aware wrapper used by dashboard test.
if 'func FetchAntigravityProjectIDWithContext(' not in s:
    marker = 'func FetchAntigravityProjectID(accessToken string) (string, error) {\n'
    if marker not in s:
        raise SystemExit('FetchAntigravityProjectID function not found')
    s = s.replace(marker, '''func FetchAntigravityProjectIDWithContext(ctx context.Context, accessToken string) (string, error) {
	return fetchAntigravityProjectID(ctx, accessToken)
}

func FetchAntigravityProjectID(accessToken string) (string, error) {
	return fetchAntigravityProjectID(context.Background(), accessToken)
}

func fetchAntigravityProjectID(ctx context.Context, accessToken string) (string, error) {
''', 1)
    s = s.replace('req, err := http.NewRequest("POST", antigravityAssistBaseURL+"/v1internal:loadCodeAssist", bytes.NewReader(reqBody))', 'req, err := http.NewRequestWithContext(ctx, "POST", antigravityAssistBaseURL+"/v1internal:loadCodeAssist", bytes.NewReader(reqBody))', 1)

path.write_text(s)

facade = Path('pkg/providers/oauth_facade.go')
f = facade.read_text()
if 'FetchAntigravityProjectIDWithContext' not in f:
    f = f.replace('import (\n\toauthprovider "github.com/sipeed/picoclaw/pkg/providers/oauth"\n)\n', 'import (\n\t"context"\n\n\toauthprovider "github.com/sipeed/picoclaw/pkg/providers/oauth"\n)\n')
    f += '''
func FetchAntigravityProjectIDWithContext(ctx context.Context, accessToken string) (string, error) {
	return oauthprovider.FetchAntigravityProjectIDWithContext(ctx, accessToken)
}
'''
facade.write_text(f)
