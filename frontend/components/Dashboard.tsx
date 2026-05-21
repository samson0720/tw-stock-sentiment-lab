"use client";

import { Activity, BarChart3, Database, Newspaper } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { BacktestRow, DailySentiment, NewsRow, ReturnRow, Summary } from "@/lib/api";

type Props = {
  summary: Summary;
  news: NewsRow[];
  daily: DailySentiment[];
  returns: ReturnRow[];
  backtests: BacktestRow[];
};

function metricValue(value: number) {
  return Number.isFinite(value) ? value.toLocaleString("zh-TW") : "0";
}

function pct(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `${(value * 100).toFixed(2)}%`;
}

export function Dashboard({ summary, news, daily, returns, backtests }: Props) {
  const latestBacktest = backtests[0];
  const latestMetrics = latestBacktest ? JSON.parse(latestBacktest.metrics) : null;
  const sentimentBars = summary.by_sentiment.map((row) => ({
    name: row.sentiment,
    count: row.count
  }));

  const trend = [...daily]
    .reverse()
    .slice(-80)
    .map((row) => ({
      date: row.trading_date,
      target: row.target,
      sentiment: Number(row.sentiment_avg.toFixed(3)),
      ma5: row.sentiment_ma5 ? Number(row.sentiment_ma5.toFixed(3)) : null,
      count: row.news_count
    }));

  return (
    <main>
      <div className="topbar">
        <div>
          <h1>台股新聞情緒分析與投資組合研究平台</h1>
          <p>本機資料分析 dashboard，用於檢查新聞情緒、日度聚合、未來報酬與回測結果，不構成投資建議。</p>
        </div>
        <span className="badge">Backend http://localhost:8000</span>
      </div>

      <div className="grid">
        <div className="metric">
          <Newspaper size={20} />
          <p>新聞總數</p>
          <strong>{metricValue(summary.news_count)}</strong>
        </div>
        <div className="metric">
          <Activity size={20} />
          <p>已分析新聞</p>
          <strong>{metricValue(summary.analyzed_count)}</strong>
        </div>
        <div className="metric">
          <Database size={20} />
          <p>日度情緒列數</p>
          <strong>{metricValue(daily.length)}</strong>
        </div>
        <div className="metric">
          <BarChart3 size={20} />
          <p>最新回測總報酬</p>
          <strong>{latestMetrics ? pct(latestMetrics.total_return) : "-"}</strong>
        </div>
      </div>

      <section className="section">
        <h2>情緒分布</h2>
        <div className="chart">
          <ResponsiveContainer>
            <BarChart data={sentimentBars}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#1f6feb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="section">
        <h2>日度情緒趨勢</h2>
        <div className="chart">
          <ResponsiveContainer>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" minTickGap={32} />
              <YAxis domain={[-1, 1]} />
              <Tooltip />
              <Line type="monotone" dataKey="sentiment" stroke="#1f6feb" dot={false} />
              <Line type="monotone" dataKey="ma5" stroke="#17803d" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="section">
        <h2>新聞情緒分析</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>時間</th>
                <th>標題</th>
                <th>類型</th>
                <th>標的</th>
                <th>情緒</th>
                <th>信心</th>
                <th>理由</th>
              </tr>
            </thead>
            <tbody>
              {news.slice(0, 30).map((row) => (
                <tr key={row.id}>
                  <td>{row.published_at?.slice(0, 10) ?? "-"}</td>
                  <td>{row.title}</td>
                  <td><span className="badge">{row.news_type ?? "-"}</span></td>
                  <td>{row.target ?? "-"}</td>
                  <td className={row.sentiment === "positive" ? "positive" : row.sentiment === "negative" ? "negative" : ""}>
                    {row.sentiment ?? "-"}
                  </td>
                  <td>{row.confidence?.toFixed(2) ?? "-"}</td>
                  <td>{row.reason ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section">
        <h2>報酬分析樣本</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>交易日</th>
                <th>標的</th>
                <th>類型</th>
                <th>情緒分數</th>
                <th>1 日</th>
                <th>3 日</th>
                <th>5 日</th>
              </tr>
            </thead>
            <tbody>
              {returns.slice(0, 30).map((row, index) => (
                <tr key={`${row.trading_date}-${row.target}-${index}`}>
                  <td>{row.trading_date}</td>
                  <td>{row.target}</td>
                  <td>{row.news_type}</td>
                  <td>{row.sentiment_score.toFixed(2)}</td>
                  <td>{pct(row.future_return_1d)}</td>
                  <td>{pct(row.future_return_3d)}</td>
                  <td>{pct(row.future_return_5d)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
