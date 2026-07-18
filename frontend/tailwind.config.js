/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        surface: '#0c0a09',
        card: '#141211',
        border: '#292524',
        muted: '#a8a29e',
        risk: {
          critical: '#ef4444',
          high: '#f97316',
          medium: '#eab308',
          low: '#22c55e',
          none: '#6b7280',
        },
      },
      backgroundImage: {
        'gradient-card': 'linear-gradient(135deg, rgba(245,158,11,0.04) 0%, rgba(244,63,94,0.02) 100%)',
        'gradient-card-hover': 'linear-gradient(135deg, rgba(245,158,11,0.08) 0%, rgba(244,63,94,0.04) 100%)',
        'gradient-sidebar': 'linear-gradient(180deg, rgba(245,158,11,0.06) 0%, transparent 100%)',
        'gradient-header': 'linear-gradient(90deg, rgba(245,158,11,0.08) 0%, rgba(244,63,94,0.04) 100%)',
      },
      boxShadow: {
        'warm': '0 0 20px rgba(245,158,11,0.06)',
        'warm-lg': '0 0 40px rgba(245,158,11,0.1)',
      },
    },
  },
  plugins: [],
};
