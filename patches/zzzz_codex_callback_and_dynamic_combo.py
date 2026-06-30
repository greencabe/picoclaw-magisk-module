from pathlib import Path

# Backend: submit pasted OAuth callback URL/code for Codex/OpenAI.
path = Path('web/backend/api/oauth.go')
s = path.read_text()
if 'mux.HandleFunc("POST /api/oauth/flows/{id}/callback"' not in s:
    s = s.replace('''\tmux.HandleFunc("POST /api/oauth/flows/{id}/poll", h.handlePollOAuthFlow)
''', '''\tmux.HandleFunc("POST /api/oauth/flows/{id}/poll", h.handlePollOAuthFlow)
\tmux.HandleFunc("POST /api/oauth/flows/{id}/callback", h.handleSubmitOAuthCallback)
''', 1)
if 'func (h *Handler) handleSubmitOAuthCallback' not in s:
    marker = 'func (h *Handler) handleOAuthCallback(w http.ResponseWriter, r *http.Request) {'
    helper = r'''func (h *Handler) handleSubmitOAuthCallback(w http.ResponseWriter, r *http.Request) {
	flowID := strings.TrimSpace(r.PathValue("id"))
	flow, ok := h.getOAuthFlow(flowID)
	if !ok {
		http.Error(w, "flow not found", http.StatusNotFound)
		return
	}
	if flow.Status != oauthFlowPending {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(flowToResponse(flow))
		return
	}

	var req struct {
		CallbackURL string `json:"callback_url"`
		Code        string `json:"code"`
		State       string `json:"state"`
	}
	if err := json.NewDecoder(io.LimitReader(r.Body, 1<<20)).Decode(&req); err != nil {
		http.Error(w, fmt.Sprintf("invalid json: %v", err), http.StatusBadRequest)
		return
	}

	code := strings.TrimSpace(req.Code)
	state := strings.TrimSpace(req.State)
	if raw := strings.TrimSpace(req.CallbackURL); raw != "" {
		if u, err := url.Parse(raw); err == nil {
			if code == "" {
				code = strings.TrimSpace(u.Query().Get("code"))
			}
			if state == "" {
				state = strings.TrimSpace(u.Query().Get("state"))
			}
		}
	}
	if code == "" {
		http.Error(w, "missing authorization code", http.StatusBadRequest)
		return
	}
	if state != "" && state != flow.OAuthState {
		h.setOAuthFlowError(flow.ID, "state mismatch")
		w.Header().Set("Content-Type", "application/json")
		updated, _ := h.getOAuthFlow(flow.ID)
		_ = json.NewEncoder(w).Encode(flowToResponse(updated))
		return
	}

	cfg, err := oauthConfigForProvider(flow.Provider)
	if err != nil {
		h.setOAuthFlowError(flow.ID, err.Error())
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	cred, err := oauthExchangeCodeForTokens(cfg, code, flow.CodeVerifier, flow.RedirectURI)
	if err != nil {
		h.setOAuthFlowError(flow.ID, fmt.Sprintf("token exchange failed: %v", err))
		w.Header().Set("Content-Type", "application/json")
		updated, _ := h.getOAuthFlow(flow.ID)
		_ = json.NewEncoder(w).Encode(flowToResponse(updated))
		return
	}
	if err := h.persistCredentialAndConfig(flow.Provider, oauthMethodTokenOrOAuth(flow.Method), cred); err != nil {
		h.setOAuthFlowError(flow.ID, fmt.Sprintf("failed to save credential: %v", err))
		w.Header().Set("Content-Type", "application/json")
		updated, _ := h.getOAuthFlow(flow.ID)
		_ = json.NewEncoder(w).Encode(flowToResponse(updated))
		return
	}
	h.setOAuthFlowSuccess(flow.ID)
	updated, _ := h.getOAuthFlow(flow.ID)
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(flowToResponse(updated))
}

'''
    s = s.replace(marker, helper + marker, 1)
# add net/url import if missing
if '"net/url"' not in s:
    s = s.replace('''\t"net/http"
''', '''\t"net/http"
\t"net/url"
''', 1)
path.write_text(s)

# Backend: OpenAI OAuth fetch returns Codex models only when logged in; no API key leak needed.
path = Path('web/backend/api/models.go')
s = path.read_text()
if 'func codexOAuthModels() []upstreamModel' not in s:
    s = s.replace('''func antigravityCuratedModels() []upstreamModel {
''', r'''func codexOAuthModels() []upstreamModel {
	return []upstreamModel{
		{ID: "gpt-5.5", OwnedBy: "openai-codex"},
		{ID: "gpt-5.5-review", OwnedBy: "openai-codex"},
		{ID: "gpt-5.4", OwnedBy: "openai-codex"},
		{ID: "gpt-5.4-review", OwnedBy: "openai-codex"},
		{ID: "gpt-5.4-mini", OwnedBy: "openai-codex"},
		{ID: "gpt-5.4-mini-review", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-review", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-xhigh", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-xhigh-review", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-high", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-high-review", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-low", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-low-review", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-none", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-none-review", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-spark", OwnedBy: "openai-codex"},
		{ID: "gpt-5.3-codex-spark-review", OwnedBy: "openai-codex"},
	}
}

func fetchCodexOAuthModels(ctx context.Context) ([]upstreamModel, error) {
	cred, err := auth.GetCredential("openai")
	if err != nil {
		return nil, err
	}
	if cred == nil {
		return nil, fmt.Errorf("openai oauth credentials not configured")
	}
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	default:
		return codexOAuthModels(), nil
	}
}

func antigravityCuratedModels() []upstreamModel {
''', 1)
s = s.replace('''\tswitch strings.ToLower(provider) {
\tcase "antigravity":
''', '''\tswitch strings.ToLower(provider) {
\tcase "openai":
\t\tif strings.TrimSpace(apiKey) == "" {
\t\t\treturn fetchCodexOAuthModels(ctx)
\t\t}
\t\tfetchURL = apiBase + "/models"
\t\treturn fetchOpenAICompatibleModels(ctx, fetchURL, apiKey)
\tcase "antigravity":
''', 1)
path.write_text(s)

# Frontend API: submit pasted callback.
path = Path('web/frontend/src/api/oauth.ts')
s = path.read_text()
if 'submitOAuthCallback' not in s:
    s += r'''

export async function submitOAuthCallback(
  flowID: string,
  callbackURL: string,
): Promise<OAuthFlowState> {
  return request<OAuthFlowState>(
    `/api/oauth/flows/${encodeURIComponent(flowID)}/callback`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ callback_url: callbackURL }),
    },
  )
}
'''
path.write_text(s)

# Frontend hook: keep active flow and expose paste submit.
path = Path('web/frontend/src/hooks/use-credentials-page.ts')
s = path.read_text()
s = s.replace('''  pollOAuthFlow,
} from "@/api/oauth"
''', '''  pollOAuthFlow,
  submitOAuthCallback,
} from "@/api/oauth"
''')
if 'const [callbackURL, setCallbackURL]' not in s:
    s = s.replace('''  const [anthropicToken, setAnthropicToken] = useState("")
''', '''  const [anthropicToken, setAnthropicToken] = useState("")
  const [callbackURL, setCallbackURL] = useState("")
''', 1)
if 'const submitCallbackURL = useCallback' not in s:
    s = s.replace('''  const saveToken = useCallback(
''', r'''  const submitCallbackURL = useCallback(async () => {
    if (!activeFlow?.flow_id || !callbackURL.trim()) return
    setError("")
    try {
      const flow = await submitOAuthCallback(activeFlow.flow_id, callbackURL.trim())
      setActiveFlow(flow)
      setCallbackURL("")
      if (flow.status === "success") {
        setWatchFlowID("")
        setWatchMode("")
        setActiveAction("")
        await loadProviders()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("credentials.errors.loginFailed"))
    }
  }, [activeFlow?.flow_id, callbackURL, loadProviders, t])

'''
    + '''  const saveToken = useCallback(
''', 1)
s = s.replace('''    openAIToken,
    anthropicToken,
''', '''    openAIToken,
    anthropicToken,
    callbackURL,
''')
s = s.replace('''    setOpenAIToken,
    setAnthropicToken,
''', '''    setOpenAIToken,
    setAnthropicToken,
    setCallbackURL,
''')
s = s.replace('''    startOpenAIDeviceCode,
    stopLoading,
''', '''    startOpenAIDeviceCode,
    submitCallbackURL,
    stopLoading,
''')
path.write_text(s)

# Frontend credentials page/card: show callback paste box during OpenAI browser flow.
path = Path('web/frontend/src/components/credentials/credentials-page.tsx')
s = path.read_text()
s = s.replace('''    anthropicToken,
''', '''    anthropicToken,
    callbackURL,
''')
s = s.replace('''    setAnthropicToken,
''', '''    setAnthropicToken,
    setCallbackURL,
''')
s = s.replace('''    startOpenAIDeviceCode,
''', '''    startOpenAIDeviceCode,
    submitCallbackURL,
''')
s = s.replace('''              onTokenChange={setOpenAIToken}
''', '''              onTokenChange={setOpenAIToken}
              callbackURL={callbackURL}
              onCallbackURLChange={setCallbackURL}
              onSubmitCallbackURL={() => void submitCallbackURL()}
''')
path.write_text(s)

path = Path('web/frontend/src/components/credentials/openai-credential-card.tsx')
s = path.read_text()
s = s.replace('''  token: string
  onTokenChange: (value: string) => void
''', '''  token: string
  callbackURL: string
  onTokenChange: (value: string) => void
  onCallbackURLChange: (value: string) => void
  onSubmitCallbackURL: () => void
''')
s = s.replace('''  token,
  onTokenChange,
''', '''  token,
  callbackURL,
  onTokenChange,
  onCallbackURLChange,
  onSubmitCallbackURL,
''')
s = s.replace('''            <div className="min-h-9 flex-1">
''', '''            {browserLoading && (
              <div className="flex gap-2">
                <Input
                  value={callbackURL}
                  onChange={(e) => onCallbackURLChange(e.target.value)}
                  placeholder="Paste final callback URL/code from auth.openai.com"
                />
                <Button size="sm" disabled={!callbackURL.trim()} onClick={onSubmitCallbackURL}>
                  Submit
                </Button>
              </div>
            )}

            <div className="min-h-9 flex-1">
''', 1)
path.write_text(s)

# Frontend combo: dynamic fetch only from active providers (oauth logged in or configured available model). No common_models fallback.
path = Path('web/frontend/src/components/combos/combos-page.tsx')
s = path.read_text()
s = s.replace('''  getModels,
  updateModel,
} from "@/api/models"
''', '''  getModels,
  updateModel,
  fetchUpstreamModels,
} from "@/api/models"
''')
if 'const [dynamicChoices, setDynamicChoices]' not in s:
    s = s.replace('''  const [saving, setSaving] = useState(false)
''', '''  const [saving, setSaving] = useState(false)
  const [dynamicChoices, setDynamicChoices] = useState<Record<string, ComboChoice[]>>({})
''')
if 'const activeProviderKeys = useMemo' not in s:
    s = s.replace('''  const selectedSet = useMemo(() => new Set(draft.models), [draft.models])
''', r'''  const activeProviderKeys = useMemo(() => {
    const active = new Set<string>()
    for (const model of models) {
      if ((model.fallbacks?.length ?? 0) > 0 || model.is_virtual || !model.available) continue
      const key = getCanonicalProviderKey(model.provider, providerOptions)
      if (key) active.add(key)
    }
    return active
  }, [models, providerOptions])

  useEffect(() => {
    let canceled = false
    const loadDynamicChoices = async () => {
      const next: Record<string, ComboChoice[]> = {}
      await Promise.all(providerOptions.map(async (option) => {
        const key = getCanonicalProviderKey(option.id, providerOptions)
        if (!key || !activeProviderKeys.has(key) || !option.supports_fetch) return
        try {
          const data = await fetchUpstreamModels({ provider: key })
          next[key] = (data.models || []).map((model) => ({
            provider: key,
            model: model.id,
            name: model.id,
            value: `${key}/${model.id}`,
          }))
        } catch {
          next[key] = []
        }
      }))
      if (!canceled) setDynamicChoices(next)
    }
    void loadDynamicChoices()
    return () => { canceled = true }
  }, [activeProviderKeys, providerOptions])

  const selectedSet = useMemo(() => new Set(draft.models), [draft.models])
''', 1)
start = s.find('  const providerGroups = useMemo(() => {')
end = s.find('  const selectedSet = useMemo', start)
if start != -1 and end != -1:
    replacement = r'''  const activeProviderKeys = useMemo(() => {
    const active = new Set<string>()
    for (const model of models) {
      if ((model.fallbacks?.length ?? 0) > 0 || model.is_virtual || !model.available) continue
      const key = getCanonicalProviderKey(model.provider, providerOptions)
      if (key) active.add(key)
    }
    return active
  }, [models, providerOptions])

  useEffect(() => {
    let canceled = false
    const loadDynamicChoices = async () => {
      const next: Record<string, ComboChoice[]> = {}
      await Promise.all(providerOptions.map(async (option) => {
        const key = getCanonicalProviderKey(option.id, providerOptions)
        if (!key || !activeProviderKeys.has(key) || !option.supports_fetch) return
        try {
          const data = await fetchUpstreamModels({ provider: key })
          next[key] = (data.models || []).map((model) => ({
            provider: key,
            model: model.id,
            name: model.id,
            value: `${key}/${model.id}`,
          }))
        } catch {
          next[key] = []
        }
      }))
      if (!canceled) setDynamicChoices(next)
    }
    void loadDynamicChoices()
    return () => { canceled = true }
  }, [activeProviderKeys, providerOptions])

  const providerGroups = useMemo(() => {
    const grouped = new Map<string, ComboChoice[]>()
    const seen = new Set<string>()
    const addChoice = (choice: ComboChoice) => {
      if (!activeProviderKeys.has(choice.provider) || seen.has(choice.value)) return
      seen.add(choice.value)
      grouped.set(choice.provider, [...(grouped.get(choice.provider) || []), choice])
    }
    for (const choices of Object.values(dynamicChoices)) {
      for (const choice of choices) addChoice(choice)
    }
    for (const model of models) {
      if ((model.fallbacks?.length ?? 0) > 0 || model.is_virtual || !model.available) continue
      const provider = getCanonicalProviderKey(model.provider, providerOptions)
      if (!provider) continue
      addChoice({ provider, model: model.model, name: model.model_name, value: `${provider}/${model.model}`, configured: true })
    }
    return [...grouped.entries()].sort(([a], [b]) => {
      const ap = providerMap.get(a)?.priority ?? 0
      const bp = providerMap.get(b)?.priority ?? 0
      if (ap !== bp) return bp - ap
      return (providerMap.get(a)?.label || a).localeCompare(providerMap.get(b)?.label || b)
    })
  }, [activeProviderKeys, dynamicChoices, models, providerMap, providerOptions])

'''
    s = s[:start] + replacement + s[end:]
path.write_text(s)
