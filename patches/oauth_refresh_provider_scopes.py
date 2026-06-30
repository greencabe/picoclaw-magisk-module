from pathlib import Path
path = Path('pkg/auth/oauth.go')
text = path.read_text()
old = '''\tdata := url.Values{\n\t\t"client_id":     {cfg.ClientID},\n\t\t"grant_type":    {"refresh_token"},\n\t\t"refresh_token": {cred.RefreshToken},\n\t\t"scope":         {"openid profile email"},\n\t}\n'''
new = '''\tdata := url.Values{\n\t\t"client_id":     {cfg.ClientID},\n\t\t"grant_type":    {"refresh_token"},\n\t\t"refresh_token": {cred.RefreshToken},\n\t}\n\tif strings.TrimSpace(cfg.Scopes) != "" {\n\t\tdata.Set("scope", cfg.Scopes)\n\t}\n'''
if old not in text:
    raise SystemExit('target refresh scope block not found')
path.write_text(text.replace(old, new))
