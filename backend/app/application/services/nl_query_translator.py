"""Translate a Spanish question into a validated :class:`QueryIntent` (ADR-008).

This is the only place a language model's output crosses into the application,
and it crosses as a **type**, not as text. Everything the model returns is fed
to Pydantic; whatever fails validation is refused. There is no path that
inspects a model-supplied string and decides it looks safe enough.

The question travels as the **user message** and the vocabulary as the **system
prompt** (design G4/D5). Fusing them into one string is what lets "ignora las
instrucciones anteriores" read as a peer instruction rather than as data. The
port has offered ``query(system_prompt, user_message, model)`` since s3.2 and
nothing had used it until now.

**Policy lives in the use case, not here.** This module raises three distinct
exceptions and takes no view on what the director should see. Collapsing
infrastructure failure into "your question is unsupported" would be a lie the
logs could not correct.

Quota: exactly one request per question. No internal retry — the free tier caps
at 50/day, and the adapter already retries transport-level failures.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.config import settings
from app.domain.value_objects.query_intent import QueryIntent
from app.ports.llm_port import ILLMPort

log = logging.getLogger(__name__)


class TranslationFailedError(Exception):
    """The model's reply could not be read as JSON at all.

    Prose instead of an object, a truncated body, an empty string. Distinct
    from :class:`OutOfVocabularyError` because it says nothing about whether
    the question was answerable — only that the translator could not tell.
    """


class OutOfVocabularyError(Exception):
    """The reply was JSON, but not a question this system can answer.

    Either the model declared the question unanswerable, or it produced an
    intent that failed validation — an invented metric, a capitalised filter
    value, an extra key. Both mean the same thing to the director: the
    vocabulary does not cover this.
    """


#: Matches the first ``{...}`` block in a reply. Free-tier models routinely wrap
#: JSON in prose or markdown fences; punishing that would fail questions the
#: model actually translated correctly. Non-greedy from the first brace to the
#: last is deliberate — nested objects (``filters``) must survive.
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class NlQueryTranslator:
    """Turns one question into one intent, or raises."""

    def __init__(
        self,
        llm_port: ILLMPort,
        prompt_dir: Path | str,
        model: str | None = None,
    ) -> None:
        self._llm = llm_port
        self._prompt_dir = Path(prompt_dir)
        self._model = model or settings.MODEL_NL_QUERY
        self._template = self._load_template()

    def _load_template(self) -> str:
        """Load at construction so a missing prompt fails wiring, not a request.

        Mirrors ``CommunicationDraftService`` and ``LLMEnrichmentService``.
        """
        template_path = self._prompt_dir / "nl_query" / "v1_translate.txt"
        try:
            return template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise RuntimeError(f"Prompt template not found at {template_path}")

    async def translate(self, question: str) -> QueryIntent:
        """Ask the model to express ``question`` in the constrained vocabulary.

        Raises:
            OutOfVocabularyError: the question cannot be expressed, or the
                model produced something outside the allowed vocabulary.
            TranslationFailedError: the reply was not usable JSON.
            ExternalServiceError: propagated untouched from the adapter, so the
                use case can distinguish "we could not ask" from "we asked and
                the answer does not fit".
        """
        raw = await self._llm.query(
            system_prompt=self._template,
            user_message=question,
            model=self._model,
        )
        payload = self._extract_json(raw)

        if payload.get("answerable") is False:
            log.info("nl_query_out_of_vocabulary", extra={"reason": "model_declined"})
            raise OutOfVocabularyError("the model reported the question as unanswerable")

        try:
            return QueryIntent.model_validate(payload)
        except Exception as exc:
            # Deliberately broad: any validation failure is the same outcome to
            # the caller, and the specific Pydantic error belongs in the log
            # rather than in a director-facing message.
            log.info("nl_query_out_of_vocabulary", extra={"reason": str(exc)})
            raise OutOfVocabularyError(
                "the model produced an intent outside the supported vocabulary"
            ) from exc

    def _extract_json(self, raw: str) -> dict[str, Any]:
        """Pull the JSON object out of a reply that may be wrapped in prose."""
        match = _JSON_BLOCK.search(raw or "")
        if match is None:
            raise TranslationFailedError("no JSON object found in the model's reply")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise TranslationFailedError(f"model reply was not valid JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise TranslationFailedError("model reply was JSON but not an object")
        return parsed
