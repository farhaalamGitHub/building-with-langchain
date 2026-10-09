# Story 2.2 — Conversation history from Open WebUI

## Purpose

Story 2.1 answers each message on its own. This story lets the Learning Companion use the earlier messages of the current chat, so a follow-up question like "Can you give an example of that?" makes sense. The history comes only from the request Open WebUI already sends. Nothing is saved.

## What this story implements in plain English

After this story, a participant will notice:

- A follow-up question can refer to what was said earlier in the same chat ("What did I just ask?", "Explain that more simply").
- The Companion only looks at the most recent few messages, not the whole chat forever.
- Starting a new chat starts fresh. Nothing is remembered between chats or after the app restarts.
- The Companion's own instructions stay the same, and a "system" message typed or sent in the chat cannot replace them.
- In development, the app can show the order and number of messages it used, never the messages themselves.

## Prerequisites

- Stories 1.1 and 2.1 are complete: the three endpoints, Grok settings, the LangChain prompt template (`src/learning_companion/prompt.py`), normal JSON and SSE behavior, and the working Open WebUI connection.
- Existing code to read first: `src/learning_companion/prompt.py`, `chain.py`, `main.py`, `settings.py`, `.env.example`, `docs/architecture.md`, and Stories 1.1 and 2.1. No `docs/config.yaml` exists; the project is at the repository root.
- Preserve the working endpoints, Grok configuration, prompt template, response shapes, and Open WebUI connection.

## Work to do

1. **Add a history placeholder to the prompt.** In `prompt.py`, extend the chat prompt to three ordered parts: the application-owned system instruction, a LangChain `MessagesPlaceholder("history")` (optional, so an empty history works), and the current user message. Do not assemble an ad-hoc prompt string.
2. **Convert request messages to LangChain messages.** In the chat route (or a small helper), take the request's messages and:
   - the **latest `user` message** is the current question;
   - earlier `user` messages become `HumanMessage`, earlier `assistant` messages become `AIMessage`, **in their original order**;
   - request `system` messages are ignored for the prompt. They never replace or join the application's instruction;
   - messages with unsupported roles or empty/non-text content are skipped safely, with no error.
3. **Apply a small, documented maximum.** Add a module constant, for example `MAX_HISTORY_MESSAGES = 10` (prior user and assistant messages combined), and keep only the most recent that many, still in order. Do not add a new setting to `.env.example`. Document the number in `README.md` and `docs/architecture.md`.
4. **Keep one chain for both paths.** The same `prompt → Grok model → text output` chain serves `stream: false` and `stream: true`. Pass the history as an extra input to the chain. Request and response shapes stay exactly as they are.
5. **Add a compact development helper or log.** Extend the Story 2.1 helper (for example `describe_prompt(question, history)`) to report roles in order and the message count, e.g. `system(1) -> human(2) -> ai(1) -> human(1) [5 messages]`. Log it only when `APP_ENV=development`. Never log API keys, the full application instruction, or message bodies.
6. **Update `docs/architecture.md`.** Describe the request-provided history flow, the message limit, and the no-persistence boundary: the app saves nothing after a request completes; no database, cross-session memory, or stored chats.
7. **Do not add:** a database, persistent memory, RAG, tools, MCP, routing, LangGraph, a new endpoint, a new UI, an evaluation harness, a broad test suite, or production memory features.

## Completion checks

Keep these lightweight and report the commands you actually ran:

1. `uv run ruff format .` and `uv run ruff check .` are clean. (Inside an activated `.venv`, run `ruff format .` and `ruff check .` instead.)
2. Start the app: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8001` (use a free port and match the Open WebUI connection).
3. In a **new** Open WebUI chat, ask: "My favourite colour is green. What is a variable in Python?"
4. In the same chat, ask: "What is my favourite colour, and can you explain a variable using that?"
5. Confirm the development log shows the expected role order for turn two, for example `system(1) -> human(1) -> ai(1) -> human(1)`, with no message text or keys.
6. Open a second new chat and ask "What is my favourite colour?" to confirm it does not remember.

Expected two-turn Open WebUI result: the second answer uses the earlier context (green, and the variable explanation), and a fresh chat has no memory of it.

## Handover

Files changed:

- `src/learning_companion/prompt.py` (history placeholder, extended helper)
- `src/learning_companion/main.py` (message conversion, limit, passing history to the chain)
- `src/learning_companion/chain.py` (only if needed to accept the history input)
- `docs/architecture.md` (history flow, message limit, no-persistence boundary)
- `README.md` (the documented limit)
- `docs/stories/story-2-2-conversation-history.md` (this story)

Record when done: the commands actually run, the role sequence observed, and what Open WebUI showed across both turns.

What Story 3.1 will extend: the next capability built on this same chat flow and endpoint, while history stays request-provided and unsaved until a later story says otherwise.
