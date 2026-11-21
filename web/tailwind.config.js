/** @type {import('tailwindcss').Config} */
// Palette: the lab's fixed seven-colour system (see app/components/theme.py in
// the Streamlit supplement) -- two warm neutrals and five vibrant accents.
// Every other tone is a derived shade of one of the seven.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0c0e14',
          900: '#11131a',
          880: '#141720',
          850: '#181b26',
          800: '#1e2230',
          750: '#242838',
          700: '#2a2e3c',
          650: '#3a3f52',
          600: '#4b5064',
          500: '#6b6f80',
          400: '#8b8d99',
          300: '#b6af9e',
          200: '#c9c5ba',
          100: '#e6e0d3',
          50: '#f5f0e6',
        },
        signal: {
          amber: '#f3c542',
          amberdim: '#7a6322',
          blue: '#4d6ff0',
          green: '#6fae4f',
          red: '#f04a32',
          violet: '#5fd0c9',
          teal: '#24a6a1',
        },
        cobalt: { DEFAULT: '#3155d9', bright: '#4d6ff0' },
        vermillion: '#f04a32',
        gold: '#f3c542',
        leaf: { DEFAULT: '#5b963f', bright: '#6fae4f' },
        turquoise: '#24a6a1',
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
