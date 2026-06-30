from pathlib import Path

# Store Codex/OpenAI OAuth logins under openai:<account_id> too, so repeated login does not destroy account pool.
path = Path('web/backend/api/oauth.go')
s = path.read_text()
old = '''\tif err := oauthSetCredential(provider, &cp); err != nil {
\t\treturn fmt.Errorf("saving credential: %w", err)
\t}
'''
new = '''\tif err := oauthSetCredential(provider, &cp); err != nil {
\t\treturn fmt.Errorf("saving credential: %w", err)
\t}
\tif provider == oauthProviderOpenAI && strings.TrimSpace(cp.AccountID) != "" {
\t\tif err := oauthSetCredential(provider+":"+strings.TrimSpace(cp.AccountID), &cp); err != nil {
\t\t\treturn fmt.Errorf("saving account credential: %w", err)
\t\t}
\t}
'''
if new not in s:
    s = s.replace(old, new, 1)
path.write_text(s)

# Make auth store preserve provider:account keys instead of canonicalizing them into the base provider.
path = Path('pkg/auth/store.go')
s = path.read_text()
if 'func credentialStoreKey(provider string) string {' not in s:
    s = s.replace('''func canonicalProvider(provider string) string {
''', '''func credentialStoreKey(provider string) string {
\tnormalized := strings.ToLower(strings.TrimSpace(provider))
\tif base, suffix, ok := strings.Cut(normalized, ":"); ok && strings.TrimSpace(suffix) != "" {
\t\treturn canonicalProvider(base) + ":" + strings.TrimSpace(suffix)
\t}
\treturn canonicalProvider(normalized)
}

func canonicalProvider(provider string) string {
''', 1)
s = s.replace('cred, ok := store.Credentials[canonicalProvider(provider)]', 'cred, ok := store.Credentials[credentialStoreKey(provider)]')
s = s.replace('canonical := canonicalProvider(provider)\n\tnormalized := cloneCredential(cred)', 'canonical := credentialStoreKey(provider)\n\tbaseProvider, _, _ := strings.Cut(canonical, ":")\n\tnormalized := cloneCredential(cred)')
s = s.replace('normalized.Provider = canonicalProvider(normalized.Provider)\n\t\tif normalized.Provider == "" {\n\t\t\tnormalized.Provider = canonical\n\t\t}', 'normalized.Provider = canonicalProvider(normalized.Provider)\n\t\tif normalized.Provider == "" {\n\t\t\tnormalized.Provider = baseProvider\n\t\t}')
s = s.replace('delete(store.Credentials, canonicalProvider(provider))', 'delete(store.Credentials, credentialStoreKey(provider))')
path.write_text(s)

# Codex provider chooses among openai + openai:<account_id> credentials round-robin, refreshing selected account.
path = Path('pkg/providers/oauth/codex_provider.go')
s = path.read_text()
if 'sync/atomic' not in s:
    s = s.replace('''\t"fmt"
\t"strings"
''', '''\t"fmt"
\t"sync/atomic"
\t"strings"
''', 1)
if 'codexCredentialCursor' not in s:
    s = s.replace('''const defaultCodexInstructions = "You are Codex, a coding assistant."
''', '''const defaultCodexInstructions = "You are Codex, a coding assistant."

var codexCredentialCursor uint64

type codexStoredCredential struct {
\tkey  string
\tcred *auth.AuthCredential
}

func loadCodexStoredCredentials() ([]codexStoredCredential, error) {
\tstore, err := auth.LoadStore()
\tif err != nil {
\t\treturn nil, err
\t}
\tout := make([]codexStoredCredential, 0, len(store.Credentials))
\tfor key, cred := range store.Credentials {
\t\tif cred == nil || cred.AccessToken == "" {
\t\t\tcontinue
\t\t}
\t\tif key == "openai" || strings.HasPrefix(key, "openai:") {
\t\t\tout = append(out, codexStoredCredential{key: key, cred: cred})
\t\t}
\t}
\tif len(out) == 0 {
\t\treturn nil, fmt.Errorf("no credentials for openai. Run: picoclaw auth login --provider openai")
\t}
\treturn out, nil
}
''', 1)
old = '''func CreateCodexTokenSource() func() (string, string, error) {
\treturn func() (string, string, error) {
\t\tcred, err := auth.GetCredential("openai")
\t\tif err != nil {
\t\t\treturn "", "", fmt.Errorf("loading auth credentials: %w", err)
\t\t}
\t\tif cred == nil {
\t\t\treturn "", "", fmt.Errorf("no credentials for openai. Run: picoclaw auth login --provider openai")
\t\t}

\t\tif cred.AuthMethod == "oauth" && cred.NeedsRefresh() && cred.RefreshToken != "" {
\t\t\toauthCfg := auth.OpenAIOAuthConfig()
\t\t\trefreshed, err := auth.RefreshAccessToken(cred, oauthCfg)
\t\t\tif err != nil {
\t\t\t\treturn "", "", fmt.Errorf("refreshing token: %w", err)
\t\t\t}
\t\t\tif refreshed.AccountID == "" {
\t\t\t\trefreshed.AccountID = cred.AccountID
\t\t\t}
\t\t\tif err := auth.SetCredential("openai", refreshed); err != nil {
\t\t\t\treturn "", "", fmt.Errorf("saving refreshed token: %w", err)
\t\t\t}
\t\t\treturn refreshed.AccessToken, refreshed.AccountID, nil
\t\t}

\t\treturn cred.AccessToken, cred.AccountID, nil
\t}
}
'''
new = '''func CreateCodexTokenSource() func() (string, string, error) {
\treturn func() (string, string, error) {
\t\tcredentials, err := loadCodexStoredCredentials()
\t\tif err != nil {
\t\t\treturn "", "", fmt.Errorf("loading auth credentials: %w", err)
\t\t}
\t\tselected := credentials[int(atomic.AddUint64(&codexCredentialCursor, 1)-1)%len(credentials)]
\t\tcred := selected.cred

\t\tif cred.AuthMethod == "oauth" && cred.NeedsRefresh() && cred.RefreshToken != "" {
\t\t\toauthCfg := auth.OpenAIOAuthConfig()
\t\t\trefreshed, err := auth.RefreshAccessToken(cred, oauthCfg)
\t\t\tif err != nil {
\t\t\t\treturn "", "", fmt.Errorf("refreshing token: %w", err)
\t\t\t}
\t\t\tif refreshed.AccountID == "" {
\t\t\t\trefreshed.AccountID = cred.AccountID
\t\t\t}
\t\t\tif err := auth.SetCredential(selected.key, refreshed); err != nil {
\t\t\t\treturn "", "", fmt.Errorf("saving refreshed token: %w", err)
\t\t\t}
\t\t\tif selected.key != "openai" && refreshed.AccountID != "" {
\t\t\t\t_ = auth.SetCredential("openai", refreshed)
\t\t\t}
\t\t\treturn refreshed.AccessToken, refreshed.AccountID, nil
\t\t}

\t\treturn cred.AccessToken, cred.AccountID, nil
\t}
}
'''
if old not in s:
    raise SystemExit('CreateCodexTokenSource anchor not found')
s = s.replace(old, new, 1)
path.write_text(s)
