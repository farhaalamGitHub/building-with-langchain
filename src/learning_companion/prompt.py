from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)

# Owned by the application. Never read from, or replaced by, the request.
INSTRUCTION = (
    "You are the Learning Companion, a friendly tutor for beginners. "
    "Explain things in short, plain English and give a small example when it helps."
)

# Most recent earlier user/assistant messages taken from the current request.
MAX_HISTORY_MESSAGES = 10

PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=INSTRUCTION),
        MessagesPlaceholder("history", optional=True),
        HumanMessagePromptTemplate.from_template("{question}"),
    ]
)

# Study-helper chain (Story 3.1): same shape, different application-owned instruction.
STUDY_HELPER_INSTRUCTION = (
    "You are the Learning Companion's study helper for beginners. "
    "Explain the technical concept the user asks about in plain language, concisely. "
    "Add a small example where it is useful. "
    "End with exactly one suggested next learning step, on its own line starting with "
    "'Next step:'. "
    "You do not research, browse, or look up course data, and you cannot guarantee that "
    "everything you say is correct."
)

STUDY_HELPER_PROMPT = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=STUDY_HELPER_INSTRUCTION),
        MessagesPlaceholder("history", optional=True),
        HumanMessagePromptTemplate.from_template("{question}"),
    ]
)


def message_text(content: Any) -> str:
    """Plain text of a message, or '' when it has no supported text content."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "\n".join(p for p in parts if isinstance(p, str)).strip()
    return ""


def split_conversation(messages: list[Any]) -> tuple[str, list[BaseMessage]]:
    """Return (latest user question, earlier history in original order).

    Request "system" messages and unsupported roles/content are ignored, so the
    application's own instruction always stays the only system message.
    """
    latest = None
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].role == "user" and message_text(messages[index].content):
            latest = index
            break
    if latest is None:
        return "", []
    history: list[BaseMessage] = []
    for message in messages[:latest]:
        text = message_text(message.content)
        if not text:
            continue
        if message.role == "user":
            history.append(HumanMessage(content=text))
        elif message.role == "assistant":
            history.append(AIMessage(content=text))
    question = message_text(messages[latest].content)
    return question, history[-MAX_HISTORY_MESSAGES:]


def describe_prompt(question: str, history: list[BaseMessage]) -> str:
    """Roles, order and count only. Never message text, the instruction, or keys."""
    messages = PROMPT.format_messages(question=question, history=history)
    return " -> ".join(m.type for m in messages) + f" [{len(messages)} messages]"
