# Story 3.2 — Visible Python routing between the two chains

## Purpose

Story 3.1 built a study-helper chain, but Open WebUI cannot reach it. This story makes both chains reachable through the same chat endpoint using one plain, visible Python `if/else`. Participants can read the rule, see which route was chosen, and understand what Session 4 will later replace with an explicit LangGraph route.

## What this story implements in plain English

After this story:

- An ordinary question, such as "Hello!", still goes to general chat and behaves exactly as before.
- A question that starts with `/study`, such as `/study Explain what an API is`, goes to the study helper instead.
- The study helper receives the question without the leading `/study`. It answers with a plain explanation and one next step.
- Both answers arrive in the same Open WebUI conversation, through the same endpoint, normal or streaming.
- The app logs which route was chosen (`general` or `study`), and the answer starts with a short route label so the path is visible in the chat.
- The choice is one fixed rule in the code. No model decides it, and this is not a LangGraph workflow or autonomous routing.

## Prerequisites

- Stories 1.1–3.1 are complete: the three endpoints, Grok settings, the prompt with request-provided history (Story 2.2, `MAX_HISTORY_MESSAGES = 10`), `build_chain` and `build_study_helper_chain`, normal JSON and SSE behavior, and the working Open WebUI connection.
- Existing code to read first: `src/learning_companion/main.py`, `prompt.py`, `chain.py`, `settings.py`, `.env.example`, `docs/architecture.md`, and Stories 1.1–3.1. No `docs/config.yaml` exists; the project is at the repository root.
- Preserve the endpoints, Grok settings, message-history handling, response shapes, and the Open WebUI connection.

## Work to do

1. **Add a small, visible routing function.** In `main.py` (or a tiny `routing.py` next to it), add something like `select_route(question) -> tuple[str, str]` returning the route name and the question to pass on. The rule is exactly:
   - if the latest user message, after leading whitespace is ignored, begins with `/study`, the route is `"study"`;
   - otherwise the route is `"general"` and the question is unchanged.

   Write it as an ordinary `if/else` with a short comment. A message such as `/studying` or `/study-plan` must not match: `/study` must be followed by whitespace or the end of the message.
2. **Strip only the leading marker.** For the study route, remove the leading `/study` and the whitespace after it. Leave the rest of the text untouched. History is built by `split_conversation` as in Story 2.2: earlier request messages, in order, capped at `MAX_HISTORY_MESSAGES`. History is not edited, even if earlier messages contain `/study`.
3. **Handle an empty study question.** If nothing follows `/study`, return a short friendly answer through the normal response path, such as "Add a question after /study, for example: /study What is an API?", and do not call the model. This is not an error response.
4. **Select the chain in the endpoint.** Replace the single `build_chain(settings)` call in `chat_completions` with: general route → `build_chain`, study route → `build_study_helper_chain`. Keep the existing `ConfigurationError` → 503 handling. Both routes use the existing `chain.invoke(...)` and `chain.stream(...)` code. Do not create a second response path.
5. **Record the route.** In `APP_ENV=development`, log one compact line next to the existing prompt log, for example `route: study`, using the existing logger. Never log keys, message text, or the application instructions.
6. **Add a short route label to the answer text.** Start the assistant text with a one-line label, `[route: general]` or `[route: study]`, followed by a blank line. In normal mode, prefix the returned text. In streaming mode, send the label as the first content chunk, then the model chunks. Keep the OpenAI-compatible shape unchanged: no custom fields, no Open WebUI plugins or events. Show the label in every environment, so participants see it in the chat. The label is added only to the response text and is never sent to the model or kept in later history by this app. It will appear in Open WebUI's stored chat, so it will be in the history Open WebUI sends back. That is acceptable for a classroom demo, but note it in the architecture doc.
7. **Update `docs/architecture.md`.** Add a section on routing that covers:
   - the `/study` rule and the exact strip behavior;
   - the selected-chain path, `endpoint → select_route → general chain or study-helper chain → same JSON/SSE adapter`;
   - the route log and the in-text label;
   - the boundary: this is deterministic application routing, not LLM classification, LangGraph, or multi-agent orchestration.

   Update the chain behaviours table so the study helper is now used by the endpoint when a message starts with `/study`, and mark Story 3.2 as done in the roadmap. Add that Story 4.1 will replace the `if/else` with an explicit LangGraph route.
8. **Update `README.md` only if it describes how to use the chat.** If it does, add one line about `/study`.
9. **Do not add:** LLM-based routing or classification, more specialists or commands, review steps, loops, a new endpoint, model provider or UI, a database, retrieval, tools, MCP, LangGraph, an autonomous agent, broad tests, or production controls.

## Completion checks

Keep these lightweight and report the commands you actually ran:

1. `uv run ruff format .` and `uv run ruff check .` are clean. (Inside an activated `.venv`, run `ruff format .` and `ruff check .` instead.)
2. Start the app: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8001` (use the port that matches the Open WebUI connection).
3. In Open WebUI, send one general-chat message: `Hello!`
4. In the same conversation, send: `/study Explain what an API is`
5. Inspect the development log for the two route lines, in order: `route: general`, then `route: study`.

Expected Open WebUI results:

- **General message:** starts with `[route: general]`, then a normal friendly reply, as before.
- **`/study` message:** starts with `[route: study]`, then a plain explanation of an API, a small example if useful, and exactly one "Next step:" line. The answer is about "Explain what an API is", not about the literal text `/study`.
- Both replies appear in the same conversation, through the same endpoint, and both stream normally.

## Handover

Files changed:

- `src/learning_companion/main.py`: route rule, chain selection, route log, label (or a small new `routing.py` for the rule)
- `docs/architecture.md`: `/study` rule, selected-chain path, boundary, roadmap
- `README.md`: one line about `/study`, only if it describes chat usage
- `docs/stories/story-3-2-visible-python-routing.md` (this story)

Record when done: the commands actually run, the two route log lines seen, and what Open WebUI showed for each message.

What Story 4.1 will extend: it replaces this visible `if/else` with an explicit LangGraph route that makes the same `general` or `study` choice, still through the same endpoint, Open WebUI conversation, and response adapter.
