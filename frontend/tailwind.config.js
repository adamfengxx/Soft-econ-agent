/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        accent: {
          DEFAULT: '#DC2626',
          hover: '#B91C1C',
          light: '#FEF2F2',
        },
      },
    },
  },
  plugins: [],
}
