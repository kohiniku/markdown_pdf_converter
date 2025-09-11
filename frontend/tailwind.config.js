/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0B1020',
        surface: '#11162A',
        text: '#E6E8EF',
        primary: '#4F8DF7',
        border: '#1E2743',
        muted: '#A0A7C1',
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans JP', 'sans-serif'],
      },
      borderRadius: {
        'DEFAULT': '14px',
      },
      fontSize: {
        'base': '14px',
      },
      spacing: {
        '4': '4px',
        '8': '8px', 
        '12': '12px',
        '16': '16px',
        '24': '24px',
        '32': '32px',
        '48': '48px',
      }
    },
  },
  plugins: [],
}