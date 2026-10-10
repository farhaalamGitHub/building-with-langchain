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

## Story 3.2 — Visible Python routing between the two chains

**What it adds:** the same chat endpoint now sends a message that starts with `/study` to the study helper and everything else to general chat; the reply starts with a `[route: general]` or `[route: study]` label. (The rule now lives in the Story 4.1 graph router.)

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"Hello!"}],"stream":false}'

curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"/study Explain what an API is"}],"stream":false}'
```

Expected: both are `chat.completion` JSON. The first content starts with `[route: general]` and is a friendly reply. The second starts with `[route: study]`, explains an API (not the literal `/study`), and ends with one `Next step:` line.

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"/study"}],"stream":false}'
```

Expected: HTTP 200 with `[route: study]` and the hint "Add a question after /study, for example: /study What is an API?" (no model answer). A message like `/studying` is not matched and goes to general chat.

## Story 4.1 — LangGraph routing workflow

**What it adds:** the route is now a small LangGraph (`router` → `general_chat` or `study_helper` → `END`); the endpoint and response shapes are unchanged.

Prerequisite: run the app with `APP_ENV=development` and watch the server log for the trace line.

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"/study Explain what an API is"}],"stream":true}'

curl -N http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"Hello!"}],"stream":true}'
```

Expected: `chat.completion.chunk` events starting with the route label, a `"finish_reason":"stop"` chunk, then `data: [DONE]`. The server log shows a `route: study | ... | nodes: router -> study_helper -> ...` line, then a `route: general | ...` line (Story 4.2 added the review fields to that line). Setting `LOG_LLM_PAYLOADS=true` also prints REQUEST, SENT TO MODEL and RESPONSE blocks in the server terminal.

## Story 4.2 — Bounded answer review and improvement

**What it adds:** each draft answer is checked once by a reviewer; if it says `improve`, an improver rewrites it once, then the answer is final. Open WebUI still shows only the final answer.

Prerequisite: run the app with `APP_ENV=development` and watch the server log for the trace line.

```bash
curl http://127.0.0.1:8000/v1/chat/completions   -H "Content-Type: application/json"   -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"Hello!"}],"stream":false}'

curl http://127.0.0.1:8000/v1/chat/completions   -H "Content-Type: application/json"   -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"/study Explain variables, loops, functions and classes"}],"stream":false}'
```

Expected: both are `chat.completion` JSON starting with `[route: general]` and `[route: study]`. The log shows `route: general | review: approve | revisions: 0 | nodes: router -> general_chat -> reviewer` for the first. For the second it shows either the same shape with `study_helper`, or, if the reviewer asks for a rewrite, `review: improve -> approve | revisions: 1 | nodes: router -> study_helper -> reviewer -> improver -> reviewer`. The reviewer is a model, so which one you get can vary. `revisions` is never above 1.

```bash
curl http://127.0.0.1:8000/v1/chat/completions   -H "Content-Type: application/json"   -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"/study"}],"stream":false}'
```

Expected: HTTP 200 with the `/study` hint and no review (`nodes: router`, no reviewer).

```bash
curl -N http://127.0.0.1:8000/v1/chat/completions   -H "Content-Type: application/json"   -d '{"model":"YOUR_MODEL","messages":[{"role":"user","content":"Hello!"}],"stream":true}'
```

Expected: `chat.completion.chunk` events that arrive together after the review finishes (not word by word), a `"finish_reason":"stop"` chunk, and `data: [DONE]`.
