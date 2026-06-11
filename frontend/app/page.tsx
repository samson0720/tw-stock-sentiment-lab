import { Dashboard } from "@/components/Dashboard";
import {
  apiGet,
  BacktestRow,
  DailyBrief,
  DailySentiment,
  NewsRow,
  ReturnRow,
  StockPriceRow,
  StockRow,
  Summary
} from "@/lib/api";

export default async function Home() {
  const [summary, news, daily, returns, backtests, stocks, marketPrices, dailyBrief] = await Promise.all([
    apiGet<Summary>("/api/sentiment/summary"),
    apiGet<NewsRow[]>("/api/news?limit=100"),
    apiGet<DailySentiment[]>("/api/sentiment/daily?limit=500"),
    apiGet<ReturnRow[]>("/api/analysis/returns?limit=500"),
    apiGet<BacktestRow[]>("/api/backtest/results"),
    apiGet<StockRow[]>("/api/stocks"),
    apiGet<StockPriceRow[]>("/api/stocks/0050/prices?limit=30"),
    apiGet<DailyBrief>("/api/daily-brief/latest").catch(() => null)
  ]);

  return (
    <Dashboard
      summary={summary}
      news={news}
      daily={daily}
      returns={returns}
      backtests={backtests}
      stocks={stocks}
      marketPrices={marketPrices}
      dailyBrief={dailyBrief}
    />
  );
}
