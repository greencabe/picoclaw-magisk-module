from pathlib import Path

# Codex OAuth must match Codex/9router fixed redirect exactly.
path = Path('web/backend/api/oauth.go')
s = path.read_text()
old = '''\t\tredirectURI := buildOAuthRedirectURI(r)
\t\tauthURL := oauthBuildAuthorizeURL(cfg, pkce, state, redirectURI)
'''
new = '''\t\tredirectURI := buildOAuthRedirectURIForProvider(provider, r)
\t\tauthURL := oauthBuildAuthorizeURL(cfg, pkce, state, redirectURI)
'''
if old in s:
    s = s.replace(old, new, 1)
if 'func buildOAuthRedirectURIForProvider(provider string, r *http.Request) string {' not in s:
    s = s.replace('''func buildOAuthRedirectURI(r *http.Request) string {
''', '''func buildOAuthRedirectURIForProvider(provider string, r *http.Request) string {
\tif provider == oauthProviderOpenAI {
\t\treturn "http://localhost:1455/auth/callback"
\t}
\treturn buildOAuthRedirectURI(r)
}

func buildOAuthRedirectURI(r *http.Request) string {
''', 1)
path.write_text(s)

# OpenAI OAuth in PicoClaw is Codex backend. Expose the 9router Codex catalog in the picker.
path = Path('pkg/providers/provider_metadata.go')
s = path.read_text()
old = 'CommonModels:        []string{"gpt-5.4", "gpt-5.4-mini", "gpt-5.5"},'
new = 'CommonModels:        []string{"gpt-5.5", "gpt-5.5-review", "gpt-5.4", "gpt-5.4-review", "gpt-5.4-mini", "gpt-5.4-mini-review", "gpt-5.3-codex", "gpt-5.3-codex-review", "gpt-5.3-codex-xhigh", "gpt-5.3-codex-xhigh-review", "gpt-5.3-codex-high", "gpt-5.3-codex-high-review", "gpt-5.3-codex-low", "gpt-5.3-codex-low-review", "gpt-5.3-codex-none", "gpt-5.3-codex-none-review", "gpt-5.3-codex-spark", "gpt-5.3-codex-spark-review"},'
s = s.replace(old, new, 1)
old_ag = 'CommonModels:        []string{"gemini-3-flash-agent", "gemini-3.5-flash-low", "gemini-3.5-flash-extra-low", "gemini-pro-agent", "claude-sonnet-4-6", "claude-opus-4-6-thinking"},'
new_ag = 'CommonModels:        []string{"claude-opus-4-6-thinking", "claude-sonnet-4-6-thinking", "gemini-3-flash", "gemini-3.1-pro-high", "gemini-3.1-pro-low", "gemini-3.5-flash-high", "gemini-3.5-flash-low", "gemini-3.5-flash-medium", "gpt-oss-120b-medium"},'
s = s.replace(old_ag, new_ag, 1)
path.write_text(s)

# Combo UI: 9router-style picker uses all provider catalog models, then merges configured custom models.
path = Path('web/frontend/src/components/combos/combos-page.tsx')
s = path.read_text()
if 'interface ComboChoice {' not in s:
    s = s.replace('''interface ComboDraft {
  name: string
  strategy: ComboStrategy
  models: string[]
  editingIndex: number | null
}
''', '''interface ComboDraft {
  name: string
  strategy: ComboStrategy
  models: string[]
  editingIndex: number | null
}

interface ComboChoice {
  provider: string
  model: string
  name: string
  value: string
  configured?: boolean
}
''', 1)
s = s.replace('''  const selectableModels = useMemo(() => models.filter((model) => (model.fallbacks?.length ?? 0) === 0 && !model.is_virtual && model.available), [models])
  const providerGroups = useMemo(() => {
    const grouped = new Map<string, ModelInfo[]>()
    for (const model of selectableModels) {
      const key = getCanonicalProviderKey(model.provider, providerOptions)
      if (!key) continue
      grouped.set(key, [...(grouped.get(key) || []), model])
    }
    return [...grouped.entries()].sort(([a], [b]) => {
      const ap = providerMap.get(a)?.priority ?? 0
      const bp = providerMap.get(b)?.priority ?? 0
      if (ap !== bp) return bp - ap
      return (providerMap.get(a)?.label || a).localeCompare(providerMap.get(b)?.label || b)
    })
  }, [providerMap, providerOptions, selectableModels])
''', '''  const providerGroups = useMemo(() => {
    const grouped = new Map<string, ComboChoice[]>()
    const seen = new Set<string>()
    const addChoice = (provider: string, model: string, name?: string, configured?: boolean) => {
      const key = getCanonicalProviderKey(provider, providerOptions)
      const cleanModel = model.trim()
      if (!key || !cleanModel) return
      const value = `${key}/${cleanModel}`
      if (seen.has(value)) return
      seen.add(value)
      grouped.set(key, [...(grouped.get(key) || []), { provider: key, model: cleanModel, name: name || cleanModel, value, configured }])
    }
    for (const option of providerOptions) {
      if (!option.create_allowed) continue
      for (const model of option.common_models || []) addChoice(option.id, model)
    }
    for (const model of models) {
      if ((model.fallbacks?.length ?? 0) > 0 || model.is_virtual || !model.available) continue
      addChoice(model.provider || "", model.model, model.model_name, true)
    }
    return [...grouped.entries()].sort(([a], [b]) => {
      const ap = providerMap.get(a)?.priority ?? 0
      const bp = providerMap.get(b)?.priority ?? 0
      if (ap !== bp) return bp - ap
      return (providerMap.get(a)?.label || a).localeCompare(providerMap.get(b)?.label || b)
    })
  }, [models, providerMap, providerOptions])
''', 1)
s = s.replace('''{providerGroups.length === 0 ? <p className="text-muted-foreground text-xs">No available provider models. Add models first.</p>''', '''{providerGroups.length === 0 ? <p className="text-muted-foreground text-xs">No provider catalog models available.</p>''')
s = s.replace('''{providerModels.map((model) => { const ref = modelRef(model); const selected = selectedSet.has(ref); return <button key={model.index} type="button" disabled={selected} className={["rounded px-2 py-1 font-mono text-[11px] transition-colors", selected ? "bg-primary/10 text-primary cursor-not-allowed" : "bg-muted hover:bg-muted/80"].join(" ")} onClick={() => addChoice(ref)}>{model.model_name}</button> })}''', '''{providerModels.map((model) => { const selected = selectedSet.has(model.value); return <button key={model.value} type="button" disabled={selected} className={["rounded px-2 py-1 font-mono text-[11px] transition-colors", selected ? "bg-primary/10 text-primary cursor-not-allowed" : "bg-muted hover:bg-muted/80"].join(" ")} onClick={() => addChoice(model.value)}>{model.name}{model.configured ? " *" : ""}</button> })}''')
path.write_text(s)
