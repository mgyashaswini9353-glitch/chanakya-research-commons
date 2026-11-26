/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cu: {
          navy: '#142B4A',
          navyHover: '#0E2038',
          gold: '#D6AA35',
          goldSoft: '#FBF5E4',
          goldDark: '#A67E1E',
          ivory: '#FAF8F2',
          white: '#FFFFFF',
          sage: '#E9EFE8',
          sageText: '#2E5438',
          warmGrey: '#F3F4F2',
          border: '#E6E2D8',
          ink: '#263247',
          muted: '#697386',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['Georgia', 'Cambria', 'Times New Roman', 'serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(20, 43, 74, 0.04), 0 1px 1px rgba(20, 43, 74, 0.03)',
        cardHover: '0 6px 18px rgba(20, 43, 74, 0.07), 0 1px 3px rgba(20, 43, 74, 0.04)',
        dropdown: '0 12px 32px rgba(20, 43, 74, 0.12), 0 2px 6px rgba(20, 43, 74, 0.05)',
      },
    },
  },
  plugins: [],
}
