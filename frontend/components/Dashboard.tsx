"use client";

import { useMemo } from "react";
import { AlertTriangle, FileText, Newspaper, RefreshCw, Sparkles } from "lucide-react";
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

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "#4a7c59",
  neutral: "#708090",
  negative: "#b7472a"
};

const TARGET_NAME_MAP: Record<string, string> = {
  "0050": "元大台灣50",
  "2330": "台積電",
  "2327": "國巨",
  "2504": "國產",
  "2609": "陽明",
  "2731": "雄獅",
  "3037": "欣興"
};

function fmtDecimal(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function labelSentiment(value: string | null | undefined) {
  if (value === "positive") return "正向";
  if (value === "negative") return "負向";
  if (value === "neutral") return "中立";
  return "待分析";
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

export function Dashboard({ summary, news, daily, dailyBrief }: Props) {
  const sentimentBars = useMemo(
    () =>
      summary.by_sentiment.map((row) => ({
        name: labelSentiment(row.sentiment),
        key: row.sentiment,
        count: row.count
      })),
    [summary.by_sentiment]
  );

  const dailyTrend = useMemo(() => {
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
        sentiment: Number((average(row.scores) ?? 0).toFixed(3)),
        newsCount: row.newsCount
      }));
  }, [daily]);

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
              <h2>新聞情緒分布</h2>
              <p className="panel-note">依 LLM 判斷結果統計新聞情緒分類</p>
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
              <h2>近期情緒趨勢</h2>
              <p className="panel-note">近期情緒波動可能受單日新聞量與標的集中度影響。</p>
            </div>
          </div>
          <div className="chart-legend" aria-label="chart legend">
            <span>
              <i className="legend-line" />
              綠線：平均情緒分數
            </span>
            <span>
              <i className="legend-bar" />
              橘柱：新聞數量
            </span>
          </div>
          <div className="chart chart-short">
            <ResponsiveContainer>
              <ComposedChart data={dailyTrend}>
                <CartesianGrid vertical={false} stroke="#d9dedb" />
                <XAxis dataKey="date" tickLine={false} axisLine={false} />
                <YAxis yAxisId="left" domain={[-1, 1]} tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" orientation="right" hide />
                <Tooltip />
                <Bar yAxisId="right" dataKey="newsCount" name="新聞數" fill="#f9a620" radius={[4, 4, 0, 0]} />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="sentiment"
                  name="情緒分數"
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
                <p>{row.reason ?? "尚無分析理由"}</p>
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
    </main>
  );
}
