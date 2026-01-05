'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import { QueryResponse, ReasoningMode } from '@/lib/types'
import QueryResult from '@/components/QueryResult'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorMessage from '@/components/ErrorMessage'

export default function QueryPage() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<'eli5' | 'exam' | 'research' | 'comparison'>('research')
  const [modes, setModes] = useState<ReasoningMode[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Load available modes on mount
  useEffect(() => {
    apiClient.getReasoningModes()
      .then(data => setModes(data.modes))
      .catch(err => console.error('Failed to load modes:', err))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!query.trim()) {
      setError('Please enter a query')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await apiClient.query({
        query: query.trim(),
        mode,
        user_id: 'demo_user',
        session_id: `session_${Date.now()}`
      })

      setResult(response)
    } catch (err: any) {
      setError(err.message || 'An error occurred while processing your query')
      console.error('Query error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ fontSize: '32px', marginBottom: '10px' }}>Ask Questions</h1>
      <p style={{ marginBottom: '30px', color: '#666' }}>
        Query your knowledge base with natural language
      </p>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="query" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Your Question
          </label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What would you like to know?"
            rows={4}
            style={{
              width: '100%',
              padding: '10px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '16px'
            }}
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="mode" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Reasoning Mode
          </label>
          <select
            id="mode"
            value={mode}
            onChange={(e) => setMode(e.target.value as any)}
            style={{
              padding: '10px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '16px'
            }}
          >
            {modes.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
          <p style={{ marginTop: '5px', fontSize: '14px', color: '#666' }}>
            {modes.find(m => m.id === mode)?.description}
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: '12px 24px',
            backgroundColor: loading ? '#ccc' : '#0070f3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Processing...' : 'Ask Question'}
        </button>
      </form>

      {loading && <LoadingSpinner message="Processing your query..." />}

      {error && (
        <ErrorMessage 
          error={error}
          onRetry={() => {
            setError(null)
            handleSubmit(new Event('submit') as any)
          }}
        />
      )}

      {!loading && result && <QueryResult result={result} />}
    </div>
  )
}
