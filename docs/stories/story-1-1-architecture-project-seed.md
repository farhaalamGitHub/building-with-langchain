# Story 1.1 — Architecture, LangChain project seed, and Open WebUI connection

## Purpose

This is the first story in a short, beginner LangChain and LangGraph classroom course. It agrees on one simple architecture with the instructor, then seeds a tiny Python project that answers chat messages from Open WebUI using a Grok model through LangChain.

## What this story implements in plain English

After this story, a participant will be able to:

- Start a small local application with one command.
- Open the Open WebUI chat they already have and pick the course model from its model list.
- Send a message and see a reply from the Learning Companion appear in Open WebUI.
- Watch the reply arrive word by word, or all at once, depending on the chat setting.
- Keep their secret key in one private file that is never shared or committed.

## Prerequisites

- Open WebUI is already installed and working. It is the supplied chat client only. Do not reinstall, reconfigure, modify, or build it.
- Python 3.12 and [UV](https://docs.astral.sh/uv/) are installed.
- The instructor has supplied the Grok model name and a Grok API key for each participant.
- Project path: no `docs/config.yaml` exists, so the project lives at the repository root.
- No existing `docs/architecture.md` or other stories existed when this story was written. Preserve any that appear before work starts.

## Work to do

### Step 1 — Architecture (stop for approval)

1. Create or update `docs/architecture.md` (keep any existing content that is still correct). Record this single classroom flow:

   `Open WebUI → this local application's OpenAI-compatible chat endpoint → LangChain prompt and Grok model → answer in Open WebUI`
2. Also record:
   - Open WebUI is already installed and working. It is the supplied chat client only and is never reinstalled, reconfigured, modified, or built by participants.
   - The capstone is a small **Learning Companion Chatbot**. It is not a custom frontend and not a second demonstration application.
   - Boundaries: API keys stay in an untracked `.env`; application instructions stay separate from user messages.
   - Out of scope: authentication, authorization, security hardening, databases, persistent memory, RAG, production deployment, and extensive tests.
3. **Stop and ask the instructor to approve `docs/architecture.md`.** Until the instructor explicitly approves, do not create seed files, install dependencies, or scaffold code. Resume this same story only after explicit approval.

### Step 2 — Project seed (only after approval)

1. Create a Python 3.12 UV project (`pyproject.toml`, `uv.lock`) with these dependencies: FastAPI, Pydantic settings, `langchain`, the Grok-compatible LangChain provider integration, Uvicorn. Dev tools: Ruff and a minimal test runner (pytest).
2. Create the layout:
   - `src/learning_companion/` — the application package
   - `tests/` — present but minimal
   - `.env.example`, `.gitignore`, `pyproject.toml`, `uv.lock`, `README.md`
3. `.env.example` uses exactly these setting names and values:

   ```
   APP_ENV=development
   GROK_API_KEY=
   GROK_API_BASE_URL=https://api.x.ai/v1
   GROK_MODEL_NAME=
   HOST=127.0.0.1
   PORT=8000
   ```

   Add no Claude, alternate-provider, database, or production settings. Document in `README.md` that the instructor supplies the model name and participants place their real key only in the untracked `.env`.
4. `.gitignore` must ignore `.env` (and the usual Python/UV artifacts such as `.venv/`, `__pycache__/`, `.ruff_cache/`, `.pytest_cache/`). Keep the existing `.gitignore` entries; add to it rather than replacing it.
5. Settings load through Pydantic settings from the environment / `.env`. The application must **start without a real API key**. Only when a model call is attempted with a missing key or model name, return an honest, clear configuration error (an OpenAI-style error JSON body with a non-2xx status, saying which setting is missing). Do not crash at startup.
6. Build a minimal FastAPI app with exactly these routes:
   - `GET /health` — simple OK response.
   - `GET /v1/models` — OpenAI-compatible model list that exposes the configured Grok model (`GROK_MODEL_NAME`) as the model Open WebUI can select.
   - `POST /v1/chat/completions` — the one chat route.
7. The chat route accepts the normal OpenAI-compatible request shape needed by Open WebUI: `model`, a list of text `messages` with role `system`, `user`, or `assistant`, and `stream`.
   - `stream: false` → normal OpenAI-compatible chat-completion JSON.
   - `stream: true` → normal text-only OpenAI-compatible SSE chunks, then a stop chunk, then `data: [DONE]`.
   - Do not create custom Open WebUI events, a second chat route, or a custom browser UI.
8. Implement one small LangChain flow: **prompt → Grok chat model → text output**. The prompt is a fixed Learning Companion instruction (kept separate from the user message) plus the latest user message. Use this same flow behind the chat endpoint for both normal and streaming requests. Keep it deliberately small; full prompt construction and conversation history belong to Story 2.1.
9. `README.md` explains: set up `.env`, `uv sync`, how to start the app, and the one application-side value a participant may need to point their existing Open WebUI connection at the local app (base URL `http://127.0.0.1:8000/v1`, then pick the model). Document only that connection value; do not alter Open WebUI itself.

### Do not add

A broad test suite, tool calls, LangGraph, agents, MCP, advanced streaming features, authentication, databases, or memory.

## Completion checks

Run only lightweight checks, and report the commands you actually ran:

1. `uv sync`
2. `uv run ruff format .` and `uv run ruff check .` — clean on the changed code.
3. Start the API: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000` (adjust the module path to the real one if different).
4. `GET http://127.0.0.1:8000/health` returns OK.
5. `GET http://127.0.0.1:8000/v1/models` lists the configured Grok model.
6. With the real key and model name in `.env`, through the existing Open WebUI setup, send one normal (non-streaming) message and one streaming message.
7. Without a key, confirm the app still starts and a chat attempt returns the honest configuration error.

Expected classroom result: one Grok reply visible in Open WebUI.

## Handover

Files created or changed:

- `docs/architecture.md` (created or updated, instructor-approved)
- `docs/stories/story-1-1-architecture-project-seed.md` (this story)
- `pyproject.toml`, `uv.lock`, `.env.example`, `.gitignore`, `README.md`
- `src/learning_companion/` (package: settings, FastAPI app, the prompt → Grok flow)
- `tests/` (minimal)

Record in the story, when done: the commands actually run, what was seen in Open WebUI, and any Open WebUI connection value that had to be set on the application side.

What Story 2.1 will extend: full prompt construction and conversation history on top of this seed's single flow, using the same chat endpoint.
