from pathlib import Path

# Backend auth store helper: list/delete account-scoped credentials.
path = Path('pkg/auth/store.go')
s = path.read_text()
if 'func ListCredentialsForProvider(provider string)' not in s:
    s += r'''

func ListCredentialsForProvider(provider string) (map[string]*AuthCredential, error) {
	store, err := LoadStore()
	if err != nil {
		return nil, err
	}
	base := credentialStoreKey(provider)
	out := make(map[string]*AuthCredential)
	for key, cred := range store.Credentials {
		if key == base || strings.HasPrefix(key, base+":") {
			out[key] = cloneCredential(cred)
		}
	}
	return out, nil
}
'''
path.write_text(s)

# Backend OAuth API: expose account list and remove account key. Also save Antigravity account-scoped keys.
path = Path('web/backend/api/oauth.go')
s = path.read_text()
if 'AccountKey  string `json:"account_key,omitempty"`' not in s:
    s = s.replace('''type oauthProviderStatus struct {
	Provider    string   `json:"provider"`
''', '''type oauthAccountStatus struct {
	AccountKey string `json:"account_key"`
	AccountID  string `json:"account_id,omitempty"`
	Email      string `json:"email,omitempty"`
	ProjectID  string `json:"project_id,omitempty"`
	Status     string `json:"status"`
}

type oauthProviderStatus struct {
	Provider    string   `json:"provider"`
''', 1)
    s = s.replace('''	ProjectID   string   `json:"project_id,omitempty"`
}
''', '''	ProjectID   string   `json:"project_id,omitempty"`
	Accounts    []oauthAccountStatus `json:"accounts,omitempty"`
}
''', 1)
if 'AccountKey  string `json:"account_key,omitempty"`' not in s:
    s = s.replace('''	Token    string `json:"token"`
}
''', '''	Token       string `json:"token"`
	AccountKey  string `json:"account_key,omitempty"`
}
''', 1)
if 'item.Accounts = oauthAccountsForProvider(provider)' not in s:
    s = s.replace('''		if cred != nil {
''', '''		item.Accounts = oauthAccountsForProvider(provider)

		if cred != nil {
''', 1)
if 'func oauthAccountsForProvider(provider string)' not in s:
    s = s.replace('''func oauthConfigForProvider(provider string) (auth.OAuthProviderConfig, error) {
''', r'''func oauthAccountsForProvider(provider string) []oauthAccountStatus {
	items, err := auth.ListCredentialsForProvider(provider)
	if err != nil || len(items) == 0 {
		return nil
	}
	accounts := make([]oauthAccountStatus, 0, len(items))
	for key, cred := range items {
		if cred == nil {
			continue
		}
		status := "connected"
		if cred.IsExpired() {
			status = "expired"
		} else if cred.NeedsRefresh() {
			status = "needs_refresh"
		}
		accounts = append(accounts, oauthAccountStatus{
			AccountKey: key,
			AccountID:  cred.AccountID,
			Email:      cred.Email,
			ProjectID:  cred.ProjectID,
			Status:     status,
		})
	}
	return accounts
}

'''+'''func oauthConfigForProvider(provider string) (auth.OAuthProviderConfig, error) {
''', 1)
if 'if req.AccountKey != "" {' not in s:
    s = s.replace('''	if err := oauthDeleteCredential(provider); err != nil {
''', '''	if strings.TrimSpace(req.AccountKey) != "" {
		if err := oauthDeleteCredential(strings.TrimSpace(req.AccountKey)); err != nil {
			http.Error(w, fmt.Sprintf("failed to delete account credential: %v", err), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{"status": "ok", "provider": provider})
		return
	}

	if err := oauthDeleteCredential(provider); err != nil {
''', 1)
if 'provider == oauthProviderGoogleAntigravity && strings.TrimSpace(cp.Email+cp.ProjectID) != ""' not in s:
    s = s.replace('''	if provider == oauthProviderOpenAI && strings.TrimSpace(cp.AccountID) != "" {
		if err := oauthSetCredential(provider+":"+strings.TrimSpace(cp.AccountID), &cp); err != nil {
			return fmt.Errorf("saving account credential: %w", err)
		}
	}
''', '''	if provider == oauthProviderOpenAI && strings.TrimSpace(cp.AccountID) != "" {
		if err := oauthSetCredential(provider+":"+strings.TrimSpace(cp.AccountID), &cp); err != nil {
			return fmt.Errorf("saving account credential: %w", err)
		}
	}
	if provider == oauthProviderGoogleAntigravity && strings.TrimSpace(cp.Email+cp.ProjectID) != "" {
		key := strings.TrimSpace(cp.Email)
		if key == "" {
			key = strings.TrimSpace(cp.ProjectID)
		}
		if err := oauthSetCredential(provider+":"+key, &cp); err != nil {
			return fmt.Errorf("saving antigravity account credential: %w", err)
		}
	}
''', 1)
path.write_text(s)

# Antigravity provider: choose from google-antigravity:* accounts round-robin, refresh selected key.
path = Path('pkg/providers/oauth/antigravity_provider.go')
s = path.read_text()
if 'sync/atomic' not in s:
    s = s.replace('''	"fmt"
	"io"
''', '''	"fmt"
	"io"
	"sync/atomic"
''', 1)
if 'antigravityCredentialCursor' not in s:
    s = s.replace('''type AntigravityOAuthProvider struct {
''', '''var antigravityCredentialCursor uint64

type antigravityStoredCredential struct {
	key  string
	cred *auth.AuthCredential
}

func loadAntigravityStoredCredentials() ([]antigravityStoredCredential, error) {
	store, err := auth.LoadStore()
	if err != nil {
		return nil, err
	}
	out := make([]antigravityStoredCredential, 0, len(store.Credentials))
	for key, cred := range store.Credentials {
		if cred == nil || cred.AccessToken == "" {
			continue
		}
		if key == "google-antigravity" || strings.HasPrefix(key, "google-antigravity:") {
			out = append(out, antigravityStoredCredential{key: key, cred: cred})
		}
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("google-antigravity credentials not configured")
	}
	return out, nil
}

type AntigravityOAuthProvider struct {
''', 1)
old = '''func antigravityOAuthCredential() (*auth.AuthCredential, error) {
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
	return cred, nil
}
'''
new = '''func antigravityOAuthCredential() (*auth.AuthCredential, error) {
	credentials, err := loadAntigravityStoredCredentials()
	if err != nil {
		return nil, err
	}
	selected := credentials[int(atomic.AddUint64(&antigravityCredentialCursor, 1)-1)%len(credentials)]
	cred := selected.cred
	if cred.NeedsRefresh() && cred.RefreshToken != "" {
		refreshed, err := auth.RefreshAccessToken(cred, auth.GoogleAntigravityOAuthConfig())
		if err != nil {
			return nil, err
		}
		refreshed.Email = cred.Email
		if refreshed.ProjectID == "" {
			refreshed.ProjectID = cred.ProjectID
		}
		if err := auth.SetCredential(selected.key, refreshed); err != nil {
			return nil, err
		}
		if selected.key != "google-antigravity" {
			_ = auth.SetCredential("google-antigravity", refreshed)
		}
		cred = refreshed
	}
	if cred.IsExpired() {
		return nil, fmt.Errorf("google-antigravity credentials expired")
	}
	return cred, nil
}
'''
if old in s:
    s = s.replace(old, new, 1)
path.write_text(s)

# Models fetch helper Antigravity also round-robins accounts.
path = Path('web/backend/api/models.go')
s = path.read_text()
if 'antigravityModelCredentialCursor' not in s:
    s = s.replace('''type upstreamModel struct {
''', '''var antigravityModelCredentialCursor uint64

type upstreamModel struct {
''', 1)
if '"sync/atomic"' not in s:
    s = s.replace('''	"strings"
	"time"
''', '''	"strings"
	"sync/atomic"
	"time"
''')
old = '''func antigravityOAuthCredential() (*auth.AuthCredential, error) {
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
'''
new = '''func antigravityOAuthCredential() (*auth.AuthCredential, error) {
	credentials, err := auth.ListCredentialsForProvider("google-antigravity")
	if err != nil {
		return nil, err
	}
	keys := make([]string, 0, len(credentials))
	for key, cred := range credentials {
		if cred != nil && cred.AccessToken != "" {
			keys = append(keys, key)
		}
	}
	if len(keys) == 0 {
		return nil, fmt.Errorf("google-antigravity credentials not configured")
	}
	key := keys[int(atomic.AddUint64(&antigravityModelCredentialCursor, 1)-1)%len(keys)]
	cred := credentials[key]
	if cred.NeedsRefresh() && cred.RefreshToken != "" {
		refreshed, err := auth.RefreshAccessToken(cred, auth.GoogleAntigravityOAuthConfig())
		if err != nil {
			return nil, err
		}
		refreshed.Email = cred.Email
		if refreshed.ProjectID == "" {
			refreshed.ProjectID = cred.ProjectID
		}
		if err := auth.SetCredential(key, refreshed); err != nil {
			return nil, err
		}
		if key != "google-antigravity" {
			_ = auth.SetCredential("google-antigravity", refreshed)
		}
		cred = refreshed
	}
'''
s=s.replace(old,new,1)
path.write_text(s)

# Frontend OAuth API: account list + delete specific account.
path = Path('web/frontend/src/api/oauth.ts')
s = path.read_text()
if 'export interface OAuthAccountStatus' not in s:
    s = s.replace('''export interface OAuthProviderStatus {
''', '''export interface OAuthAccountStatus {
  account_key: string
  account_id?: string
  email?: string
  project_id?: string
  status: "connected" | "expired" | "needs_refresh" | "not_logged_in"
}

export interface OAuthProviderStatus {
''')
    s = s.replace('''  project_id?: string
}
''', '''  project_id?: string
  accounts?: OAuthAccountStatus[]
}
''', 1)
s = s.replace('''export async function logoutOAuth(
  provider: OAuthProvider,
): Promise<{ status: string; provider: OAuthProvider }> {
''', '''export async function logoutOAuth(
  provider: OAuthProvider,
  accountKey?: string,
): Promise<{ status: string; provider: OAuthProvider }> {
''')
s = s.replace('''      body: JSON.stringify({ provider }),
''', '''      body: JSON.stringify({ provider, account_key: accountKey }),
''')
path.write_text(s)

# Hook: delete account and expose handler.
path = Path('web/frontend/src/hooks/use-credentials-page.ts')
s = path.read_text()
if 'deleteAccount' not in s:
    insert = r'''  const deleteAccount = useCallback(
    async (provider: OAuthProvider, accountKey: string) => {
      const actionID = `${provider}:delete:${accountKey}`
      setActiveAction(actionID)
      setError("")
      try {
        await logoutOAuth(provider, accountKey)
        await loadProviders()
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : t("credentials.errors.logoutFailed"),
        )
      } finally {
        setActiveAction("")
      }
    },
    [loadProviders, t],
  )

'''
    s = s.replace('''  const askLogout = useCallback((provider: OAuthProvider) => {
''', insert + '''  const askLogout = useCallback((provider: OAuthProvider) => {
''')
    s = s.replace('''    saveToken,
    askLogout,
''', '''    saveToken,
    deleteAccount,
    askLogout,
''')
path.write_text(s)

# Credentials page pass deleteAccount.
path = Path('web/frontend/src/components/credentials/credentials-page.tsx')
s = path.read_text()
s = s.replace('''    saveToken,
    askLogout,
''', '''    saveToken,
    deleteAccount,
    askLogout,
''')
s = s.replace('''              onAskLogout={() => askLogout("openai")}
''', '''              onDeleteAccount={(accountKey) => void deleteAccount("openai", accountKey)}
              onAskLogout={() => askLogout("openai")}
''')
s = s.replace('''              onAskLogout={() => askLogout("google-antigravity")}
''', '''              onDeleteAccount={(accountKey) =>
                void deleteAccount("google-antigravity", accountKey)
              }
              onAskLogout={() => askLogout("google-antigravity")}
''')
path.write_text(s)

# OpenAI card: compact callback until user taps paste, plus accounts list delete buttons.
path = Path('web/frontend/src/components/credentials/openai-credential-card.tsx')
s = path.read_text()
if 'IconTrash' not in s:
    s = s.replace('''  IconPlayerStopFilled,
} from "@tabler/icons-react"
''', '''  IconPlayerStopFilled,
  IconTrash,
} from "@tabler/icons-react"
''')
if 'useState' not in s:
    s = s.replace('''import { useTranslation } from "react-i18next"
''', '''import { useState } from "react"
import { useTranslation } from "react-i18next"
''')
s = s.replace('''  onSubmitCallbackURL: () => void
  onStartBrowserOAuth: () => void
''', '''  onSubmitCallbackURL: () => void
  onDeleteAccount: (accountKey: string) => void
  onStartBrowserOAuth: () => void
''')
s = s.replace('''  onSubmitCallbackURL,
  onStartBrowserOAuth,
''', '''  onSubmitCallbackURL,
  onDeleteAccount,
  onStartBrowserOAuth,
''')
s = s.replace('''  const actionBusy = activeAction !== ""
''', '''  const [showCallbackPaste, setShowCallbackPaste] = useState(false)
  const actionBusy = activeAction !== ""
''')
s = s.replace('''            {browserLoading && (
              <div className="rounded-md border border-dashed p-2">
''', '''            {browserLoading && !showCallbackPaste && (
              <Button size="sm" variant="ghost" onClick={() => setShowCallbackPaste(true)}>
                Paste callback manually
              </Button>
            )}

            {browserLoading && showCallbackPaste && (
              <div className="rounded-md border border-dashed p-2">
''')
s = s.replace('''                  <Button size="sm" disabled={!callbackURL.trim()} onClick={onSubmitCallbackURL}>
                    Submit
                  </Button>
''', '''                  <Button size="sm" disabled={!callbackURL.trim()} onClick={onSubmitCallbackURL}>
                    Submit
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setShowCallbackPaste(false)}>
                    Hide
                  </Button>
''')
s = s.replace('''          </div>
        </div>
      }
''', '''          </div>
          {(status?.accounts?.length ?? 0) > 0 && (
            <div className="mt-3 space-y-1 rounded-md border p-2 text-xs">
              <p className="text-muted-foreground font-medium">Accounts</p>
              {status?.accounts?.map((account) => (
                <div key={account.account_key} className="flex items-center justify-between gap-2">
                  <span className="min-w-0 truncate font-mono">
                    {account.account_id || account.email || account.project_id || account.account_key}
                  </span>
                  <Button
                    size="icon-xs"
                    variant="ghost"
                    onClick={() => onDeleteAccount(account.account_key)}
                    disabled={activeAction !== ""}
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <IconTrash className="size-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      }
''', 1)
path.write_text(s)

# Antigravity card: compact callback fallback + accounts list delete.
path = Path('web/frontend/src/components/credentials/antigravity-credential-card.tsx')
s = path.read_text()
if 'IconTrash' not in s:
    s = s.replace('''  IconPlayerStopFilled,
} from "@tabler/icons-react"
''', '''  IconPlayerStopFilled,
  IconTrash,
} from "@tabler/icons-react"
''')
if 'useState' not in s:
    s = s.replace('''import { useTranslation } from "react-i18next"
''', '''import { useState } from "react"
import { useTranslation } from "react-i18next"
''')
s = s.replace('''  onSubmitCallbackURL: () => void
  onStopLoading: () => void
''', '''  onSubmitCallbackURL: () => void
  onDeleteAccount: (accountKey: string) => void
  onStopLoading: () => void
''')
s = s.replace('''  onSubmitCallbackURL,
  onStopLoading,
''', '''  onSubmitCallbackURL,
  onDeleteAccount,
  onStopLoading,
''')
s = s.replace('''  const actionBusy = activeAction !== ""
''', '''  const [showCallbackPaste, setShowCallbackPaste] = useState(false)
  const actionBusy = activeAction !== ""
''')
s = s.replace('''          {browserLoading && (
            <div className="rounded-md border border-dashed p-2">
''', '''          {browserLoading && !showCallbackPaste && (
            <Button size="sm" variant="ghost" onClick={() => setShowCallbackPaste(true)}>
              Paste callback manually
            </Button>
          )}

          {browserLoading && showCallbackPaste && (
            <div className="rounded-md border border-dashed p-2">
''')
s = s.replace('''                <Button size="sm" disabled={!callbackURL.trim()} onClick={onSubmitCallbackURL}>
                  Submit
                </Button>
''', '''                <Button size="sm" disabled={!callbackURL.trim()} onClick={onSubmitCallbackURL}>
                  Submit
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowCallbackPaste(false)}>
                  Hide
                </Button>
''')
s = s.replace('''          )}
        </div>
      }
''', '''          )}
          {(status?.accounts?.length ?? 0) > 0 && (
            <div className="space-y-1 rounded-md border p-2 text-xs">
              <p className="text-muted-foreground font-medium">Accounts</p>
              {status?.accounts?.map((account) => (
                <div key={account.account_key} className="flex items-center justify-between gap-2">
                  <span className="min-w-0 truncate font-mono">
                    {account.email || account.project_id || account.account_key}
                  </span>
                  <Button
                    size="icon-xs"
                    variant="ghost"
                    onClick={() => onDeleteAccount(account.account_key)}
                    disabled={activeAction !== ""}
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <IconTrash className="size-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      }
''', 1)
path.write_text(s)

# Correct Antigravity runtime token source anchor in upstream provider.
path = Path('pkg/providers/oauth/antigravity_provider.go')
s = path.read_text()
old = '''func createAntigravityTokenSource() func() (string, string, error) {
	return func() (string, string, error) {
		cred, err := auth.GetCredential("google-antigravity")
		if err != nil {
			return "", "", fmt.Errorf("loading auth credentials: %w", err)
		}
		if cred == nil {
			return "", "", fmt.Errorf(
				"no credentials for google-antigravity. Run: picoclaw auth login --provider google-antigravity",
			)
		}

		// Refresh if needed
		if cred.NeedsRefresh() && cred.RefreshToken != "" {
			oauthCfg := auth.GoogleAntigravityOAuthConfig()
			refreshed, err := auth.RefreshAccessToken(cred, oauthCfg)
			if err != nil {
				return "", "", fmt.Errorf("refreshing token: %w", err)
			}
			refreshed.Email = cred.Email
			if refreshed.ProjectID == "" {
				refreshed.ProjectID = cred.ProjectID
			}
			if err := auth.SetCredential("google-antigravity", refreshed); err != nil {
				return "", "", fmt.Errorf("saving refreshed token: %w", err)
			}
			cred = refreshed
		}
'''
new = '''func createAntigravityTokenSource() func() (string, string, error) {
	return func() (string, string, error) {
		credentials, err := loadAntigravityStoredCredentials()
		if err != nil {
			return "", "", fmt.Errorf("loading auth credentials: %w", err)
		}
		selected := credentials[int(atomic.AddUint64(&antigravityCredentialCursor, 1)-1)%len(credentials)]
		cred := selected.cred

		// Refresh if needed
		if cred.NeedsRefresh() && cred.RefreshToken != "" {
			oauthCfg := auth.GoogleAntigravityOAuthConfig()
			refreshed, err := auth.RefreshAccessToken(cred, oauthCfg)
			if err != nil {
				return "", "", fmt.Errorf("refreshing token: %w", err)
			}
			refreshed.Email = cred.Email
			if refreshed.ProjectID == "" {
				refreshed.ProjectID = cred.ProjectID
			}
			if err := auth.SetCredential(selected.key, refreshed); err != nil {
				return "", "", fmt.Errorf("saving refreshed token: %w", err)
			}
			if selected.key != "google-antigravity" {
				_ = auth.SetCredential("google-antigravity", refreshed)
			}
			cred = refreshed
		}
'''
if old in s:
    s=s.replace(old,new,1)
path.write_text(s)

# Insert Antigravity multi-account helpers for actual upstream type name.
path = Path('pkg/providers/oauth/antigravity_provider.go')
s = path.read_text()
if 'func loadAntigravityStoredCredentials()' not in s:
    s = s.replace('''type AntigravityProvider struct {
''', '''var antigravityCredentialCursor uint64

type antigravityStoredCredential struct {
	key  string
	cred *auth.AuthCredential
}

func loadAntigravityStoredCredentials() ([]antigravityStoredCredential, error) {
	store, err := auth.LoadStore()
	if err != nil {
		return nil, err
	}
	out := make([]antigravityStoredCredential, 0, len(store.Credentials))
	for key, cred := range store.Credentials {
		if cred == nil || cred.AccessToken == "" {
			continue
		}
		if key == "google-antigravity" || strings.HasPrefix(key, "google-antigravity:") {
			out = append(out, antigravityStoredCredential{key: key, cred: cred})
		}
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("google-antigravity credentials not configured")
	}
	return out, nil
}

type AntigravityProvider struct {
''', 1)
path.write_text(s)

# Fix model API imports and logout request shape.
path = Path('web/backend/api/models.go')
s = path.read_text()
if '"sync/atomic"' not in s:
    s = s.replace('''\t"sync"
\t"time"
''', '''\t"sync"
\t"sync/atomic"
\t"time"
''')
path.write_text(s)

path = Path('web/backend/api/oauth.go')
s = path.read_text()
s = s.replace('''\tvar req struct {
\t\tProvider string `json:"provider"`
\t}
''', '''\tvar req struct {
\t\tProvider   string `json:"provider"`
\t\tAccountKey string `json:"account_key,omitempty"`
\t}
''', 1)
path.write_text(s)
