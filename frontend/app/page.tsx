import { Dashboard } from "@/components/Dashboard";
import { apiGet, BacktestRow, DailySentiment, NewsRow, ReturnRow, Summary } from "@/lib/api";

export default async function Home() {
  const [summary, news, daily, returns, backtests] = await Promise.all([
    apiGet<Summary>("/api/sentiment/summary"),
    apiGet<NewsRow[]>("/api/news?limit=100"),
    apiGet<DailySentiment[]>("/api/sentiment/daily?limit=500"),
    apiGet<ReturnRow[]>("/api/analysis/returns?limit=200"),
    apiGet<BacktestRow[]>("/api/backtest/results")
  ]);

  return <Dashboard summary={summary} news={news} daily={daily} returns={returns} backtests={backtests} />;
}
