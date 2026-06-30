from pathlib import Path

# 1) Persist latest WhatsApp native QR code where dashboard can read it.
p = Path('pkg/channels/whatsapp_native/whatsapp_native.go')
s = p.read_text()
old = '''\t\t\t\t\tif evt.Event == "code" {\n\t\t\t\t\t\tlogger.InfoCF("whatsapp", "Scan this QR code with WhatsApp (Linked Devices):", nil)\n\t\t\t\t\t\tqrterminal.GenerateWithConfig(evt.Code, qrterminal.Config{\n\t\t\t\t\t\t\tLevel:      qrterminal.L,\n\t\t\t\t\t\t\tWriter:     os.Stdout,\n\t\t\t\t\t\t\tHalfBlocks: true,\n\t\t\t\t\t\t})\n\t\t\t\t\t} else {\n\t\t\t\t\t\tlogger.InfoCF("whatsapp", "WhatsApp login event", map[string]any{"event": evt.Event})\n\t\t\t\t\t}\n'''
new = '''\t\t\t\t\tif evt.Event == "code" {\n\t\t\t\t\t\t_ = os.MkdirAll(c.storePath, 0o700)\n\t\t\t\t\t\t_ = os.WriteFile(filepath.Join(c.storePath, "qr.txt"), []byte(evt.Code), 0o600)\n\t\t\t\t\t\tlogger.InfoCF("whatsapp", "Scan this QR code with WhatsApp (Linked Devices):", nil)\n\t\t\t\t\t\tqrterminal.GenerateWithConfig(evt.Code, qrterminal.Config{\n\t\t\t\t\t\t\tLevel:      qrterminal.L,\n\t\t\t\t\t\t\tWriter:     os.Stdout,\n\t\t\t\t\t\t\tHalfBlocks: true,\n\t\t\t\t\t\t})\n\t\t\t\t\t} else {\n\t\t\t\t\t\tif evt.Event == "success" {\n\t\t\t\t\t\t\t_ = os.Remove(filepath.Join(c.storePath, "qr.txt"))\n\t\t\t\t\t\t}\n\t\t\t\t\t\tlogger.InfoCF("whatsapp", "WhatsApp login event", map[string]any{"event": evt.Event})\n\t\t\t\t\t}\n'''
if old not in s:
    raise SystemExit('whatsapp QR event block not found')
p.write_text(s.replace(old, new, 1))

# 2) Backend endpoint: GET /api/whatsapp-native/qr
Path('web/backend/api/whatsapp_native_qr.go').write_text(r'''package api

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

type whatsappNativeQRResponse struct {
	Status    string `json:"status"`
	QRDataURI string `json:"qr_data_uri,omitempty"`
	Error     string `json:"error,omitempty"`
}

func (h *Handler) registerWhatsAppNativeRoutes(mux *http.ServeMux) {
	mux.HandleFunc("GET /api/whatsapp-native/qr", h.handleWhatsAppNativeQR)
}

func (h *Handler) handleWhatsAppNativeQR(w http.ResponseWriter, r *http.Request) {
	if strings.TrimSpace(r.URL.Query().Get("active")) != "1" {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(whatsappNativeQRResponse{Status: "idle"})
		return
	}
	content, err := os.ReadFile(whatsappNativeQRPath())
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(whatsappNativeQRResponse{Status: "pending"})
		return
	}
	code := strings.TrimSpace(string(content))
	if code == "" {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(whatsappNativeQRResponse{Status: "pending"})
		return
	}
	dataURI, err := generateQRDataURI(code)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(whatsappNativeQRResponse{Status: "error", Error: err.Error()})
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(whatsappNativeQRResponse{Status: "code", QRDataURI: dataURI})
}

func whatsappNativeQRPath() string {
	home := strings.TrimSpace(os.Getenv("PICOCLAW_HOME"))
	if home == "" {
		home = "/data/adb/picoclaw"
	}
	return filepath.Join(home, "whatsapp", "qr.txt")
}
''')

# 3) Register backend route.
p = Path('web/backend/api/router.go')
s = p.read_text()
old = '''\t// WeCom QR login flow\n\th.registerWecomRoutes(mux)\n'''
new = '''\t// WeCom QR login flow\n\th.registerWecomRoutes(mux)\n\n\t// WhatsApp Native QR login display\n\th.registerWhatsAppNativeRoutes(mux)\n'''
if old not in s:
    raise SystemExit('router registration marker not found')
p.write_text(s.replace(old, new, 1))

# 4) Frontend API type + function.
p = Path('web/frontend/src/api/channels.ts')
s = p.read_text()
old = '''export interface WecomFlowResponse {\n  flow_id: string\n  status: "wait" | "scaned" | "confirmed" | "expired" | "error"\n  qr_data_uri?: string\n  bot_id?: string\n  error?: string\n}\n'''
new = old + '''\nexport interface WhatsAppNativeQRResponse {\n  status: "pending" | "code" | "error"\n  qr_data_uri?: string\n  error?: string\n}\n'''
if old not in s:
    raise SystemExit('api type marker not found')
s = s.replace(old, new, 1)
old = '''export async function pollWecomFlow(\n  flowID: string,\n): Promise<WecomFlowResponse> {\n  return request<WecomFlowResponse>(\n    `/api/wecom/flows/${encodeURIComponent(flowID)}`,\n  )\n}\n'''
new = old + '''\nexport async function getWhatsAppNativeQR(): Promise<WhatsAppNativeQRResponse> {\n  return request<WhatsAppNativeQRResponse>("/api/whatsapp-native/qr")\n}\n'''
if old not in s:
    raise SystemExit('api function marker not found')
p.write_text(s.replace(old, new, 1))

# 5) Frontend card component.
Path('web/frontend/src/components/channels/channel-forms/whatsapp-native-qr-card.tsx').write_text(r'''import { IconLoader2, IconQrcode, IconRefresh } from "@tabler/icons-react"
import { useCallback, useEffect, useRef, useState } from "react"

import { getWhatsAppNativeQR } from "@/api/channels"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export function WhatsAppNativeQRCard() {
  const [active, setActive] = useState(false)
  const [qrDataURI, setQrDataURI] = useState<string | null>(null)
  const [status, setStatus] = useState<"idle" | "loading" | "pending" | "code" | "error">("idle")
  const [error, setError] = useState("")
  const inFlightRef = useRef(false)

  const refresh = useCallback(async () => {
    if (!active || inFlightRef.current) return
    inFlightRef.current = true
    try {
      const resp = await getWhatsAppNativeQR(true)
      setStatus(resp.status)
      setQrDataURI(resp.qr_data_uri ?? null)
      setError(resp.error ?? "")
    } catch (e) {
      setStatus("error")
      setQrDataURI(null)
      setError(e instanceof Error ? e.message : "Failed to load WhatsApp QR")
    } finally {
      inFlightRef.current = false
    }
  }, [active])

  useEffect(() => {
    if (!active) return
    void refresh()
    const timer = setInterval(() => void refresh(), 2000)
    return () => clearInterval(timer)
  }, [active, refresh])

  const start = () => {
    setActive(true)
    setStatus("loading")
    setQrDataURI(null)
    setError("")
  }

  return (
    <Card className="border-border/60 shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <IconQrcode size={18} />
          WhatsApp QR Login
        </CardTitle>
        <CardDescription>
          Enable WhatsApp Native and restart service. Press Bind WhatsApp only when you need QR login.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!active ? (
          <div className="flex flex-col items-center gap-4 py-6">
            <p className="text-muted-foreground text-sm">QR hidden until binding starts.</p>
            <Button onClick={start} className="gap-2">
              <IconQrcode size={16} />
              Bind WhatsApp
            </Button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 py-2">
            {qrDataURI ? (
              <img
                src={qrDataURI}
                alt="WhatsApp QR Code"
                className="border-border/60 h-56 w-56 rounded-xl border bg-white p-2 shadow-sm"
              />
            ) : (
              <div className="border-border/60 bg-muted flex h-56 w-56 items-center justify-center rounded-xl border">
                <IconLoader2 className="text-muted-foreground animate-spin" size={32} />
              </div>
            )}
            {status === "code" ? (
              <p className="text-muted-foreground text-sm">Scan with WhatsApp → Linked devices → Link a device.</p>
            ) : status === "error" ? (
              <p className="text-destructive text-sm">{error || "QR unavailable"}</p>
            ) : (
              <p className="text-muted-foreground text-sm">Waiting for QR from running WhatsApp Native service…</p>
            )}
            <Button variant="ghost" size="sm" onClick={() => void refresh()} className="text-muted-foreground">
              <IconRefresh size={14} className="mr-1" />
              Refresh
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
''')

# 6) Render QR card above generic WhatsApp Native form.
p = Path('web/frontend/src/components/channels/channel-config-page.tsx')
s = p.read_text()
imp = 'import { WeixinForm } from "@/components/channels/channel-forms/weixin-form"\n'
if imp not in s:
    raise SystemExit('import marker not found')
s = s.replace(imp, imp + 'import { WhatsAppNativeQRCard } from "@/components/channels/channel-forms/whatsapp-native-qr-card"\n', 1)
case = '''      case "wecom":\n        return (\n          <>\n            <WecomForm\n'''
insert = '''      case "whatsapp_native":\n        return (\n          <>\n            <WhatsAppNativeQRCard />\n            <GenericForm\n              config={editConfig}\n              onChange={handleChange}\n              configuredSecrets={configuredSecrets}\n              hiddenKeys={hiddenKeys}\n              requiredKeys={requiredKeys}\n              fieldErrors={fieldErrors}\n              registerArrayFieldFlusher={registerArrayFieldFlusher}\n              arrayFieldResetVersion={arrayFieldResetVersion}\n            />\n          </>\n        )\n'''
if case not in s:
    raise SystemExit('wecom case marker not found')
s = s.replace(case, insert + case, 1)
p.write_text(s)
