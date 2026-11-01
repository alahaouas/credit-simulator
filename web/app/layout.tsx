import type { Metadata } from "next";
import localFont from "next/font/local";
import { I18nProvider } from "@/lib/i18n";
import { SITE_URL } from "@/lib/site";
import { ThemeProvider } from "@/components/ThemeProvider";
import { LegalFooter } from "@/components/LegalFooter";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Credit Simulator — mortgage and loan simulator",
    // Every page below sets its own title; this keeps the brand on all of them.
    template: "%s — Credit Simulator",
  },
  description:
    "Simulate a mortgage for eight European and US markets: optimal loan plan, monthly payment, full amortization schedule and down-payment sweet spot.",
  alternates: { canonical: "/" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // The UI language is chosen client-side (localStorage), so the server can
    // only render a default. I18nProvider corrects document.documentElement.lang
    // once it knows the locale. A proper fix is locale-routed URLs — see docs/seo.md.
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider>
          <I18nProvider>
            {children}
            <LegalFooter />
          </I18nProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
