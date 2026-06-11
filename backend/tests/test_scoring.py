"""Tests for backend/app/analysis/scoring.py.

Covers sentiment_score, normalize_analysis, and augment_with_explicit_targets.
All tests are self-contained and require no network or database access.
"""

import unittest

from app.analysis.scoring import (
    augment_with_explicit_targets,
    normalize_analysis,
    sentiment_score,
)


class SentimentScoreTests(unittest.TestCase):
    """Unit tests for the sentiment_score helper."""

    def test_positive_sentiment_returns_positive_score(self) -> None:
        """sentiment_score('positive', 0.8) should return 0.8."""
        self.assertAlmostEqual(sentiment_score("positive", 0.8), 0.8)

    def test_negative_sentiment_returns_negative_score(self) -> None:
        """sentiment_score('negative', 0.6) should return -0.6."""
        self.assertAlmostEqual(sentiment_score("negative", 0.6), -0.6)

    def test_neutral_sentiment_returns_zero(self) -> None:
        """sentiment_score('neutral', 0.9) should return 0.0 regardless of confidence."""
        self.assertAlmostEqual(sentiment_score("neutral", 0.9), 0.0)

    def test_none_sentiment_returns_zero(self) -> None:
        """sentiment_score(None, 0.5) should default to 0.0."""
        self.assertAlmostEqual(sentiment_score(None, 0.5), 0.0)

    def test_confidence_of_zero_returns_zero(self) -> None:
        """Even positive sentiment with zero confidence yields 0.0."""
        self.assertAlmostEqual(sentiment_score("positive", 0.0), 0.0)


class NormalizeAnalysisTests(unittest.TestCase):
    """Unit tests for normalize_analysis."""

    def test_other_news_type_clears_target_and_forces_neutral(self) -> None:
        """news_type='other' must clear target/target_name and force sentiment to neutral."""
        result = normalize_analysis(
            {
                "news_type": "other",
                "target_type": "stock",
                "target": "2330",
                "target_name": "台積電",
                "sentiment": "negative",
                "confidence": 0.8,
            }
        )
        self.assertEqual(result["news_type"], "other")
        self.assertIsNone(result["target"])
        self.assertEqual(result["target_name"], "")
        self.assertEqual(result["targets"], [])
        self.assertEqual(result["sentiment"], "neutral")
        self.assertAlmostEqual(result["sentiment_score"], 0.0)

    def test_valid_stock_target_returns_correct_news_type_and_sentiment(self) -> None:
        """A well-formed stock analysis record should be normalised cleanly."""
        result = normalize_analysis(
            {
                "news_type": "stock",
                "target_type": "stock",
                "target": "2330",
                "target_name": "台積電",
                "sentiment": "positive",
                "confidence": 0.9,
            }
        )
        self.assertEqual(result["news_type"], "stock")
        self.assertEqual(result["target"], "2330")
        self.assertEqual(result["sentiment"], "positive")
        self.assertAlmostEqual(result["confidence"], 0.9)
        self.assertAlmostEqual(result["sentiment_score"], 0.9)

    def test_confidence_above_one_is_clipped_to_one(self) -> None:
        """Confidence values greater than 1.0 must be clipped to 1.0."""
        result = normalize_analysis(
            {
                "news_type": "stock",
                "target_type": "stock",
                "target": "2330",
                "sentiment": "positive",
                "confidence": 1.5,
            }
        )
        self.assertAlmostEqual(result["confidence"], 1.0)
        self.assertAlmostEqual(result["sentiment_score"], 1.0)

    def test_confidence_below_zero_is_clipped_to_zero(self) -> None:
        """Confidence values less than 0.0 must be clipped to 0.0."""
        result = normalize_analysis(
            {
                "news_type": "stock",
                "target_type": "stock",
                "target": "2330",
                "sentiment": "positive",
                "confidence": -0.3,
            }
        )
        self.assertAlmostEqual(result["confidence"], 0.0)
        self.assertAlmostEqual(result["sentiment_score"], 0.0)

    def test_multi_target_list_is_truncated_to_five_items(self) -> None:
        """The 'targets' list in the result must never exceed 5 entries."""
        raw_targets = [
            {"target_type": "stock", "target": str(2000 + i), "sentiment": "neutral", "confidence": 0.5}
            for i in range(8)
        ]
        result = normalize_analysis(
            {
                "news_type": "industry",
                "target_type": "industry",
                "target": "半導體",
                "sentiment": "neutral",
                "confidence": 0.5,
                "targets": raw_targets,
            }
        )
        self.assertLessEqual(len(result["targets"]), 5)

    def test_unknown_news_type_is_normalised_to_other(self) -> None:
        """An unrecognised news_type value should fall back to 'other'."""
        result = normalize_analysis(
            {
                "news_type": "garbage",
                "target": "2330",
                "sentiment": "positive",
                "confidence": 0.7,
            }
        )
        self.assertEqual(result["news_type"], "other")
        self.assertIsNone(result["target"])
        self.assertEqual(result["sentiment"], "neutral")


class AugmentWithExplicitTargetsTests(unittest.TestCase):
    """Unit tests for augment_with_explicit_targets."""

    def test_two_stock_pattern_augments_targets(self) -> None:
        """「這2檔」 with two named stocks should populate 'targets' with at least two items."""
        base_analysis: dict = {
            "news_type": "stock",
            "target_type": "stock",
            "target": "2303",
            "target_name": "聯電",
            "targets": [],
            "sentiment": "positive",
            "confidence": 0.7,
            "sentiment_score": 0.7,
            "reason": "",
        }
        title = "這2檔半導體股值得關注"
        content = "聯電(2303)與台積電(2330)近期表現亮眼，這2檔均受外資青睞。"
        result = augment_with_explicit_targets(base_analysis, title, content)
        target_ids = [item["target"] for item in result.get("targets", [])]
        self.assertIn("2303", target_ids)
        self.assertIn("2330", target_ids)
        self.assertGreaterEqual(len(result["targets"]), 2)

    def test_no_multi_target_marker_returns_original_analysis(self) -> None:
        """Without a multi-target marker the function should return the analysis unchanged."""
        base_analysis: dict = {
            "news_type": "stock",
            "target_type": "stock",
            "target": "2330",
            "targets": [],
            "sentiment": "positive",
            "confidence": 0.9,
            "sentiment_score": 0.9,
            "reason": "",
        }
        title = "台積電業績亮眼"
        content = "台積電(2330)第一季淨利創歷史新高。"
        result = augment_with_explicit_targets(base_analysis, title, content)
        # Should be unchanged (no multi-target marker found)
        self.assertEqual(result["targets"], [])

    def test_fewer_than_two_explicit_targets_returns_original(self) -> None:
        """If only one stock is found in the explicit pattern the analysis is unchanged."""
        base_analysis: dict = {
            "news_type": "stock",
            "target_type": "stock",
            "target": "2330",
            "targets": [],
            "sentiment": "positive",
            "confidence": 0.9,
            "sentiment_score": 0.9,
            "reason": "",
        }
        title = "這2檔明星股"
        content = "台積電(2330)是市場焦點，這2檔裡的另一檔尚未揭露。"
        result = augment_with_explicit_targets(base_analysis, title, content)
        # Only one stock matched → no augmentation
        self.assertEqual(result["targets"], [])


if __name__ == "__main__":
    unittest.main()
