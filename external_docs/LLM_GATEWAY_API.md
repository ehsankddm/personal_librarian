# LLM Gateway API

OpenAI-compatible HTTP API with health checks and model routing, suitable for both humans and AI agents.

- Base URL: `http://localhost:7766`
- Versioned prefix: `/v1`
- Auth: `Authorization: Bearer <GATEWAY_API_KEY>` (if configured)

## Quick Start

- Health: `curl -s http://localhost:7766/healthz`
- Models: `curl -s -H "Authorization: Bearer YOUR_KEY" http://localhost:7766/v1/models`
- Chat:
  ```bash
  curl -s -H "Authorization: Bearer YOUR_KEY" \
       -H "Content-Type: application/json" \
       -d '{
             "model":"gpt-4o-mini",
             "messages":[{"role":"user","content":"Hello!"}],
             "temperature":0.2,
             "max_tokens":128
           }' \
       http://localhost:7766/v1/chat/completions
  ```
- Embeddings:
  ```bash
  curl -s -H "Authorization: Bearer YOUR_KEY" \
       -H "Content-Type: application/json" \
       -d '{"model":"text-embedding-3-small","input":["Hello world"]}' \
       http://localhost:7766/v1/embeddings
  ```

## Authentication

- Header: `Authorization: Bearer <GATEWAY_API_KEY>`
- Config: set `GATEWAY_API_KEY` in environment. If unset or null, auth is disabled for `/v1/*`.

## Model Routing

- Configure `config/models.yaml` (or set `MODELS_CONFIG_PATH`).
- Your client uses alias IDs from `/v1/models`. The gateway maps each alias to a provider+model.

Example `models.yaml`:
```yaml
models:
  gpt-4o-mini:
    provider: openai
    model: gpt-4o-mini
  claude-3-5-sonnet:
    provider: anthropic
    model: claude-3-5-sonnet-20241022
```

## Endpoints

### GET /healthz
- Purpose: liveness probe.
- Auth: none.
- Response: `{"status":"ok"}`

### GET /readyz
- Purpose: readiness probe.
- Auth: none.
- Response: `{"status":"ready"}`

### GET /v1/models
- Purpose: list configured model aliases available via the gateway.
- Auth: required if `GATEWAY_API_KEY` is set.
- Response body:
  ```json
  {
    "data": [
      {"id": "gpt-4o-mini", "object": "model", "owned_by": "system"}
    ],
    "object": "list"
  }
  ```

### POST /v1/chat/completions
- Purpose: OpenAI-compatible chat completion.
- Auth: required if `GATEWAY_API_KEY` is set.
- Request body:
  ```json
  {
    "model": "<alias>",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.2,
    "max_tokens": 1024,
    "top_p": 1.0,
    "stream": false,
    "extra": { }
  }
  ```
  Notes:
  - `stream`: accepted but server returns non-streaming responses only.
  - `extra`: dict for provider-specific options (passed through).
- Response body:
  ```json
  {
    "id": "cmpl-...",
    "object": "chat.completion",
    "model": "<resolved-provider-model>",
    "choices": [
      {
        "index": 0,
        "message": {"role": "assistant", "content": "Hello!"},
        "finish_reason": "stop"
      }
    ]
  }
  ```

### POST /v1/embeddings
- Purpose: OpenAI-compatible embeddings.
- Auth: required if `GATEWAY_API_KEY` is set.
- Request body:
  ```json
  {
    "model": "<alias>",
    "input": ["Hello world"]
  }
  ```
- Response body:
  ```json
  {
    "data": [
      {"index": 0, "embedding": [0.0123, 0.0456, 0.0789]}
    ],
    "model": "<resolved-provider-model>"
  }
  ```

## Error Handling

- 401 Unauthorized: missing `Authorization` header when auth is enabled.
- 403 Forbidden: invalid API key.
- 404 Not Found: unknown `model` alias.
- 500 Provider error: upstream provider or internal error.

Example error:
```json
{
  "detail": "Provider error: <message>"
}
```

## Environment Variables

- `GATEWAY_PORT` (default: 7766)
- `GATEWAY_API_KEY` (optional)
- `MODELS_CONFIG_PATH` (default: `/app/config/models.yaml`)
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
- `LOG_LEVEL` (default: `INFO`)

## Usage Patterns for AI Agents

- Protocol: identical to OpenAI’s `/v1` JSON shape above.
- Headers: always send `Content-Type: application/json`. Include `Authorization` if required.
- Retry: consider retry on 5xx with exponential backoff.
- Timeouts: select reasonable HTTP client timeouts (e.g., 30–60s) for chat calls.
- Streaming: not currently supported; set `stream=false` (or omit) and expect full JSON.
- Model discovery: call `/v1/models` and cache alias IDs; do not assume provider-specific names.

### MCP Server (optional for agent frameworks)

- Transport: stdio
- Run: `uv run python -m app.mcp_server`
- Tools:
  - `models`: list configured aliases
  - `chat`: send chat with `{ alias, messages, ... }`
  - `embeddings`: create embeddings with `{ alias, input }`

## Minimal Client Examples

Python (httpx):
```python
import httpx
BASE = "http://localhost:7766"
API_KEY = "YOUR_KEY"

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# Models
r = httpx.get(f"{BASE}/v1/models", headers=headers)
print(r.json())

# Chat
payload = {
  "model": "gpt-4o-mini",
  "messages": [{"role": "user", "content": "Hello!"}],
  "temperature": 0.2,
  "max_tokens": 128,
}
r = httpx.post(f"{BASE}/v1/chat/completions", headers=headers, json=payload, timeout=60)
print(r.json())

# Embeddings
payload = {"model": "text-embedding-3-small", "input": ["Hello world"]}
r = httpx.post(f"{BASE}/v1/embeddings", headers=headers, json=payload)
print(r.json())
```

curl (auth enabled):
```bash
export BASE=http://localhost:7766
export KEY=YOUR_KEY

curl -s $BASE/healthz
curl -s -H "Authorization: Bearer $KEY" $BASE/v1/models
curl -s -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hello!"}]}' \
  $BASE/v1/chat/completions
```

## Compatibility Notes

- The API aims to be OpenAI-compatible for Chat and Embeddings; not all provider-specific options are surfaced.
- The `extra` field lets you pass through provider-specific parameters when needed.
- Streaming is planned but currently disabled.

