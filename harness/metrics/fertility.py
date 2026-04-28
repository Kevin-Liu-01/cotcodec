"""Tokenizer fertility measurement across languages and models.

Fertility = tokens(text_in_language_L) / tokens(text_in_english)

A fertility < 1 means L is more token-efficient than English.
A fertility > 1 means L is less token-efficient.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import tiktoken


@dataclass
class FertilityResult:
    """Fertility measurement for one text sample."""

    text_id: str
    model: str
    language: str
    token_count: int
    english_token_count: int
    fertility: float
    char_count: int
    english_char_count: int

    def to_dict(self) -> dict:
        return {
            "text_id": self.text_id,
            "model": self.model,
            "language": self.language,
            "token_count": self.token_count,
            "english_token_count": self.english_token_count,
            "fertility": round(self.fertility, 4),
            "char_count": self.char_count,
            "english_char_count": self.english_char_count,
        }


class FertilityMeasurer:
    """Measures tokenizer fertility across languages for a given model.

    Currently supports tiktoken-based models (GPT-4, GPT-4o, etc.).
    Anthropic token counting requires the API (added when needed).
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def measure_fertility(
        self,
        text_id: str,
        english_text: str,
        translated_text: str,
        language: str,
    ) -> FertilityResult:
        en_tokens = self.count_tokens(english_text)
        lang_tokens = self.count_tokens(translated_text)

        return FertilityResult(
            text_id=text_id,
            model=self.model,
            language=language,
            token_count=lang_tokens,
            english_token_count=en_tokens,
            fertility=lang_tokens / max(1, en_tokens),
            char_count=len(translated_text),
            english_char_count=len(english_text),
        )

    def measure_batch(
        self,
        samples: list[dict],
        output_path: str | Path | None = None,
    ) -> list[FertilityResult]:
        """Measure fertility for a batch of parallel text samples.

        Each sample dict must have:
        - text_id: str
        - english: str
        - translations: dict[language_code, translated_text]
        """
        results = []
        for sample in samples:
            text_id = sample["text_id"]
            english = sample["english"]
            for lang, translated in sample["translations"].items():
                result = self.measure_fertility(text_id, english, translated, lang)
                results.append(result)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(
                    {"model": self.model, "results": [r.to_dict() for r in results]},
                    f,
                    indent=2,
                )

        return results
