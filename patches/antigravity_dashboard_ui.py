from pathlib import Path

for file_name, model_field in [
    ('web/frontend/src/components/models/edit-model-sheet.tsx', 'modelId'),
    ('web/frontend/src/components/models/add-model-sheet.tsx', 'model'),
]:
    path = Path(file_name)
    s = path.read_text()
    marker = '''  const canonicalProvider = getCanonicalProviderKey(
    form.provider,
    providerOptions,
  )
'''
    repl = marker + '''  const visibleCatalogModels = canonicalProvider === "antigravity" ? [] : catalogModels
'''
    if 'const visibleCatalogModels = canonicalProvider === "antigravity" ? [] : catalogModels' not in s:
        if marker not in s:
            raise SystemExit(f'canonicalProvider marker not found in {file_name}')
        s = s.replace(marker, repl, 1)
    s = s.replace('''                {catalogModels.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {catalogModels.map((m) => (
''', '''                {visibleCatalogModels.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {visibleCatalogModels.map((m) => (
''')
    path.write_text(s)
