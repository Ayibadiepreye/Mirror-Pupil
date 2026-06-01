/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Knights of the Blood Oath Theme
        'kob': {
          'base': '#16161a',        // Base Layer (sidebar/navigation)
          'app': '#1e1e24',          // App Layer (main content)
          'crimson': '#b22222',      // Accent Layer (guild crimson - headers/tabs)
          'red': '#e74c3c',          // Interactive Layer (vibrant red - buttons/focus)
          'text': '#e0e0e0',         // Primary text
          'text-dim': '#a0a0a0',     // Secondary text
          'border': '#2a2a30',       // Borders
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
