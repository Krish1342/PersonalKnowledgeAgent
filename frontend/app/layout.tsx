import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Personal Knowledge Agent',
  description: 'AI-powered personal knowledge management system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <div style={{ display: 'flex', minHeight: '100vh' }}>
          {/* Sidebar Navigation */}
          <nav style={{
            width: '250px',
            backgroundColor: '#f5f5f5',
            padding: '20px',
            borderRight: '1px solid #ddd'
          }}>
            <h1 style={{ marginBottom: '30px', fontSize: '20px' }}>
              Personal Knowledge Agent
            </h1>
            
            <ul style={{ listStyle: 'none', padding: 0 }}>
              <li style={{ marginBottom: '15px' }}>
                <Link href="/query" style={{ textDecoration: 'none', color: '#333' }}>
                  📝 Ask Questions
                </Link>
              </li>
              <li style={{ marginBottom: '15px' }}>
                <Link href="/upload" style={{ textDecoration: 'none', color: '#333' }}>
                  📤 Upload Knowledge
                </Link>
              </li>
              <li style={{ marginBottom: '15px' }}>
                <Link href="/sources" style={{ textDecoration: 'none', color: '#333' }}>
                  📚 View Sources
                </Link>
              </li>
              <li style={{ marginBottom: '15px' }}>
                <Link href="/timeline" style={{ textDecoration: 'none', color: '#333' }}>
                  🕐 Memory Timeline
                </Link>
              </li>
            </ul>
          </nav>

          {/* Main Content */}
          <main style={{
            flex: 1,
            padding: '40px',
            maxWidth: '1200px'
          }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
