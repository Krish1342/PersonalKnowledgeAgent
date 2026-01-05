'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import { MemoryEvent } from '@/lib/types'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorMessage from '@/components/ErrorMessage'

export default function TimelinePage() {
  const [events, setEvents] = useState<MemoryEvent[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(7)

  const loadTimeline = async (daysParam: number) => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.getMemoryTimeline(daysParam)
      setEvents(response.events)
      setStats(response.stats)
    } catch (err: any) {
      setError(err.message || 'Failed to load timeline')
      console.error('Load timeline error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTimeline(days)
  }, [days])

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'query': return '❓'
      case 'upload': return '📤'
      case 'update': return '🔄'
      case 'prune': return '✂️'
      default: return '📌'
    }
  }

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'query': return '#e3f2fd'
      case 'upload': return '#f3e5f5'
      case 'update': return '#fff3e0'
      case 'prune': return '#ffebee'
      default: return '#f5f5f5'
    }
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString()
  }

  return (
    <div>
      <h1 style={{ fontSize: '32px', marginBottom: '10px' }}>Memory Timeline</h1>
      <p style={{ marginBottom: '30px', color: '#666' }}>
        View the history of queries, uploads, and system learning
      </p>

      <div style={{ marginBottom: '30px' }}>
        <label htmlFor="days" style={{ marginRight: '10px', fontWeight: 'bold' }}>
          Time Range:
        </label>
        <select
          id="days"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          style={{
            padding: '8px 12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontSize: '16px'
          }}
        >
          <option value={1}>Last 24 hours</option>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {stats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '15px',
          marginBottom: '30px'
        }}>
          {Object.entries(stats).map(([key, value]) => (
            <div key={key} style={{
              padding: '15px',
              backgroundColor: '#f9f9f9',
              border: '1px solid #ddd',
              borderRadius: '8px'
            }}>
              <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px' }}>
                {key.replace(/_/g, ' ').toUpperCase()}
              </div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
                {typeof value === 'number' ? value.toFixed(1) : value}
              </div>
            </div>
          ))}
        </div>
      )}

      {loading && <LoadingSpinner message="Loading timeline..." />}

      {error && <ErrorMessage error={error} onRetry={() => loadTimeline(days)} />}

      {!loading && !error && events.length === 0 && (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          backgroundColor: '#f9f9f9',
          border: '1px solid #ddd',
          borderRadius: '8px'
        }}>
          <p>No events found in the selected time range.</p>
        </div>
      )}

      {!loading && events.length > 0 && (
        <div style={{ position: 'relative' }}>
          {/* Timeline line */}
          <div style={{
            position: 'absolute',
            left: '20px',
            top: '10px',
            bottom: '10px',
            width: '2px',
            backgroundColor: '#ddd'
          }} />

          {/* Events */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {events.map((event) => (
              <div key={event.id} style={{
                position: 'relative',
                paddingLeft: '60px'
              }}>
                {/* Timeline dot */}
                <div style={{
                  position: 'absolute',
                  left: '10px',
                  top: '10px',
                  width: '22px',
                  height: '22px',
                  borderRadius: '50%',
                  backgroundColor: getEventColor(event.event_type),
                  border: '2px solid #ddd',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px'
                }}>
                  {getEventIcon(event.event_type)}
                </div>

                {/* Event card */}
                <div style={{
                  padding: '15px',
                  backgroundColor: 'white',
                  border: '1px solid #ddd',
                  borderRadius: '8px'
                }}>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'start',
                    marginBottom: '8px'
                  }}>
                    <div>
                      <span style={{
                        display: 'inline-block',
                        padding: '4px 8px',
                        fontSize: '12px',
                        backgroundColor: getEventColor(event.event_type),
                        borderRadius: '4px',
                        marginRight: '10px'
                      }}>
                        {event.event_type.toUpperCase()}
                      </span>
                      <span style={{ fontSize: '14px', color: '#666' }}>
                        {formatDate(event.timestamp)}
                      </span>
                    </div>
                  </div>

                  <div style={{ fontSize: '16px', marginBottom: '8px' }}>
                    {event.description}
                  </div>

                  {event.metadata && Object.keys(event.metadata).length > 0 && (
                    <details style={{ marginTop: '10px' }}>
                      <summary style={{
                        cursor: 'pointer',
                        fontSize: '14px',
                        color: '#666'
                      }}>
                        Additional Details
                      </summary>
                      <div style={{
                        marginTop: '10px',
                        padding: '10px',
                        backgroundColor: '#f9f9f9',
                        borderRadius: '4px',
                        fontSize: '14px'
                      }}>
                        <pre style={{
                          margin: 0,
                          whiteSpace: 'pre-wrap',
                          wordWrap: 'break-word'
                        }}>
                          {JSON.stringify(event.metadata, null, 2)}
                        </pre>
                      </div>
                    </details>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
