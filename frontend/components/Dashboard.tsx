"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Database,
  LineChart as LineChartIcon,
  Newspaper,
  PieChart,
  ShieldCheck,
  Table2,
  TrendingUp
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { BacktestRow, DailyBrief, DailySentiment, NewsRow, ReturnRow, StockRow, Summary } from "@/lib/api";

type Props = {
  summary: Summary;
  news: NewsRow[];
  daily: DailySentiment[];
  returns: ReturnRow[];
  backtests: BacktestRow[];
  stocks: StockRow[];
  dailyBrief: DailyBrief | null;
};

type ParsedBacktest = {
  strategy?: MetricBlock;
  benchmark?: MetricBlock;
};

type MetricBlock = {
  total_return?: number;
  annualized_return?: number;
  annualized_volatility?: number;
  sharpe_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
  number_of_rebalances?: number;
};

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "#12845c",
  neutral: "#7b8494",
  negative: "#c74737"
};

const TYPE_COLORS: Record<string, string> = {
  market: "#2f6f9f",
  stock: "#8665d8",
  industry: "#c98a22",
  ignore: "#9aa2af"
};

function fmtNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return value.toLocaleString("zh-TW");
}

function fmtPct(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `${(value * 100).toFixed(digits)}%`;
}

function fmtDecimal(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function parseJson<T>(value: string | null | undefined): T | null {
  if (!value) return null;
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

function labelSentiment(value: string | null | undefined) {
  if (value === "positive") return "正向";
  if (value === "negative") return "負向";
  if (value === "neutral") return "中立";
  return value ?? "-";
}

function labelType(value: string | null | undefined) {
  if (value === "market") return "市場";
  if (value === "stock") return "個股";
  if (value === "industry") return "產業";
  if (value === "ignore") return "忽略";
  return value ?? "-";
}

function shortDate(value: string | null | undefined) {
  return value ? value.slice(0, 10) : "-";
}

function average(values: number[]) {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function nonNullRatio(rows: ReturnRow[], key: "future_return_1d" | "future_return_3d" | "future_return_5d") {
  if (rows.length === 0) return 0;
  return rows.filter((row) => row[key] !== null && row[key] !== undefined).length / rows.length;
}

export function Dashboard({ summary, news, daily, returns, backtests, stocks, dailyBrief }: Props) {
  const [activeTarget, setActiveTarget] = useState("ALL");
  const latestBacktest = backtests[0];
  const latestMetrics = parseJson<ParsedBacktest>(latestBacktest?.metrics);
  const latestConfig = parseJson<Record<string, string | number>>(latestBacktest?.config);

  const sentimentBars = useMemo(
    () =>
      summary.by_sentiment.map((row) => ({
        name: labelSentiment(row.sentiment),
        key: row.sentiment,
        count: row.count,
        ratio: summary.analyzed_count ? row.count / summary.analyzed_count : 0
      })),
    [summary.analyzed_count, summary.by_sentiment]
  );

  const typeBars = useMemo(
    () =>
      summary.by_type.map((row) => ({
        name: labelType(row.news_type),
        key: row.news_type,
        count: row.count,
        ratio: summary.analyzed_count ? row.count / summary.analyzed_count : 0
      })),
    [summary.analyzed_count, summary.by_type]
  );

  const topTargets = useMemo(() => {
    const counts = new Map<string, number>();
    daily.forEach((row) => counts.set(row.target, (counts.get(row.target) ?? 0) + row.news_count));
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([target, count]) => ({ target, count }));
  }, [daily]);

  const filteredDaily = activeTarget === "ALL" ? daily : daily.filter((row) => row.target === activeTarget);

  const dailyTrend = useMemo(() => {
    const byDate = new Map<string, { scores: number[]; ma5: number[]; newsCount: number }>();
    filteredDaily.forEach((row) => {
      const current = byDate.get(row.trading_date) ?? { scores: [], ma5: [], newsCount: 0 };
      current.scores.push(row.sentiment_avg);
      if (row.sentiment_ma5 !== null && row.sentiment_ma5 !== undefined) current.ma5.push(row.sentiment_ma5);
      current.newsCount += row.news_count;
      byDate.set(row.trading_date, current);
    });
    return [...byDate.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, row]) => ({
        date,
        sentiment: Number((average(row.scores) ?? 0).toFixed(3)),
        ma5: Number((average(row.ma5) ?? average(row.scores) ?? 0).toFixed(3)),
        newsCount: row.newsCount
      }));
  }, [filteredDaily]);

  const returnBySentiment = useMemo(() => {
    const groups = new Map<string, ReturnRow[]>();
    returns.forEach((row) => {
      const key = row.sentiment ?? "unknown";
      groups.set(key, [...(groups.get(key) ?? []), row]);
    });
    return ["positive", "neutral", "negative"].map((sentiment) => {
      const rows = groups.get(sentiment) ?? [];
      return {
        name: labelSentiment(sentiment),
        key: sentiment,
        count: rows.length,
        r1d: average(rows.map((row) => row.future_return_1d).filter((value): value is number => value !== null)),
        r3d: average(rows.map((row) => row.future_return_3d).filter((value): value is number => value !== null)),
        r5d: average(rows.map((row) => row.future_return_5d).filter((value): value is number => value !== null))
      };
    });
  }, [returns]);

  const returnByType = useMemo(() => {
    const groups = new Map<string, ReturnRow[]>();
    returns.forEach((row) => {
      groups.set(row.news_type, [...(groups.get(row.news_type) ?? []), row]);
    });
    return [...groups.entries()]
      .map(([type, rows]) => ({
        type,
        name: labelType(type),
        count: rows.length,
        r1d: average(rows.map((row) => row.future_return_1d).filter((value): value is number => value !== null)),
        r3d: average(rows.map((row) => row.future_return_3d).filter((value): value is number => value !== null)),
        r5d: average(rows.map((row) => row.future_return_5d).filter((value): value is number => value !== null))
      }))
      .sort((a, b) => b.count - a.count);
  }, [returns]);

  const dateRange = useMemo(() => {
    const dates = returns.map((row) => row.trading_date).filter(Boolean).sort();
    if (dates.length === 0) return "-";
    return `${dates[0]} - ${dates[dates.length - 1]}`;
  }, [returns]);

  const analyzedRatio = summary.news_count ? summary.analyzed_count / summary.news_count : 0;
  const failedRatio = summary.analyzed_count ? summary.failed_count / summary.analyzed_count : 0;
  const tapeItems = [
    `RAW NEWS ${fmtNumber(summary.news_count)}`,
    `LLM ${fmtNumber(summary.analyzed_count)} ANALYZED`,
    `1D COVERAGE ${fmtPct(nonNullRatio(returns, "future_return_1d"))}`,
    `3D COVERAGE ${fmtPct(nonNullRatio(returns, "future_return_3d"))}`,
    `5D COVERAGE ${fmtPct(nonNullRatio(returns, "future_return_5d"))}`,
    `BACKTEST ${fmtPct(latestMetrics?.strategy?.total_return, 2)}`,
    `BENCHMARK ${fmtPct(latestMetrics?.benchmark?.total_return, 2)}`
  ];

  return (
    <main className="dashboard-shell">
      <header className="masthead">
        <div>
          <div className="eyebrow">
            <Database size={15} />
            TW Stock Sentiment Lab
          </div>
          <h1>台股新聞情緒研究工作台</h1>
          <p className="lead">離線 LLM 標註、股價對齊、未來報酬與初版回測的整合檢視。</p>
        </div>
        <div className="status-stack" aria-label="pipeline status">
          <span className="status-pill good">
            <ShieldCheck size={15} />
            Offline LLM pipeline
          </span>
          <span className="status-pill warn">
            <AlertTriangle size={15} />
            Research only
          </span>
        </div>
      </header>

      <section className="daily-brief-panel" aria-label="daily market observation">
        <div className="daily-brief-main">
          <div className="panel-heading">
            <div>
              <h2>今日市場觀察</h2>
              <p>{dailyBrief?.brief_date ?? "資料不足"} · daily tool layer</p>
            </div>
            <span className={`brief-label ${dailyBrief?.market_label === "情緒偏多" ? "positive" : dailyBrief?.market_label === "情緒偏空" ? "negative" : ""}`}>
              {dailyBrief?.market_label ?? "資料不足"}
            </span>
          </div>
          <p className="brief-summary">
            {dailyBrief?.summary_text ?? "目前尚未產生 daily_brief。請先執行 backend/scripts/run_daily_update.py 或 generate_daily_brief.py。"}
          </p>
        </div>
        <div className="brief-stat-grid">
          <div>
            <span>市場情緒分數</span>
            <strong>{fmtDecimal(dailyBrief?.market_sentiment_score, 2)}</strong>
          </div>
          <div>
            <span>今日新聞數</span>
            <strong>{fmtNumber(dailyBrief?.news_count)}</strong>
          </div>
          <div>
            <span>LLM 分析數</span>
            <strong>{fmtNumber(dailyBrief?.analyzed_count)}</strong>
          </div>
          <div>
            <span>最後更新</span>
            <strong className="brief-time">{dailyBrief?.created_at ? dailyBrief.created_at.replace("T", " ").slice(0, 19) : "-"}</strong>
          </div>
        </div>
        <div className="brief-targets">
          <div>
            <span>今日觀察標的</span>
            <div>
              {(dailyBrief?.top_positive_targets.length ? dailyBrief.top_positive_targets : []).slice(0, 5).map((row) => (
                <strong key={row.target}>{row.target}</strong>
              ))}
              {!dailyBrief?.top_positive_targets.length && <em>資料不足</em>}
            </div>
          </div>
          <div>
            <span>今日風險標的</span>
            <div>
              {(dailyBrief?.risk_flags.length ? dailyBrief.risk_flags : []).slice(0, 5).map((row) => (
                <strong key={`${row.target}-${row.reason}`}>{row.target}</strong>
              ))}
              {!dailyBrief?.risk_flags.length && <em>暫無明顯集中風險</em>}
            </div>
          </div>
        </div>
      </section>

      <section className="market-tape" aria-label="pipeline tape">
        <div>
          {[...tapeItems, ...tapeItems].map((item, index) => (
            <span key={`${item}-${index}`}>{item}</span>
          ))}
        </div>
      </section>

      <section className="metric-grid" aria-label="data overview">
        <article className="metric-card">
          <span className="metric-icon blue">
            <Newspaper size={18} />
          </span>
          <span className="metric-label">Raw news</span>
          <strong>{fmtNumber(summary.news_count)}</strong>
          <small>{fmtPct(analyzedRatio)} analyzed</small>
        </article>
        <article className="metric-card">
          <span className="metric-icon green">
            <Activity size={18} />
          </span>
          <span className="metric-label">LLM analysis</span>
          <strong>{fmtNumber(summary.analyzed_count)}</strong>
          <small>{fmtPct(failedRatio)} failed</small>
        </article>
        <article className="metric-card">
          <span className="metric-icon amber">
            <CalendarDays size={18} />
          </span>
          <span className="metric-label">Aligned returns</span>
          <strong>{fmtNumber(returns.length)}</strong>
          <small>{dateRange}</small>
        </article>
        <article className="metric-card">
          <span className="metric-icon violet">
            <LineChartIcon size={18} />
          </span>
          <span className="metric-label">Daily signals</span>
          <strong>{fmtNumber(daily.length)}</strong>
          <small>{fmtNumber(stocks.length)} price series</small>
        </article>
      </section>

      <section className="analysis-grid">
        <article className="panel span-7">
          <div className="panel-heading">
            <div>
              <h2>情緒分布</h2>
              <p>LLM classification mix</p>
            </div>
            <PieChart size={18} />
          </div>
          <div className="chart chart-short">
            <ResponsiveContainer>
              <BarChart data={sentimentBars}>
                <CartesianGrid vertical={false} stroke="#dde3eb" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip formatter={(value, name) => [value, name === "count" ? "筆數" : name]} />
                <Bar dataKey="count" radius={[5, 5, 0, 0]}>
                  {sentimentBars.map((entry) => (
                    <Cell key={entry.key} fill={SENTIMENT_COLORS[entry.key] ?? "#718096"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel span-5">
          <div className="panel-heading">
            <div>
              <h2>新聞類型</h2>
              <p>market / stock / industry</p>
            </div>
            <BarChart3 size={18} />
          </div>
          <div className="distribution-list">
            {typeBars.map((row) => (
              <div className="distribution-row" key={row.key}>
                <div>
                  <span>{row.name}</span>
                  <small>{fmtPct(row.ratio)}</small>
                </div>
                <div className="track">
                  <span
                    style={{
                      width: `${Math.max(row.ratio * 100, 2)}%`,
                      backgroundColor: TYPE_COLORS[row.key] ?? "#6b7280"
                    }}
                  />
                </div>
                <strong>{fmtNumber(row.count)}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading align-end">
          <div>
            <h2>日度情緒訊號</h2>
            <p>sentiment_avg and sentiment_ma5</p>
          </div>
          <div className="target-tabs" aria-label="target filter">
            <button className={activeTarget === "ALL" ? "active" : ""} onClick={() => setActiveTarget("ALL")}>
              全部
            </button>
            {topTargets.map((row) => (
              <button
                className={activeTarget === row.target ? "active" : ""}
                key={row.target}
                onClick={() => setActiveTarget(row.target)}
              >
                {row.target}
              </button>
            ))}
          </div>
        </div>
        <div className="chart chart-wide">
          <ResponsiveContainer>
            <ComposedChart data={dailyTrend}>
              <CartesianGrid vertical={false} stroke="#dde3eb" />
              <XAxis dataKey="date" tickLine={false} axisLine={false} minTickGap={28} />
              <YAxis yAxisId="left" domain={[-1, 1]} tickLine={false} axisLine={false} />
              <YAxis yAxisId="right" orientation="right" allowDecimals={false} tickLine={false} axisLine={false} />
              <Tooltip />
              <Legend />
              <Bar yAxisId="right" dataKey="newsCount" name="news count" fill="#d7b46a" radius={[3, 3, 0, 0]} />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="sentiment"
                name="sentiment_avg"
                stroke="#2f6f9f"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="ma5"
                name="sentiment_ma5"
                stroke="#12845c"
                strokeWidth={2}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="analysis-grid">
        <article className="panel span-7">
          <div className="panel-heading">
            <div>
              <h2>情緒與未來報酬</h2>
              <p>average future returns by sentiment</p>
            </div>
            <TrendingUp size={18} />
          </div>
          <div className="chart chart-short">
            <ResponsiveContainer>
              <BarChart data={returnBySentiment}>
                <CartesianGrid vertical={false} stroke="#dde3eb" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis tickFormatter={(value) => `${(Number(value) * 100).toFixed(0)}%`} tickLine={false} axisLine={false} />
                <Tooltip formatter={(value) => fmtPct(Number(value), 2)} />
                <Legend />
                <Bar dataKey="r1d" name="1d" fill="#2f6f9f" radius={[4, 4, 0, 0]} />
                <Bar dataKey="r3d" name="3d" fill="#12845c" radius={[4, 4, 0, 0]} />
                <Bar dataKey="r5d" name="5d" fill="#c98a22" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="panel span-5">
          <div className="panel-heading">
            <div>
              <h2>Future return coverage</h2>
              <p>non-null ratio</p>
            </div>
            <Table2 size={18} />
          </div>
          <div className="coverage-grid">
            <div>
              <span>1d</span>
              <strong>{fmtPct(nonNullRatio(returns, "future_return_1d"))}</strong>
            </div>
            <div>
              <span>3d</span>
              <strong>{fmtPct(nonNullRatio(returns, "future_return_3d"))}</strong>
            </div>
            <div>
              <span>5d</span>
              <strong>{fmtPct(nonNullRatio(returns, "future_return_5d"))}</strong>
            </div>
          </div>
          <table className="compact-table">
            <thead>
              <tr>
                <th>類型</th>
                <th>筆數</th>
                <th>1d</th>
                <th>3d</th>
                <th>5d</th>
              </tr>
            </thead>
            <tbody>
              {returnByType.map((row) => (
                <tr key={row.type}>
                  <td>{row.name}</td>
                  <td>{row.count}</td>
                  <td>{fmtPct(row.r1d, 2)}</td>
                  <td>{fmtPct(row.r3d, 2)}</td>
                  <td>{fmtPct(row.r5d, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>

      <section className="analysis-grid">
        <article className="panel span-5">
          <div className="panel-heading">
            <div>
              <h2>初版回測</h2>
              <p>High Sentiment Equal Weight</p>
            </div>
            <Activity size={18} />
          </div>
          <div className="backtest-block">
            <div>
              <span>Strategy total return</span>
              <strong>{fmtPct(latestMetrics?.strategy?.total_return, 2)}</strong>
            </div>
            <div>
              <span>Benchmark total return</span>
              <strong>{fmtPct(latestMetrics?.benchmark?.total_return, 2)}</strong>
            </div>
            <div>
              <span>Max drawdown</span>
              <strong>{fmtPct(latestMetrics?.strategy?.max_drawdown, 2)}</strong>
            </div>
            <div>
              <span>Rebalances</span>
              <strong>{fmtNumber(latestMetrics?.strategy?.number_of_rebalances)}</strong>
            </div>
          </div>
          <div className="config-line">
            {latestBacktest?.start_date ?? "-"} - {latestBacktest?.end_date ?? "-"} · top{" "}
            {latestConfig?.top_n ?? "-"} · {latestConfig?.rebalance_frequency ?? "-"} · cost{" "}
            {fmtPct(Number(latestConfig?.transaction_cost ?? 0), 2)}
          </div>
        </article>

        <article className="panel span-7">
          <div className="panel-heading">
            <div>
              <h2>股價資料覆蓋</h2>
              <p>available price series</p>
            </div>
            <Database size={18} />
          </div>
          <div className="stock-grid">
            {stocks.map((row) => (
              <div className="stock-chip" key={row.stock_id}>
                <strong>{row.stock_id}</strong>
                <span>{fmtNumber(row.rows)} rows</span>
                <small>
                  {row.start_date} - {row.end_date}
                </small>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>最新新聞分析</h2>
            <p>latest analyzed and pending rows</p>
          </div>
          <Newspaper size={18} />
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>標題</th>
                <th>類型</th>
                <th>標的</th>
                <th>情緒</th>
                <th>分數</th>
                <th>信心</th>
                <th>理由</th>
              </tr>
            </thead>
            <tbody>
              {news.slice(0, 36).map((row) => (
                <tr key={row.id}>
                  <td className="nowrap">{shortDate(row.published_at)}</td>
                  <td className="title-cell">{row.title}</td>
                  <td>
                    <span className="tag">{labelType(row.news_type)}</span>
                  </td>
                  <td className="nowrap">{row.target ?? "-"}</td>
                  <td>
                    <span className={`sentiment ${row.sentiment ?? "unknown"}`}>{labelSentiment(row.sentiment)}</span>
                  </td>
                  <td>{fmtDecimal(row.sentiment_score, 2)}</td>
                  <td>{fmtDecimal(row.confidence, 2)}</td>
                  <td className="reason-cell">{row.reason ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
