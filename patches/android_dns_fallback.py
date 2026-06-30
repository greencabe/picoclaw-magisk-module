from pathlib import Path

pkg_dir = Path('pkg/androidnet')
pkg_dir.mkdir(parents=True, exist_ok=True)
(pkg_dir / 'dns.go').write_text(r'''package androidnet

import (
	"context"
	"net"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"time"
)

func init() {
	if runtime.GOOS != "android" {
		return
	}
	servers := androidDNSServers()
	if len(servers) == 0 {
		return
	}
	net.DefaultResolver = &net.Resolver{
		PreferGo: true,
		Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
			dialer := &net.Dialer{Timeout: 2 * time.Second}
			var lastErr error
			for _, server := range servers {
				conn, err := dialer.DialContext(ctx, network, net.JoinHostPort(server, "53"))
				if err == nil {
					return conn, nil
				}
				lastErr = err
			}
			return nil, lastErr
		},
	}
}

func androidDNSServers() []string {
	seen := map[string]bool{}
	servers := make([]string, 0, 6)
	add := func(value string) {
		for _, part := range strings.FieldsFunc(value, func(r rune) bool {
			return r == ',' || r == ' ' || r == '\n' || r == '\t'
		}) {
			part = strings.TrimSpace(part)
			if part == "" || part == "::1" || part == "127.0.0.1" || seen[part] || net.ParseIP(part) == nil {
				continue
			}
			seen[part] = true
			servers = append(servers, part)
		}
	}
	add(os.Getenv("PICOCLAW_DNS_SERVERS"))
	for _, prop := range []string{"net.dns1", "net.dns2", "net.dns3", "net.dns4"} {
		out, err := exec.Command("/system/bin/getprop", prop).Output()
		if err == nil {
			add(string(out))
		}
	}
	add("8.8.8.8,1.1.1.1")
	return servers
}
''')

for file in [Path('cmd/picoclaw/main.go'), Path('web/backend/main.go')]:
    text = file.read_text()
    imp = '\n\t_ "github.com/sipeed/picoclaw/pkg/androidnet"\n'
    if 'github.com/sipeed/picoclaw/pkg/androidnet' not in text:
        marker = 'import (\n'
        text = text.replace(marker, marker + imp, 1)
        file.write_text(text)
