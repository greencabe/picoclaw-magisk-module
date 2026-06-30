from pathlib import Path
path = Path('Makefile')
text = path.read_text()
old = 'GOOS=android GOARCH=arm64 $(GO) build -tags stdjson -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_NAME)-android-arm64 ./$(CMD_DIR)'
new = 'GOOS=android GOARCH=arm64 $(GO) build -tags stdjson,whatsapp_native -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_NAME)-android-arm64 ./$(CMD_DIR)'
if old not in text:
    raise SystemExit('android build target not found')
path.write_text(text.replace(old, new, 1))
