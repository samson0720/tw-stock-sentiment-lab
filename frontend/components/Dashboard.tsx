"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, FileText, Newspaper, RefreshCw, Search, Sparkles } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { BacktestRow, DailyBrief, DailySentiment, NewsRow, RagCitation, RagResult, ReturnRow, StockPriceRow, StockRow, Summary } from "@/lib/api";
import { ragQuery } from "@/lib/api";

type Props = {
  summary: Summary;
  news: NewsRow[];
  daily: DailySentiment[];
  returns: ReturnRow[];
  backtests: BacktestRow[];
  stocks: StockRow[];
  marketPrices: StockPriceRow[];
  dailyBrief: DailyBrief | null;
};

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "#4a7c59",
  neutral: "#708090",
  negative: "#b7472a"
};

const SENTIMENT_KEYS = ["positive", "neutral", "negative"] as const;
type SentimentKey = (typeof SENTIMENT_KEYS)[number];

const TARGET_NAME_MAP: Record<string, string> = {
  "0050": "元大台灣50",
  "1234": "王品",
  "1303": "南亞",
  "1722": "台肥",
  "1802": "台玻",
  "2002": "中鋼",
  "2303": "聯電",
  "2308": "台達電",
  "2312": "金寶",
  "2313": "華通",
  "2317": "鴻海",
  "2327": "國巨",
  "2330": "台積電",
  "2337": "旺宏",
  "2344": "華邦電",
  "2354": "鴻勁",
  "2382": "廣達",
  "2408": "南亞科",
  "2454": "聯發科",
  "2504": "國產",
  "2609": "陽明",
  "2610": "華航",
  "2731": "雄獅",
  "3017": "奇鋐",
  "3037": "欣興",
  "3231": "緯創",
  "3416": "融程電",
  "3481": "群創",
  "3711": "日月光投控",
  "4919": "新唐",
  "4958": "臻鼎-KY",
  "5269": "祥碩",
  "6116": "嘉晶",
  "6139": "亞翔",
  "6584": "南俊國際",
  "6617": "共信-KY",
  "6669": "緯穎",
  "9914": "築間"
};

function fmtDecimal(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function fmtPercent(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `${value.toFixed(digits)}%`;
}

function proxySentimentFromReturn(returnPct: number) {
  return Number(Math.max(-1, Math.min(1, returnPct / 2)).toFixed(2));
}

function fmtProxySentiment(value: number) {
  if (value > 0.15) return `偏多 ${value.toFixed(2)}`;
  if (value < -0.15) return `偏空 ${value.toFixed(2)}`;
  return `中性 ${value.toFixed(2)}`;
}

function labelSentiment(value: string | null | undefined) {
  if (value === "positive") return "正向";
  if (value === "negative") return "負向";
  if (value === "neutral") return "中立";
  return "待分析";
}

function isSentimentKey(value: string | null | undefined): value is SentimentKey {
  return SENTIMENT_KEYS.includes(value as SentimentKey);
}

function labelType(value: string | null | undefined) {
  if (value === "market") return "市場";
  if (value === "stock") return "個股";
  if (value === "etf") return "ETF";
  if (value === "industry") return "產業";
  if (value === "macro") return "總經";
  if (value === "other" || value === "ignore") return "其他";
  return "待分類";
}

function shortDate(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "-";
}

function minuteDateTime(value: string | null | undefined) {
  return value ? value.replace("T", " ").slice(0, 16) : "-";
}

function average(values: number[]) {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function targetLabel(target: string) {
  const name = TARGET_NAME_MAP[target];
  return name ? `${target} ${name}` : target;
}

function marketToneText(label: string | null | undefined) {
  if (label === "情緒偏多") return "偏多";
  if (label === "情緒偏空") return "偏空";
  if (label?.includes("中性")) return "偏中性";
  return "資料不足";
}

function joinTargets(targets: string[]) {
  if (targets.length === 0) return "暫無明顯集中標的";
  return targets.map(targetLabel).join("、");
}

function buildBriefText(dailyBrief: DailyBrief | null, observedTargetCount: number) {
  if (!dailyBrief) return "目前尚未產生 daily_brief。執行 daily update 後，這裡會顯示最新摘要。";

  const tone = marketToneText(dailyBrief.market_label);
  const score = fmtDecimal(dailyBrief.market_sentiment_score, 2);
  const positiveTargets = dailyBrief.top_positive_targets.slice(0, 3).map((row) => row.target);
  const riskTargets = [
    ...dailyBrief.top_negative_targets.map((row) => row.target),
    ...dailyBrief.risk_flags.map((row) => row.target)
  ].filter((target, index, values) => values.indexOf(target) === index);

  return `${dailyBrief.brief_date} 整體市場情緒${tone}，情緒分數為 ${score}。當日完成 ${dailyBrief.analyzed_count} 則新聞的 LLM 分析，其中 ${observedTargetCount} 個標的形成每日觀察訊號。偏多標的包含 ${joinTargets(
    positiveTargets
  )}；偏空與風險提醒標的則集中在 ${joinTargets(
    riskTargets.slice(0, 3)
  )}。由於本摘要根據已處理新聞與情緒模型產生，因此僅作為市場觀察參考，不作為投資建議。`;
}

const BACKTEST_SHORT_DAYS = 30;

function parseMetrics(raw: string): Record<string, number | string> {
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function tradingDaysBetween(start: string | null, end: string | null): number | null {
  if (!start || !end) return null;
  const msPerDay = 86400000;
  const from = new Date(start).getTime();
  const to = new Date(end).getTime();
  if (Number.isNaN(from) || Number.isNaN(to)) return null;
  const calendarDays = Math.round((to - from) / msPerDay) + 1;
  // rough weekday count (no holiday calendar)
  return Math.round(calendarDays * 5 / 7);
}

function sentimentLabel(s: string | null) {
  if (s === "positive") return "正向";
  if (s === "negative") return "負向";
  if (s === "neutral") return "中立";
  return "—";
}

function sentimentClass(s: string | null) {
  if (s === "positive") return "positive";
  if (s === "negative") return "negative";
  return "";
}

export function Dashboard({ summary, news, daily, returns, backtests, marketPrices, dailyBrief }: Props) {
  type ChatEntry = { question: string; result: RagResult | null; error: string | null };

  const [ragQ, setRagQ] = useState("");
  const [ragStock, setRagStock] = useState("");
  const [ragDateFrom, setRagDateFrom] = useState("");
  const [ragDateTo, setRagDateTo] = useState("");
  const [ragLoading, setRagLoading] = useState(false);
  const [ragHistory, setRagHistory] = useState<ChatEntry[]>([]);
  const [ragShowFilters, setRagShowFilters] = useState(false);

  async function handleRagSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = ragQ.trim();
    if (!q) return;
    setRagQ("");
    setRagLoading(true);
    setRagHistory((h) => [...h, { question: q, result: null, error: null }]);
    try {
      const result = await ragQuery(q, ragStock || undefined, ragDateFrom || undefined, ragDateTo || undefined);
      setRagHistory((h) => h.map((e, i) => i === h.length - 1 ? { ...e, result } : e));
    } catch {
      setRagHistory((h) => h.map((e, i) => i === h.length - 1 ? { ...e, error: "查詢失敗，請確認後端服務正在執行。" } : e));
    } finally {
      setRagLoading(false);
    }
  }
  const marketPriceTrend = useMemo(() => {
    const sortedPrices = [...marketPrices].sort((a, b) => a.date.localeCompare(b.date));

    const points = sortedPrices.reduce<{ date: string; marketReturnPct: number }[]>((items, row, index) => {
      const previous = sortedPrices[index - 1];
      if (!previous || previous.close === 0) return items;
      items.push({
        date: row.date,
        marketReturnPct: Number(((row.close / previous.close - 1) * 100).toFixed(2))
      });
      return items;
    }, []);

    const sortedPoints = points.sort((a, b) => a.date.localeCompare(b.date));
    const proxyByNewsDate = new Map<string, number>();
    sortedPoints.forEach((point, index) => {
      const previousDate = sortedPoints[index - 1]?.date;
      if (previousDate) {
        proxyByNewsDate.set(previousDate, proxySentimentFromReturn(point.marketReturnPct));
      }
    });
    const latestPoint = sortedPoints.at(-1);
    if (latestPoint && !proxyByNewsDate.has(latestPoint.date)) {
      proxyByNewsDate.set(latestPoint.date, proxySentimentFromReturn(latestPoint.marketReturnPct));
    }

    return sortedPoints
      .slice(-18)
      .map((point) => ({
        date: point.date.slice(5),
        marketReturnPct: point.marketReturnPct,
        proxyNewsSentiment: proxyByNewsDate.get(point.date)
      }));
  }, [marketPrices]);

  const sentimentTrendFallback = useMemo(() => {
    const byDate = new Map<string, { scores: number[]; newsCount: number }>();
    daily.forEach((row) => {
      const current = byDate.get(row.trading_date) ?? { scores: [], newsCount: 0 };
      current.scores.push(row.sentiment_avg);
      current.newsCount += row.news_count;
      byDate.set(row.trading_date, current);
    });

    return [...byDate.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-18)
      .map(([date, row]) => ({
        date: date.slice(5),
        marketReturnPct: Number(((average(row.scores) ?? 0) * 100).toFixed(2))
      }));
  }, [daily]);

  const marketTrend = useMemo(() => {
    const byDate = new Map<string, { returns: number[]; newsCount: number }>();
    returns.forEach((row) => {
      if (row.future_return_1d === null || row.future_return_1d === undefined) return;
      const current = byDate.get(row.trading_date) ?? { returns: [], newsCount: 0 };
      current.returns.push(row.future_return_1d);
      current.newsCount += 1;
      byDate.set(row.trading_date, current);
    });

    return [...byDate.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-18)
      .map(([date, row]) => ({
        date: date.slice(5),
        marketReturnPct: Number(((average(row.returns) ?? 0) * 100).toFixed(2))
      }));
  }, [returns]);

  const dailyTrend = marketPriceTrend.length ? marketPriceTrend : marketTrend.length ? marketTrend : sentimentTrendFallback;

  const latestAnalyzedNews = useMemo(
    () => news.filter((row) => row.sentiment || row.news_type).slice(0, 10),
    [news]
  );

  const observedTargetCount = useMemo(() => {
    if (!dailyBrief?.brief_date) return 0;
    const targets = new Set(daily.filter((row) => row.trading_date === dailyBrief.brief_date).map((row) => row.target));
    if (targets.size > 0) return targets.size;

    return new Set([
      ...dailyBrief.top_positive_targets.map((row) => row.target),
      ...dailyBrief.top_negative_targets.map((row) => row.target),
      ...dailyBrief.risk_flags.map((row) => row.target)
    ]).size;
  }, [daily, dailyBrief]);

  const marketToneClass =
    dailyBrief?.market_label === "情緒偏多" ? "positive" : dailyBrief?.market_label === "情緒偏空" ? "negative" : "";

  const updatedAt = minuteDateTime(dailyBrief?.created_at);
  const observationDate = dailyBrief?.brief_date ?? "-";
  const briefText = buildBriefText(dailyBrief, observedTargetCount);
  const sentimentBars = useMemo(() => {
    const counts = new Map<string, number>();
    const todaysNews = dailyBrief?.brief_date
      ? news.filter((row) => shortDate(row.published_at) === dailyBrief.brief_date)
      : news;

    todaysNews.forEach((row) => {
      if (isSentimentKey(row.sentiment)) {
        counts.set(row.sentiment, (counts.get(row.sentiment) ?? 0) + 1);
      }
    });

    return SENTIMENT_KEYS.map((sentiment) => ({
      name: labelSentiment(sentiment),
      key: sentiment,
      count: counts.get(sentiment) ?? 0
    }));
  }, [dailyBrief?.brief_date, news]);

  return (
    <main className="dashboard-shell">
      <section className="hero-panel" aria-label="daily news analysis">
        <div className="hero-copy">
          <div className="eyebrow">
            <Newspaper size={16} />
            Daily news automation
          </div>
          <h1>每日新聞自動分析</h1>
          <p className="lead">集中查看新聞爬蟲、LLM 分析與每日摘要產出狀態。</p>
          <div className="daily-flow" aria-label="automation flow">
            <span>
              <Newspaper size={15} />
              新聞
            </span>
            <i />
            <span>
              <Sparkles size={15} />
              分析
            </span>
            <i />
            <span>
              <FileText size={15} />
              摘要
            </span>
          </div>
        </div>

        <div className="hero-status" aria-label="latest daily brief status">
          <span className={`brief-label ${marketToneClass}`}>{dailyBrief?.market_label ?? "資料不足"}</span>
          <dl>
            <div>
              <dt>資料日期</dt>
              <dd>{observationDate}</dd>
            </div>
            <div>
              <dt>更新時間</dt>
              <dd>{updatedAt}</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="kpi-grid" aria-label="daily update metrics">
        <article>
          <span>今日新聞數</span>
          <strong>{dailyBrief?.news_count ?? summary.news_count}</strong>
        </article>
        <article>
          <span>完成分析</span>
          <strong>{dailyBrief?.analyzed_count ?? summary.analyzed_count}</strong>
        </article>
        <article>
          <span>觀察標的</span>
          <strong>{observedTargetCount || "-"}</strong>
        </article>
        <article>
          <span>市場情緒</span>
          <strong>{fmtDecimal(dailyBrief?.market_sentiment_score, 2)}</strong>
        </article>
      </section>

      <section className="brief-layout">
        <article className="brief-card">
          <div className="section-heading">
            <div>
              <span>Daily brief</span>
              <h2>今日摘要</h2>
            </div>
            <button className="refresh-button" type="button" onClick={() => window.location.reload()}>
              <RefreshCw size={15} />
              重新整理
            </button>
          </div>
          <p className="brief-summary">{briefText}</p>
        </article>

        <aside className="focus-card" aria-label="focus targets">
          <div className="section-heading compact">
            <div>
              <span>Focus</span>
              <h2>重點觀察</h2>
            </div>
          </div>

          <div className="focus-group">
            <span>偏多</span>
            <div>
              {(dailyBrief?.top_positive_targets.length ? dailyBrief.top_positive_targets : []).slice(0, 4).map((row) => (
                <strong key={row.target}>{targetLabel(row.target)}</strong>
              ))}
              {!dailyBrief?.top_positive_targets.length && <em>資料不足</em>}
            </div>
          </div>

          <div className="focus-group">
            <span>偏空</span>
            <div>
              {(dailyBrief?.top_negative_targets.length ? dailyBrief.top_negative_targets : []).slice(0, 4).map((row) => (
                <strong key={row.target}>{targetLabel(row.target)}</strong>
              ))}
              {!dailyBrief?.top_negative_targets.length && <em>資料不足</em>}
            </div>
          </div>

          <div className="focus-group risk">
            <span>風險提醒</span>
            <div>
              {(dailyBrief?.risk_flags.length ? dailyBrief.risk_flags : []).slice(0, 4).map((row) => (
                <strong key={`${row.target}-${row.reason}`}>{targetLabel(row.target)}</strong>
              ))}
              {!dailyBrief?.risk_flags.length && <em>暫無明顯集中風險</em>}
            </div>
          </div>
        </aside>
      </section>

      <section className="insight-grid">
        <article className="panel">
          <div className="section-heading">
            <div>
              <span>Sentiment mix</span>
              <h2>今日新聞情緒分布</h2>
              <p className="panel-note">依今日已完成 LLM 判斷結果統計新聞情緒分類</p>
            </div>
          </div>
          <div className="chart chart-short">
            <ResponsiveContainer>
              <BarChart data={sentimentBars}>
                <CartesianGrid vertical={false} stroke="#d9dedb" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip formatter={(value) => [value, "筆數"]} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  <LabelList dataKey="count" position="top" className="bar-label" />
                  {sentimentBars.map((entry) => (
                    <Cell key={entry.key} fill={SENTIMENT_COLORS[entry.key] ?? "#708090"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel">
          <div className="section-heading">
            <div>
              <span>Daily signal</span>
              <h2>近期股市趨勢</h2>
              <p className="panel-note">橘柱為股價回推新聞情緒：以前一天新聞對照隔天台股漲跌暫估。</p>
            </div>
          </div>
          <div className="chart-legend" aria-label="chart legend">
            <span>
              <i className="legend-line" />
              綠線：台股漲跌幅
            </span>
            <span>
              <i className="legend-bar" />
              橘柱：回推新聞情緒
            </span>
          </div>
          <div className="chart chart-short">
            <ResponsiveContainer>
              <ComposedChart data={dailyTrend}>
                <CartesianGrid vertical={false} stroke="#d9dedb" />
                <XAxis dataKey="date" tickLine={false} axisLine={false} />
                <YAxis yAxisId="left" domain={[-8, 8]} tickFormatter={(value) => `${value}%`} tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" domain={[-1, 1]} orientation="right" hide />
                <Tooltip
                  formatter={(value, name) => {
                    if (name === "台股漲跌幅") return [fmtPercent(Number(value)), name];
                    if (name === "回推新聞情緒") return [fmtProxySentiment(Number(value)), name];
                    return [value, name];
                  }}
                />
                <Bar yAxisId="right" dataKey="proxyNewsSentiment" name="回推新聞情緒" fill="#f9a620" radius={[4, 4, 0, 0]} />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="marketReturnPct"
                  name="台股漲跌幅"
                  stroke="#4a7c59"
                  strokeWidth={3}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <section className="news-panel">
        <div className="section-heading">
          <div>
            <span>Latest analysis</span>
            <h2>最新新聞分析</h2>
            <p className="panel-note">資料來源：Yahoo 股市新聞</p>
          </div>
          <AlertTriangle size={18} />
        </div>
        <div className="news-list">
          {latestAnalyzedNews.map((row) => (
            <article className="news-item" key={row.id}>
              <div>
                <time>{shortDate(row.published_at)}</time>
                <h3>{row.title}</h3>
                <p className="news-reason">
                  <span>判斷理由</span>
                  {row.reason || "尚無分析理由"}
                </p>
              </div>
              <aside>
                <span className="tag">{labelType(row.news_type)}</span>
                <span className={`sentiment ${row.sentiment ?? "unknown"}`}>{labelSentiment(row.sentiment)}</span>
                <strong>{fmtDecimal(row.sentiment_score, 2)}</strong>
              </aside>
            </article>
          ))}
        </div>
      </section>

      {backtests.length > 0 && (
        <section className="backtest-panel" aria-label="backtest results">
          <div className="section-heading">
            <div>
              <span>Backtest</span>
              <h2>回測績效</h2>
              <p className="panel-note">基於歷史新聞情緒訊號的策略模擬結果</p>
            </div>
          </div>

          <div className="backtest-warning" role="alert">
            <AlertTriangle size={16} />
            <p>
              <strong>統計警示：</strong>回測期間僅 17 個交易日（2026-04-29 ~ 2026-05-22），樣本過短，Sharpe Ratio 與年化報酬等指標統計上不具參考意義。至少需累積 252 個交易日（一年）以上的資料，方可作為策略評估依據。
            </p>
          </div>

          <div className="backtest-table-wrap">
            <table className="backtest-table">
              <thead>
                <tr>
                  <th>策略名稱</th>
                  <th>回測期間</th>
                  <th>交易日數</th>
                  <th>Sharpe Ratio</th>
                  <th>年化報酬</th>
                  <th>最大回撤</th>
                  <th>勝率</th>
                </tr>
              </thead>
              <tbody>
                {backtests.map((row) => {
                  const m = parseMetrics(row.metrics);
                  const days = tradingDaysBetween(row.start_date, row.end_date);
                  const isShort = days !== null && days < BACKTEST_SHORT_DAYS;
                  const sharpe = typeof m.sharpe_ratio === "number" ? m.sharpe_ratio : null;
                  const isSuspiciousSharpe = sharpe !== null && sharpe > 5;
                  const showSampleWarning = isShort || isSuspiciousSharpe;
                  return (
                    <tr key={row.id} className={showSampleWarning ? "row-warn" : ""}>
                      <td>{row.strategy_name}</td>
                      <td className="date-range">
                        {shortDate(row.start_date)} ~ {shortDate(row.end_date)}
                      </td>
                      <td>
                        {days !== null ? (
                          <span className={isShort ? "days-warn" : ""}>{days} 日{isShort ? " ⚠" : ""}</span>
                        ) : "-"}
                      </td>
                      <td>
                        {sharpe !== null ? (
                          <span className={isSuspiciousSharpe ? "value-warn" : ""}>
                            {fmtDecimal(sharpe)}{isSuspiciousSharpe ? " *" : ""}
                          </span>
                        ) : "-"}
                      </td>
                      <td>{typeof m.annualized_return === "number" ? fmtPercent(m.annualized_return) : "-"}</td>
                      <td>{typeof m.max_drawdown === "number" ? fmtPercent(m.max_drawdown) : "-"}</td>
                      <td>{typeof m.win_rate === "number" ? fmtPercent(m.win_rate) : "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="panel-note" style={{ marginTop: "10px" }}>* 樣本不足：交易日數 &lt; 30 日或 Sharpe Ratio &gt; 5，年化指標為短期外推，不具統計意義。</p>
        </section>
      )}
      <section className="rag-panel">
        <div className="rag-header">
          <div className="rag-header-left">
            <Sparkles size={17} className="rag-sparkle" />
            <div>
              <span className="rag-eyebrow">News Q&amp;A</span>
              <h2>新聞問答</h2>
            </div>
          </div>
          <button
            className={`rag-filter-toggle ${ragShowFilters ? "active" : ""}`}
            type="button"
            onClick={() => setRagShowFilters((v) => !v)}
          >
            <Search size={13} />
            篩選條件
          </button>
        </div>

        {ragShowFilters && (
          <div className="rag-filter-bar">
            <label>
              <span>股票代號</span>
              <input type="text" placeholder="2330" value={ragStock} onChange={(e) => setRagStock(e.target.value)} maxLength={6} />
            </label>
            <label>
              <span>起始日期</span>
              <input type="date" value={ragDateFrom} onChange={(e) => setRagDateFrom(e.target.value)} />
            </label>
            <label>
              <span>結束日期</span>
              <input type="date" value={ragDateTo} onChange={(e) => setRagDateTo(e.target.value)} />
            </label>
          </div>
        )}

        <div className="rag-messages">
          {ragHistory.length === 0 && (
            <div className="rag-empty">
              <Sparkles size={28} />
              <p>試著問：台積電最近有什麼重要消息？</p>
            </div>
          )}

          {ragHistory.map((entry, i) => (
            <div key={i} className="rag-exchange">
              <div className="rag-bubble user">
                <p>{entry.question}</p>
              </div>

              {entry.result === null && entry.error === null && (
                <div className="rag-bubble ai loading">
                  <Sparkles size={14} className="rag-ai-icon" />
                  <span className="rag-dots"><i /><i /><i /></span>
                </div>
              )}

              {entry.error && (
                <div className="rag-bubble ai error">
                  <Sparkles size={14} className="rag-ai-icon" />
                  <p>{entry.error}</p>
                </div>
              )}

              {entry.result && (
                <div className="rag-bubble ai">
                  <Sparkles size={14} className="rag-ai-icon" />
                  <div className="rag-ai-body">
                    <p className="rag-answer">{entry.result.answer}</p>
                    {entry.result.citations.length > 0 && (
                      <div className="rag-citations">
                        <span className="rag-citations-label">引用來源</span>
                        {entry.result.citations.map((c: RagCitation) => (
                          <article key={c.news_id} className="rag-citation-item">
                            <div className="rag-citation-meta">
                              <time>{c.published_at}</time>
                              {c.target && <strong>{targetLabel(c.target)}</strong>}
                              <span className={`sentiment ${sentimentClass(c.sentiment)}`}>{sentimentLabel(c.sentiment)}</span>
                              <span className="rag-score">{(c.score * 100).toFixed(1)}%</span>
                            </div>
                            <p>{c.title}</p>
                          </article>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <form className="rag-input-bar" onSubmit={handleRagSubmit}>
          <input
            type="text"
            className="rag-question"
            placeholder="輸入問題…"
            value={ragQ}
            onChange={(e) => setRagQ(e.target.value)}
            disabled={ragLoading}
          />
          <button className="rag-submit" type="submit" disabled={ragLoading || !ragQ.trim()}>
            <Search size={15} />
          </button>
        </form>
      </section>
    </main>
  );
}
