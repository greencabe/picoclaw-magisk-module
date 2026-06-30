from pathlib import Path

path = Path('pkg/providers/oauth/antigravity_provider.go')
s = path.read_text()
s = s.replace('req.Header.Set("User-Agent", fmt.Sprintf("antigravity/%s linux/amd64", antigravityVersion))', 'req.Header.Set("User-Agent", antigravityChatUserAgent)')
s = s.replace('req.Header.Set("User-Agent", fmt.Sprintf("antigravity/cli/%s (%s; os_type=darwin; arch=arm64)", antigravityVersion, antigravityClientName))', 'req.Header.Set("User-Agent", antigravityChatUserAgent)')
chat = '''	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("User-Agent", antigravityChatUserAgent)
	req.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)
	req.Header.Set("Client-Metadata", string(clientMetadata))
'''
chat_final = '''	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("User-Agent", antigravityChatUserAgent)
	req.Header.Set(antigravityRequestSourceName, antigravityRequestSource)
	req.Header.Set("X-Machine-Session-Id", antigravitySessionID())
	req.Header.Set("X-Goog-Api-Client", antigravityXGoogClient)
	req.Header.Set("Client-Metadata", string(clientMetadata))
'''
if chat in s:
    s = s.replace(chat, chat_final, 1)
if 'req.Header.Set("User-Agent", antigravityChatUserAgent)' not in s or 'X-Machine-Session-Id' not in s:
    raise SystemExit('antigravity 9router chat headers not finalized')
path.write_text(s)
