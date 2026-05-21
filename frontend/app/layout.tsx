import "./styles.css";

export const metadata = {
  title: "台股新聞情緒分析",
  description: "Local TW stock news sentiment research dashboard"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant">
      <body>{children}</body>
    </html>
  );
}
