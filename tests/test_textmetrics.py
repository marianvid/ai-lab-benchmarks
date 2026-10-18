"""Word and character error counts, as every transcription study scores them."""

import unittest

from harness.shared.textmetrics import ErrorTotals, distance, error_counts, normalized, rate


class TextMetricsTests(unittest.TestCase):
    def test_text_is_normalised_before_comparing(self):
        self.assertEqual(normalized("  Bună, ZIUA!  "), "bună ziua")
        self.assertEqual(normalized("Bună, ziua!", strip_diacritics=True), "buna ziua")

    def test_distance_counts_edits(self):
        self.assertEqual(distance(list("kitten"), list("sitting")), 3)
        self.assertEqual(distance(["a", "b"], ["a", "b"]), 0)

    def test_error_counts(self):
        self.assertEqual(error_counts("unu doi trei", "unu trei"), (1, 3, 4, 12))

    def test_totals_add_up_with_and_without_diacritics(self):
        totals = ErrorTotals()
        self.assertEqual(totals.add("ziua bună", "ziua buna"), (1, 2, 1, 9))
        rates = totals.rates()
        self.assertEqual(rates["wer"], 0.5)
        self.assertEqual(rates["wer_without_diacritics"], 0.0)
        self.assertEqual(rate(0, 0), None)
