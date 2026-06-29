from pathlib import Path

path = Path('pkg/providers/oauth/antigravity_provider.go')
s = path.read_text()

old_consts = '''\tantigravityUserAgent    = "antigravity"
\tantigravityXGoogClient  = "google-cloud-sdk vscode_cloudshelleditor/0.1"
\tantigravityVersion      = "1.15.8"
'''
new_consts = '''\tantigravityUserAgent    = "antigravity"
\tantigravityXGoogClient  = "google-cloud-sdk vscode_cloudshelleditor/0.1"
\tantigravityVersion      = "1.0.14"
\tantigravityClientName   = "aidev_client"
'''

old_header = '''\treq.Header.Set("User-Agent", fmt.Sprintf("antigravity/%s linux/amd64", antigravityVersion))
'''
new_header = '''\treq.Header.Set("User-Agent", fmt.Sprintf("antigravity/cli/%s (%s; os_type=darwin; arch=arm64)", antigravityVersion, antigravityClientName))
'''

if new_consts in s and new_header in s:
    raise SystemExit(0)
if old_consts not in s:
    raise SystemExit('antigravity const anchor not found')
if old_header not in s:
    raise SystemExit('antigravity user-agent anchor not found')

s = s.replace(old_consts, new_consts, 1)
s = s.replace(old_header, new_header, 1)
path.write_text(s)
