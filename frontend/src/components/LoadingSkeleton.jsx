export default function LoadingSkeleton({ count = 6 }) {
  return (
    <div className="skeleton-wrap">
      {Array.from({ length: 2 }).map((_, si) => (
        <div key={si} className="skeleton-section">
          <div className="skeleton-section-header">
            <div className="skeleton-block skeleton-block--icon" />
            <div className="skeleton-block skeleton-block--title" />
          </div>
          <div className="cards-grid">
            {Array.from({ length: Math.ceil(count / 2) }).map((_, i) => (
              <div key={i} className="skeleton-card">
                <div className="skeleton-block" style={{ width: '35%', height: '12px' }} />
                <div className="skeleton-block" style={{ width: '100%', height: '12px', marginTop: '14px' }} />
                <div className="skeleton-block" style={{ width: '95%', height: '12px', marginTop: '7px' }} />
                <div className="skeleton-block" style={{ width: '78%', height: '12px', marginTop: '7px' }} />
                <div className="skeleton-block" style={{ width: '55%', height: '12px', marginTop: '7px' }} />
                <div className="skeleton-block" style={{ width: '40%', height: '10px', marginTop: '18px' }} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}