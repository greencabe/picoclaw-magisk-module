from pathlib import Path

path = Path('pkg/providers/oauth/antigravity_provider.go')
text = path.read_text()
text = text.replace('antigravityBaseURL      = "https://cloudcode-pa.googleapis.com"\n', 'antigravityBaseURL      = "https://cloudcode-pa.googleapis.com"\n\tantigravityChatBaseURL  = "https://daily-cloudcode-pa.googleapis.com"\n')
text = text.replace('antigravityVersion      = "1.15.8"', 'antigravityVersion      = "1.107.0"')
text = text.replace('apiURL := fmt.Sprintf("%s/v1internal:streamGenerateContent?alt=sse", antigravityBaseURL)', 'apiURL := fmt.Sprintf("%s/v1internal:streamGenerateContent?alt=sse", antigravityChatBaseURL)')
text = text.replace('req.Header.Set("User-Agent", fmt.Sprintf("antigravity/%s linux/amd64", antigravityVersion))', 'req.Header.Set("User-Agent", fmt.Sprintf("antigravity/%s android/arm64", antigravityVersion))')
needle = 'req.Header.Set("Accept", "text/event-stream")\n'
replacement = 'req.Header.Set("Accept", "text/event-stream")\n\treq.Header.Set("x-request-source", "local")\n\treq.Header.Set("X-Machine-Session-Id", fmt.Sprintf("agent-%d-%s", time.Now().UnixMilli(), randomString(9)))\n'
if replacement.strip() not in text:
    text = text.replace(needle, replacement, 1)
path.write_text(text)
