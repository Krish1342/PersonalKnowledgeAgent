/**
 * Reusable component for displaying query results
 */

import { QueryResponse } from '@/lib/types'

interface QueryResultProps {
  result: QueryResponse
}

export default function QueryResult({ result }: QueryResultProps) {
  return (
    <div style={{
      marginTop: '40px',
      padding: '20px',
      backgroundColor: '#f9f9f9',
      border: '1px solid #ddd',
      borderRadius: '8px'
    }}>
      {/* Query Info */}
      <div style={{ marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid #ddd' }}>
        <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px' }}>
          Query
        </div>
        <div style={{ fontSize: '16px', fontWeight: 'bold' }}>
          {result.query}
        </div>
      </div>

      {/* Answer */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ fontSize: '14px', color: '#666', marginBottom: '10px', fontWeight: 'bold' }}>
          Answer
        </div>
        <div style={{
          lineHeight: '1.8',
          fontSize: '16px',
          whiteSpace: 'pre-wrap'
        }}>
          {result.answer}
        </div>
      </div>

      {/* Metrics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: '15px',
        marginBottom: '20px',
        padding: '15px',
        backgroundColor: 'white',
        borderRadius: '4px'
      }}>
        <div>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
            Confidence
          </div>
          <div style={{
            fontSize: '24px',
            fontWeight: 'bold',
            color: result.confidence >= 80 ? '#0a0' : result.confidence >= 60 ? '#f90' : '#f00'
          }}>
            {result.confidence.toFixed(1)}%
          </div>
        </div>

        <div>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
            Sources
          </div>
          <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
            {result.sources_count}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
            Validation
          </div>
          <div style={{
            fontSize: '18px',
            fontWeight: 'bold',
            color: result.validation_passed ? '#0a0' : '#f00'
          }}>
            {result.validation_passed ? '✓ Passed' : '✗ Failed'}
          </div>
        </div>

        <div>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
            Processing Time
          </div>
          <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
            {result.processing_time_ms.toFixed(0)}ms
          </div>
        </div>
      </div>

      {/* Citations */}
      {result.citations && result.citations.length > 0 && (
        <details style={{ marginTop: '20px' }}>
          <summary style={{
            cursor: 'pointer',
            fontWeight: 'bold',
            padding: '10px',
            backgroundColor: 'white',
            borderRadius: '4px',
            border: '1px solid #ddd'
          }}>
            📚 Citations ({result.citations.length})
          </summary>
          <div style={{ marginTop: '10px' }}>
            {result.citations.map((citation, idx) => (
              <div key={idx} style={{
                padding: '15px',
                marginTop: '10px',
                backgroundColor: 'white',
                border: '1px solid #ddd',
                borderRadius: '4px'
              }}>
                <div style={{
                  fontSize: '12px',
                  color: '#0070f3',
                  marginBottom: '8px',
                  fontWeight: 'bold'
                }}>
                  Source {idx + 1}: {citation.source || citation.chunk_id}
                </div>
                <div style={{
                  fontSize: '14px',
                  lineHeight: '1.6',
                  fontStyle: 'italic',
                  color: '#333'
                }}>
                  "{citation.text}"
                </div>
                {citation.confidence && (
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                    Confidence: {citation.confidence.toFixed(1)}%
                  </div>
                )}
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Reasoning Steps */}
      {result.reasoning_steps && result.reasoning_steps.length > 0 && (
        <details style={{ marginTop: '20px' }}>
          <summary style={{
            cursor: 'pointer',
            fontWeight: 'bold',
            padding: '10px',
            backgroundColor: 'white',
            borderRadius: '4px',
            border: '1px solid #ddd'
          }}>
            🧠 Reasoning Steps ({result.reasoning_steps.length})
          </summary>
          <ol style={{ marginTop: '10px', paddingLeft: '20px' }}>
            {result.reasoning_steps.map((step) => (
              <li key={step.step_number} style={{
                marginTop: '10px',
                padding: '10px',
                backgroundColor: 'white',
                borderRadius: '4px',
                lineHeight: '1.6'
              }}>
                {step.content}
              </li>
            ))}
          </ol>
        </details>
      )}

      {/* Suggestions */}
      {result.suggestions && result.suggestions.length > 0 && (
        <div style={{
          marginTop: '20px',
          padding: '15px',
          backgroundColor: '#fff9e6',
          border: '1px solid #ffd700',
          borderRadius: '4px'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '10px' }}>
            💡 Suggestions for Improvement
          </div>
          <ul style={{ marginTop: '5px', paddingLeft: '20px' }}>
            {result.suggestions.map((suggestion, idx) => (
              <li key={idx} style={{ marginTop: '5px' }}>
                {suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Knowledge Gaps */}
      {result.knowledge_gaps && result.knowledge_gaps.length > 0 && (
        <div style={{
          marginTop: '20px',
          padding: '15px',
          backgroundColor: '#ffe6e6',
          border: '1px solid #ffcccc',
          borderRadius: '4px'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '10px' }}>
            ⚠️ Knowledge Gaps Detected
          </div>
          <ul style={{ marginTop: '5px', paddingLeft: '20px' }}>
            {result.knowledge_gaps.map((gap, idx) => (
              <li key={idx} style={{ marginTop: '5px' }}>
                {gap}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Metadata */}
      <div style={{
        marginTop: '20px',
        padding: '10px',
        backgroundColor: '#f0f0f0',
        borderRadius: '4px',
        fontSize: '12px',
        color: '#666'
      }}>
        <div>Query ID: {result.query_id}</div>
        {result.session_id && <div>Session ID: {result.session_id}</div>}
        <div>Mode: {result.mode}</div>
        <div>Timestamp: {new Date(result.timestamp).toLocaleString()}</div>
      </div>
    </div>
  )
}
