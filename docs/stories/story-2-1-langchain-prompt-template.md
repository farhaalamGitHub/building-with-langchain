# Story 2.1 — LangChain prompt template

## Purpose

Story 1.1 gave us a working chat flow with a fixed instruction and the latest user message. This story makes that flow reusable and easy to understand by building the prompt with proper LangChain chat-prompt pieces: one stable instruction owned by the application, and the current user message.

## What this story implements in plain English

After this story, a participant using the chatbot will notice:

- The chatbot answers in the same friendly Learning Companion style every time.
- Typing your own "system" or "act as..." text into the chat cannot replace the Companion's built-in instructions. It is treated as part of what you said.
- Chat in Open WebUI works exactly as before, including the word-by-word reply.
- Only your latest message is used. The Companion does not remember earlier messages yet.
- When running in development, the app can show which kinds of messages it built, without ever showing secrets.

## Prerequisites

- Story 1.1 is complete: `GET /health`, `GET /v1/models`, `POST /v1/chat/completions`, `.env` settings, and the working Open WebUI connection.
- Existing code to read first: `src/learning_companion/chain.py`, `src/learning_companion/main.py`, `src/learning_companion/settings.py`, `.env.example`, `docs/architecture.md`, and Story 1.1. No `docs/config.yaml` exists; the project is at the repository root.
- Preserve existing routes, settings, `.env.example`, and the Open WebUI connection. Do not rename settings.

## Work to do

1. **Build the prompt with LangChain abstractions.** In `src/learning_companion/chain.py` (or a small `prompt.py` next to it), replace the seed's fixed latest-message prompt with a `ChatPromptTemplate` made of two clearly separate parts:
   - a stable Learning Companion **system** instruction owned by the application (a module-level constant, not read from the request);
   - the current **user** message as a template variable.

   Use `ChatPromptTemplate` with `SystemMessage`/`HumanMessagePromptTemplate` (or `from_messages` with role tuples). Do not concatenate a large ad-hoc string.
2. **Select only the latest supported user message.** In the chat route, pick the most recent message with role `user` from the request. Ignore earlier messages and assistant messages for the prompt. If there is no user message, keep the existing 400 error. Do not add history handling; Story 2.2 does that.
3. **Treat request `system` messages as user-provided content.** A `system` message in the request must never replace or be merged into the application's system instruction. For this story it is simply ignored for prompt purposes (it is not promoted to the system role). Add a one-line comment saying why.
4. **Keep the same chain for both paths.** The existing `prompt → Grok model → text output` chain serves both `stream: false` (normal JSON) and `stream: true` (SSE chunks, stop chunk, `[DONE]`). Do not add a second chat path, custom message formats, or Open WebUI plugins.
5. **Add a compact development-only inspectable helper.** Add a small function (for example `describe_prompt(question) -> list[str]` or a `logging` line emitted only when `APP_ENV=development`) that reports message **roles and counts** in order, e.g. `prompt: system(1) -> human(1)`. It must never print API keys, the full system instruction, or full user text.
6. **Update `docs/architecture.md`.** Add the message flow (request → pick latest user message → fixed system instruction + user message → Grok → text → OpenAI-compatible response) and state the deliberate **no-persistence boundary**: no history, no database, no memory yet.
7. **Do not add:** a command-line-only chatbot, a second chat path, conversation history, a database, persistent memory, RAG, tools, MCP, LangGraph, a new frontend, an evaluation harness, a broad test suite, or a security programme.

## Completion checks

Keep verification small and report the commands you actually ran:

1. `uv run ruff format .` and `uv run ruff check .` are clean. (Inside an activated `.venv`, run `ruff format .` and `ruff check .` instead.)
2. Start the app: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000` (use another port if 8000 is taken, and match the Open WebUI connection).
3. Ask one ordinary question through the existing Open WebUI chat.
4. Using the development helper or log, confirm the prompt order is the fixed application instruction first, then the latest user message, and that no key or full instruction is printed.
5. Confirm Open WebUI still renders the answer.

Expected Open WebUI result: one Learning Companion answer to the question, rendered as before (streamed if streaming is on).

## Handover

Files changed:

- `src/learning_companion/chain.py` (and optionally a new `src/learning_companion/prompt.py`)
- `src/learning_companion/main.py` (latest user message selection, helper or log call)
- `docs/architecture.md` (message flow, no-persistence boundary)
- `docs/stories/story-2-1-langchain-prompt-template.md` (this story)

Record when done: the commands actually run, the prompt role order observed, and what Open WebUI showed.

What Story 2.2 will extend: conversation history, so earlier messages from the same chat are included in the prompt on top of this stable instruction plus current message structure.
