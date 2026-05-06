import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import SessionWrapper from '@/components/SessionWrapper'

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

export const viewport: Viewport = {
    width: 'device-width',
    initialScale: 1,
    themeColor: '#0a0a0f',
}

export const metadata: Metadata = {
    title: 'SARANG — Professional Research Environment',
    description: 'Open source research-to-code engine for professional researchers. Deconstructing scientific papers into validated implementations.',
    keywords: ['SARANG', 'Research', 'AI Agents', 'Open Source', 'Scientific Computing', 'Reproducibility'],
    authors: [{ name: 'SARANG Org' }],
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
            <body className="bg-bg-primary text-text-primary antialiased">
                <SessionWrapper>
                    {children}
                </SessionWrapper>
            </body>
        </html>
    )
}
