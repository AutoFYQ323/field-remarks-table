# -*- coding: utf-8 -*-
"""Replace placements: standard, around the match, and the whole field."""

import unittest

from fill_replace import MODE_AROUND, MODE_FIELD, MODE_STANDARD, SIDE_BEFORE, apply_replace


class ReplaceTests(unittest.TestCase):
    def test_standard_replaces_every_span_and_keeps_the_rest(self):
        text, hits = apply_replace("abXab", "ab", "Q", MODE_STANDARD)
        self.assertEqual(text, "QXQ")
        self.assertEqual(hits, 2)

    def test_standard_empty_constant_deletes_the_span(self):
        text, hits = apply_replace("a-b-a", "a", "", MODE_STANDARD)
        self.assertEqual(text, "-b-")
        self.assertEqual(hits, 2)

    def test_around_inserts_after_by_default_and_keeps_the_match(self):
        text, hits = apply_replace("abXab", "ab", "1", MODE_AROUND)
        self.assertEqual(text, "ab1Xab1")
        self.assertEqual(hits, 2)

    def test_around_inserts_before(self):
        text, hits = apply_replace("abXab", "ab", "1", MODE_AROUND, SIDE_BEFORE)
        self.assertEqual(text, "1abX1ab")
        self.assertEqual(hits, 2)

    def test_field_replaces_the_whole_cell_once(self):
        text, hits = apply_replace("abXab", "ab", "Z", MODE_FIELD)
        self.assertEqual(text, "Z")
        self.assertEqual(hits, 1)

    def test_exact_requires_the_whole_cell(self):
        text, hits = apply_replace("abX", "ab", "Z", MODE_STANDARD, exact=True)
        self.assertEqual(text, "abX")
        self.assertEqual(hits, 0)
        text, hits = apply_replace("ab", "ab", "Z", MODE_FIELD, exact=True)
        self.assertEqual(text, "Z")
        self.assertEqual(hits, 1)

    def test_case_fold_is_optional(self):
        text, hits = apply_replace("Ab", "ab", "Z", MODE_STANDARD, case_sensitive=False)
        self.assertEqual(text, "Z")
        self.assertEqual(hits, 1)
        text, hits = apply_replace("Ab", "ab", "Z", MODE_STANDARD, case_sensitive=True)
        self.assertEqual(hits, 0)
        self.assertEqual(text, "Ab")

    def test_empty_keyword_matches_nothing(self):
        text, hits = apply_replace("abc", "", "Z", MODE_FIELD)
        self.assertEqual(hits, 0)
        self.assertEqual(text, "abc")

    def test_no_match_leaves_the_cell(self):
        text, hits = apply_replace("abc", "z", "Q", MODE_STANDARD)
        self.assertEqual((text, hits), ("abc", 0))


if __name__ == "__main__":
    unittest.main()
