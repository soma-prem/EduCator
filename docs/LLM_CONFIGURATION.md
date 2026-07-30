# EduCator LLM Configuration

This document explains how to configure EduCator to use Ollama, Gemini, OpenAI, or Groq as the LLM provider.

## Supported Providers

- `ollama`
- `gemini`
- `openai`
- `groq`

The backend is configured entirely through environment variables. No frontend or business logic changes are required to switch providers.

## Primary and Fallback Provider Selection

Use one of these environment variables to choose the primary provider:

- `LLM_PROVIDER`
- `PRIMARY_PROVIDER`

The application first checks `LLM_PROVIDER`. If it is not set, it falls back to `PRIMARY_PROVIDER`. If neither is set, the default provider is `gemini`.

### Example

```env
LLM_PROVIDER=ollama
FALLBACK_PROVIDER=gemini
```

## Ollama Configuration

When using Ollama, configure the model and server URL:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEMPERATURE=0.2
OLLAMA_MAX_TOKENS=1200
OLLAMA_TIMEOUT_SECONDS=30
OLLAMA_MAX_RETRIES=2
```

### Recommended Local Models

- `gemma3`
- `qwen3:8b`
- `llama3.2`
- `mistral`
- `deepseek-r1`

## Gemini Configuration

For Gemini, use:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_SECONDS=90
GEMINI_MAX_RETRIES=1
```

## OpenAI Configuration

For OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=1
```

## Groq Configuration

For Groq:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.1-8b-instant
LLM_TIMEOUT_SECONDS=30
```

## Fallback Provider

If you want to keep `ollama` as the primary provider and use `gemini` only when Ollama is unavailable, use:

```env
LLM_PROVIDER=ollama
FALLBACK_PROVIDER=gemini
```

The fallback is optional. If `FALLBACK_PROVIDER` is not set, no fallback occurs.

## Startup Validation

When the backend starts, it validates the configured provider(s) and logs warnings when:

- the primary provider is unavailable
- the requested model is missing
- the fallback provider is unavailable

This does not crash the application.

## Provider Health Endpoint

Use the system endpoint to inspect provider status:

```
GET /api/system/providers
```

Response example:

```json
{
  "current_provider": "ollama",
  "current_model": "qwen3:8b",
  "fallback_provider": "gemini",
  "available_providers": ["gemini", "ollama", "openai", "groq"],
  "status": {
    "ok": true,
    "provider": "llm_provider_manager",
    "selected_provider": "ollama",
    "fallback_provider": "gemini",
    "primary": {
      "ok": true,
      "provider": "ollama",
      "model": "qwen3:8b",
      "base_url": "http://localhost:11434"
    },
    "fallback": {
      "ok": true,
      "provider": "gemini",
      "model": "gemini-2.5-flash"
    },
    "available_providers": ["gemini", "ollama", "openai", "groq"]
  }
}
```

## Performance Recommendations

- Local Ollama models generally perform best when the prompt is compact.
- Use `LLM_TEMPERATURE=0.2` for QA and summaries to improve determinism.
- Use `OLLAMA_MAX_TOKENS` or `LLM_MAX_TOKENS` to reduce response length and latency.
- If latency is a concern, reduce `OLLAMA_TIMEOUT_SECONDS` or `LLM_TIMEOUT_SECONDS` carefully.

## Recommended Models by Use Case

- Summary: `gemma3`, `qwen3:8b`, `llama3.2`
- QA: `qwen3:8b`, `llama3.2`, `mistral`
- MCQs / Flashcards: `qwen3:8b`, `gemma3`, `deepseek-r1`

## Troubleshooting

- If the provider is unreachable, verify `OLLAMA_BASE_URL` and make sure the Ollama server is running.
- If the model is missing, verify that the model name exists in Ollama’s model list.
- For `gemini`, verify `GEMINI_API_KEY` is set and valid.
- Use `/api/system/providers` to inspect current provider state.
