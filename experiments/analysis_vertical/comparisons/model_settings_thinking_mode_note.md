# Model Settings Note: Gemma4 Thinking Mode

## Local Model Metadata

`ollama show gemma4:e2b` reports:

- architecture: `gemma4`
- parameters: `5.1B`
- context length: `131072`
- quantization: `Q4_K_M`
- capabilities include `thinking`
- default temperature: `1`

The experiment runners currently override temperature to `0` and request JSON mode.

## Documentation Check

Ollama documents thinking-capable models as using a request-level `think` field on chat or generate requests. The response separates the reasoning trace from final content. Ollama's chat API also documents `think` as a request body field that can be boolean or a supported string level.

The installed `langchain-ollama` package maps this to `ChatOllama(reasoning=True)`.

## Local Smoke Test

Using:

```python
ChatOllama(model="gemma4:e2b", format="json", temperature=0, reasoning=True)
```

The model returned:

```json
{"classification":"in_meeting_action"}
```

and placed the reasoning trace separately under:

```python
AIMessage.additional_kwargs["reasoning_content"]
```

## Implication

The next experiment should compare the existing V4 repaired classifier pipeline against the same pipeline with `reasoning=True`. This is preferable to relying only on a system prompt that says "work in thinking mode," because Ollama and LangChain both expose thinking as an actual model request setting.

