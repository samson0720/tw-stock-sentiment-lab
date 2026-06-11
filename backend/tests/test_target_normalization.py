import unittest

from app.analysis.scoring import normalize_analysis
from app.analysis.targets import normalize_target, normalize_target_record


class TargetNormalizationTests(unittest.TestCase):
    def test_mismatched_ticker_uses_company_name(self) -> None:
        target_type, target, target_name = normalize_target_record("stock", "2303", "台達電")

        self.assertEqual(target_type, "stock")
        self.assertEqual(target, "2308")
        self.assertEqual(target_name, "台達電")

    def test_foreign_company_is_not_converted_to_tw_ticker(self) -> None:
        target_type, target, target_name = normalize_target_record("stock", "2330", "超微")

        self.assertEqual(target_type, "company_foreign")
        self.assertEqual(target, "AMD")
        self.assertEqual(target_name, "超微")

    def test_special_tw_stock_names_are_preserved(self) -> None:
        self.assertEqual(normalize_target("stock", "KY", "共信-KY"), "6617")
        self.assertEqual(normalize_target("stock", "南俊國際"), "6584")
        self.assertEqual(normalize_target("stock", "1722", "弘塑"), "3131")
        self.assertEqual(
            normalize_analysis(
                {
                    "news_type": "stock",
                    "target_type": "company_foreign",
                    "target": "KY",
                    "target_name": "",
                    "sentiment": "positive",
                    "confidence": 0.8,
                },
                context="共信-KY多引擎助攻，下半年業績拚倍數跳",
            )["target"],
            "6617",
        )

    def test_ai_chip_target_requires_chip_context(self) -> None:
        analysis = normalize_analysis(
            {
                "news_type": "industry",
                "target_type": "industry",
                "target": "AI晶片",
                "sentiment": "neutral",
                "confidence": 0.7,
                "reason": "聚焦AI核心營運與智慧客服",
            },
            context="邁達特聚焦AI核心營運、智慧客服與資安治理",
        )

        self.assertEqual(analysis["target"], "智慧客服")

    def test_other_news_sentiment_is_neutral(self) -> None:
        analysis = normalize_analysis(
            {
                "news_type": "other",
                "target_type": "other",
                "target": "",
                "sentiment": "negative",
                "confidence": 0.8,
            }
        )

        self.assertEqual(analysis["sentiment"], "neutral")
        self.assertEqual(analysis["sentiment_score"], 0.0)

    def test_market_news_maps_to_0050(self) -> None:
        # TAIEX market news should resolve to 0050 as proxy
        from app.analysis.targets import normalize_target
        self.assertEqual(normalize_target("market", None), "0050")
        self.assertEqual(normalize_target("market", "TAIEX"), "0050")
        self.assertEqual(normalize_target("market", "TAIEX/0050"), "0050")


if __name__ == "__main__":
    unittest.main()
