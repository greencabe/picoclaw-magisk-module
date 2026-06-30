from pathlib import Path
path = Path('web/frontend/src/components/channels/channel-config-page.tsx')
text = path.read_text()
old = '  const payload: ChannelConfig = { enabled, type: channel.config_key }\n'
new = '  const payload: ChannelConfig = {\n    enabled,\n    type: channel.name === "whatsapp_native" ? "whatsapp_native" : channel.config_key,\n  }\n'
if old not in text:
    raise SystemExit('save payload type line not found')
path.write_text(text.replace(old, new, 1))
