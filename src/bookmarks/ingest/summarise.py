"""The summariser prompt: building the request and validating the reply."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ValidationError, field_validator

from bookmarks.ingest.llm.provider import LLMRequest

PROMPT_PATH = Path(__file__).parent / "prompts" / "summarise.md"


@dataclass(frozen=True)
class Prompt:
    text: str
    hash: str


def load_prompt(path: Path = PROMPT_PATH) -> Prompt:
    """The prompt version is the content hash of the prompt file."""
    text = path.read_text(encoding="utf-8")
    return Prompt(text=text, hash=hashlib.sha256(text.encode()).hexdigest()[:12])


def cap_source(text: str, cap_chars: int) -> tuple[str, bool]:
    """Keep the beginning; cut at the last whitespace before the cap."""
    if len(text) <= cap_chars:
        return text, False
    cut = text[:cap_chars]
    space = cut.rfind(" ")
    return (cut[:space] if space > cap_chars // 2 else cut), True


def build_request(
    prompt: Prompt,
    *,
    url: str,
    title: str | None,
    description: str | None,
    types: list[str],
    source: str,
    truncated: bool,
) -> LLMRequest:
    lines = [f"URL: {url}"]
    if title:
        lines.append(f"Page title: {title}")
    if description:
        lines.append(f"Page description: {description}")
    lines.append(f"Types in use: {', '.join(types)}")
    if truncated:
        lines.append(
            "Note: the page text below was truncated; only its beginning is "
            "included. Summarise what is there."
        )
    lines += ["", "Page text:", "<<<", source, ">>>"]
    return LLMRequest(system_prompt=prompt.text, user_prompt="\n".join(lines))


class Summary(BaseModel):
    title: str
    type: str
    summary: str
    entities: list[str]

    @field_validator("title", "type", "summary")
    @classmethod
    def _non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("type")
    @classmethod
    def _type_name(cls, value: str) -> str:
        return value.lower()

    @field_validator("entities")
    @classmethod
    def _entities(cls, value: list[str]) -> list[str]:
        seen: dict[str, str] = {}
        for entity in (e.strip() for e in value):
            if entity and entity.casefold() not in seen:
                seen[entity.casefold()] = entity
        return list(seen.values())


@dataclass(frozen=True)
class Unreadable:
    reason: str


class InvalidReply(Exception):
    """The reply is not the JSON the prompt asks for (a transient failure)."""


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def parse_reply(text: str) -> Summary | Unreadable:
    text = text.strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise InvalidReply(f"reply is not JSON: {text[:200]!r}") from None
    if not isinstance(data, dict):
        raise InvalidReply(f"reply is not a JSON object: {text[:200]!r}")
    if "unreadable" in data:
        reason = str(data["unreadable"]).strip() or "unreadable"
        return Unreadable(reason=reason)
    try:
        return Summary.model_validate(data)
    except ValidationError as exc:
        raise InvalidReply(f"reply fails the schema: {exc}") from None
