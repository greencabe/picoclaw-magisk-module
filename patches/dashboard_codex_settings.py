from pathlib import Path

# Backend API: /api/models/codex-settings
p = Path("web/backend/api/models.go")
s = p.read_text()
s = s.replace('"net/url"\n', '"net/url"\n\t"os"\n')
s = s.replace(
    'mux.HandleFunc("POST /api/models/test-inline", h.handleTestInlineModel)\n',
    'mux.HandleFunc("POST /api/models/test-inline", h.handleTestInlineModel)\n\tmux.HandleFunc("GET /api/models/codex-settings", h.handleGetCodexSettings)\n\tmux.HandleFunc("PUT /api/models/codex-settings", h.handlePutCodexSettings)\n',
)
append = '''

type codexSettingsResponse struct {
	ReasoningEffort string `json:"reasoning_effort"`
}

func codexReasoningEffortPath() string {
	return strings.TrimRight(config.GetHome(), "/") + "/codex-reasoning-effort"
}

func normalizeCodexReasoningEffort(value string) string {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "none", "minimal", "low", "medium", "high", "xhigh":
		return strings.ToLower(strings.TrimSpace(value))
	default:
		return "low"
	}
}

func readCodexReasoningEffort() string {
	data, err := os.ReadFile(codexReasoningEffortPath())
	if err != nil {
		return "low"
	}
	return normalizeCodexReasoningEffort(string(data))
}

func (h *Handler) handleGetCodexSettings(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(codexSettingsResponse{ReasoningEffort: readCodexReasoningEffort()})
}

func (h *Handler) handlePutCodexSettings(w http.ResponseWriter, r *http.Request) {
	var req codexSettingsResponse
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON", http.StatusBadRequest)
		return
	}
	effort := normalizeCodexReasoningEffort(req.ReasoningEffort)
	if err := os.WriteFile(codexReasoningEffortPath(), []byte(effort+"\\n"), 0o644); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(codexSettingsResponse{ReasoningEffort: effort})
}
'''
if "type codexSettingsResponse" not in s:
    s += append
p.write_text(s)

# Frontend API
p = Path("web/frontend/src/api/models.ts")
s = p.read_text()
add = '''
export type CodexReasoningEffort = "none" | "minimal" | "low" | "medium" | "high" | "xhigh"

export interface CodexSettings {
  reasoning_effort: CodexReasoningEffort
}

export async function getCodexSettings(): Promise<CodexSettings> {
  return request<CodexSettings>("/api/models/codex-settings")
}

export async function updateCodexSettings(
  settings: CodexSettings,
): Promise<CodexSettings> {
  return request<CodexSettings>("/api/models/codex-settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  })
}
'''
if "getCodexSettings" not in s:
    s += add
p.write_text(s)

# Frontend Models page
p = Path("web/frontend/src/components/models/models-page.tsx")
s = p.read_text()
s = s.replace("IconDatabase,\n", "IconBrain,\n  IconDatabase,\n")
s = s.replace("type ModelInfo,\n", "type CodexReasoningEffort,\n  type ModelInfo,\n")
s = s.replace("getModels,\n", "getCodexSettings,\n  getModels,\n")
s = s.replace("setDefaultModel,\n", "setDefaultModel,\n  updateCodexSettings,\n")
s = s.replace(
    'import { Button } from "@/components/ui/button"\n',
    'import { Button } from "@/components/ui/button"\nimport { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"\nimport { Label } from "@/components/ui/label"\nimport { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"\n',
)
s = s.replace(
    'const [fetchError, setFetchError] = useState("")\n',
    'const [fetchError, setFetchError] = useState("")\n  const [codexEffort, setCodexEffort] = useState<CodexReasoningEffort>("low")\n  const [savingCodexEffort, setSavingCodexEffort] = useState(false)\n',
)
s = s.replace(
    'useEffect(() => {\n    fetchModels()\n  }, [fetchModels])\n',
    'useEffect(() => {\n    fetchModels()\n    getCodexSettings()\n      .then((settings) => setCodexEffort(settings.reasoning_effort))\n      .catch(() => undefined)\n  }, [fetchModels])\n',
)
marker = "  const handleSetDefault = async (model: ModelInfo) => {"
handler = '''  const handleCodexEffortChange = async (value: CodexReasoningEffort) => {
    setCodexEffort(value)
    setSavingCodexEffort(true)
    try {
      await updateCodexSettings({ reasoning_effort: value })
      toast.success("Codex reasoning effort saved")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save Codex settings")
    } finally {
      setSavingCodexEffort(false)
    }
  }

'''
if "handleCodexEffortChange" not in s:
    s = s.replace(marker, handler + marker)
settings_card = '''        <Card className="mt-4">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <IconBrain className="text-muted-foreground size-5" />
              <div>
                <CardTitle className="text-base">Settings</CardTitle>
                <CardDescription>
                  Codex OAuth behavior for OpenAI models.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-2 sm:max-w-xs">
              <Label htmlFor="codex-reasoning-effort">Codex reasoning effort</Label>
              <Select
                value={codexEffort}
                onValueChange={(value) => {
                  void handleCodexEffortChange(value as CodexReasoningEffort)
                }}
                disabled={savingCodexEffort}
              >
                <SelectTrigger id="codex-reasoning-effort">
                  <SelectValue placeholder="Select effort" />
                </SelectTrigger>
                <SelectContent>
                  {(["none", "minimal", "low", "medium", "high", "xhigh"] as CodexReasoningEffort[]).map((effort) => (
                    <SelectItem key={effort} value={effort}>
                      {effort}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-muted-foreground text-xs">
                Stored at /data/adb/picoclaw/codex-reasoning-effort.
              </p>
            </div>
          </CardContent>
        </Card>

'''
if "codex-reasoning-effort" not in s:
    s = s.replace("        {loading && (", settings_card + "        {loading && (")
p.write_text(s)
