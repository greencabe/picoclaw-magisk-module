from pathlib import Path

# Backend: expose fallbacks in model API.
path = Path('web/backend/api/models.go')
s = path.read_text()
s = s.replace('''\tFallbacks []string `json:"fallbacks,omitempty"`\n''', '')
if 'Fallbacks []string `json:"fallbacks,omitempty"`' not in s:
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

# Runtime: support combo_strategy=round_robin stored in model extra_body.
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
    marker = 'func resolveModelCandidates(\n'
    insert = '''var comboRotationMu sync.Mutex
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

'''
    s = s.replace(marker, insert + marker, 1)
s = s.replace('''\treturn candidates
}

func resolvedCandidateModel''', '''\treturn applyComboCandidateStrategy(cfg, primary, candidates)
}

func resolvedCandidateModel''', 1)
path.write_text(s)

# Frontend API: add fallbacks.
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

# Frontend Models page: add Combos sub-tab and minimal combo editor.
path = Path('web/frontend/src/components/models/models-page.tsx')
s = path.read_text()
s = s.replace('''import {
  IconDatabase,
  IconLoader2,
  IconPlus,
  IconStar,
} from "@tabler/icons-react"
''', '''import {
  IconDatabase,
  IconGitBranch,
  IconLoader2,
  IconPlus,
  IconStar,
  IconTrash,
} from "@tabler/icons-react"
''')
s = s.replace('''  type ModelProviderOption,
  getModels,
  setDefaultModel,
} from "@/api/models"
''', '''  type ModelProviderOption,
  addModel,
  deleteModel,
  getModels,
  setDefaultModel,
  updateModel,
} from "@/api/models"
''')
if 'type ModelsTab = "models" | "combos"' not in s:
    s = s.replace('''interface ProviderGroup {
''', '''type ModelsTab = "models" | "combos"
type ComboStrategy = "fallback" | "round_robin"

interface ProviderGroup {
''', 1)

if 'const [activeTab, setActiveTab]' not in s:
    s = s.replace('''  const [catalogOpen, setCatalogOpen] = useState(false)
''', '''  const [catalogOpen, setCatalogOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<ModelsTab>("models")
  const [comboName, setComboName] = useState("")
  const [comboModels, setComboModels] = useState("")
  const [comboStrategy, setComboStrategy] = useState<ComboStrategy>("fallback")
  const [editingComboIndex, setEditingComboIndex] = useState<number | null>(null)
''', 1)

helpers = r'''
  const comboEntries = models.filter((model) => (model.fallbacks?.length ?? 0) > 0)
  const modelChoices = models.filter((model) => (model.fallbacks?.length ?? 0) === 0)

  const resetComboForm = () => {
    setComboName("")
    setComboModels("")
    setComboStrategy("fallback")
    setEditingComboIndex(null)
  }

  const strategyFromCombo = (model: ModelInfo): ComboStrategy => {
    const strategy = model.extra_body?.combo_strategy
    return strategy === "round_robin" ? "round_robin" : "fallback"
  }

  const modelRefForCombo = (model: ModelInfo) => {
    const provider = (model.provider || "").trim()
    return provider ? `${provider}/${model.model}` : model.model
  }

  const saveCombo = async () => {
    const name = comboName.trim()
    const refs = comboModels
      .split(/\n|,/)
      .map((item) => item.trim())
      .filter(Boolean)
    if (!name) {
      toast.error("Combo name required")
      return
    }
    if (refs.length < 2) {
      toast.error("Combo needs at least 2 models")
      return
    }
    const [primary, ...fallbacks] = refs
    const slash = primary.indexOf("/")
    const provider = slash > 0 ? primary.slice(0, slash) : ""
    const modelId = slash > 0 ? primary.slice(slash + 1) : primary
    const payload: Partial<ModelInfo> = {
      model_name: name,
      provider,
      model: modelId,
      fallbacks,
      enabled: true,
      extra_body: { combo_strategy: comboStrategy },
    }
    try {
      if (editingComboIndex === null) {
        await addModel(payload)
      } else {
        await updateModel(editingComboIndex, payload)
      }
      resetComboForm()
      await fetchModels()
      toast.success("Combo saved")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save combo")
    }
  }

  const editCombo = (model: ModelInfo) => {
    setComboName(model.model_name)
    setComboModels([modelRefForCombo(model), ...(model.fallbacks || [])].join("\n"))
    setComboStrategy(strategyFromCombo(model))
    setEditingComboIndex(model.index)
  }

  const removeCombo = async (model: ModelInfo) => {
    try {
      await deleteModel(model.index)
      if (editingComboIndex === model.index) resetComboForm()
      await fetchModels()
      toast.success("Combo deleted")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete combo")
    }
  }

'''
if 'const comboEntries = models.filter' not in s:
    s = s.replace('''  const defaultModel = models.find((model) => model.is_default)

  return (
''', helpers + '''  const defaultModel = models.find((model) => model.is_default)

  return (
''', 1)

# Header buttons: add tab selector and conditional actions.
s = s.replace('''      <PageHeader title={t("navigation.models")}>
        <div className="flex items-center gap-3">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setCatalogOpen(true)}
            disabled={providerOptions.length === 0}
          >
            <IconDatabase className="size-4" />
            {t("models.catalog.button")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setAddOpen(true)}
            disabled={providerOptions.length === 0}
          >
            <IconPlus className="size-4" />
            {t("models.add.button")}
          </Button>
        </div>
      </PageHeader>
''', '''      <PageHeader title={activeTab === "combos" ? "Combos" : t("navigation.models")}>
        <div className="flex items-center gap-2">
          <Button size="sm" variant={activeTab === "models" ? "default" : "outline"} onClick={() => setActiveTab("models")}>
            {t("navigation.models")}
          </Button>
          <Button size="sm" variant={activeTab === "combos" ? "default" : "outline"} onClick={() => setActiveTab("combos")}>
            <IconGitBranch className="size-4" />
            Combos
          </Button>
          {activeTab === "models" && (
            <>
              <Button size="sm" variant="outline" onClick={() => setCatalogOpen(true)} disabled={providerOptions.length === 0}>
                <IconDatabase className="size-4" />
                {t("models.catalog.button")}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setAddOpen(true)} disabled={providerOptions.length === 0}>
                <IconPlus className="size-4" />
                {t("models.add.button")}
              </Button>
            </>
          )}
        </div>
      </PageHeader>
''')

models_block = '''        {!loading && !fetchError && (
          <div className="pb-8">
            {providerGroups.map((providerGroup) => (
              <ProviderSection
                key={providerGroup.key}
                provider={providerGroup.provider}
                models={providerGroup.models}
                onEdit={setEditingModel}
                onSetDefault={handleSetDefault}
                onDelete={setDeletingModel}
                settingDefaultIndex={settingDefaultIndex}
              />
            ))}
          </div>
        )}
'''
combo_block = '''        {!loading && !fetchError && activeTab === "models" && (
          <div className="pb-8">
            {providerGroups.map((providerGroup) => (
              <ProviderSection
                key={providerGroup.key}
                provider={providerGroup.provider}
                models={providerGroup.models}
                onEdit={setEditingModel}
                onSetDefault={handleSetDefault}
                onDelete={setDeletingModel}
                settingDefaultIndex={settingDefaultIndex}
              />
            ))}
          </div>
        )}

        {!loading && !fetchError && activeTab === "combos" && (
          <div className="grid gap-4 pb-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
            <div className="space-y-3">
              <p className="text-muted-foreground text-sm">
                Group models under one name. Fallback tries in order; Round Robin rotates first model each request. Capacity auto-switch uses PicoClaw cooldown/fallback engine.
              </p>
              {comboEntries.length === 0 ? (
                <div className="text-muted-foreground rounded-xl border border-dashed p-6 text-sm">No combos yet.</div>
              ) : (
                comboEntries.map((combo) => (
                  <div key={combo.index} className="bg-card rounded-xl border p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{combo.model_name}</span>
                          <span className="bg-muted text-muted-foreground rounded px-1.5 py-0.5 text-[10px] uppercase">{strategyFromCombo(combo).replace("_", " ")}</span>
                        </div>
                        <ol className="text-muted-foreground mt-2 list-decimal space-y-1 pl-5 font-mono text-xs">
                          {[modelRefForCombo(combo), ...(combo.fallbacks || [])].map((item) => <li key={item}>{item}</li>)}
                        </ol>
                      </div>
                      <div className="flex shrink-0 gap-1">
                        <Button size="sm" variant="outline" onClick={() => editCombo(combo)}>Edit</Button>
                        <Button size="icon-sm" variant="ghost" onClick={() => void removeCombo(combo)} className="text-muted-foreground hover:text-destructive hover:bg-destructive/10">
                          <IconTrash className="size-3.5" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="bg-card h-fit rounded-xl border p-4">
              <h2 className="font-semibold">{editingComboIndex === null ? "Create Combo" : "Edit Combo"}</h2>
              <div className="mt-3 space-y-3">
                <label className="block text-sm">
                  <span className="text-muted-foreground">Name</span>
                  <input className="bg-background mt-1 w-full rounded-md border px-3 py-2" value={comboName} onChange={(e) => setComboName(e.target.value)} placeholder="always-on" />
                </label>
                <label className="block text-sm">
                  <span className="text-muted-foreground">Strategy</span>
                  <select className="bg-background mt-1 w-full rounded-md border px-3 py-2" value={comboStrategy} onChange={(e) => setComboStrategy(e.target.value as ComboStrategy)}>
                    <option value="fallback">Fallback</option>
                    <option value="round_robin">Round Robin</option>
                  </select>
                </label>
                <label className="block text-sm">
                  <span className="text-muted-foreground">Models, one per line</span>
                  <textarea className="bg-background mt-1 min-h-36 w-full rounded-md border px-3 py-2 font-mono text-xs" value={comboModels} onChange={(e) => setComboModels(e.target.value)} placeholder={"antigravity/gemini-3-flash-agent\\nantigravity/claude-sonnet-4-6"} />
                </label>
                {modelChoices.length > 0 && (
                  <div className="max-h-40 overflow-y-auto rounded-md border p-2">
                    <p className="text-muted-foreground mb-2 text-xs">Click to add existing model:</p>
                    <div className="flex flex-wrap gap-1">
                      {modelChoices.map((model) => (
                        <button key={model.index} type="button" className="bg-muted hover:bg-muted/80 rounded px-2 py-1 font-mono text-[11px]" onClick={() => setComboModels((value) => `${value}${value.trim() ? "\\n" : ""}${modelRefForCombo(model)}`)}>
                          {model.model_name}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <div className="flex gap-2">
                  <Button onClick={() => void saveCombo()}>{editingComboIndex === null ? "Create" : "Save"}</Button>
                  {editingComboIndex !== null && <Button variant="outline" onClick={resetComboForm}>Cancel</Button>}
                </div>
              </div>
            </div>
          </div>
        )}
'''
if models_block in s:
    s = s.replace(models_block, combo_block, 1)
else:
    raise SystemExit('models render block not found')

path.write_text(s)
