import Link from 'next/link'

export default function Home() {
  return (
    <div>
      <h1 style={{ fontSize: '32px', marginBottom: '20px' }}>
        Welcome to Personal Knowledge Agent
      </h1>
      
      <p style={{ marginBottom: '30px', lineHeight: '1.6' }}>
        An AI-powered system for managing and querying your personal knowledge base.
        The system uses advanced retrieval and reasoning techniques to provide grounded,
        accurate answers to your questions.
      </p>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '20px',
        marginTop: '40px'
      }}>
        <Link href="/query" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div style={{
            border: '1px solid #ddd',
            padding: '20px',
            borderRadius: '8px'
          }}>
            <h2 style={{ fontSize: '20px', marginBottom: '10px' }}>📝 Ask Questions</h2>
            <p>Query your knowledge base with natural language and get grounded answers with sources.</p>
          </div>
        </Link>

        <Link href="/upload" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div style={{
            border: '1px solid #ddd',
            padding: '20px',
            borderRadius: '8px'
          }}>
            <h2 style={{ fontSize: '20px', marginBottom: '10px' }}>📤 Upload Knowledge</h2>
            <p>Add new information to your knowledge base for future retrieval and reasoning.</p>
          </div>
        </Link>

        <Link href="/sources" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div style={{
            border: '1px solid #ddd',
            padding: '20px',
            borderRadius: '8px'
          }}>
            <h2 style={{ fontSize: '20px', marginBottom: '10px' }}>📚 View Sources</h2>
            <p>Browse and manage all the knowledge chunks stored in your database.</p>
          </div>
        </Link>

        <Link href="/timeline" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div style={{
            border: '1px solid #ddd',
            padding: '20px',
            borderRadius: '8px'
          }}>
            <h2 style={{ fontSize: '20px', marginBottom: '10px' }}>🕐 Memory Timeline</h2>
            <p>View the history of queries, uploads, and system learning over time.</p>
          </div>
        </Link>
      </div>
    </div>
  )
}
