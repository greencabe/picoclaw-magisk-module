from pathlib import Path

path = Path('pkg/auth/oauth.go')
s = path.read_text()
needle = '''var (
	openBrowserFunc             = OpenBrowser
	browserLoginInput io.Reader = os.Stdin
)
'''
insert = needle + r'''

func init() {
	if runtime.GOOS != "android" {
		return
	}
	resolver := &net.Resolver{
		PreferGo: true,
		Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
			dialer := net.Dialer{Timeout: 5 * time.Second}
			return dialer.DialContext(ctx, "udp", "8.8.8.8:53")
		},
	}
	dialer := &net.Dialer{
		Timeout:  30 * time.Second,
		Resolver: resolver,
	}
	http.DefaultTransport = &http.Transport{
		Proxy:                 http.ProxyFromEnvironment,
		DialContext:           dialer.DialContext,
		ForceAttemptHTTP2:     true,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
	}
}
'''
if insert in s:
    raise SystemExit(0)
if needle not in s:
    raise SystemExit('oauth var anchor not found')
s = s.replace(needle, insert, 1)
path.write_text(s)
