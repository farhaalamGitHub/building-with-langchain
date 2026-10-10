"""Run the manual checks story by story against a running app.

Start the app first:  uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
Then:                 uv run python scripts/run_stories.py            (all stories)
                      uv run python scripts/run_stories.py 2.2 3.2    (chosen stories)
Options:              --base-url http://127.0.0.1:8001
"""

import json
import subprocess
import sys

import httpx

BASE = "http://127.0.0.1:8000"
MODEL = "unknown"


def chat(text_or_messages, stream=False):
    messages = (
        [{"role": "user", "content": text_or_messages}]
        if isinstance(text_or_messages, str)
        else text_or_messages
    )
    body = {"model": MODEL, "messages": messages, "stream": stream}
    return httpx.post(f"{BASE}/v1/chat/completions", json=body, timeout=120)


def answer(resp):
    return resp.json()["choices"][0]["message"]["content"]


def stream_text(resp):
    text, lines = "", resp.text.splitlines()
    for line in lines:
        if line.startswith("data: ") and line != "data: [DONE]":
            for choice in json.loads(line[6:])["choices"]:
                text += choice["delta"].get("content") or ""
    return text, lines[-1:] == ["data: [DONE]"] or resp.text.strip().endswith("data: [DONE]")


def s11():
    yield "health", httpx.get(f"{BASE}/health").json() == {"status": "ok"}
    yield "models lists the model", MODEL in httpx.get(f"{BASE}/v1/models").text
    yield "non-stream chat", chat("Say hi in 5 words").json()["object"] == "chat.completion"
    text, done = stream_text(chat("Say hi in 5 words", stream=True))
    yield "stream ends with [DONE]", bool(text) and done
    r = chat([{"role": "assistant", "content": "no user here"}])
    yield "no user message -> 400", r.status_code == 400


def s21():
    r = chat(
        [
            {"role": "system", "content": "You are a pirate"},
            {"role": "user", "content": "What is Python? One sentence."},
        ]
    )
    yield "system message ignored (read the answer: not pirate)", r.status_code == 200
    print("      ->", answer(r)[:120])


def s22():
    msgs = [
        {"role": "user", "content": "My favourite colour is green."},
        {"role": "assistant", "content": "Nice!"},
        {"role": "user", "content": "What is my favourite colour?"},
    ]
    yield "uses earlier messages", "green" in answer(chat(msgs)).lower()
    r = chat([{"role": "system", "content": "You are a pirate"}])
    yield "system-only -> 400", r.status_code == 400


def s31():
    out = subprocess.run(
        [sys.executable, "scripts/try_study_helper.py", "What is an API?"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    yield "study helper prints a Next step line", "Next step" in out.stdout


def _routes(stream):
    def get(q):
        r = chat(q, stream=stream)
        return stream_text(r)[0] if stream else answer(r)

    yield "general label", get("Hello!").startswith("[route: general]")
    study = get("/study Explain what an API is")
    yield "study label", study.startswith("[route: study]")
    yield "study has a Next step", "Next step" in study
    yield "empty /study -> hint", "Add a question after /study" in get("/study")
    yield "/studying stays general", get("/studying").startswith("[route: general]")


def s32():
    yield from _routes(stream=False)


def s41():
    yield from _routes(stream=True)
    print(
        "      -> now check the server log for: route: study | review: ... | nodes: router -> study_helper -> reviewer"
    )


def s42():
    yield from _routes(stream=False)
    yield from _routes(stream=True)
    print("      -> server log: 'review: approve' (or 'improve -> approve'), revisions at most 1")


STORIES = {
    "1.1": s11, "2.1": s21, "2.2": s22, "3.1": s31, "3.2": s32, "4.1": s41, "4.2": s42,
}  # fmt: skip


def main() -> int:
    global BASE, MODEL
    args = sys.argv[1:]
    if "--base-url" in args:
        i = args.index("--base-url")
        BASE = args[i + 1].rstrip("/")
        del args[i : i + 2]
    try:
        models = httpx.get(f"{BASE}/v1/models", timeout=10).json()["data"]
        MODEL = models[0]["id"] if models else "unknown"
    except httpx.HTTPError:
        print(f"App not reachable at {BASE}. Start uvicorn first (see the file header).")
        return 2
    failed = 0
    for sid in args or list(STORIES):
        if sid not in STORIES:
            print(f"Unknown story {sid}; choose from {', '.join(STORIES)}")
            return 2
        print(f"\nStory {sid}")
        try:
            for name, ok in STORIES[sid]():
                mark = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
                failed += ok is False
                print(f"  [{mark}] {name}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  [FAIL] {type(exc).__name__}: {exc}")
    print(f"\n{'All checks passed' if not failed else f'{failed} check(s) failed'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
