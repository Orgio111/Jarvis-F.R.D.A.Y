import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // JARVIS cockpit colour palette
        jarvis: {
          bg:        '#080c14',
          'bg-2':    '#0d1424',
          'bg-3':    '#111d2e',
          panel:     'rgba(13, 20, 36, 0.85)',
          border:    'rgba(0, 212, 255, 0.18)',
          'border-strong': 'rgba(0, 212, 255, 0.45)',
          cyan:      '#00d4ff',
          'cyan-dim': 'rgba(0, 212, 255, 0.35)',
          blue:      '#0066ff',
          'blue-dim': 'rgba(0, 102, 255, 0.35)',
          green:     '#00ff88',
          yellow:    '#ffd700',
          red:       '#ff4466',
          purple:    '#9b59ff',
          text:      '#c8d8f0',
          'text-dim': '#6b8ab5',
          'text-bright': '#e8f4ff',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'jarvis-grid': `
          linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px)
        `,
        'jarvis-radial': 'radial-gradient(ellipse at 50% 0%, rgba(0,102,255,0.12) 0%, transparent 70%)',
        'neon-glow-cyan': 'radial-gradient(ellipse at center, rgba(0,212,255,0.15) 0%, transparent 60%)',
      },
      backgroundSize: {
        'grid-24': '24px 24px',
      },
      boxShadow: {
        'neon-cyan': '0 0 12px rgba(0,212,255,0.5), 0 0 24px rgba(0,212,255,0.2)',
        'neon-blue': '0 0 12px rgba(0,102,255,0.5), 0 0 24px rgba(0,102,255,0.2)',
        'neon-green': '0 0 12px rgba(0,255,136,0.4)',
        'panel': '0 4px 24px rgba(0,0,0,0.6), inset 0 1px 0 rgba(0,212,255,0.1)',
        'panel-hover': '0 4px 32px rgba(0,0,0,0.8), inset 0 1px 0 rgba(0,212,255,0.25)',
      },
      animation: {
        'pulse-cyan': 'pulse-cyan 2s ease-in-out infinite',
        'scan': 'scan 3s linear infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
      },
      keyframes: {
        'pulse-cyan': {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 8px rgba(0,212,255,0.4)' },
          '50%': { opacity: '0.7', boxShadow: '0 0 20px rgba(0,212,255,0.8)' },
        },
        'scan': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'glow': {
          '0%': { textShadow: '0 0 4px rgba(0,212,255,0.4)' },
          '100%': { textShadow: '0 0 12px rgba(0,212,255,0.9)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(16px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};

export default config;
