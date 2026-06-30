from pathlib import Path

path = Path('web/backend/api/models.go')
s = path.read_text()

old = '''\tm := cfg.ModelList[idx]
\tstart := time.Now()
\tsummary := modelConfigurationStatus(m)
\tlatency := time.Since(start).Milliseconds()

\tresult := map[string]any{
\t\t"success":    summary.Available,
\t\t"latency_ms": latency,
\t\t"status":     summary.Status,
\t}

\tif !summary.Available {
\t\tif summary.Status == modelStatusUnconfigured {
\t\t\tresult["error"] = "API key not configured"
\t\t} else {
\t\t\tresult["error"] = "Endpoint unreachable"
\t\t}
\t}
'''
new = '''\tm := cfg.ModelList[idx]
\tstart := time.Now()
\tsummary := modelConfigurationStatus(m)
\tif providers.NormalizeProvider(modelProtocol(m)) == "antigravity" && summary.Available {
\t\tif err := probeAntigravityOAuthModelError(splitModelID(m)); err != nil {
\t\t\tsummary.Available = false
\t\t\tsummary.Status = modelStatusUnreachable
\t\t}
\t}
\tlatency := time.Since(start).Milliseconds()

\tresult := map[string]any{
\t\t"success":    summary.Available,
\t\t"latency_ms": latency,
\t\t"status":     summary.Status,
\t}

\tif !summary.Available {
\t\tif summary.Status == modelStatusUnconfigured {
\t\t\tresult["error"] = "OAuth credential not configured"
\t\t} else if providers.NormalizeProvider(modelProtocol(m)) == "antigravity" {
\t\t\tresult["error"] = probeAntigravityOAuthModelError(splitModelID(m)).Error()
\t\t} else {
\t\t\tresult["error"] = "Endpoint unreachable"
\t\t}
\t}
'''
if old in s:
    s = s.replace(old, new, 1)
elif 'probeAntigravityOAuthModelError(splitModelID(m))' not in s:
    raise SystemExit('handleTestModel anchor not found')

old = '''\t// Perform a real network probe
\tstart := time.Now()
\tavailable := probeModelConnectivity(m)
\tlatency := time.Since(start).Milliseconds()

\tresult := map[string]any{
\t\t"success":    available,
\t\t"latency_ms": latency,
\t}
\tif available {
\t\tresult["status"] = modelStatusAvailable
\t} else {
\t\tresult["status"] = modelStatusUnreachable
\t\tresult["error"] = "Endpoint unreachable"
\t}
'''
new = '''\t// Perform a real network probe
\tstart := time.Now()
\tvar probeErr error
\tavailable := false
\tif providers.NormalizeProvider(modelProtocol(m)) == "antigravity" {
\t\tprobeErr = probeAntigravityOAuthModelError(splitModelID(m))
\t\tavailable = probeErr == nil
\t} else {
\t\tavailable = probeModelConnectivity(m)
\t}
\tlatency := time.Since(start).Milliseconds()

\tresult := map[string]any{
\t\t"success":    available,
\t\t"latency_ms": latency,
\t}
\tif available {
\t\tresult["status"] = modelStatusAvailable
\t} else {
\t\tresult["status"] = modelStatusUnreachable
\t\tif probeErr != nil {
\t\t\tresult["error"] = probeErr.Error()
\t\t} else {
\t\t\tresult["error"] = "Endpoint unreachable"
\t\t}
\t}
'''
if old in s:
    s = s.replace(old, new, 1)
elif 'var probeErr error' not in s:
    raise SystemExit('handleTestInlineModel anchor not found')

old = '''func probeAntigravityOAuthModel(modelID string) bool {
\tmodelID = normalizeAntigravityProbeModel(modelID)
\tctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
\tdefer cancel()
\tprovider := providers.NewAntigravityProvider()
\t_, err := provider.Chat(ctx, []providers.Message{{Role: "user", Content: "Reply with OK."}}, nil, modelID, map[string]any{"max_tokens": 8})
\treturn err == nil
}
'''
new = '''func probeAntigravityOAuthModel(modelID string) bool {
\treturn probeAntigravityOAuthModelError(modelID) == nil
}

func splitModelID(m *config.ModelConfig) string {
\t_, modelID := splitModel(m)
\treturn modelID
}

func probeAntigravityOAuthModelError(modelID string) error {
\tmodelID = normalizeAntigravityProbeModel(modelID)
\tif _, err := antigravityOAuthCredential(); err != nil {
\t\treturn err
\t}
\tctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
\tdefer cancel()
\tprovider := providers.NewAntigravityProvider()
\t_, err := provider.Chat(ctx, []providers.Message{{Role: "user", Content: "Reply exactly: OK"}}, nil, modelID, map[string]any{"max_tokens": 16, "temperature": 0})
\tif err != nil {
\t\treturn fmt.Errorf("antigravity test failed for %s: %w", modelID, err)
\t}
\treturn nil
}
'''
if old in s:
    s = s.replace(old, new, 1)
elif 'func probeAntigravityOAuthModelError' not in s:
    raise SystemExit('probeAntigravityOAuthModel anchor not found')

path.write_text(s)
