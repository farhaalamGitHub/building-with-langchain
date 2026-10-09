"""Development helper: run the study-helper chain once. Not used by the Open WebUI endpoint.

Usage: uv run python scripts/try_study_helper.py "What is an API?"
"""

import sys

from learning_companion.chain import ConfigurationError, build_study_helper_chain
from learning_companion.settings import get_settings


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage: python scripts/try_study_helper.py "your question"')
        return 2
    try:
        chain = build_study_helper_chain(get_settings())
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}")
        return 1
    print(chain.invoke({"question": question, "history": []}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
