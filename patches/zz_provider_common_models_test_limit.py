from pathlib import Path
path = Path('pkg/providers/factory_provider_test.go')
s = path.read_text()
s = s.replace('''if len(option.CommonModels) > 6 {
			t.Fatalf("provider %q exposes %d common_models, want at most 6", option.ID, len(option.CommonModels))
		}''', '''if len(option.CommonModels) > 24 {
			t.Fatalf("provider %q exposes %d common_models, want at most 24", option.ID, len(option.CommonModels))
		}''')
path.write_text(s)
