from pathlib import Path

# Models page: display combo/fallback entries under a separate Custom provider group.
path = Path('web/frontend/src/components/models/models-page.tsx')
s = path.read_text()
old = '''  for (const model of models) {
    const providerKey = getCanonicalProviderKey(model.provider, providerOptions)
    const providerDef = providerKey ? providerMap.get(providerKey) : undefined
    if (!grouped[providerKey]) {
      grouped[providerKey] = {
        provider: {
          key: providerKey,
          label: providerDef?.label || providerKey,
          iconSlug: providerDef?.iconSlug,
          domain: providerDef?.domain,
        },
        models: [],
      }
    }
    grouped[providerKey].models.push(model)
  }
'''
new = '''  for (const model of models) {
    const isCombo = (model.fallbacks?.length ?? 0) > 0
    const providerKey = isCombo
      ? "custom"
      : getCanonicalProviderKey(model.provider, providerOptions)
    const providerDef = providerKey ? providerMap.get(providerKey) : undefined
    if (!grouped[providerKey]) {
      grouped[providerKey] = {
        provider: {
          key: providerKey,
          label: isCombo ? "Custom" : providerDef?.label || providerKey,
          iconSlug: isCombo ? undefined : providerDef?.iconSlug,
          domain: isCombo ? undefined : providerDef?.domain,
        },
        models: [],
      }
    }
    grouped[providerKey].models.push(model)
  }
'''
s = s.replace(old, new, 1)
path.write_text(s)

# Credentials hook already has one active flow; expose callback paste to Antigravity too.
path = Path('web/frontend/src/components/credentials/credentials-page.tsx')
s = path.read_text()
s = s.replace('''            <AntigravityCredentialCard
              status={antigravityStatus}
              activeAction={activeAction}
              onStopLoading={stopLoading}
              onStartBrowserOAuth={() =>
                void startBrowserOAuth("google-antigravity")
              }
              onAskLogout={() => askLogout("google-antigravity")}
            />
''', '''            <AntigravityCredentialCard
              status={antigravityStatus}
              activeAction={activeAction}
              callbackURL={callbackURL}
              onCallbackURLChange={setCallbackURL}
              onSubmitCallbackURL={() => void submitCallbackURL()}
              onStopLoading={stopLoading}
              onStartBrowserOAuth={() =>
                void startBrowserOAuth("google-antigravity")
              }
              onAskLogout={() => askLogout("google-antigravity")}
            />
''', 1)
path.write_text(s)

# OpenAI callback UI: make card taller and stack controls cleanly on mobile.
path = Path('web/frontend/src/components/credentials/openai-credential-card.tsx')
s = path.read_text()
s = s.replace('''        <div className="border-muted flex h-[120px] flex-col rounded-lg border p-3">
          <div className="flex h-full flex-col gap-3">
''', '''        <div className="border-muted flex min-h-[12rem] flex-col rounded-lg border p-3">
          <div className="flex h-full flex-col gap-3">
''')
s = s.replace('''              <div className="flex flex-nowrap items-center gap-2 overflow-x-auto">
''', '''              <div className="flex flex-wrap items-center gap-2">
''')
s = s.replace('''            {browserLoading && (
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
''', '''            {browserLoading && (
              <div className="rounded-md border border-dashed p-2">
                <p className="text-muted-foreground mb-2 text-xs">
                  If the browser does not return automatically, paste the final OpenAI callback URL/code here.
                </p>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Input
                    value={callbackURL}
                    onChange={(e) => onCallbackURLChange(e.target.value)}
                    placeholder="http://localhost:1455/auth/callback?code=..."
                    className="min-w-0 flex-1"
                  />
                  <Button size="sm" disabled={!callbackURL.trim()} onClick={onSubmitCallbackURL}>
                    Submit
                  </Button>
                </div>
              </div>
            )}
''')
path.write_text(s)

# Antigravity: same optional callback paste fallback.
path = Path('web/frontend/src/components/credentials/antigravity-credential-card.tsx')
s = path.read_text()
if 'import { Button } from "@/components/ui/button"' in s and 'components/ui/input' not in s:
    s = s.replace('''import { Button } from "@/components/ui/button"
''', '''import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
''')
s = s.replace('''  activeAction: string
  onStopLoading: () => void
''', '''  activeAction: string
  callbackURL: string
  onCallbackURLChange: (value: string) => void
  onSubmitCallbackURL: () => void
  onStopLoading: () => void
''')
s = s.replace('''  activeAction,
  onStopLoading,
''', '''  activeAction,
  callbackURL,
  onCallbackURLChange,
  onSubmitCallbackURL,
  onStopLoading,
''')
s = s.replace('''        <div className="border-muted flex h-[120px] flex-col justify-center rounded-lg border p-3">
          <div className="flex flex-wrap items-center gap-2">
''', '''        <div className="border-muted flex min-h-[12rem] flex-col justify-center gap-3 rounded-lg border p-3">
          <div className="flex flex-wrap items-center gap-2">
''')
s = s.replace('''          </div>
        </div>
''', '''          </div>
          {browserLoading && (
            <div className="rounded-md border border-dashed p-2">
              <p className="text-muted-foreground mb-2 text-xs">
                Optional fallback: paste the final Google callback URL/code if browser return fails.
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  value={callbackURL}
                  onChange={(e) => onCallbackURLChange(e.target.value)}
                  placeholder="http://127.0.0.1:18800/oauth/callback?code=..."
                  className="min-w-0 flex-1"
                />
                <Button size="sm" disabled={!callbackURL.trim()} onClick={onSubmitCallbackURL}>
                  Submit
                </Button>
              </div>
            </div>
          )}
        </div>
''', 1)
path.write_text(s)
