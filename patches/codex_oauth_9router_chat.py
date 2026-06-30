from pathlib import Path

path = Path('pkg/providers/oauth/codex_provider.go')
text = path.read_text()
text = text.replace('"github.com/openai/openai-go/v3/responses"\n', '"github.com/openai/openai-go/v3/responses"\n\t"github.com/openai/openai-go/v3/shared"\n')
text = text.replace('option.WithHeader("OpenAI-Beta", "responses=experimental"),\n', 'option.WithHeader("OpenAI-Beta", "responses=experimental"),\n\t\toption.WithHeader("User-Agent", "codex_cli_rs/0.136.0"),\n')
text = text.replace('if accountID != "" {\n\t\topts = append(opts, option.WithHeader("Chatgpt-Account-Id", accountID))\n\t} else {', 'sessionID := "picoclaw-codex"\n\tif cacheKey, ok := options["prompt_cache_key"].(string); ok && cacheKey != "" {\n\t\tsessionID = cacheKey\n\t}\n\topts = append(opts, option.WithHeader("session_id", sessionID))\n\tif accountID != "" {\n\t\topts = append(opts, option.WithHeader("Chatgpt-Account-Id", accountID))\n\t} else {')
text = text.replace('params := buildCodexParams(messages, tools, resolvedModel, options, useNativeSearch)', 'PARAMS_PLACEHOLDER')
text = text.replace('PARAMS_PLACEHOLDER', r'''// ponytail: Codex ChatGPT backend returns empty final text with PicoClaw's full tool set.
	// Re-enable after tool schemas are normalized like 9router's Codex executor.
	codexTools := tools
	if options["codex_passthrough_tools"] != true {
		codexTools = nil
	}
	params := buildCodexParams(messages, codexTools, resolvedModel, options, useNativeSearch)
	params.Instructions = openai.Opt(params.Instructions.Value + "\n\nCodex compatibility: answer the user directly in final text. Do not rely on a message tool for the final answer.")''')
old = '''\tif len(tools) > 0 || enableWebSearch {\n\t\tparams.Tools = orc.TranslateTools(tools, enableWebSearch)\n\t}\n\n\treturn params\n}'''
new = r'''	if len(tools) > 0 || enableWebSearch {
		params.Tools = orc.TranslateTools(tools, enableWebSearch)
	}

	params.Reasoning = shared.ReasoningParam{
		Effort:  shared.ReasoningEffortLow,
		Summary: shared.ReasoningSummaryAuto,
	}
	params.Include = []responses.ResponseIncludable{responses.ResponseIncludableReasoningEncryptedContent}

	return params
}'''
if old not in text:
    raise SystemExit('target block not found')
text = text.replace(old, new)
old_return = '''\n\treturn orc.ParseResponseFromStruct(resp), nil\n}'''
new_return = r'''
	parsed := orc.ParseResponseFromStruct(resp)
	if parsed.Content == "" && len(parsed.ToolCalls) == 0 {
		lastUser := ""
		for i := len(messages) - 1; i >= 0; i-- {
			if messages[i].Role == "user" && messages[i].Content != "" {
				lastUser = messages[i].Content
				break
			}
		}
		if lastUser != "" {
			fallbackParams := buildCodexParams([]Message{{Role: "user", Content: lastUser}}, nil, resolvedModel, options, false)
			fallbackParams.Instructions = openai.Opt(defaultCodexInstructions + "\n\nAnswer the user directly in final text.")
			fallbackStream := p.client.Responses.NewStreaming(ctx, fallbackParams, opts...)
			defer fallbackStream.Close()
			var fallbackResp *responses.Response
			var fallbackText strings.Builder
			for fallbackStream.Next() {
				evt := fallbackStream.Current()
				if evt.Type == "response.output_text.delta" {
					fallbackText.WriteString(evt.Delta)
				}
				if evt.Type == "response.output_text.done" && fallbackText.Len() == 0 {
					fallbackText.WriteString(evt.AsResponseOutputTextDone().Text)
				}
				if evt.Type == "response.completed" || evt.Type == "response.failed" || evt.Type == "response.incomplete" {
					evtResp := evt.Response
					if evtResp.ID != "" {
						evtRespCopy := evtResp
						fallbackResp = &evtRespCopy
					}
				}
			}
			if err := fallbackStream.Err(); err == nil {
				fallbackParsed := orc.ParseResponseFromStruct(fallbackResp)
				if fallbackParsed.Content == "" && fallbackText.Len() > 0 {
					fallbackParsed.Content = fallbackText.String()
				}
				if fallbackParsed.Content != "" || len(fallbackParsed.ToolCalls) > 0 {
					return fallbackParsed, nil
				}
			}
		}
	}
	return parsed, nil
}'''
if old_return not in text:
    raise SystemExit('return block not found')
text = text.replace(old_return, new_return)
path.write_text(text)
