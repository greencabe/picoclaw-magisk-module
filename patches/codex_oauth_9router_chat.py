from pathlib import Path

path = Path('pkg/providers/oauth/codex_provider.go')
text = path.read_text()
text = text.replace('"github.com/openai/openai-go/v3/responses"\n', '"github.com/openai/openai-go/v3/responses"\n\t"github.com/openai/openai-go/v3/shared"\n')
text = text.replace('option.WithHeader("OpenAI-Beta", "responses=experimental"),\n', 'option.WithHeader("OpenAI-Beta", "responses=experimental"),\n\t\toption.WithHeader("User-Agent", "codex_cli_rs/0.136.0"),\n')
text = text.replace('if accountID != "" {\n\t\topts = append(opts, option.WithHeader("Chatgpt-Account-Id", accountID))\n\t} else {', 'sessionID := "picoclaw-codex"\n\tif cacheKey, ok := options["prompt_cache_key"].(string); ok && cacheKey != "" {\n\t\tsessionID = cacheKey\n\t}\n\topts = append(opts, option.WithHeader("session_id", sessionID))\n\tif accountID != "" {\n\t\topts = append(opts, option.WithHeader("Chatgpt-Account-Id", accountID))\n\t} else {')
text = text.replace('params := buildCodexParams(messages, tools, resolvedModel, options, useNativeSearch)', '// ponytail: Codex ChatGPT backend returns empty final text with PicoClaw\'s full tool set.\n\t// Re-enable after tool schemas are normalized like 9router\'s Codex executor.\n\tcodexTools := tools\n\tif options["codex_passthrough_tools"] != true {\n\t\tcodexTools = nil\n\t}\n\tparams := buildCodexParams(messages, codexTools, resolvedModel, options, useNativeSearch)\n\tparams.Instructions = openai.Opt(params.Instructions.Value + "\\n\\nCodex compatibility: answer the user directly in final text. Do not rely on a message tool for the final answer.")')
old = '''\tif len(tools) > 0 || enableWebSearch {\n\t\tparams.Tools = orc.TranslateTools(tools, enableWebSearch)\n\t}\n\n\treturn params\n}'''
new = '''\tif len(tools) > 0 || enableWebSearch {\n\t\tparams.Tools = orc.TranslateTools(tools, enableWebSearch)\n\t}\n\n\tparams.Reasoning = shared.ReasoningParam{\n\t\tEffort:  shared.ReasoningEffortLow,\n\t\tSummary: shared.ReasoningSummaryAuto,\n\t}\n\tparams.Include = []responses.ResponseIncludable{responses.ResponseIncludableReasoningEncryptedContent}\n\n\treturn params\n}'''
if old not in text:
    raise SystemExit('target block not found')
text = text.replace(old, new)
path.write_text(text)
