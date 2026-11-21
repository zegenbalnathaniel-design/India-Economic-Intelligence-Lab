/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#08090a',
          900: '#0b0d0f',
          880: '#0f1214',
          850: '#131719',
          800: '#181d20',
          750: '#1e2428',
          700: '#262d32',
          650: '#323b41',
          600: '#414c53',
          500: '#5d6a72',
          400: '#818e96',
          300: '#a4afb5',
          200: '#c8d0d4',
          100: '#e4e8ea',
          50: '#f4f6f6',
        },
        signal: {
          amber: '#e8933a',
          amberdim: '#7d5426',
          blue: '#5b9bd5',
          green: '#4fae86',
          red: '#d3675d',
          violet: '#8b7fd4',
          teal: '#4aa5a8',
        },
      },
      fontFamily: {
        display: ['Newsreader', 'Iowan Old Style', 'Georgia', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: { '2xs': ['0.6875rem', { lineHeight: '1rem' }] },
      letterSpacing: { widest2: '0.22em' },
      maxWidth: { reading: '68ch' },
    },
  },
  plugins: [],
};
