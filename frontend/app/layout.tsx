import type { Metadata, Viewport } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "SIGNAL — We surface the talent that credentials hide",
    template: "%s — SIGNAL",
  },
  description:
    "Evidence-based capability profiles for students. SIGNAL analyzes your GitHub and projects to reveal the skills your transcript never showed.",
  keywords: ["capability profile", "GitHub analysis", "student portfolio", "skill assessment", "evidence-based"],
  openGraph: {
    title: "SIGNAL",
    description: "We surface the talent that credentials hide.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#080808",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${geistMono.variable} dark h-full`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
