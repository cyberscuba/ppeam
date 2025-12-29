/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#21B0E3',
          50: '#E8F7FC',
          100: '#D1EFF9',
          200: '#A3DFF3',
          300: '#75CFED',
          400: '#47BFE7',
          500: '#21B0E3',
          600: '#1A8DB6',
          700: '#146A89',
          800: '#0D475C',
          900: '#07242E',
        },
        secondary: {
          DEFAULT: '#6B8B4A',
          50: '#F2F5ED',
          100: '#E5EBDB',
          200: '#CBD7B7',
          300: '#B1C393',
          400: '#97AF6F',
          500: '#6B8B4A',
          600: '#566F3B',
          700: '#40532C',
          800: '#2B381E',
          900: '#151C0F',
        },
        neutral: {
          DEFAULT: '#B4C3AE',
          light: '#FCFDFA',
          dark: '#0D1214',
        }
      },
      fontSize: {
        'base': '16px',
        'lg': '18px',
        'xl': '20px',
      }
    },
  },
  plugins: [],
}
