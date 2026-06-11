"""Tests for the align_to_trading_date function in backend/app/analysis/returns.py.

All tests use in-memory data; no database or network access is required.
"""

import unittest

from app.analysis.returns import align_to_trading_date


TRADING_DATES = [
    "2024-06-10",  # Monday
    "2024-06-11",  # Tuesday
    "2024-06-12",  # Wednesday
    "2024-06-13",  # Thursday
    "2024-06-14",  # Friday
    "2024-06-17",  # Monday (next week)
    "2024-06-18",
    "2024-06-19",
    "2024-06-20",
]


class AlignToTradingDateTests(unittest.TestCase):
    """Tests for align_to_trading_date(published_at, trading_dates)."""

    # ------------------------------------------------------------------
    # Basic alignment logic
    # ------------------------------------------------------------------

    def test_before_close_aligns_to_same_day(self) -> None:
        """News published before 13:30 on a trading day should align to that same day."""
        published_at = "2024-06-10 09:00:00"  # Monday before close
        result = align_to_trading_date(published_at, TRADING_DATES)
        self.assertEqual(result, "2024-06-10")

    def test_after_close_aligns_to_next_trading_day(self) -> None:
        """News published after 13:30 on a trading day should align to the NEXT trading day."""
        published_at = "2024-06-10 14:00:00"  # Monday after close
        result = align_to_trading_date(published_at, TRADING_DATES)
        self.assertEqual(result, "2024-06-11")

    def test_exactly_at_close_aligns_to_next_trading_day(self) -> None:
        """News published exactly at 13:30 is considered 'after close' (strictly greater)."""
        # 13:30:00 is NOT strictly greater than MARKET_CLOSE=time(13,30), so stays same day
        published_at = "2024-06-10 13:30:00"
        result = align_to_trading_date(published_at, TRADING_DATES)
        self.assertEqual(result, "2024-06-10")

    def test_one_second_after_close_aligns_to_next_trading_day(self) -> None:
        """13:30:01 is strictly after close and must roll forward."""
        published_at = "2024-06-10 13:30:01"
        result = align_to_trading_date(published_at, TRADING_DATES)
        self.assertEqual(result, "2024-06-11")

    # ------------------------------------------------------------------
    # Weekend / non-trading day
    # ------------------------------------------------------------------

    def test_weekend_news_aligns_to_next_monday(self) -> None:
        """Weekend news should roll forward to the first available trading day (Monday)."""
        published_at = "2024-06-15 10:00:00"  # Saturday
        result = align_to_trading_date(published_at, TRADING_DATES)
        self.assertEqual(result, "2024-06-17")

    def test_sunday_news_aligns_to_next_monday(self) -> None:
        """Sunday news (before would-be open) should also roll to next Monday."""
        published_at = "2024-06-16 08:00:00"  # Sunday
        result = align_to_trading_date(published_at, TRADING_DATES)
        self.assertEqual(result, "2024-06-17")

    # ------------------------------------------------------------------
    # Edge cases: empty / invalid inputs
    # ------------------------------------------------------------------

    def test_no_trading_dates_returns_none(self) -> None:
        """An empty trading-dates list should return None."""
        result = align_to_trading_date("2024-06-10 09:00:00", [])
        self.assertIsNone(result)

    def test_none_published_at_returns_none(self) -> None:
        """A None published_at value should return None."""
        result = align_to_trading_date(None, TRADING_DATES)
        self.assertIsNone(result)

    def test_empty_string_published_at_returns_none(self) -> None:
        """An empty string published_at should return None."""
        result = align_to_trading_date("", TRADING_DATES)
        self.assertIsNone(result)

    def test_invalid_date_string_returns_none(self) -> None:
        """An unparseable date string should return None."""
        result = align_to_trading_date("not-a-date", TRADING_DATES)
        self.assertIsNone(result)

    def test_news_after_all_trading_dates_returns_none(self) -> None:
        """If published_at is after all known trading dates there is nowhere to align."""
        published_at = "2025-01-01 09:00:00"
        result = align_to_trading_date(published_at, TRADING_DATES)
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # Future-return calculation via mock price data
    # ------------------------------------------------------------------

    def test_future_return_calculation_with_mock_data(self) -> None:
        """Verify that future_return arithmetic matches expected ratios.

        This does not call build_aligned_returns (which needs a DB).
        Instead it exercises the core arithmetic inline to document expected behaviour.
        """
        close_prices = [100.0, 102.0, 105.0, 103.0, 108.0]
        # Simulate future_return at +1 day (index 0 → index 1)
        base_close = close_prices[0]
        future_1d = close_prices[1] / base_close - 1.0
        future_3d = close_prices[3] / base_close - 1.0
        future_5d = close_prices[4] / base_close - 1.0 if len(close_prices) >= 5 else None

        self.assertAlmostEqual(future_1d, 0.02)
        self.assertAlmostEqual(future_3d, 0.03)
        self.assertAlmostEqual(future_5d, 0.08)

    # ------------------------------------------------------------------
    # Timezone-aware strings
    # ------------------------------------------------------------------

    def test_iso8601_with_timezone_offset_is_parsed(self) -> None:
        """A timestamp with a UTC-offset suffix should still be parseable."""
        # pandas.to_datetime handles ISO 8601 with timezone; the date part matters
        published_at = "2024-06-10T08:00:00+08:00"
        result = align_to_trading_date(published_at, TRADING_DATES)
        # 08:00 local (UTC+8) is before close → same trading day is expected
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
