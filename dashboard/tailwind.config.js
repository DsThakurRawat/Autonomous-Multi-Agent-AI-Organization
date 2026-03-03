/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './app/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                // Design system — dark theme
                bg: {
                    primary: '#0a0a0f',
                    secondary: '#111118',
                    card: '#16161f',
                    hover: '#1c1c28',
                    border: '#252535',
                },
                accent: {
                    blue: '#4f8ef7',
                    purple: '#8b5cf6',
                    cyan: '#22d3ee',
                    green: '#10b981',
                    amber: '#f59e0b',
                    red: '#ef4444',
                    pink: '#ec4899',
                },
                text: {
                    primary: '#f1f5f9',
                    secondary: '#94a3b8',
                    muted: '#4b5563',
                },
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'fade-in': 'fadeIn 0.3s ease-in-out',
                'slide-up': 'slideUp 0.3s ease-out',
                'glow': 'glow 2s ease-in-out infinite alternate',
                'scan-line': 'scanLine 2s linear infinite',
            },
            keyframes: {
                fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
                slideUp: { from: { transform: 'translateY(10px)', opacity: '0' }, to: { transform: 'translateY(0)', opacity: '1' } },
                glow: { from: { boxShadow: '0 0 5px rgba(79,142,247,0.3)' }, to: { boxShadow: '0 0 20px rgba(79,142,247,0.6)' } },
                scanLine: { from: { transform: 'translateY(-100%)' }, to: { transform: 'translateY(100vh)' } },
            },
            backgroundImage: {
                'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
                'grid-pattern': "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23252535' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
            },
        },
    },
    plugins: [],
}
