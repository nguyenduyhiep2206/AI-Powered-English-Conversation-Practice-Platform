import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-dashboard",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "My plan — EnglishFlow",
    template: "%s — EnglishFlow",
  },
  description: "Practice English with a path built around your level.",
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className={`${jakarta.variable} font-[family-name:var(--font-dashboard)]`}
    >
      {children}
    </div>
  );
}
