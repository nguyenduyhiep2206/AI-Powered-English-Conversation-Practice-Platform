// app/layout.tsx ← ĐÚNG
import type { Metadata } from "next";
import { AuthSessionRefresh } from "@/components/AuthSessionRefresh";
import "./globals.css";

export const metadata: Metadata = {
  title: "EnglishFlow",
  description: "Practice English conversations with AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthSessionRefresh />
        {children}
      </body>
    </html>
  );
}