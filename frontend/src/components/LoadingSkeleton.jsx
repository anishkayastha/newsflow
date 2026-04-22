/**
 * Renders N placeholder skeleton cards in a grid while the digest is loading.
 */
export default function LoadingSkeleton({ count = 8 }) {
  return (
    <div className="digest-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-card">
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <div className="skeleton" style={{ width: 20, height: 12, borderRadius: 3 }} />
            <div className="skeleton" style={{ width: 90, height: 18, borderRadius: 6 }} />
            <div className="skeleton" style={{ width: 44, height: 3, marginLeft: 'auto', borderRadius: 2 }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <div className="skeleton" style={{ width: '100%', height: 12, borderRadius: 3 }} />
            <div className="skeleton" style={{ width: '95%',  height: 12, borderRadius: 3 }} />
            <div className="skeleton" style={{ width: '80%',  height: 12, borderRadius: 3 }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <div className="skeleton" style={{ width: 100, height: 11, borderRadius: 3 }} />
            <div className="skeleton" style={{ width: 60, height: 11, borderRadius: 3, marginLeft: 'auto' }} />
          </div>
        </div>
      ))}
    </div>
  )
}
