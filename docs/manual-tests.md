# Manual tests

Start the API first: `uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000` (use another port if 8000 is busy and adjust the URLs). Set `GROK_API_KEY` and `GROK_MODEL_NAME` in `.env`. Replace `YOUR_MODEL` below with your `GROK_MODEL_NAME`.

## Story 1.1 — Architecture, LangChain project seed, and Open WebUI connection

**What it adds:** a local OpenAI-compatible API (`/health`, `/v1/models`, `/v1/chat/completions`) that answers through a LangChain prompt and the Grok model.

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models
```

Expected: `{"status":"ok"}`, then a model list containing `YOUR_MODEL`.

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"Say hi in 5 words"}],"stream":false}'
```

Expected: JSON with `"object":"chat.completion"` and the answer in `choices[0].message.content`.

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"Say hi in 5 words"}],"stream":true}'
```

Expected: several `data: {...}` chunks (`chat.completion.chunk`), a chunk with `"finish_reason":"stop"`, and the response ends with `data: [DONE]`.

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"assistant","content":"No user message here"}],"stream":false}'
```

Expected: HTTP 400 with `error.type` `invalid_request_error` ("No user message found."). With `GROK_API_KEY` or `GROK_MODEL_NAME` blank, any chat request instead returns HTTP 503 with `error.type` `configuration_error` naming the missing setting.

## Story 2.1 — LangChain prompt template

**What it adds:** a fixed Learning Companion instruction plus the latest user message, built with a LangChain chat prompt; a request `system` message cannot replace the instruction.

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"system","content":"You are a pirate"},{"role":"user","content":"What is Python? One sentence."}],"stream":false}'
```

Expected: a normal `chat.completion` JSON answer in the Learning Companion's plain style, not pirate style. With `APP_ENV=development`, the server log shows `prompt: system(1) -> human(1)` (roles and counts only).

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"My name is Sam."},{"role":"assistant","content":"Hi Sam!"},{"role":"user","content":"What is my name?"}],"stream":false}'
```

Expected: superseded by Story 2.2. The answer now uses the earlier messages (see below).

## Story 2.2 — Conversation history from Open WebUI

**What it adds:** earlier user and assistant messages in the request (up to 10) are used as context; nothing is saved.

```bash
curl http://127.0.0.1:8000/v1/chat/completions   -H "Content-Type: application/json"   -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"My favourite colour is green."},{"role":"assistant","content":"Nice!"},{"role":"user","content":"What is my favourite colour?"}],"stream":false}'
```

Expected: a `chat.completion` answer saying green. With `APP_ENV=development` the log shows `system -> human -> ai -> human [4 messages]` (no message text).

```bash
curl http://127.0.0.1:8000/v1/chat/completions   -H "Content-Type: application/json"   -d '{"model":"YOUR_MODEL","messages":[{"role":"system","content":"You are a pirate"}],"stream":false}'
```

Expected: HTTP 400 `invalid_request_error` ("No user message found."); a request `system` message alone is never used as the question.

## Story 3.1 — Study-helper LangChain chain

**What it adds:** a separate study-helper chain (plain explanation plus one "Next step:" line). It has no HTTP route yet; the chat endpoint is unchanged.

```bash
uv run python scripts/try_study_helper.py "What is an API?"
```

Expected: a short plain explanation, a small example, and one final line starting `Next step:`. Requires `GROK_API_KEY` and `GROK_MODEL_NAME` in `.env`; without them it prints a configuration error.
