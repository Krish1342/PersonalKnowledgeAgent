'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import { Chunk } from '@/lib/types'
import ChunkCard from '@/components/ChunkCard'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorMessage from '@/components/ErrorMessage'

export default function SourcesPage() {
  const [chunks, setChunks] = useState<Chunk[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const loadChunks = async (pageNum: number) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.getChunks(pageNum, 20)
      setChunks(response.chunks)
      setTotalPages(Math.ceil(response.total / response.page_size))
    } catch (err: any) {
      setError(err.message || 'Failed to load sources')
      console.error('Load chunks error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadChunks(page)
  }, [page])

  const handleDelete = async (chunkId: string) => {
    if (!confirm('Are you sure you want to delete this chunk?')) {
      return
    }

    try {
      await apiClient.deleteChunk(chunkId)
      // Reload current page
      loadChunks(page)
    } catch (err: any) {
      alert(`Failed to delete: ${err.message}`)
    }
  }

  return (
    <div>
      <h1 style={{ fontSize: '32px', marginBottom: '10px' }}>View Sources</h1>
      <p style={{ marginBottom: '30px', color: '#666' }}>
        Browse and manage knowledge chunks in your database
      </p>

      {loading && <LoadingSpinner message="Loading sources..." />}

      {error && <ErrorMessage error={error} onRetry={() => loadChunks(page)} />}

      {!loading && !error && chunks.length === 0 && (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          backgroundColor: '#f9f9f9',
          border: '1px solid #ddd',
          borderRadius: '8px'
        }}>
          <p>No sources found. Upload some knowledge to get started!</p>
        </div>
      )}

      {!loading && chunks.length > 0 && (
        <div>
          <div style={{ marginBottom: '20px' }}>
            <strong>Total Sources:</strong> {chunks.length}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {chunks.map((chunk) => (
              <ChunkCard 
                key={chunk.id} 
                chunk={chunk} 
                onDelete={handleDelete}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{
              marginTop: '30px',
              display: 'flex',
              justifyContent: 'center',
              gap: '10px',
              alignItems: 'center'
            }}>
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{
                  padding: '10px 20px',
                  fontSize: '16px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  backgroundColor: page === 1 ? '#f5f5f5' : 'white',
                  cursor: page === 1 ? 'not-allowed' : 'pointer'
                }}
              >
                Previous
              </button>
              
              <span style={{ fontSize: '16px' }}>
                Page {page} of {totalPages}
              </span>

              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                style={{
                  padding: '10px 20px',
                  fontSize: '16px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  backgroundColor: page === totalPages ? '#f5f5f5' : 'white',
                  cursor: page === totalPages ? 'not-allowed' : 'pointer'
                }}
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
