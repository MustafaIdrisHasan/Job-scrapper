"""Tests for NLP tech stack inference."""

from __future__ import annotations

import unittest

from app import nlp_infer
from app.models import InternshipListing


class NLPInferenceTest(unittest.TestCase):
    def test_detects_keywords(self) -> None:
        listing = InternshipListing(
            source="unit",
            company="ExampleCo",
            role_title="Backend Engineering Intern",
            source_url="https://example.com/job/1",
            responsibilities="Work on Python APIs and deploy to AWS using Docker.",
        )

        stack = nlp_infer.infer_for_listing(listing)

        self.assertIn("Python", stack)
        self.assertIn("AWS", stack)


if __name__ == "__main__":
    unittest.main()

