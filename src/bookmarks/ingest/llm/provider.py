"""Provider adapter contract.

Copied and adapted from adventure-library `src/adventure_library/llm/provider.py`
at commit b264b17. Adapters normalise results and classify failures
internally; callers see LLMResult or ProviderFailure."""

from dataclasses import dataclass
from typing import Protocol

# failure classes that must pause the queue instead of retrying
PAUSE_CLASSES = ("auth", "rate_limit", "unavailable")


@dataclass(frozen=True)
class LLMRequest:
    system_prompt: str
    user_prompt: str


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str


class ProviderFailure(Exception):
    def __init__(self, failure_class: str, message: str):
        super().__init__(message)
        self.failure_class = failure_class


class LLMProvider(Protocol):
    name: str

    def submit(self, request: LLMRequest) -> LLMResult: ...
