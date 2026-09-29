"""Model providers. Only offline providers exist until an API budget is approved.

A provider reports its price and an upper bound on the tokens a text can take, so the
runner can estimate cost before spending anything.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["FakeProvider", "Provider", "Response", "get_provider"]


@dataclass(frozen=True)
class Response:
    text: str
    input_tokens: int
    output_tokens: int


class Provider:
    name: str
    usd_per_million_input: float
    usd_per_million_output: float

    def max_tokens_for(self, text: str) -> int:
        """Upper bound on tokens for `text`. Byte-level tokenizers use at most one token
        per UTF-8 byte; Khmer costs up to 1.5 tokens per character in common tokenizers
        (reports/tokenizers.md), well under its 3 bytes."""
        return len(text.encode("utf-8"))

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            input_tokens * self.usd_per_million_input + output_tokens * self.usd_per_million_output
        ) / 1e6

    def generate(self, prompt: str, max_tokens: int) -> Response:
        raise NotImplementedError


class FakeProvider(Provider):
    """Offline provider for tests: `fake:echo` repeats the last line of the prompt,
    `fake:constant:TEXT` always answers TEXT. Priced at $1 / $2 per million tokens so
    budget logic can be tested."""

    usd_per_million_input = 1.0
    usd_per_million_output = 2.0

    def __init__(self, name: str) -> None:
        self.name = name
        _, mode, *rest = name.split(":", 2)
        self.mode, self.constant = mode, rest[0] if rest else ""

    def generate(self, prompt: str, max_tokens: int) -> Response:
        text = prompt.rstrip().splitlines()[-1] if self.mode == "echo" else self.constant
        return Response(text, self.max_tokens_for(prompt), self.max_tokens_for(text))


def get_provider(name: str) -> Provider:
    if name.startswith("fake:"):
        return FakeProvider(name)
    raise SystemExit(f"unknown model {name!r}; only fake:* exists until an API budget is approved")
