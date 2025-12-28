/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./popup.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'traffic-green': '#10b981',
        'traffic-yellow': '#f59e0b',
        'traffic-red': '#ef4444',
      },
    },
  },
  plugins: [],
}
