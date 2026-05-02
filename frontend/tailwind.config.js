/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Score band colors used across map and legend.
        band: {
          low: "#22c55e",
          medium: "#eab308",
          high: "#f97316",
          critical: "#ef4444",
        },
        // Mil-grade dark theme palette.
        ink: {
          900: "#050810",
          800: "#0b1220",
          700: "#111a2e",
          600: "#1e293b",
          500: "#334155",
        },
        accent: {
          cyan: "#22d3ee",
          amber: "#f59e0b",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(34, 211, 238, 0.18)",
        "glow-critical": "0 0 24px rgba(239, 68, 68, 0.35)",
      },
    },
  },
  plugins: [],
};
