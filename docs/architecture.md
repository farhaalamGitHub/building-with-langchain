# Architecture — Learning Companion Chatbot

Status: **Draft — awaiting instructor approval** (Story 1.1 must not create seed files until approved).

## Classroom flow

There is one flow only:

`Open WebUI → this local application's OpenAI-compatible chat endpoint → LangChain prompt and Grok model → answer in Open WebUI`

1. The participant types a message in Open WebUI.
2. Open WebUI sends it to this local application's `POST /v1/chat/completions`.
3. The application builds a LangChain prompt (fixed Learning Companion instruction + the latest user message) and calls the Grok chat model.
4. The reply goes back in OpenAI-compatible format (JSON, or text-only SSE chunks when streaming) and appears in Open WebUI.

## Message flow (Stories 2.1 and 2.2)

1. Open WebUI sends an OpenAI-compatible request: `model`, `messages` (roles `system`, `user`, `assistant`), `stream`.
2. The app takes the **latest `user` message** as the current question.
3. Earlier `user` and `assistant` messages from the same request become history, in their original order, capped at the most recent **10** (`MAX_HISTORY_MESSAGES`).
4. Request `system` messages, unsupported roles, and empty or non-text content are ignored. A request `system` message never replaces the application's instruction.
5. A LangChain `ChatPromptTemplate` builds, in this order: application **system** instruction, a `MessagesPlaceholder("history")`, then the current **human** message.
6. The chain `prompt -> Grok model -> text output` serves both paths: `stream: false` returns chat-completion JSON; `stream: true` returns text-only SSE chunks, a stop chunk, then `[DONE]`.
7. A development-only log shows roles, order and message count (for example `system -> human -> ai -> human [4 messages]`). Never keys, the instruction, or message text.

## No-persistence boundary

History is only what the current Open WebUI request already contains. The app saves nothing after a request completes: no database, cross-session memory, or stored chats. A new chat starts fresh.

## Chain behaviours (Story 3.1)

| Chain | Responsibility | Used by endpoint? |
|---|---|---|
| General chat (`build_chain`) | Greetings and ordinary conversation | Yes, for every message that does not start with `/study` |
| Study helper (`build_study_helper_chain`) | Beginner technical concepts in plain language, a small example, one "Next step:" line. No research, browsing, retrieval, or correctness guarantee. | Yes, when the message starts with `/study` (also runnable via `scripts/try_study_helper.py`) |

Both use the same configured Grok model and the same request history. Story 3.1 creates the study-helper capability only; selecting between the chains (a visible `/study` rule) is Story 3.2.

## LangGraph workflow: routing and bounded review (Stories 3.2, 4.1, 4.2)

The endpoint, Open WebUI connection, Grok settings, history conversion and the JSON/SSE adapter are unchanged. Inside the endpoint, `src/learning_companion/graph.py` holds one small LangGraph graph that reuses the two existing answer chains and adds a reviewer and an improver.

```
START -> router --(general)-----------> general_chat --+
               +--(study)-------------> study_helper ---+--> reviewer --(approve)--> END
               +--(empty /study)--> END                       |
                                                              +--(improve, only when
                                                                  revision_count = 0)--> improver
                                                                                            |
                                                              reviewer <--------------------+
```

State (created per request, never saved):

| Field | Meaning |
|---|---|
| `question` | Current user message (the leading `/study` is stripped on the study route) |
| `history` | Earlier request messages, capped at `MAX_HISTORY_MESSAGES` |
| `route` | `general` or `study`, written by the router |
| `draft_answer` | Current answer text: the first draft, then the improver's rewrite |
| `review_decision` | `approve` or `improve`, written by the reviewer each time it runs |
| `review_reason` | One short plain-English reason for that decision |
| `revision_count` | How many times the improver has rewritten the draft (starts at 0, never above 1) |
| `final_answer` | The answer sent to Open WebUI, written when the draft is accepted |
| `nodes` | Trace only: node names in the order they ran |

Nodes (a node is a focused piece of work, not automatically an agent):

- `router`: ordinary Python, no model. A message beginning with `/study` (followed by whitespace or the end) selects `study`; everything else selects `general`. `/study` alone returns a short hint as `final_answer` and ends without a model call or review.
- `general_chat` and `study_helper`: run the existing chains and write `draft_answer`.
- `reviewer`: a small Grok-powered specialist. It checks the draft against a short fixed rule (general: friendly, clear, answers the question; study: plain explanation, small example when useful, exactly one `Next step:` line) and returns a structured `approve` or `improve` with one short reason. When it approves, it copies the draft to `final_answer`.
- `improver`: a small Grok-powered specialist. It rewrites the draft once using the reviewer's reason and increments `revision_count`. No tools, browsing, retrieval, planning or routing.

Edge rules: `START -> router`; router to `general_chat`, `study_helper` or `END`; each answer node `-> reviewer`; reviewer `approve -> END`, `improve -> improver`; `improver -> reviewer`. The single cycle is reviewer, improver, reviewer. The limit is enforced in plain Python: when `revision_count` is 1, the reviewer makes no model call and accepts the current draft as final. So there is at most one improvement and no other loop or retry.

Response path: the draft must be reviewed first, so the final text is sent only once the graph finishes. For `stream: true`, the endpoint then sends it as ordinary SSE text chunks, a stop chunk and `[DONE]`, so the first text appears after the review rather than word by word. Each reply starts with a `[route: general]` or `[route: study]` label. Open WebUI stores that label in the chat, so it comes back in later history.

Trace: in development the log shows one line per request, for example `route: study | review: improve -> approve | revisions: 1 | nodes: router -> study_helper -> reviewer -> improver -> reviewer`. It never contains keys, message text, drafts or instructions. With `LOG_LLM_PAYLOADS=true` the terminal also prints REQUEST, SENT TO MODEL and RESPONSE blocks.

Out of scope: LLM-based routing, planners, tools, MCP (a future node could call one), persistence, retrieval, human approval, extra agents, and any loop beyond the one revision.

## Components

| Component | Role |
|---|---|
| Open WebUI | Supplied chat client. Already installed and working. Participants never reinstall, reconfigure, modify, or build it. |
| Local application (FastAPI) | Exposes `GET /health`, `GET /v1/models`, `POST /v1/chat/completions`. |
| LangChain / LangGraph flow | Router, answer chains (prompt → Grok chat model → text), reviewer and improver. |
| Grok (xAI) | Model provider, reached via `GROK_API_BASE_URL`. Model name supplied by the instructor. |

## Technology

Python 3.12, UV, FastAPI, Uvicorn, Pydantic settings, `langchain` with the Grok-compatible provider integration, Ruff, and a minimal test runner.

Planned layout: `src/learning_companion/`, `tests/`, `.env.example`, `.gitignore`, `pyproject.toml`, `uv.lock`, `README.md`.

## Configuration

Settings come from environment variables / an untracked `.env`:

`APP_ENV=development`, `GROK_API_KEY` (blank), `GROK_API_BASE_URL=https://api.x.ai/v1`, `GROK_MODEL_NAME` (blank, instructor-supplied), `HOST=127.0.0.1`, `PORT=8000`.

The app starts without a real key and returns an honest configuration error only when a model call is attempted.

## Boundaries

- The capstone is a small **Learning Companion Chatbot** — not a custom frontend, not a second demo application.
- API keys live only in the untracked `.env`.
- Application instructions stay separate from user messages.
- Only one chat route; no custom Open WebUI events.

## Out of scope

Authentication, authorization, security hardening, databases, persistent memory, RAG, production deployment, extensive tests, tool calls, agents, MCP.

## Roadmap

- Story 1.1: this architecture and the project seed.
- Story 2.1: LangChain chat prompt template (stable system instruction + latest user message).
- Story 2.2: request-provided conversation history on the same endpoint.
- Story 3.1: study-helper chain (development invocation only).
- Story 3.2: `/study` route rule selecting between the chains.
- Story 4.1: the same rule as a LangGraph workflow (router, general_chat, study_helper).
- Story 4.2: bounded review and one improvement (reviewer, improver) added to the same graph.
