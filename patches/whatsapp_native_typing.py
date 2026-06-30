from pathlib import Path
path = Path('pkg/channels/whatsapp_native/whatsapp_native.go')
text = path.read_text()
marker = '''func (c *WhatsAppNativeChannel) Send(ctx context.Context, msg bus.OutboundMessage) ([]string, error) {\n'''
insert = '''func (c *WhatsAppNativeChannel) StartTyping(ctx context.Context, chatID string) (func(), error) {\n\tc.mu.Lock()\n\tclient := c.client\n\tc.mu.Unlock()\n\tif client == nil || !client.IsConnected() || client.Store.ID == nil {\n\t\treturn func() {}, nil\n\t}\n\tto, err := parseJID(chatID)\n\tif err != nil {\n\t\treturn nil, err\n\t}\n\tif err := client.SendChatPresence(ctx, to, types.ChatPresenceComposing, types.ChatPresenceMediaText); err != nil {\n\t\treturn nil, err\n\t}\n\tonce := sync.Once{}\n\tstop := func() {\n\t\tonce.Do(func() {\n\t\t\tstopCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)\n\t\t\tdefer cancel()\n\t\t\t_ = client.SendChatPresence(stopCtx, to, types.ChatPresencePaused, types.ChatPresenceMediaText)\n\t\t})\n\t}\n\treturn stop, nil\n}\n\n'''
if insert in text:
    raise SystemExit('typing patch already present')
if marker not in text:
    raise SystemExit('send marker not found')
path.write_text(text.replace(marker, insert + marker, 1))
