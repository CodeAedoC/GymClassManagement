/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gym: {
          dark: '#0f172a',
          card: '#1e293b',
          accent: '#f97316',
          danger: '#ef4444',
          success: '#10b981',
          primary: '#6366f1',
        }
      }
    },
  },
  plugins: [],
}
