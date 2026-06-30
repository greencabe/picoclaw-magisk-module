from pathlib import Path
import re

# Backend: expose model fallbacks in API.
path = Path('web/backend/api/models.go')
s = path.read_text()
if 'Fallbacks  []string `json:"fallbacks,omitempty"`' not in s:
    s = s.replace('''\tProxy      string `json:"proxy,omitempty"`
\tAuthMethod string `json:"auth_method,omitempty"`
''', '''\tProxy      string   `json:"proxy,omitempty"`
\tFallbacks  []string `json:"fallbacks,omitempty"`
\tAuthMethod string   `json:"auth_method,omitempty"`
''', 1)
if 'Fallbacks:           append([]string(nil), m.Fallbacks...),' not in s:
    s = s.replace('''\t\t\tProxy:               m.Proxy,
\t\t\tAuthMethod:          m.AuthMethod,
''', '''\t\t\tProxy:               m.Proxy,
\t\t\tFallbacks:           append([]string(nil), m.Fallbacks...),
\t\t\tAuthMethod:          m.AuthMethod,
''', 1)
path.write_text(s)

# Runtime: optional combo round-robin strategy stored in extra_body.combo_strategy.
path = Path('pkg/agent/model_resolution.go')
s = path.read_text()
if 'comboRotationMu' not in s:
    s = s.replace('''import (
\t"fmt"
\t"strings"
''', '''import (
\t"fmt"
\t"sync"
\t"strings"
''', 1)
    s = s.replace('func resolveModelCandidates(\n', '''var comboRotationMu sync.Mutex
var comboRotationState = map[string]int{}

func comboStrategyForModel(cfg *config.Config, modelName string) string {
\tif cfg == nil {
\t\treturn ""
\t}
\tmc, err := cfg.GetModelConfig(strings.TrimSpace(modelName))
\tif err != nil || mc == nil || len(mc.Fallbacks) == 0 || mc.ExtraBody == nil {
\t\treturn ""
\t}
\tif value, ok := mc.ExtraBody["combo_strategy"].(string); ok {
\t\treturn strings.ToLower(strings.TrimSpace(value))
\t}
\treturn ""
}

func applyComboCandidateStrategy(cfg *config.Config, primary string, candidates []providers.FallbackCandidate) []providers.FallbackCandidate {
\tif len(candidates) <= 1 || comboStrategyForModel(cfg, primary) != "round_robin" {
\t\treturn candidates
\t}
\tcomboRotationMu.Lock()
\tidx := comboRotationState[primary]
\tcomboRotationState[primary] = idx + 1
\tcomboRotationMu.Unlock()
\tshift := idx % len(candidates)
\tif shift == 0 {
\t\treturn candidates
\t}
\trotated := append([]providers.FallbackCandidate{}, candidates[shift:]...)
\trotated = append(rotated, candidates[:shift]...)
\treturn rotated
}

func resolveModelCandidates(\n''', 1)
s = s.replace('''\treturn candidates
}

func resolvedCandidateModel''', '''\treturn applyComboCandidateStrategy(cfg, primary, candidates)
}

func resolvedCandidateModel''', 1)
path.write_text(s)

# Frontend API: add fallbacks field.
path = Path('web/frontend/src/api/models.ts')
s = path.read_text()
if 'fallbacks?: string[]' not in s:
    s = s.replace('''  proxy?: string
  auth_method?: string
''', '''  proxy?: string
  fallbacks?: string[]
  auth_method?: string
''', 1)
path.write_text(s)

# Frontend: top-level Combos page with provider-grouped selector.
combo_dir = Path('web/frontend/src/components/combos')
combo_dir.mkdir(parents=True, exist_ok=True)
(combo_dir / 'combos-page.tsx').write_text(r'''import {
  IconArrowDown,
  IconArrowUp,
  IconGitBranch,
  IconLoader2,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import {
  type ModelInfo,
  type ModelProviderOption,
  addModel,
  deleteModel,
  getModels,
  updateModel,
} from "@/api/models"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { refreshGatewayState } from "@/store/gateway"

import { ProviderIcon } from "../models/provider-icon"
import {
  getCanonicalProviderKey,
  getProviderCatalogMap,
} from "../models/provider-registry"

type ComboStrategy = "fallback" | "round_robin"

interface ComboDraft {
  name: string
  strategy: ComboStrategy
  models: string[]
  editingIndex: number | null
}

const emptyDraft: ComboDraft = {
  name: "",
  strategy: "fallback",
  models: [],
  editingIndex: null,
}

function modelRef(model: ModelInfo) {
  const provider = (model.provider || "").trim()
  return provider ? `${provider}/${model.model}` : model.model
}

function parseModelRef(ref: string) {
  const slash = ref.indexOf("/")
  if (slash <= 0 || slash === ref.length - 1) return { provider: "", model: ref }
  return { provider: ref.slice(0, slash), model: ref.slice(slash + 1) }
}

function comboStrategy(model: ModelInfo): ComboStrategy {
  return model.extra_body?.combo_strategy === "round_robin" ? "round_robin" : "fallback"
}

export function CombosPage() {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [providerOptions, setProviderOptions] = useState<ModelProviderOption[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [draft, setDraft] = useState<ComboDraft>(emptyDraft)
  const [saving, setSaving] = useState(false)
  const providerMap = getProviderCatalogMap(providerOptions)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getModels()
      setModels(data.models || [])
      setProviderOptions(data.provider_options || [])
      setError("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load combos")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const combos = useMemo(() => models.filter((model) => (model.fallbacks?.length ?? 0) > 0), [models])
  const selectableModels = useMemo(() => models.filter((model) => (model.fallbacks?.length ?? 0) === 0 && !model.is_virtual && model.available), [models])
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
  const selectedSet = useMemo(() => new Set(draft.models), [draft.models])

  const addChoice = (ref: string) => setDraft((current) => current.models.includes(ref) ? current : { ...current, models: [...current.models, ref] })
  const removeChoice = (index: number) => setDraft((current) => ({ ...current, models: current.models.filter((_, idx) => idx !== index) }))
  const moveChoice = (index: number, direction: -1 | 1) => setDraft((current) => {
    const nextIndex = index + direction
    if (nextIndex < 0 || nextIndex >= current.models.length) return current
    const next = [...current.models]
    ;[next[index], next[nextIndex]] = [next[nextIndex], next[index]]
    return { ...current, models: next }
  })
  const editCombo = (combo: ModelInfo) => setDraft({ name: combo.model_name, strategy: comboStrategy(combo), models: [modelRef(combo), ...(combo.fallbacks || [])], editingIndex: combo.index })
  const reset = () => setDraft(emptyDraft)

  const save = async () => {
    const name = draft.name.trim()
    if (!/^[a-zA-Z0-9_.-]+$/.test(name)) return toast.error("Combo name can only use letters, numbers, -, _ and .")
    if (draft.models.length < 2) return toast.error("Combo needs at least two models")
    const primary = parseModelRef(draft.models[0])
    if (!primary.provider || !primary.model) return toast.error("Primary model must be provider/model")
    setSaving(true)
    try {
      const payload: Partial<ModelInfo> = {
        model_name: name,
        provider: primary.provider,
        model: primary.model,
        fallbacks: draft.models.slice(1),
        enabled: true,
        extra_body: { combo_strategy: draft.strategy },
      }
      if (draft.editingIndex === null) await addModel(payload)
      else await updateModel(draft.editingIndex, payload)
      await load()
      await refreshGatewayState({ force: true })
      reset()
      toast.success("Combo saved")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save combo")
    } finally {
      setSaving(false)
    }
  }

  const removeCombo = async (combo: ModelInfo) => {
    if (!globalThis.confirm(`Delete combo ${combo.model_name}?`)) return
    try {
      await deleteModel(combo.index)
      await load()
      await refreshGatewayState({ force: true })
      toast.success("Combo deleted")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete combo")
    }
  }

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Combos">
        <Button size="sm" variant="outline" onClick={reset}><IconPlus className="size-4" />New Combo</Button>
      </PageHeader>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-8 sm:px-6">
        <p className="text-muted-foreground mt-2 text-sm">Create 9router-style ordered combos from configured valid provider models. Fallback tries in order; Round Robin rotates first attempt.</p>
        {loading && <div className="flex items-center justify-center py-20"><IconLoader2 className="text-muted-foreground size-6 animate-spin" /></div>}
        {error && <div className="bg-destructive/10 text-destructive mt-4 rounded-lg px-4 py-3 text-sm">{error}</div>}
        {!loading && !error && (
          <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
            <section className="space-y-3">
              {combos.length === 0 ? <div className="text-muted-foreground rounded-xl border border-dashed p-6 text-sm">No combos yet. Pick provider models on the right and save one.</div> : combos.map((combo) => (
                <div key={combo.index} className="bg-card rounded-xl border p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2"><IconGitBranch className="text-primary size-4" /><span className="font-semibold">{combo.model_name}</span><span className="bg-muted text-muted-foreground rounded px-1.5 py-0.5 text-[10px] uppercase">{comboStrategy(combo).replace("_", " ")}</span></div>
                      <ol className="text-muted-foreground mt-3 list-decimal space-y-1 pl-5 font-mono text-xs">{[modelRef(combo), ...(combo.fallbacks || [])].map((item) => <li key={item}>{item}</li>)}</ol>
                    </div>
                    <div className="flex shrink-0 gap-1"><Button size="sm" variant="outline" onClick={() => editCombo(combo)}>Edit</Button><Button size="sm" variant="ghost" onClick={() => void removeCombo(combo)}>Delete</Button></div>
                  </div>
                </div>
              ))}
            </section>
            <aside className="bg-card h-fit rounded-xl border p-4">
              <div className="space-y-4">
                <div><label className="text-sm font-medium">Combo name</label><input className="bg-background mt-1 w-full rounded-md border px-3 py-2 text-sm" value={draft.name} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} placeholder="fast-fallback" /></div>
                <div><label className="text-sm font-medium">Strategy</label><select className="bg-background mt-1 w-full rounded-md border px-3 py-2 text-sm" value={draft.strategy} onChange={(event) => setDraft((current) => ({ ...current, strategy: event.target.value as ComboStrategy }))}><option value="fallback">Fallback order</option><option value="round_robin">Round Robin</option></select></div>
                <div><label className="text-sm font-medium">Selected models</label>{draft.models.length === 0 ? <div className="text-muted-foreground rounded-md border border-dashed p-3 text-xs">Select at least two models below.</div> : <div className="space-y-1">{draft.models.map((ref, index) => <div key={`${ref}-${index}`} className="bg-muted/50 flex items-center gap-1 rounded-md px-2 py-1 font-mono text-xs"><span className="text-muted-foreground min-w-5">{index + 1}.</span><span className="min-w-0 flex-1 truncate">{ref}</span><Button size="icon-sm" variant="ghost" disabled={index === 0} onClick={() => moveChoice(index, -1)}><IconArrowUp className="size-3" /></Button><Button size="icon-sm" variant="ghost" disabled={index === draft.models.length - 1} onClick={() => moveChoice(index, 1)}><IconArrowDown className="size-3" /></Button><Button size="icon-sm" variant="ghost" onClick={() => removeChoice(index)}><IconTrash className="size-3" /></Button></div>)}</div>}</div>
                <div className="max-h-80 overflow-y-auto rounded-md border p-2"><p className="text-muted-foreground mb-2 text-xs">Valid configured models by provider</p>{providerGroups.length === 0 ? <p className="text-muted-foreground text-xs">No available provider models. Add models first.</p> : <div className="space-y-3">{providerGroups.map(([providerKey, providerModels]) => { const provider = providerMap.get(providerKey); return <div key={providerKey}><div className="text-muted-foreground mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide"><ProviderIcon provider={{ key: providerKey, label: provider?.label || providerKey, iconSlug: provider?.iconSlug, domain: provider?.domain }} />{provider?.label || providerKey}</div><div className="flex flex-wrap gap-1">{providerModels.map((model) => { const ref = modelRef(model); const selected = selectedSet.has(ref); return <button key={model.index} type="button" disabled={selected} className={["rounded px-2 py-1 font-mono text-[11px] transition-colors", selected ? "bg-primary/10 text-primary cursor-not-allowed" : "bg-muted hover:bg-muted/80"].join(" ")} onClick={() => addChoice(ref)}>{model.model_name}</button> })}</div></div> })}</div>}</div>
                <div className="flex gap-2"><Button onClick={() => void save()} disabled={saving}>{saving ? "Saving..." : draft.editingIndex === null ? "Create" : "Save"}</Button>{draft.editingIndex !== null && <Button variant="outline" onClick={reset}>Cancel</Button>}</div>
              </div>
            </aside>
          </div>
        )}
      </div>
    </div>
  )
}
''')

# Route file.
Path('web/frontend/src/routes/combos.tsx').write_text('''import { createFileRoute } from "@tanstack/react-router"\n\nimport { CombosPage } from "@/components/combos/combos-page"\n\nexport const Route = createFileRoute("/combos")({\n  component: CombosPage,\n})\n''')

# Sidebar: menu item between Models and Credentials.
path = Path('web/frontend/src/components/app-sidebar.tsx')
s = path.read_text()
if 'IconGitBranch' not in s:
    s = s.replace('''  IconChevronsUp,
  IconKey,
''', '''  IconChevronsUp,
  IconGitBranch,
  IconKey,
''', 1)
if 'url: "/combos"' not in s:
    s = s.replace('''          {
            title: "navigation.models",
            url: "/models",
            icon: IconAtom,
            translateTitle: true,
          },
          {
            title: "navigation.credentials",
''', '''          {
            title: "navigation.models",
            url: "/models",
            icon: IconAtom,
            translateTitle: true,
          },
          {
            title: "navigation.combos",
            url: "/combos",
            icon: IconGitBranch,
            translateTitle: true,
          },
          {
            title: "navigation.credentials",
''', 1)
path.write_text(s)

# i18n labels.
for rel, label in [('web/frontend/src/i18n/locales/en.json', 'Combos'), ('web/frontend/src/i18n/locales/zh.json', '组合'), ('web/frontend/src/i18n/locales/pt-br.json', 'Combos')]:
    path = Path(rel)
    s = path.read_text()
    if '"combos"' not in s.split('"navigation"', 1)[1].split('}', 1)[0]:
        s = s.replace('''    "models": ''', f'''    "combos": "{label}",\n    "models": ''', 1)
    path.write_text(s)

# Patch routeTree.gen.ts for checked-in router tree. Idempotent: strip old combos, insert once.
path = Path('web/frontend/src/routeTree.gen.ts')
s = path.read_text()
s = s.replace("import { Route as CombosRouteImport } from './routes/combos'\n", "")
s = re.sub(r"const CombosRoute = CombosRouteImport\.update\(\{\n  id: '/combos',\n  path: '/combos',\n  getParentRoute: \(\) => rootRouteImport,\n\} as any\)\n", "", s)
s = s.replace("  '/combos': typeof CombosRoute\n", "")
s = s.replace("    | '/combos'\n", "")
s = s.replace("  CombosRoute: typeof CombosRoute\n", "")
s = s.replace("  CombosRoute: CombosRoute,\n", "")
s = re.sub(r"    '/combos': \{\n      id: '/combos'\n      path: '/combos'\n      fullPath: '/combos'\n      preLoaderRoute: typeof CombosRouteImport\n      parentRoute: typeof rootRouteImport\n    \}\n", "", s)
s = s.replace("import { Route as ModelsRouteImport } from './routes/models'\n", "import { Route as ModelsRouteImport } from './routes/models'\nimport { Route as CombosRouteImport } from './routes/combos'\n", 1)
s = s.replace("const ModelsRoute = ModelsRouteImport.update({\n  id: '/models',\n  path: '/models',\n  getParentRoute: () => rootRouteImport,\n} as any)\n", "const ModelsRoute = ModelsRouteImport.update({\n  id: '/models',\n  path: '/models',\n  getParentRoute: () => rootRouteImport,\n} as any)\nconst CombosRoute = CombosRouteImport.update({\n  id: '/combos',\n  path: '/combos',\n  getParentRoute: () => rootRouteImport,\n} as any)\n", 1)
s = s.replace("  '/credentials': typeof CredentialsRoute\n", "  '/combos': typeof CombosRoute\n  '/credentials': typeof CredentialsRoute\n", 3)
s = s.replace("    | '/credentials'\n", "    | '/combos'\n    | '/credentials'\n", 3)
s = s.replace("  CredentialsRoute: typeof CredentialsRoute\n", "  CombosRoute: typeof CombosRoute\n  CredentialsRoute: typeof CredentialsRoute\n", 1)
s = s.replace("    '/credentials': {\n", "    '/combos': {\n      id: '/combos'\n      path: '/combos'\n      fullPath: '/combos'\n      preLoaderRoute: typeof CombosRouteImport\n      parentRoute: typeof rootRouteImport\n    }\n    '/credentials': {\n", 1)
s = s.replace("  CredentialsRoute: CredentialsRoute,\n", "  CombosRoute: CombosRoute,\n  CredentialsRoute: CredentialsRoute,\n", 1)
path.write_text(s)
