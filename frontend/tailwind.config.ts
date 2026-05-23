import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg:        '#080c14',
          'bg-2':    '#0a1020',
          'bg-3':    '#0e1a2a',
          'bg-4':    '#142030',
          panel:     'rgba(10, 18, 36, 0.72)',
          'panel-solid': '#0c1628',
          border:    'rgba(0, 212, 255, 0.15)',
          'border-strong': 'rgba(0, 212, 255, 0.35)',
          'border-glow': 'rgba(0, 212, 255, 0.5)',
          cyan:      '#00d4ff',
          'cyan-dim':  'rgba(0, 212, 255, 0.3)',
          'cyan-mid':  'rgba(0, 212, 255, 0.6)',
          blue:      '#0066ff',
          'blue-dim':  'rgba(0, 102, 255, 0.3)',
          green:     '#00ff88',
          'green-dim': 'rgba(0, 255, 136, 0.3)',
          yellow:    '#ffd700',
          red:       '#ff4466',
          purple:    '#9b59ff',
          'purple-dim': 'rgba(155, 89, 255, 0.3)',
          text:      '#c8d8f0',
          'text-dim':  '#5a7a9e',
          'text-bright': '#e8f4ff',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'jarvis-grid': `
          linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px)
        `,
        'jarvis-radial': 'radial-gradient(ellipse at 50% 0%, rgba(0,102,255,0.10) 0%, transparent 60%)',
        'jarvis-radial-cyan': 'radial-gradient(ellipse at 50% 0%, rgba(0,212,255,0.06) 0%, transparent 60%)',
        'neon-glow-cyan': 'radial-gradient(ellipse at center, rgba(0,212,255,0.15) 0%, transparent 60%)',
        'neon-glow-blue': 'radial-gradient(ellipse at center, rgba(0,102,255,0.12) 0%, transparent 60%)',
        'neon-glow-green': 'radial-gradient(ellipse at center, rgba(0,255,136,0.10) 0%, transparent 60%)',
        'gradient-cyan-blue': 'linear-gradient(135deg, #00d4ff, #0066ff)',
        'gradient-green-cyan': 'linear-gradient(135deg, #00ff88, #00d4ff)',
        'gradient-purple-blue': 'linear-gradient(135deg, #9b59ff, #0066ff)',
        'gradient-card': 'linear-gradient(135deg, rgba(0,212,255,0.08) 0%, rgba(0,102,255,0.03) 100%)',
        'gradient-card-hover': 'linear-gradient(135deg, rgba(0,212,255,0.12) 0%, rgba(0,102,255,0.06) 100%)',
        'shimmer': 'linear-gradient(90deg, transparent, rgba(0,212,255,0.05), transparent)',
      },
      backgroundSize: {
        'grid-24': '24px 24px',
        'grid-32': '32px 32px',
        '200%': '200% 100%',
      },
      boxShadow: {
        'neon-cyan': '0 0 12px rgba(0,212,255,0.5), 0 0 24px rgba(0,212,255,0.2)',
        'neon-blue': '0 0 12px rgba(0,102,255,0.5), 0 0 24px rgba(0,102,255,0.2)',
        'neon-green': '0 0 12px rgba(0,255,136,0.4)',
        'neon-purple': '0 0 12px rgba(155,89,255,0.4)',
        'panel': '0 4px 24px rgba(0,0,0,0.5), inset 0 1px 0 rgba(0,212,255,0.08)',
        'panel-hover': '0 8px 40px rgba(0,0,0,0.7), inset 0 1px 0 rgba(0,212,255,0.2)',
        'panel-glow': '0 0 30px rgba(0,212,255,0.08), 0 4px 24px rgba(0,0,0,0.5)',
        'inner-glow': 'inset 0 0 20px rgba(0,212,255,0.04)',
        'glass': '0 8px 32px rgba(0,0,0,0.4)',
      },
      animation: {
        'pulse-cyan': 'pulse-cyan 2s ease-in-out infinite',
        'pulse-slow': 'pulse-slow 3s ease-in-out infinite',
        'scan': 'scan 3s linear infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'glow-fast': 'glow 1s ease-in-out infinite alternate',
        'fade-in': 'fade-in 0.3s ease-out',
        'fade-in-up': 'fade-in-up 0.4s ease-out',
        'fade-in-down': 'fade-in-down 0.3s ease-out',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'slide-in-left': 'slide-in-left 0.3s ease-out',
        'float': 'float 4s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'pulse-ring': 'pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 8s linear infinite',
        'bounce-gentle': 'bounce-gentle 1s ease-in-out infinite',
        'count-up': 'count-up 0.6s ease-out',
        'breath': 'breath 3s ease-in-out infinite',
      },
      keyframes: {
        'pulse-cyan': {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 8px rgba(0,212,255,0.4)' },
          '50%': { opacity: '0.7', boxShadow: '0 0 24px rgba(0,212,255,0.9)' },
        },
        'pulse-slow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'scan': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'glow': {
          '0%': { textShadow: '0 0 4px rgba(0,212,255,0.3)' },
          '100%': { textShadow: '0 0 16px rgba(0,212,255,0.9), 0 0 32px rgba(0,212,255,0.3)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in-down': {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(16px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'slide-in-left': {
          '0%': { transform: 'translateX(-16px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(1)', opacity: '1' },
          '100%': { transform: 'scale(2.5)', opacity: '0' },
        },
        'bounce-gentle': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-3px)' },
        },
        'count-up': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'breath': {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      transitionDuration: {
        '250': '250ms',
        '350': '350ms',
        '400': '400ms',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'out-back': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [],
};

export default config;
