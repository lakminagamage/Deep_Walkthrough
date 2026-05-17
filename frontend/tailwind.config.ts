import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['var(--font-mono)', 'JetBrains Mono', 'monospace'],
        sans: ['var(--font-sans)', 'DM Sans', 'sans-serif'],
      },
      colors: {
        base:    '#0d0d0f',
        surface: '#161618',
        raised:  '#1e1e22',
        border:  '#2a2a30',
        muted:   '#555568',
        dim:     '#8888a0',
        ink:     '#e8e8ec',
        green:   '#22c55e',
        amber:   '#f59e0b',
        red:     '#ef4444',
        blue:    '#3b82f6',
        purple:  '#a855f7',
      },
      animation: {
        'pulse-fast': 'pulse 1s cubic-bezier(0.4,0,0.6,1) infinite',
      },
    },
  },
  plugins: [],
}
export default config
