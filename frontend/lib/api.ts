const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type RagCitation = {
  news_id: number;
  title: string;
  published_at: string;
  sentiment: string | null;
  target: string | null;
  score: number;
};

export type RagResult = {
  answer: string;
  citations: RagCitation[];
};

export async function ragQuery(
  q: string,
  stock?: string,
  dateFrom?: string,
  dateTo?: string,
  topK = 5,
): Promise<RagResult> {
  const params = new URLSearchParams({ q, top_k: String(topK) });
  if (stock) params.set("stock", stock);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  return apiGet<RagResult>(`/api/rag/query?${params}`);
}

export async function apiGet<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 50_000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
      next: { revalidate: 120 },
    });
    if (!response.ok) {
      throw new Error(`API ${path} failed: ${response.status}`);
    }
    return response.json();
  } finally {
    clearTimeout(timer);
  }
}

export type Summary = {
  news_count: number;
  analyzed_count: number;
  failed_count: number;
  by_sentiment: { sentiment: string; count: number }[];
  by_type: { news_type: string; count: number }[];
};

export type NewsRow = {
  id: number;
  title: string;
  source: string;
  published_at: string | null;
  news_type: string | null;
  target_type: string | null;
  target: string | null;
  target_name: string | null;
  targets: string | null;
  sentiment: string | null;
  sentiment_score: number | null;
  confidence: number | null;
  reason: string | null;
};

export type DailySentiment = {
  target: string;
  trading_date: string;
  news_count: number;
  sentiment_avg: number;
  positive_ratio: number;
  negative_ratio: number;
  sentiment_ma5: number | null;
};

export type ReturnRow = {
  trading_date: string;
  target: string;
  news_type: string;
  sentiment_score: number;
  future_return_1d: number | null;
  future_return_3d: number | null;
  future_return_5d: number | null;
  sentiment: string;
};

export type BacktestRow = {
  id: number;
  strategy_name: string;
  config: string;
  start_date: string | null;
  end_date: string | null;
  metrics: string;
  created_at: string;
};

export type StockRow = {
  stock_id: string;
  start_date: string | null;
  end_date: string | null;
  rows: number;
};

export type StockPriceRow = {
  stock_id: string;
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
  source: string;
};

export type DailyBriefTarget = {
  target: string;
  sentiment_score: number | null;
  sentiment_ma5: number | null;
  news_count: number;
  positive_ratio?: number | null;
  negative_ratio?: number | null;
};

export type DailyBriefRiskFlag = {
  target: string;
  flag: string;
  reason: string;
  sentiment_score?: number | null;
  negative_ratio?: number | null;
  news_count?: number;
  confidence?: number | null;
  example_title?: string;
};

export type DailyBrief = {
  id: number;
  brief_date: string;
  market_sentiment_score: number | null;
  market_label: string;
  top_positive_targets: DailyBriefTarget[];
  top_negative_targets: DailyBriefTarget[];
  risk_flags: DailyBriefRiskFlag[];
  summary_text: string;
  created_at: string;
  news_count: number;
  analyzed_count: number;
};
