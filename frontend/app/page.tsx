import { Dashboard } from "@/components/Dashboard";
import {
  apiGet,
  DailyBrief,
  DailySentiment,
  NewsRow,
  ReturnRow,
  StockPriceRow,
  Summary
} from "@/lib/api";

const empty = <T,>(fallback: T) => (e: unknown) => { console.error(e); return fallback; };

export default async function Home() {
  const [summary, news, daily, returns, marketPrices, dailyBrief] = await Promise.all([
    apiGet<Summary>("/api/sentiment/summary").catch(empty({ news_count: 0, analyzed_count: 0, failed_count: 0, by_sentiment: [], by_type: [] })),
    apiGet<NewsRow[]>("/api/news?limit=100").catch(empty([] as NewsRow[])),
    apiGet<DailySentiment[]>("/api/sentiment/daily?limit=500").catch(empty([] as DailySentiment[])),
    apiGet<ReturnRow[]>("/api/analysis/returns?limit=2000").catch(empty([] as ReturnRow[])),
    apiGet<StockPriceRow[]>("/api/stocks/0050/prices?limit=30").catch(empty([] as StockPriceRow[])),
    apiGet<DailyBrief>("/api/daily-brief/latest").catch(() => null)
  ]);

  return (
    <Dashboard
      summary={summary}
      news={news}
      daily={daily}
      returns={returns}
      marketPrices={marketPrices}
      dailyBrief={dailyBrief}
    />
  );
}
