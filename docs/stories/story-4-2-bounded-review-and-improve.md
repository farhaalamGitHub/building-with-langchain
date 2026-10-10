# Story 4.2 — Bounded answer review and improvement

## Purpose

Story 4.1 routes a question to the right answering step and returns that answer. This story adds a small quality check. A reviewer looks at the draft answer once. If it is not clear or not right for its role, an improver rewrites it once. Then the workflow stops. It adds two nodes to the existing graph and does not rebuild it.

## What this story implements in plain English

After this story:

- The chatbot first writes a **draft** answer, using the same general-chat or `/study` path as before.
- A **reviewer** checks the draft once against a short fixed classroom rule and answers `approve` or `improve`, with one short reason.
- If the answer is `improve`, an **improver** rewrites the draft **once**, using the reviewer's reason. The reviewer then looks again and the draft is accepted as final, whatever the decision. The chatbot can never improve an answer more than once.
- Then the workflow stops. There is no unlimited self-correction, no planning, and no tools. It is a fixed, short path.
- Open WebUI shows only the final answer, as before. A short development log shows whether the draft was approved or improved.

## Prerequisites

- Stories 1.1–4.1 are complete: the three endpoints, Grok settings, request-provided history, the two chains (`build_chain`, `build_study_helper_chain`), the three-node LangGraph in `src/learning_companion/graph.py` (`router`, `general_chat`, `study_helper`), the `[route: ...]` label, the route trace, normal JSON and SSE behavior, and the working Open WebUI connection.
- Existing code to read first: `src/learning_companion/graph.py`, `main.py`, `chain.py`, `prompt.py`, `debug.py`, `settings.py`, `.env.example`, `docs/architecture.md`, and Stories 1.1–4.1. No `docs/config.yaml` exists; the project is at the repository root.
- No new dependency is needed. LangGraph is already installed.
- Preserve the endpoints, request/response shape, Grok settings, message-history conversion, normal JSON replies, streaming SSE behavior, and the existing routing path.

## Work to do

1. **Learn the words first.** Use these terms precisely in the code comments and `docs/architecture.md`:
   - The **router** is ordinary Python logic. It is not an agent.
   - The **reviewer** and **improver** are small LLM-powered specialist nodes. For this classroom example they may be called specialist agents.
   - A **cycle** is a path that returns to an earlier node. This story has exactly one: reviewer → improver → reviewer.
   - There is no MCP tool call here. An MCP call could be a future node. It is outside this story.
2. **Extend the graph state with exactly five fields.** In `graph.py`, add to the existing state (keep `question`, `history`, `route` and the trace list as they are):

   | New field | Plain meaning |
   |---|---|
   | `draft_answer` | The current answer text. An answer node writes the first draft, and the improver replaces it with the rewrite. |
   | `review_decision` | `approve` or `improve`, written by the reviewer each time it runs. |
   | `review_reason` | One short plain-English reason for the decision. |
   | `revision_count` | How many times the improver has rewritten the draft. Starts at 0, never goes above 1. |
   | `final_answer` | The answer sent to Open WebUI. Written once, when the reviewer accepts the draft. |

   The Story 4.1 `answer` field is replaced by `draft_answer`. The answer nodes now write a draft, not a final answer. Initialise `revision_count` to 0 in the endpoint's starting state.
3. **Change the existing nodes only as needed.**
   - `router`: unchanged, except that the empty `/study` reply is written straight to `final_answer`. That reply skips review and goes to `END` through the existing conditional edge.
   - `general_chat` and `study_helper`: call the same chains as before, but write `draft_answer`. Remove their stream writer, because a draft must not reach the user before it is reviewed.
4. **Add the reviewer node (Grok-powered).** Add a small fixed rule and use LangChain structured output (a small Pydantic model with `decision: Literal["approve", "improve"]` and `reason: str`). It receives `draft_answer`, `route`, and the user's `question`. The rule is short and fixed, for example:
   - **general:** friendly, clear, plain English, answers what was asked.
   - **study:** a plain explanation of a beginner concept, a small example if useful, and exactly one "Next step:" line.

   The reviewer's own instruction is kept in the application, separate from the user's text, and is never logged. It writes `review_decision` and `review_reason`. When it approves, it also copies `draft_answer` to `final_answer`.
   - **The limit is enforced in Python, not by the model.** If `revision_count` is already 1, the reviewer does not ask the model. It writes `approve` with the reason `revision limit reached` and sets `final_answer` to the current draft.
5. **Add the improver node (Grok-powered).** It receives `draft_answer`, `review_reason`, `route` and the question, and rewrites the answer once. It writes the new `draft_answer` and sets `revision_count` to `revision_count + 1`. It does not use tools, browse, retrieve information, plan, or choose a route. Its instruction keeps the route's role (general or study, including the single "Next step:" line).
6. **Wire the bounded edges with `StateGraph`**, in the same place as the Story 4.1 edges:
   - `START → router` and the router's conditional edge are unchanged.
   - `general_chat → reviewer` and `study_helper → reviewer`.
   - conditional edge from `reviewer`: `approve` → `END`; `improve` → `improver` (only possible when `revision_count` is 0, because the reviewer approves at 1).
   - `improver → reviewer`.

   This gives a visible cycle (reviewer → improver → reviewer) and a maximum of one improvement. There is no other loop, retry, planner, tool, or open-ended behaviour.
7. **If the reviewer or improver model call fails,** the endpoint's existing 502 handling applies. Do not add a retry.
8. **Keep both response paths.** Return `final_answer` through the existing adapter:
   - `stream: false`: the existing JSON reply with `[route: ...]` label plus `final_answer`.
   - `stream: true`: the existing SSE shape (role chunk, text chunks, stop chunk, `[DONE]`). The draft has to be reviewed first, so the final text is sent as SSE chunks once the graph finishes, not token by token. This means a slightly longer wait before the first text appears. Say so in the architecture doc. Do not add custom fields, events, or a second endpoint. Replace the Story 4.1 custom-stream code in `main.py` accordingly.
9. **Add a compact trace.** In `APP_ENV=development`, log one line per request, for example:
   `route: study | review: improve -> approve | revisions: 1 | nodes: router -> study_helper -> reviewer -> improver -> reviewer`

   Record the reviewer's decision each time it runs. Never log API keys, message text, the draft, the reviewer's instruction, or full prompts. The short review reason may be logged, because it is the reviewer's own output and contains no user text.
10. **Update `docs/architecture.md`.** Add the two nodes, the five new state fields, the full graph diagram, the edge rules, the one-revision limit, the streaming note, and the scope boundary. Diagram:

    ```
    START → router ──(general)──► general_chat ──┐
                   └─(study)────► study_helper ──┤
                   └─(empty /study)──► END       ▼
                                             reviewer ◄──── improver
                                              │  │              ▲
                                  approve ────┘  └── improve ───┘
                                     ▼        (only when revision_count = 0)
                                    END
    ```

    Mark Story 4.2 as done in the roadmap.
11. **Update `README.md` only if it describes the internals.** If it does, add one line about the review step.
12. **Do not add:** databases, persistence, RAG, web search, tools, MCP, human approval, further agents, more loops or retries, broad test suites, production controls, observability platforms, or deployment work.

## Completion checks

Keep these lightweight and report the commands you actually ran:

1. `uv run ruff format .` and `uv run ruff check .` are clean. (Inside an activated `.venv`, run `ruff format .` and `ruff check .` instead.)
2. Start the app: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8001` (use the port that matches the Open WebUI connection).
3. In Open WebUI, send an ordinary question that the reviewer should approve directly: `Hello!`
4. Send a `/study` question that is likely to benefit from clearer wording, for example: `/study Explain variables, loops, functions and classes`. A broad question like this often produces a long answer or more than one next step.
5. Confirm both final answers appear in the same Open WebUI conversation, and inspect the compact trace.

Expected Open WebUI results:

- **`Hello!`:** `[route: general]`, then a friendly reply. It is the draft, unchanged.
- **The `/study` question:** `[route: study]`, then a clear beginner explanation with exactly one "Next step:" line. It is the improved draft if the reviewer asked for improvement.

Expected traces:

```
route: general | review: approve | revisions: 0 | nodes: router -> general_chat -> reviewer
route: study | review: improve -> approve | revisions: 1 | nodes: router -> study_helper -> reviewer -> improver -> reviewer
```

The reviewer is a model, so the second example may be approved on the first pass (`nodes: router -> study_helper -> reviewer`). If so, record that honestly and try a broader question. A trace never shows more than one improver run.

## Handover

Files changed:

- `src/learning_companion/graph.py`: five new state fields, reviewer and improver nodes, the bounded edges, draft-writing answer nodes
- `src/learning_companion/main.py`: return `final_answer` through the existing adapter, send the final text as SSE chunks, extended trace line
- `src/learning_companion/prompt.py` (or a new `review_prompt.py`): the fixed review rule and improver instruction, kept as application-owned text
- `docs/architecture.md`: new nodes, state, full diagram, edge rules, one-revision limit, scope
- `README.md`: one line, only if it describes internals
- `docs/stories/story-4-2-bounded-review-and-improve.md` (this story)

Record when done: the commands actually run, both trace lines seen, and what Open WebUI showed for each message.

Final capstone outcome: one Open WebUI chat connected to one FastAPI endpoint. Python routes each message with a visible LangGraph router, and two specialist behaviours (general chat and study helper) write a draft. A reviewer checks the draft once, an improver may rewrite it once, and the final answer comes back through the same OpenAI-compatible adapter. Everything is bounded and visible in code and in a compact trace. There are no tools, MCP, persistence, or open-ended agents. MCP could be a future node and is not part of this course.
