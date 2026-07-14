/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      colors: {
        trust: {
          50:  "#f0f4ff",
          100: "#e0e9ff",
          200: "#c0d0ff",
          300: "#91aeff",
          400: "#5f84ff",
          500: "#3b5bff",
          600: "#1f38f5",
          700: "#1427e1",
          800: "#1321b5",
          900: "#15228e",
          950: "#0d1560",
        },
        neon: {
          green:  "#00ff88",
          blue:   "#00d4ff",
          purple: "#bf5af2",
        },
      },
      backgroundImage: {
        "hero-gradient": "radial-gradient(ellipse at 50% 0%, hsl(230, 90%, 12%) 0%, hsl(240, 70%, 6%) 60%, hsl(250, 80%, 4%) 100%)",
        "card-gradient": "linear-gradient(135deg, hsl(230, 40%, 14%) 0%, hsl(240, 40%, 10%) 100%)",
        "glow-blue":    "radial-gradient(ellipse at center, rgba(59, 91, 255, 0.15) 0%, transparent 70%)",
        "glow-green":   "radial-gradient(ellipse at center, rgba(0, 255, 136, 0.12) 0%, transparent 70%)",
      },
      animation: {
        "pulse-slow":   "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "float":        "float 6s ease-in-out infinite",
        "shimmer":      "shimmer 2s linear infinite",
        "fade-in":      "fadeIn 0.6s ease-out forwards",
        "slide-up":     "slideUp 0.5s ease-out forwards",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%":       { transform: "translateY(-8px)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        fadeIn: {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(20px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
      boxShadow: {
        "glow-blue":   "0 0 30px rgba(59, 91, 255, 0.3)",
        "glow-green":  "0 0 30px rgba(0, 255, 136, 0.25)",
        "glow-purple": "0 0 30px rgba(191, 90, 242, 0.25)",
        "card":        "0 4px 32px rgba(0, 0, 0, 0.4), 0 1px 0 rgba(255,255,255,0.05) inset",
      },
    },
  },
  plugins: [],
};
