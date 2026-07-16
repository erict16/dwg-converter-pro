import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThemeToggle } from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "DWG Converter Pro",
  description:
    "Batch convert Chinese CAD drawings (DWG/DXF) to English — glossary-first for power equipment terminology.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <div className="shell">
            <header className="topbar">
              <div className="brand">
                <span className="brand-mark">DWG</span>
                <div>
                  <div className="brand-title">Converter Pro</div>
                  <div className="brand-sub">ZH → EN · batch drawings</div>
                </div>
              </div>
              <nav className="nav">
                <a href="/">Convert</a>
                <a href="/glossary">Glossary</a>
                <a
                  href="https://github.com/erict16/dwg-converter-pro"
                  target="_blank"
                  rel="noreferrer"
                >
                  GitHub
                </a>
                <ThemeToggle />
              </nav>
            </header>
            <main className="main">{children}</main>
            <footer className="footer">
              Glossary-first translation · output drawings only
            </footer>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
