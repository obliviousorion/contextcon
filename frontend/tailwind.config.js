/** @type {import('tailwindcss').Config} */
// Colors are CSS variables defined in src/index.css ("evidentiary registry" palette).
// They are plain hex variables, so Tailwind opacity modifiers (bg-x/50) are not used.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        sunken: "var(--sunken)",
        ink: "var(--ink)",
        muted: "var(--muted)",
        line: "var(--border)",
        accent: { DEFAULT: "var(--accent)", hover: "var(--accent-hover)", tint: "var(--accent-tint)" },
        ok: { DEFAULT: "var(--ok)", tint: "var(--ok-tint)" },
        refuse: { DEFAULT: "var(--refuse)", tint: "var(--refuse-tint)" },
        stale: { DEFAULT: "var(--stale)", tint: "var(--stale-tint)" },
        later: { DEFAULT: "var(--later)", tint: "var(--later-tint)" },
        danger: { DEFAULT: "var(--danger)", tint: "var(--danger-tint)" },
      },
      fontFamily: {
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        meta: ["0.8125rem", { lineHeight: "1.25rem" }], // 13px minimum for metadata
      },
      zIndex: { nav: "10", drawer: "40", modal: "50" },
      maxWidth: { file: "880px" },
    },
  },
  plugins: [],
};
