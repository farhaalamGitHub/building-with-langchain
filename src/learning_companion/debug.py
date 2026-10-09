import json
import sys
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


def print_block(title: str, body: Any) -> None:
    print(f"\n===== {title} =====", file=sys.stderr)
    print(body if isinstance(body, str) else json.dumps(body, indent=2), file=sys.stderr)
    sys.stderr.flush()


class PayloadPrinter(BaseCallbackHandler):
    """Development aid: print what is sent to, and received from, the LLM. Never prints keys."""

    def __init__(self, model: str, base_url: str) -> None:
        self.model = model
        self.base_url = base_url

    def _print(self, title: str, body: Any) -> None:
        print(f"\n===== {title} =====", file=sys.stderr)
        print(body if isinstance(body, str) else json.dumps(body, indent=2), file=sys.stderr)
        sys.stderr.flush()

    def on_chat_model_start(self, serialized, messages, **kwargs: Any) -> None:
        for batch in messages:
            self._print(
                f"LLM REQUEST  POST {self.base_url}/chat/completions",
                {
                    "model": self.model,
                    "messages": [{"role": m.type, "content": m.content} for m in batch],
                },
            )

    def on_llm_end(self, response, **kwargs: Any) -> None:
        text = "".join(g.text for gens in response.generations for g in gens)
        self._print("LLM RESPONSE", text)

    def on_llm_error(self, error, **kwargs: Any) -> None:
        self._print("LLM ERROR", repr(error))
