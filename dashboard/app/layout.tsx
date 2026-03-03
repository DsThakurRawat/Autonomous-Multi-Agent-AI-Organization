import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'

const inter = Inter({
    subsets: ['latin'],
    variable: '--font-inter',
    display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
    subsets: ['latin'],
    variable: '--font-mono',
    display: 'swap',
})

export const metadata: Metadata = {
    title: 'AI Organization — Control Center',
    description: 'Autonomous Multi-Agent AI Organization — Real-time project orchestration dashboard',
    keywords: ['AI', 'agents', 'orchestration', 'automation', 'LLM'],
    authors: [{ name: 'AI Organization' }],
    themeColor: '#0a0a0f',
    viewport: 'width=device-width, initial-scale=1',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
            <body className="bg-bg-primary text-text-primary antialiased">
                {children}
            </body>
        </html>
    )
}
