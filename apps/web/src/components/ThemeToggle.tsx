"use client";

import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label="Toggle color theme"
      title="Toggle dark / light"
    >
      {theme === "dark" ? "☾ Dark" : "☀ Light"}
    </button>
  );
}
