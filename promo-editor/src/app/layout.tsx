import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "App Store Screenshots — 生计",
  description: "Design and export App Store + Google Play screenshots.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body style={{ fontFamily: "'Noto Sans SC', 'Source Han Sans SC', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', 'WenQuanYi Micro Hei', sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
