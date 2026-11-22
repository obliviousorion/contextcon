/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      keyframes: {
        "slide-in": { "0%": { opacity: "0", transform: "translateY(-6px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        "skip-in": { "0%": { opacity: "0", transform: "translateX(-12px)" }, "100%": { opacity: "0.75", transform: "translateX(0)" } },
        "grow-y": { "0%": { transform: "scaleY(0)" }, "100%": { transform: "scaleY(1)" } },
        "grow-x": { "0%": { transform: "scaleX(0)" }, "100%": { transform: "scaleX(1)" } },
        "drawer-in": { "0%": { transform: "translateX(100%)" }, "100%": { transform: "translateX(0)" } },
      },
      animation: {
        "slide-in": "slide-in 220ms ease-out both",
        "skip-in": "skip-in 420ms ease-out both",
        "grow-y": "grow-y 600ms cubic-bezier(.2,.8,.2,1) both",
        "grow-x": "grow-x 600ms cubic-bezier(.2,.8,.2,1) both",
        "drawer-in": "drawer-in 200ms ease-out both",
      },
    },
  },
  plugins: [],
};
