/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sentinel: {
          bg: "#0B0F17",
          card: "#121826",
          border: "#1E293B",
          accent: "#3B82F6",
          danger: "#EF4444",
          warning: "#F59E0B",
          success: "#10B981"
        }
      }
    },
  },
  plugins: [],
}
