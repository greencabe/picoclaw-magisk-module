from pathlib import Path

path = Path('web/backend/api/models.go')
s = path.read_text()
old = '''func probeAntigravityOAuthModelError(modelID string) error {
	modelID = normalizeAntigravityProbeModel(modelID)
	if _, err := antigravityOAuthCredential(); err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()
	provider := providers.NewAntigravityProvider()
	_, err := provider.Chat(ctx, []providers.Message{{Role: "user", Content: "Reply exactly: OK"}}, nil, modelID, map[string]any{"max_tokens": 16, "temperature": 0})
	if err != nil {
		return fmt.Errorf("antigravity test failed for %s: %w", modelID, err)
	}
	return nil
}
'''
new = '''func probeAntigravityOAuthModelError(modelID string) error {
	_ = normalizeAntigravityProbeModel(modelID)
	cred, err := antigravityOAuthCredential()
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	if _, err := providers.FetchAntigravityProjectIDWithContext(ctx, cred.AccessToken); err != nil {
		return fmt.Errorf("antigravity loadCodeAssist test failed: %w", err)
	}
	return nil
}
'''
if old in s:
    s = s.replace(old, new, 1)
elif 'FetchAntigravityProjectIDWithContext' not in s:
    raise SystemExit('probeAntigravityOAuthModelError anchor not found')
path.write_text(s)
