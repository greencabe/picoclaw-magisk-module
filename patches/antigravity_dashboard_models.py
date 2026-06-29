from pathlib import Path

meta = Path('pkg/providers/provider_metadata.go')
s = meta.read_text()
old = '''\t"antigravity": {
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
new = '''\t"antigravity": {
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
\t\tCommonModels:        []string{"gemini-3-flash-agent", "gemini-3.5-flash-low", "gemini-3.5-flash-extra-low", "gemini-pro-agent"},
\t\tAliases:             []string{"google-antigravity"},
\t},
'''
if new not in s:
    if old not in s:
        raise SystemExit('antigravity metadata anchor not found')
    meta.write_text(s.replace(old, new, 1))

models = Path('web/backend/api/models.go')
s = models.read_text()
if '"github.com/sipeed/picoclaw/pkg/auth"' not in s:
    s = s.replace('''\t"github.com/sipeed/picoclaw/pkg/audio/asr"
''', '''\t"github.com/sipeed/picoclaw/pkg/audio/asr"
\t"github.com/sipeed/picoclaw/pkg/auth"
''', 1)

api_key_anchor = '''\tapiKey := strings.TrimSpace(req.APIKey)
\tapiBase := strings.TrimSpace(req.APIBase)

\tif apiKey == "" && req.ModelIndex != nil {
'''
api_key_repl = '''\tapiKey := strings.TrimSpace(req.APIKey)
\tapiBase := strings.TrimSpace(req.APIBase)
\tprovider := providers.NormalizeProvider(req.Provider)

\tif apiKey == "" && req.ModelIndex != nil {
'''
if api_key_repl not in s and api_key_anchor in s:
    s = s.replace(api_key_anchor, api_key_repl, 1)

api_base_anchor = '''\tif apiBase == "" {
\t\tapiBase = providers.DefaultAPIBaseForProtocol(req.Provider)
\t}
\tif apiBase == "" {
\t\thttp.Error(w, fmt.Sprintf("No default API base for provider %q", req.Provider), http.StatusBadRequest)
\t\treturn
\t}
'''
api_base_repl = '''\tif apiBase == "" {
\t\tapiBase = providers.DefaultAPIBaseForProtocol(req.Provider)
\t}
\tif apiBase == "" && provider != "antigravity" {
\t\thttp.Error(w, fmt.Sprintf("No default API base for provider %q", req.Provider), http.StatusBadRequest)
\t\treturn
\t}
'''
if api_base_repl not in s and api_base_anchor in s:
    s = s.replace(api_base_anchor, api_base_repl, 1)

if 'return fetchAntigravityOAuthModels(ctx)' not in s:
    variants = [
        ('''\tcase "nearai":
\t\tfetchURL = apiBase + "/model/list"
\t\treturn fetchNearAIModels(ctx, fetchURL, apiKey)
\tdefault:
''', '''\tcase "nearai":
\t\tfetchURL = apiBase + "/model/list"
\t\treturn fetchNearAIModels(ctx, fetchURL, apiKey)
\tcase "antigravity":
\t\treturn fetchAntigravityOAuthModels(ctx)
\tdefault:
'''),
        ('''\tcase "ollama":
\t\t// Strip /v1 suffix if present to get the Ollama root
''', '''\tcase "antigravity":
\t\treturn fetchAntigravityOAuthModels(ctx)
\tcase "ollama":
\t\t// Strip /v1 suffix if present to get the Ollama root
'''),
    ]
    for old_fetch, new_fetch in variants:
        if old_fetch in s:
            s = s.replace(old_fetch, new_fetch, 1)
            break
    else:
        raise SystemExit('fetchUpstreamModels anchor not found')

old_probe = '''\tcase "codex-cli":
\t\treturn probeCommandAvailable("codex")
\tdefault:
'''
new_probe = '''\tcase "codex-cli":
\t\treturn probeCommandAvailable("codex")
\tcase "antigravity":
\t\treturn probeAntigravityOAuthModel(modelID)
\tdefault:
'''
if new_probe not in s:
    if old_probe not in s:
        raise SystemExit('probeModelConnectivity anchor not found')
    s = s.replace(old_probe, new_probe, 1)

helper = r'''func antigravityOAuthCredential() (*auth.AuthCredential, error) {
	cred, err := auth.GetCredential("google-antigravity")
	if err != nil {
		return nil, err
	}
	if cred == nil {
		return nil, fmt.Errorf("google-antigravity credentials not configured")
	}
	if cred.NeedsRefresh() && cred.RefreshToken != "" {
		refreshed, err := auth.RefreshAccessToken(cred, auth.GoogleAntigravityOAuthConfig())
		if err != nil {
			return nil, err
		}
		refreshed.Email = cred.Email
		if refreshed.ProjectID == "" {
			refreshed.ProjectID = cred.ProjectID
		}
		if err := auth.SetCredential("google-antigravity", refreshed); err != nil {
			return nil, err
		}
		cred = refreshed
	}
	if cred.IsExpired() {
		return nil, fmt.Errorf("google-antigravity credentials expired")
	}
	if cred.ProjectID == "" {
		projectID, err := providers.FetchAntigravityProjectID(cred.AccessToken)
		if err != nil {
			return nil, err
		}
		cred.ProjectID = projectID
		_ = auth.SetCredential("google-antigravity", cred)
	}
	return cred, nil
}

func fetchAntigravityOAuthModels(ctx context.Context) ([]upstreamModel, error) {
	cred, err := antigravityOAuthCredential()
	if err != nil {
		return nil, err
	}
	result := make(chan struct {
		models []providers.AntigravityModelInfo
		err    error
	}, 1)
	go func() {
		models, err := providers.FetchAntigravityModels(cred.AccessToken, cred.ProjectID)
		result <- struct {
			models []providers.AntigravityModelInfo
			err    error
		}{models: models, err: err}
	}()
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case res := <-result:
		if res.err != nil {
			return nil, res.err
		}
		models := make([]upstreamModel, 0, len(res.models))
		for _, model := range res.models {
			id := strings.TrimSpace(model.ID)
			if id != "" {
				models = append(models, upstreamModel{ID: id, OwnedBy: "google-antigravity"})
			}
		}
		return models, nil
	}
}

'''
if 'func antigravityOAuthCredential()' not in s:
    if 'func fetchNearAIModels(ctx context.Context' in s:
        s = s.replace('func fetchNearAIModels(ctx context.Context', helper + 'func fetchNearAIModels(ctx context.Context', 1)
    elif 'func fetchOpenAICompatibleModels(ctx context.Context' in s:
        s = s.replace('func fetchOpenAICompatibleModels(ctx context.Context', helper + 'func fetchOpenAICompatibleModels(ctx context.Context', 1)
    else:
        raise SystemExit('model fetch helper anchor not found')

probe_helper = r'''func probeAntigravityOAuthModel(modelID string) bool {
	modelID = strings.TrimSpace(modelID)
	if modelID == "" {
		modelID = "gemini-3-flash-agent"
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	provider := providers.NewAntigravityProvider()
	_, err := provider.Chat(ctx, []providers.Message{{Role: "user", Content: "Reply with OK."}}, nil, modelID, map[string]any{"max_tokens": 8})
	return err == nil
}

'''
if 'func probeAntigravityOAuthModel(' not in s:
    if 'func probeModelConnectivity(m *config.ModelConfig) bool {' not in s:
        raise SystemExit('probeModelConnectivity function anchor not found')
    s = s.replace('func probeModelConnectivity(m *config.ModelConfig) bool {', probe_helper + 'func probeModelConnectivity(m *config.ModelConfig) bool {', 1)

models.write_text(s)


# UI can pass virtual/chat model names when testing edited rows. Normalize those
# to a real Antigravity model before probing.
models = Path('web/backend/api/models.go')
s = models.read_text()
normalize_helper = r'''func normalizeAntigravityProbeModel(modelID string) string {
	modelID = strings.TrimSpace(modelID)
	if modelID == "" || strings.HasPrefix(strings.ToLower(modelID), "chat_") {
		return "gemini-3-flash-agent"
	}
	return modelID
}

'''
if 'func normalizeAntigravityProbeModel(' not in s:
    if 'func probeAntigravityOAuthModel(modelID string) bool {' not in s:
        raise SystemExit('probeAntigravityOAuthModel anchor for normalize helper not found')
    s = s.replace('func probeAntigravityOAuthModel(modelID string) bool {', normalize_helper + 'func probeAntigravityOAuthModel(modelID string) bool {', 1)
old = '''func probeAntigravityOAuthModel(modelID string) bool {
	modelID = strings.TrimSpace(modelID)
	if modelID == "" {
		modelID = "gemini-3-flash-agent"
	}
'''
new = '''func probeAntigravityOAuthModel(modelID string) bool {
	modelID = normalizeAntigravityProbeModel(modelID)
'''
if new not in s:
    if old not in s:
        raise SystemExit('probeAntigravityOAuthModel body anchor not found')
    s = s.replace(old, new, 1)
old = '''		if providerMatch && baseMatch {
				if stored.APIKey() != "" {
					m.SetAPIKey(stored.APIKey())
				}
				if m.APIBase == "" && stored.APIBase != "" {
					m.APIBase = stored.APIBase
				}
			}
'''
new = '''		if providerMatch && baseMatch {
				if stored.APIKey() != "" {
					m.SetAPIKey(stored.APIKey())
				}
				if m.APIBase == "" && stored.APIBase != "" {
					m.APIBase = stored.APIBase
				}
				if providers.NormalizeProvider(m.Provider) == "antigravity" && strings.HasPrefix(strings.ToLower(m.Model), "chat_") {
					m.Model = stored.Model
				}
			}
'''
if new not in s:
    if old not in s:
        raise SystemExit('inline stored credential block anchor not found')
    s = s.replace(old, new, 1)
models.write_text(s)
