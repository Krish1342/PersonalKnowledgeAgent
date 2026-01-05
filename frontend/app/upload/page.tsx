'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { UploadResponse } from '@/lib/types'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorMessage from '@/components/ErrorMessage'

export default function UploadPage() {
  const [content, setContent] = useState('')
  const [title, setTitle] = useState('')
  const [source, setSource] = useState('')
  const [topic, setTopic] = useState('')
  const [tags, setTags] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!content.trim()) {
      setError('Please enter some content to upload')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await apiClient.upload({
        content: content.trim(),
        metadata: {
          title: title.trim() || undefined,
          source: source.trim() || undefined,
          topic: topic.trim() || undefined,
          tags: tags.trim() ? tags.split(',').map(t => t.trim()) : undefined
        }
      })

      setResult(response)
      
      // Clear form on success
      if (response.success) {
        setContent('')
        setTitle('')
        setSource('')
        setTopic('')
        setTags('')
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred while uploading')
      console.error('Upload error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ fontSize: '32px', marginBottom: '10px' }}>Upload Knowledge</h1>
      <p style={{ marginBottom: '30px', color: '#666' }}>
        Add new information to your knowledge base
      </p>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="content" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Content *
          </label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Enter the knowledge content you want to store..."
            rows={10}
            required
            style={{
              width: '100%',
              padding: '10px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '16px',
              fontFamily: 'inherit'
            }}
          />
          <p style={{ marginTop: '5px', fontSize: '14px', color: '#666' }}>
            {content.length} characters
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '20px',
          marginBottom: '20px'
        }}>
          <div>
            <label htmlFor="title" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Title
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Optional title"
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '16px'
              }}
            />
          </div>

          <div>
            <label htmlFor="source" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Source
            </label>
            <input
              id="source"
              type="text"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="e.g., Book title, URL"
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '16px'
              }}
            />
          </div>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '20px',
          marginBottom: '20px'
        }}>
          <div>
            <label htmlFor="topic" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Topic
            </label>
            <input
              id="topic"
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., Machine Learning"
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '16px'
              }}
            />
          </div>

          <div>
            <label htmlFor="tags" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Tags
            </label>
            <input
              id="tags"
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="Comma-separated tags"
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '16px'
              }}
            />
          </div>
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
          {loading ? 'Uploading...' : 'Upload Knowledge'}
        </button>
      </form>

      {loading && <LoadingSpinner message="Uploading your knowledge..." />}

      {error && (
        <ErrorMessage 
          error={error}
          onRetry={() => {
            setError(null)
            handleSubmit(new Event('submit') as any)
          }}
        />
      )}

      {result && (
        <div style={{
          marginTop: '30px',
          padding: '20px',
          backgroundColor: result.success ? '#efe' : '#fee',
          border: `1px solid ${result.success ? '#cfc' : '#fcc'}`,
          borderRadius: '8px'
        }}>
          <h2 style={{ marginBottom: '10px', fontSize: '20px' }}>
            {result.success ? '✓ Upload Successful' : '✗ Upload Failed'}
          </h2>
          <p>{result.message}</p>
          
          {result.chunk_id && (
            <div style={{ marginTop: '10px' }}>
              <strong>Chunk ID:</strong> {result.chunk_id}
            </div>
          )}
          
          {result.quality_score !== undefined && (
            <div style={{ marginTop: '10px' }}>
              <strong>Quality Score:</strong> {result.quality_score.toFixed(1)}%
            </div>
          )}
        </div>
      )}
    </div>
  )
}
