# Story 4.1 — LangGraph routing workflow

## Purpose

Story 3.2 chooses between the two chains with a visible Python `if/else`. This story replaces only that internal choice with one small LangGraph workflow that makes the same choice. The route, the state, the nodes and the edges become visible in code. For the participant, nothing changes: same Open WebUI chat, same endpoint, same answers.

## What this story implements in plain English

After this story, a question typed in Open WebUI goes through these steps:

- The chat endpoint receives it exactly as before and hands it to a small workflow.
- The workflow starts at a **router**, a few lines of ordinary Python, not an AI agent. If the message starts with `/study`, it picks `study`. Otherwise it picks `general`.
- The workflow then runs one answering step: the general-chat step or the study-helper step. Each calls the chain that already exists and writes the final answer.
- The workflow ends, and the endpoint sends the answer back to Open WebUI in the usual normal or streaming format.
- In development, a short log shows the route and the steps that ran, for example `route: study | nodes: router -> study_helper`.

## Prerequisites

- Stories 1.1–3.2 are complete: the three endpoints, Grok settings, request-provided history (Story 2.2, `MAX_HISTORY_MESSAGES = 10`), `build_chain` and `build_study_helper_chain`, the visible `/study` rule and route log (Story 3.2), normal JSON and SSE behavior, and the working Open WebUI connection.
- If Story 3.2 is not yet implemented, build it first or add its `/study` rule as specified there. This story must reproduce that rule, not invent a new one.
- Existing code to read first: `src/learning_companion/main.py`, `prompt.py`, `chain.py`, `debug.py`, `settings.py`, `.env.example`, `docs/architecture.md`, and Stories 1.1–3.2. No `docs/config.yaml` exists; the project is at the repository root.
- Preserve the endpoints, request/response shape, Grok settings, message-history conversion, normal JSON replies, streaming SSE behavior, and the Open WebUI connection.
- `langgraph` is not yet a project dependency. Adding it with `uv add langgraph` is part of this story's work.

## Work to do

1. **Learn the words first.** In the story's handover notes and in `docs/architecture.md`, use these terms precisely:
   - A **node** is one focused piece of work. It is not automatically an agent.
   - The **router node** is ordinary application logic.
   - The **general-chat** and **study-helper** nodes are small specialist behaviours, each powered by Grok through an existing chain.
   - An **edge** says which node runs next. A **conditional edge** picks the next node from the state.
   - An MCP tool call could sit inside a future node. MCP is **not** implemented here.
2. **Define the graph state.** In a new `src/learning_companion/graph.py`, add a small typed state (a `TypedDict`) with four fields:

   | Field | Plain meaning |
   |---|---|
   | `question` | The current user message, the latest `user` message from the request. |
   | `history` | The current conversation messages: earlier request messages as LangChain messages, built by `split_conversation` and capped as in Story 2.2. |
   | `route` | `"general"` or `"study"`. Empty until the router writes it. |
   | `answer` | The final answer text. Empty until an answer node writes it. |

   A node returns only the fields it changes. The state is created per request and is never saved.
3. **Add the three nodes, and only these.**
   - `router`: ordinary Python. It applies the Story 3.2 `/study` rule unchanged: the leading `/study` marker (followed by whitespace or the end of the message) selects `study`, and the marker is stripped from `question` for that route. Otherwise it selects `general`. It writes `route` (and the stripped `question`). No model call. Keep the Story 3.2 empty-`/study` friendly reply. For that case the router writes the reply to `answer`, and the graph ends without calling a model, still using only the three nodes. Choose the simplest wiring that keeps the edges below.
   - `general_chat`: calls the existing `build_chain` chain with `question` and `history`, and writes `answer`.
   - `study_helper`: calls the existing `build_study_helper_chain` chain with `question` and `history`, and writes `answer`.

   Do not rewrite or change either chain or its prompt. Build the graph from the settings-built chains, and keep the `ConfigurationError` → 503 handling working in the endpoint.
4. **Wire the edges explicitly with `StateGraph`.**
   - `START → router`
   - conditional edge from `router` to `general_chat` or `study_helper`, chosen by `state["route"]`
   - `general_chat → END`
   - `study_helper → END`

   Write these as plain `add_node`, `add_edge` and `add_conditional_edges` calls in one place so the diagram can be read straight from the code. No reviewer, improver, loop, or retry. Story 4.2 adds the bounded review path.
5. **Call the graph from the existing endpoint.** In `chat_completions`, replace the Story 3.2 `if/else` chain selection with one graph invocation. Keep `split_conversation`, the 400 for no user message, the 503 for configuration problems, and the 502 for model failures.
6. **Keep both response paths.**
   - `stream: false`: run the graph (`invoke`) and return the final `answer` through the existing JSON response.
   - `stream: true`: keep the existing SSE adapter shape (role chunk, text chunks, stop chunk, `[DONE]`). The graph must not break streaming. A simple, acceptable approach: run the router step through the graph for the route decision, then stream the selected chain's output through the existing adapter. Or, where LangGraph's streaming works cleanly, stream the answer node's text. Pick one approach, and state it in the story handover and architecture doc. Do not create a second response format, custom fields, or a second endpoint.
   - Keep the Story 3.2 in-text route label (`[route: general]` or `[route: study]`) on both paths, if Story 3.2 added it.
7. **Add a compact trace.** In `APP_ENV=development`, log one line per request with the route and the node sequence, for example `route: study | nodes: router -> study_helper`. Record each node name as it runs (for example by appending it to a small list in the state or by a tiny logging wrapper). It is acceptable to add that list as a fifth internal state field only if it stays out of the four documented fields in the architecture doc. Never log API keys, message text, or the application instructions.
8. **Update `docs/architecture.md`.** Add a LangGraph section with:
   - a small diagram, for example:

     ```
     START → router ──(route = general)──► general_chat ──► END
                    └─(route = study)────► study_helper ──► END
     ```
   - the state fields and their plain meanings;
   - the three node responsibilities;
   - the edge rules;
   - the streaming approach chosen;
   - what stays out of scope: the FastAPI service, endpoint, Open WebUI, Grok settings and history conversion are unchanged. No LLM routing, review, loop, retry, tools, MCP, persistence or extra agents.

   Update the chain behaviours table to say the chains are now called from graph nodes, and mark Story 4.1 in the roadmap. Add that Story 4.2 adds the bounded review path.
9. **Update `README.md` only if it describes the internals.** If it does, add one line about the graph. Otherwise leave it.
10. **Do not add:** databases, persistence, RAG, web search, tool execution, MCP, human approval, review steps, loops, retries, additional agents, a second application or chat route, broad test suites, security programmes, observability platforms, or deployment work.

## Completion checks

Keep these lightweight and report the commands you actually ran:

1. `uv add langgraph`, then `uv run ruff format .` and `uv run ruff check .` are clean. (Inside an activated `.venv`, run `ruff format .` and `ruff check .` instead.)
2. Start the app: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8001` (use the port that matches the Open WebUI connection).
3. In Open WebUI, send one general-chat message: `Hello!`
4. In the same conversation, send: `/study Explain what an API is`
5. Inspect the compact trace in the development log.

Expected Open WebUI results:

- **General message:** a normal friendly reply, as before (with `[route: general]` if Story 3.2 added the label).
- **`/study` message:** a plain explanation of an API, a small example if useful, and exactly one "Next step:" line, about "Explain what an API is" and not the literal `/study` (with `[route: study]` if labelled).
- Both final answers appear in the same Open WebUI conversation, through the same endpoint, and stream normally.

Expected trace, in order:

```
route: general | nodes: router -> general_chat
route: study | nodes: router -> study_helper
```

## Handover

Files changed:

- `pyproject.toml` and `uv.lock`: `langgraph` dependency
- `src/learning_companion/graph.py` (new): state, three nodes, explicit edges, compiled graph
- `src/learning_companion/main.py`: replace the Story 3.2 `if/else` with the graph call, keep both response paths, add the trace line
- `docs/architecture.md`: graph diagram, state fields, node responsibilities, edge rules, scope
- `README.md`: one line, only if it describes internals
- `docs/stories/story-4-1-langgraph-routing-workflow.md` (this story)

Record when done: the commands actually run, the streaming approach chosen, the two trace lines seen, and what Open WebUI showed for each message.

What Story 4.2 will extend: a bounded review path added to this same graph. A reviewer step checks the answer and may send it back for one limited improvement before `END`. It uses the same state, endpoint and Open WebUI conversation, and keeps this routing intact.
