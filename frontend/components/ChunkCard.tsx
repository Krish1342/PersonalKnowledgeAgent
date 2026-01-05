/**
 * Reusable component for displaying a knowledge chunk/source
 */

import { Chunk } from '@/lib/types'
import { useState } from 'react'

interface ChunkCardProps {
  chunk: Chunk
  onDelete?: (chunkId: string) => void
}

export default function ChunkCard({ chunk, onDelete }: ChunkCardProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div style={{
      border: '1px solid #ddd',
      borderRadius: '8px',
      padding: '20px',
      backgroundColor: 'white'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div style={{ flex: 1 }}>
          {/* Title */}
          <h3 style={{ fontSize: '20px', marginBottom: '12px', fontWeight: 'bold' }}>
            {chunk.metadata.title || 'Untitled'}
          </h3>
          
          {/* Metadata badges */}
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '10px',
            marginBottom: '15px',
            fontSize: '14px',
            color: '#666'
          }}>
            {chunk.metadata.source && (
              <span style={{
                padding: '4px 10px',
                backgroundColor: '#e3f2fd',
                borderRadius: '12px'
              }}>
                📄 {chunk.metadata.source}
              </span>
            )}
            {chunk.metadata.topic && (
              <span style={{
                padding: '4px 10px',
                backgroundColor: '#f3e5f5',
                borderRadius: '12px'
              }}>
                🏷️ {chunk.metadata.topic}
              </span>
            )}
            {chunk.metadata.quality_score !== undefined && (
              <span style={{
                padding: '4px 10px',
                backgroundColor: chunk.metadata.quality_score >= 80 ? '#e8f5e9' : '#fff3e0',
                borderRadius: '12px'
              }}>
                ⭐ Quality: {chunk.metadata.quality_score.toFixed(1)}%
              </span>
            )}
            {chunk.metadata.confidence !== undefined && (
              <span style={{
                padding: '4px 10px',
                backgroundColor: '#fce4ec',
                borderRadius: '12px'
              }}>
                🎯 Confidence: {chunk.metadata.confidence.toFixed(1)}%
              </span>
            )}
          </div>

          {/* Content preview/full */}
          <div style={{
            fontSize: '15px',
            lineHeight: '1.7',
            maxHeight: expanded ? 'none' : '120px',
            overflow: 'hidden',
            position: 'relative',
            color: '#333'
          }}>
            {chunk.content}
            {!expanded && chunk.content.length > 200 && (
              <div style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                height: '40px',
                background: 'linear-gradient(transparent, white)'
              }} />
            )}
          </div>

          {/* Expand/collapse button */}
          {chunk.content.length > 200 && (
            <button
              onClick={() => setExpanded(!expanded)}
              style={{
                marginTop: '12px',
                padding: '6px 14px',
                fontSize: '13px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                backgroundColor: 'white',
                cursor: 'pointer',
                color: '#0070f3'
              }}
            >
              {expanded ? 'Show Less ▲' : 'Show More ▼'}
            </button>
          )}

          {/* Tags */}
          {chunk.metadata.tags && chunk.metadata.tags.length > 0 && (
            <div style={{ marginTop: '15px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {chunk.metadata.tags.map((tag: string, idx: number) => (
                <span key={idx} style={{
                  display: 'inline-block',
                  padding: '4px 10px',
                  fontSize: '12px',
                  backgroundColor: '#e0e0e0',
                  borderRadius: '4px',
                  color: '#333'
                }}>
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Footer metadata */}
          <div style={{
            marginTop: '15px',
            paddingTop: '12px',
            borderTop: '1px solid #eee',
            fontSize: '12px',
            color: '#999',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '15px'
          }}>
            <span>ID: {chunk.id.substring(0, 12)}...</span>
            {chunk.metadata.access_count !== undefined && (
              <span>Accessed: {chunk.metadata.access_count} times</span>
            )}
            {chunk.metadata.created_at && (
              <span>Created: {new Date(chunk.metadata.created_at).toLocaleDateString()}</span>
            )}
            {chunk.metadata.last_accessed && (
              <span>Last accessed: {new Date(chunk.metadata.last_accessed).toLocaleDateString()}</span>
            )}
          </div>
        </div>

        {/* Delete button */}
        {onDelete && (
          <button
            onClick={() => onDelete(chunk.id)}
            style={{
              padding: '8px 14px',
              marginLeft: '20px',
              backgroundColor: '#f44336',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#d32f2f'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#f44336'}
          >
            Delete
          </button>
        )}
      </div>
    </div>
  )
}
