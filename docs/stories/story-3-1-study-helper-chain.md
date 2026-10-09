# Story 3.1 — Study-helper LangChain chain

## Purpose

So far the Learning Companion has one way of answering: general chat. This story adds a second, separate behaviour, a study helper, that explains beginner technical ideas in plain language and ends with one small next step. This story only builds the study helper. Choosing between the two is the next story (3.2).

## What this story implements in plain English

After this story:

- The project has a study helper that explains a beginner technical idea simply, with a small example when useful.
- Each study-helper answer ends with exactly one suggested next learning step.
- Ordinary chat in Open WebUI works exactly as before, including greetings and follow-up questions.
- Developers can try the study helper from the project folder with one command. Open WebUI does not use it yet.
- The study helper does not browse, look things up, or promise to be correct. It is just the same model with a different instruction.

## Prerequisites

- Stories 1.1–2.2 are complete: the three endpoints, Grok settings, the LangChain prompt template with request-provided history, normal JSON and SSE behavior, and the working Open WebUI connection.
- Existing code to read first: `src/learning_companion/prompt.py`, `chain.py`, `main.py`, `settings.py`, `.env.example`, `docs/architecture.md`, and Stories 1.1–2.2. No `docs/config.yaml` exists; the project is at the repository root.
- If Story 2.2 is not yet implemented, build the study-helper chain on the current prompt structure and add the history placeholder in the same way Story 2.2 specifies.
- Preserve the endpoints, Grok settings, request/response behavior, Open WebUI connection, and message handling.

## Work to do

1. **Leave the general-chat chain untouched.** Do not change its prompt, name, or behaviour.
2. **Add a separately named study-helper prompt.** Create it next to the existing prompt (for example `STUDY_HELPER_PROMPT` in `prompt.py`, or a new `study_prompt.py`). It has the same shape as the general prompt: an application-owned system instruction, the history placeholder, and the current user message. The study-helper instruction must ask for:
   - a concise, plain-language explanation of a beginner technical concept;
   - a small example where it is useful;
   - exactly one suggested next learning step at the end.

   It must **not** claim to do research, browse, retrieve course data, or guarantee correctness. Keep this instruction separate from user content.
3. **Add a separately named chain.** In `chain.py` add `build_study_helper_chain(settings)` returning `STUDY_HELPER_PROMPT → same Grok model → text output`. Reuse the existing settings check and the same model construction (share a small helper rather than copying it, without changing general-chat behaviour). Both chains use the same configured model and the same current-request history.
4. **Do not change the active route.** `POST /v1/chat/completions` keeps using the general-chat chain for every request. No `/study` handling, no routing, no classification. Story 3.2 adds that.
5. **Add a project-local way to invoke it in development.** Add a small script, for example `scripts/try_study_helper.py` (or `python -m learning_companion.try_study_helper`), that takes a question as an argument, builds the study-helper chain with the real settings, and prints the answer. It must not add an endpoint, a CLI chatbot, or any change to the Open WebUI path.
6. **Update `docs/architecture.md`.** Describe the two available chain behaviours and their responsibilities:
   - general chat: greetings and ordinary conversation (used by the endpoint);
   - study helper: beginner concept explanations with one next step (available, not yet selected by the endpoint).

   State clearly that this story creates the study-helper capability only and that selection between the chains is Story 3.2.
7. **Do not add:** routing, LLM-based classification, more specialists, loops, review steps, a second application, endpoint, model provider, or UI, a database, retrieval, MCP, tool calls, LangGraph, an autonomous agent, broad tests, or production controls.

## Completion checks

Keep these lightweight and report the commands you actually ran:

1. `uv run ruff format .` and `uv run ruff check .` are clean. (Inside an activated `.venv`, run `ruff format .` and `ruff check .` instead.)
2. Start the app: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8001`. In Open WebUI, send one general-chat message (for example "Hello!") and confirm it behaves exactly as before.
3. Run the study helper once from the project folder, for example: `uv run python scripts/try_study_helper.py "What is an API?"` (use your actual script name).
4. Confirm the study-helper answer contains a plain explanation and exactly one next step, and does not claim to browse or look things up.

Expected results: Open WebUI general chat is unchanged; the local study-helper run prints a short explanation, a small example if useful, and one "next step" line.

## Handover

Files changed:

- `src/learning_companion/prompt.py` (or a new `study_prompt.py`): study-helper prompt
- `src/learning_companion/chain.py`: `build_study_helper_chain`
- `scripts/try_study_helper.py` (or equivalent): development invocation
- `docs/architecture.md`: the two chain behaviours
- `docs/stories/story-3-1-study-helper-chain.md` (this story)

Record when done: the commands actually run, the Open WebUI general-chat result, and the study-helper output seen.

What Story 3.2 will extend: a visible `/study` route rule so the endpoint selects the study-helper chain for study requests and the general-chat chain otherwise, using the same endpoint and Open WebUI conversation.
