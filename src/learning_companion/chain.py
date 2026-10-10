from typing import Literal

from langchain_core.output_parsers import StrOutputParser
from langchain_xai import ChatXAI
from pydantic import BaseModel, Field

from learning_companion.debug import PayloadPrinter
from learning_companion.prompt import (
    IMPROVER_PROMPT,
    PROMPT,
    REVIEW_PROMPT,
    STUDY_HELPER_PROMPT,
)
from learning_companion.settings import Settings


class ConfigurationError(Exception):
    pass


def _build_model(settings: Settings) -> ChatXAI:
    missing = [
        name
        for name, value in (
            ("GROK_API_KEY", settings.grok_api_key),
            ("GROK_MODEL_NAME", settings.grok_model_name),
        )
        if not value
    ]
    if missing:
        raise ConfigurationError(
            f"Missing setting(s): {', '.join(missing)}. Set them in your untracked .env file."
        )
    callbacks = []
    if settings.log_llm_payloads:
        callbacks.append(PayloadPrinter(settings.grok_model_name, settings.grok_api_base_url))
    return ChatXAI(
        model=settings.grok_model_name,
        api_key=settings.grok_api_key,
        xai_api_base=settings.grok_api_base_url,
        callbacks=callbacks,
    )


def build_chain(settings: Settings):
    """General chat: prompt -> Grok chat model -> text output."""
    return PROMPT | _build_model(settings) | StrOutputParser()


def build_study_helper_chain(settings: Settings):
    """Study helper: study prompt -> same Grok chat model -> text output."""
    return STUDY_HELPER_PROMPT | _build_model(settings) | StrOutputParser()


class ReviewDecision(BaseModel):
    decision: Literal["approve", "improve"]
    reason: str = Field(description="One short plain-English reason.")


def build_reviewer_chain(settings: Settings):
    """Reviewer: review prompt -> same Grok model -> structured approve/improve decision."""
    return REVIEW_PROMPT | _build_model(settings).with_structured_output(ReviewDecision)


def build_improver_chain(settings: Settings):
    """Improver: improver prompt -> same Grok model -> rewritten answer text."""
    return IMPROVER_PROMPT | _build_model(settings) | StrOutputParser()
