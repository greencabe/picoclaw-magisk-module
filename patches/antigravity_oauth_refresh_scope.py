from pathlib import Path

path = Path('pkg/auth/oauth.go')
s = path.read_text()
old = '''\tdata := url.Values{
\t\t"client_id":     {cfg.ClientID},
\t\t"grant_type":    {"refresh_token"},
\t\t"refresh_token": {cred.RefreshToken},
\t\t"scope":         {"openid profile email"},
\t}
'''
new = '''\tdata := url.Values{
\t\t"client_id":     {cfg.ClientID},
\t\t"grant_type":    {"refresh_token"},
\t\t"refresh_token": {cred.RefreshToken},
\t}
\tif strings.TrimSpace(cfg.Scopes) != "" {
\t\tdata.Set("scope", cfg.Scopes)
\t} else {
\t\tdata.Set("scope", "openid profile email")
\t}
'''
if new not in s:
    if old not in s:
        raise SystemExit('RefreshAccessToken scope anchor not found')
    s = s.replace(old, new, 1)
path.write_text(s)

path = Path('pkg/providers/oauth/antigravity_provider.go')
s = path.read_text()
old = '''\tvar result struct {
\t\tCloudAICompanionProject string `json:"cloudaicompanionProject"`
\t}
\tif err := json.Unmarshal(body, &result); err != nil {
\t\treturn "", err
\t}

\tif result.CloudAICompanionProject == "" {
\t\treturn "", fmt.Errorf("no project ID in loadCodeAssist response")
\t}

\treturn result.CloudAICompanionProject, nil
'''
new = '''\tvar result struct {
\t\tCloudAICompanionProject any `json:"cloudaicompanionProject"`
\t}
\tif err := json.Unmarshal(body, &result); err != nil {
\t\treturn "", err
\t}

\tswitch project := result.CloudAICompanionProject.(type) {
\tcase string:
\t\tproject = strings.TrimSpace(project)
\t\tif project != "" {
\t\t\treturn project, nil
\t\t}
\tcase map[string]any:
\t\tif id, ok := project["id"].(string); ok && strings.TrimSpace(id) != "" {
\t\t\treturn strings.TrimSpace(id), nil
\t\t}
\t}

\treturn "", fmt.Errorf("no project ID in loadCodeAssist response")
'''
if new not in s:
    if old not in s:
        raise SystemExit('FetchAntigravityProjectID parse anchor not found')
    s = s.replace(old, new, 1)
path.write_text(s)
