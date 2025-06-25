/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.{html,js}',
    './*/templates/**/*.{html,js}',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        'primary': {
          DEFAULT: '#10B981',
          'dark': '#059669',
          'light': '#34D399',
        },
        'secondary': {
          DEFAULT: '#6B7280',
          'dark': '#374151',
          'light': '#D1D5DB',
        },
        'success': '#10B981',
        'warning': '#F59E0B',
        'danger': '#EF4444',
        'info': '#3B82F6',
        'produce': '#84CC16',
        'dairy': '#60A5FA',
        'meat': '#F87171',
        'pantry': '#FBBF24',
        'frozen': '#A78BFA',
      },
      fontFamily: {
        'sans': ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
      },
      animation: {
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'fade-in': 'fadeIn 0.3s ease-out',
      },
      keyframes: {
        slideUp: {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}