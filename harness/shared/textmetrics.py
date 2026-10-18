"""Word and character error counts, the way every transcription study here scores.

Text is compared after Unicode normalisation (NFKC), case folding and turning
punctuation and symbols into spaces; optionally without diacritics, so a model
that writes Romanian without its accents is scored separately.
"""

from __future__ import annotations

import re
import unicodedata


def normalized(text: str, strip_diacritics: bool = False) -> str:
    """The text as compared: normalised, case-folded, punctuation as spaces."""
    text = unicodedata.normalize("NFKC", text or "").casefold()
    if strip_diacritics:
        text = "".join(char for char in unicodedata.normalize("NFD", text)
                       if unicodedata.category(char) != "Mn")
    text = "".join(" " if unicodedata.category(char)[0] in {"P", "S"} else char
                   for char in text)
    return re.sub(r"\s+", " ", text).strip()


def distance(reference: list | str, hypothesis: list | str) -> int:
    """Levenshtein distance between two sequences (words, or characters)."""
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, 1):
        current = [row]
        for column, actual in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[column] + 1,
                               previous[column - 1] + (expected != actual)))
        previous = current
    return previous[-1]


def error_counts(reference: str, hypothesis: str,
                 strip_diacritics: bool = False) -> tuple[int, int, int, int]:
    """(word errors, reference words, character errors, reference characters)."""
    ref = normalized(reference, strip_diacritics)
    hyp = normalized(hypothesis, strip_diacritics)
    ref_words, hyp_words = ref.split(), hyp.split()
    return (distance(ref_words, hyp_words), len(ref_words),
            distance(list(ref), list(hyp)), len(ref))


def rate(errors: int, total: int) -> float | None:
    """errors / total to six places, or None when there was nothing to count."""
    return round(errors / total, 6) if total else None


class ErrorTotals:
    """Error counts summed over a run, with and without diacritics."""

    KEYS = ("word_errors", "words", "char_errors", "chars")

    def __init__(self) -> None:
        self.counts = dict.fromkeys([*self.KEYS, *(f"ascii_{key}" for key in self.KEYS)], 0)

    def add(self, reference: str, hypothesis: str) -> tuple[int, int, int, int]:
        """Count one transcription; returns its plain counts (as `error_counts`)."""
        plain = error_counts(reference, hypothesis)
        stripped = error_counts(reference, hypothesis, True)
        for key, value, ascii_value in zip(self.KEYS, plain, stripped, strict=True):
            self.counts[key] += value
            self.counts[f"ascii_{key}"] += ascii_value
        return plain

    def rates(self) -> dict[str, float | None]:
        """WER and CER, with and without diacritics."""
        counts = self.counts
        return {
            "wer": rate(counts["word_errors"], counts["words"]),
            "cer": rate(counts["char_errors"], counts["chars"]),
            "wer_without_diacritics": rate(counts["ascii_word_errors"], counts["ascii_words"]),
            "cer_without_diacritics": rate(counts["ascii_char_errors"], counts["ascii_chars"]),
        }
