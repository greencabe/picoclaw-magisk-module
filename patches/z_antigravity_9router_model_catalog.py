from pathlib import Path

path = Path('pkg/providers/provider_metadata.go')
s = path.read_text()
old_block = '''\t"antigravity": {
\t\tID:                  "antigravity",
\t\tDisplayName:         "Google Code Assist",
\t\tDomain:              "antigravity.google",
\t\tEmptyAPIKeyAllowed:  true,
\t\tCreateAllowed:       true,
\t\tDefaultModelAllowed: true,
\t\tDefaultAuthMethod:   "oauth",
\t\tAuthMethodLocked:    true,
\t\tPriority:            54,
\t\tAliases:             []string{"google-antigravity"},
\t},
'''
new_block = '''\t"antigravity": {
\t\tID:                  "antigravity",
\t\tDisplayName:         "Google Code Assist",
\t\tDomain:              "antigravity.google",
\t\tEmptyAPIKeyAllowed:  true,
\t\tCreateAllowed:       true,
\t\tDefaultModelAllowed: true,
\t\tSupportsFetch:       true,
\t\tDefaultAuthMethod:   "oauth",
\t\tAuthMethodLocked:    true,
\t\tPriority:            54,
\t\tCommonModels:        []string{"gemini-3-flash-agent", "gemini-3.5-flash-low", "gemini-3.5-flash-extra-low", "gemini-pro-agent", "claude-sonnet-4-6", "claude-opus-4-6-thinking"},
\t\tAliases:             []string{"google-antigravity"},
\t},
'''
old_common = 'CommonModels:        []string{"gemini-3-flash-agent", "gemini-3.5-flash-low", "gemini-3.5-flash-extra-low", "gemini-pro-agent"},'
new_common = 'CommonModels:        []string{"gemini-3-flash-agent", "gemini-3.5-flash-low", "gemini-3.5-flash-extra-low", "gemini-pro-agent", "claude-sonnet-4-6", "claude-opus-4-6-thinking"},'
if old_block in s:
    s = s.replace(old_block, new_block, 1)
elif old_common in s:
    s = s.replace(old_common, new_common, 1)
elif new_common not in s:
    raise SystemExit('antigravity metadata anchor not found')
path.write_text(s)

path = Path('web/backend/api/models.go')
s = path.read_text()
helper = r'''func antigravityCuratedModels() []upstreamModel {
	return []upstreamModel{
		{ID: "gemini-3-flash-agent", OwnedBy: "google-antigravity"},
		{ID: "gemini-3.5-flash-low", OwnedBy: "google-antigravity"},
		{ID: "gemini-3.5-flash-extra-low", OwnedBy: "google-antigravity"},
		{ID: "gemini-pro-agent", OwnedBy: "google-antigravity"},
		{ID: "gemini-3.1-pro-low", OwnedBy: "google-antigravity"},
		{ID: "gemini-3-flash", OwnedBy: "google-antigravity"},
		{ID: "claude-sonnet-4-6", OwnedBy: "google-antigravity"},
		{ID: "claude-opus-4-6-thinking", OwnedBy: "google-antigravity"},
		{ID: "gpt-oss-120b-medium", OwnedBy: "google-antigravity"},
	}
}

'''
if 'func antigravityCuratedModels()' not in s:
    if 'func fetchAntigravityOAuthModels(ctx context.Context)' not in s:
        raise SystemExit('fetchAntigravityOAuthModels anchor missing')
    s = s.replace('func fetchAntigravityOAuthModels(ctx context.Context)', helper + 'func fetchAntigravityOAuthModels(ctx context.Context)', 1)
start = s.find('func fetchAntigravityOAuthModels(ctx context.Context) ([]upstreamModel, error) {')
if start < 0:
    raise SystemExit('fetchAntigravityOAuthModels function not found')
end = s.find('\n}\n\nfunc fetchOpenAICompatibleModels', start)
if end < 0:
    end = s.find('\n}\n\nfunc fetchNearAIModels', start)
if end < 0:
    raise SystemExit('fetchAntigravityOAuthModels end not found')
end += len('\n}\n')
new_func = '''func fetchAntigravityOAuthModels(ctx context.Context) ([]upstreamModel, error) {
\tif _, err := antigravityOAuthCredential(); err != nil {
\t\treturn nil, err
\t}
\tselect {
\tcase <-ctx.Done():
\t\treturn nil, ctx.Err()
\tdefault:
\t\treturn antigravityCuratedModels(), nil
\t}
}
'''
if s[start:end] != new_func:
    s = s[:start] + new_func + s[end:]
path.write_text(s)
