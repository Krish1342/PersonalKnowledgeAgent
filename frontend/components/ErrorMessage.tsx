/**
 * Error display component
 */

interface ErrorMessageProps {
  error: string
  onRetry?: () => void
}

export default function ErrorMessage({ error, onRetry }: ErrorMessageProps) {
  return (
    <div style={{
      padding: '20px',
      backgroundColor: '#fee',
      border: '1px solid #fcc',
      borderRadius: '8px',
      color: '#c00'
    }}>
      <div style={{ display: 'flex', alignItems: 'start', gap: '10px' }}>
        <div style={{ fontSize: '24px' }}>⚠️</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '16px' }}>
            Error
          </div>
          <div style={{ lineHeight: '1.6' }}>
            {error}
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              style={{
                marginTop: '15px',
                padding: '8px 16px',
                backgroundColor: '#fff',
                color: '#c00',
                border: '1px solid #fcc',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold'
              }}
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
