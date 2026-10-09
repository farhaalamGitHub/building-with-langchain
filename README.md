# Learning Companion Chatbot

Open WebUI -> this app's OpenAI-compatible chat endpoint -> LangChain prompt and Grok model -> answer in Open WebUI.

Open WebUI is already installed and is only the chat client; do not modify it.

## Setup

1. `uv sync`
2. Copy `.env.example` to `.env`. The instructor supplies `GROK_MODEL_NAME`; put your real `GROK_API_KEY` only in `.env` (it is untracked).
3. Start: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000`

The app starts without a key; a chat request without one returns a clear configuration error.

## Open WebUI connection

If needed, point your existing OpenAI-compatible connection at `http://127.0.0.1:8000/v1` (use `http://host.docker.internal:8000/v1` if Open WebUI runs in Docker), then select the model listed by `/v1/models`.

## Conversation history

The app uses up to the 10 most recent earlier user/assistant messages from the current Open WebUI request. Nothing is saved; a new chat starts fresh.

## Study helper (development)

`uv run python scripts/try_study_helper.py "What is an API?"` runs the study-helper chain once. Open WebUI does not use it yet.

## Checks

`uv run ruff format .` · `uv run ruff check .` · `uv run pytest`
