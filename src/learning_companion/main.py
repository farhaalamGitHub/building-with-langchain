import json
import logging
import time
import uuid
from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from learning_companion.chain import ConfigurationError, build_chain
from learning_companion.debug import print_block
from learning_companion.prompt import describe_prompt, split_conversation
from learning_companion.settings import get_settings

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Learning Companion")


class Message(BaseModel):
    # Lenient on purpose: unsupported roles or non-text content are ignored, not rejected.
    role: str
    content: str | list | None = None


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool = False


def _error(status: int, message: str, kind: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"message": message, "type": kind}})


def _chunk(cid: str, created: int, model: str, delta: dict, finish: str | None) -> str:
    data = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(data)}\n\n"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/v1/models")
def models() -> dict:
    name = get_settings().grok_model_name
    data = [{"id": name, "object": "model", "created": 0, "owned_by": "xai"}] if name else []
    return {"object": "list", "data": data}


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest):
    settings = get_settings()
    trace = settings.log_llm_payloads
    if trace:
        print_block("REQUEST", req.model_dump(exclude_none=True))
    try:
        chain = build_chain(settings)
    except ConfigurationError as exc:
        return _error(503, str(exc), "configuration_error")

    # Latest user message = question; earlier user/assistant messages = history (request-provided,
    # capped, never saved). A request "system" message never replaces the application instruction.
    question, history = split_conversation(req.messages)
    if not question:
        return _error(400, "No user message found.", "invalid_request_error")

    if settings.app_env == "development":
        logger.info("prompt: %s", describe_prompt(question, history))

    cid = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    model = settings.grok_model_name

    if not req.stream:
        try:
            text = chain.invoke({"question": question, "history": history})
        except Exception as exc:  # noqa: BLE001 - surface provider problems honestly
            return _error(502, f"Model call failed: {exc}", "upstream_error")
        body = {
            "id": cid,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
        }
        if trace:
            print_block("RESPONSE", body)
        return body

    def events() -> Iterator[str]:
        yield _chunk(cid, created, model, {"role": "assistant"}, None)
        parts: list[str] = []
        try:
            for piece in chain.stream({"question": question, "history": history}):
                if piece:
                    parts.append(piece)
                    yield _chunk(cid, created, model, {"content": piece}, None)
        except Exception as exc:  # noqa: BLE001
            yield _chunk(cid, created, model, {"content": f"[Model call failed: {exc}]"}, None)
        if trace:
            print_block("RESPONSE (streamed)", "".join(parts))
        yield _chunk(cid, created, model, {}, "stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
