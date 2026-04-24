import { timeAgo } from '../utils/time.js'

function scoreLabel(score) {
  if (score >= 0.85) return { label: 'Top story',   color: 'var(--accent-teal)' }
  if (score >= 0.70) return { label: 'High impact', color: 'var(--accent-orange)' }
  if (score >= 0.55) return { label: 'Notable',     color: 'var(--accent-purple)' }
  return                     { label: 'Story',       color: 'var(--text-3)' }
}

export default function DigestCard({ item, rank, topicColor }) {
  const score   = parseFloat(item.score ?? 0)
  const sources = Array.isArray(item.sources) ? item.sources : []
  const ago     = timeAgo(item.generated_at)
  const color   = topicColor ?? 'var(--accent-teal)'
  const { label: sLabel, color: sBadgeColor } = scoreLabel(score)

  const sourceUrl   = item.top_source_url   ?? ''
  const sourceTitle = item.top_source_title ?? ''
  const sourceName  = item.top_source_name  ?? sources[0] ?? ''

  return (
    <article className="digest-card">
      <div className="digest-card__accent" style={{ background: color }} />

      <div className="digest-card__body">

        {/* Score badge only — no rank, no redundant topic label */}
        <div className="digest-card__ai-header">
          <span className="digest-card__score-badge" style={{ color: sBadgeColor }}>
            {sLabel}
          </span>
        </div>

        {/* Headline — from top authority article title */}
        {sourceTitle && (
          <h3 className="digest-card__headline">{sourceTitle}</h3>
        )}

        {/* Summary */}
        <p className="digest-card__summary">{item.summary}</p>

        {/* Metrics */}
        <div className="digest-card__metrics">
          <div className="digest-card__metric">
            <span className="digest-card__metric-val">{score.toFixed(3)}</span>
            <span className="digest-card__metric-lbl">score</span>
          </div>
          <div className="digest-card__metric">
            <span className="digest-card__metric-val">{item.article_count ?? '—'}</span>
            <span className="digest-card__metric-lbl">articles</span>
          </div>
          <div className="digest-card__metric">
            <span className="digest-card__metric-val">{sources.length}</span>
            <span className="digest-card__metric-lbl">sources</span>
          </div>
          <div className="digest-card__metric">
            <span className="digest-card__metric-val">
              {parseFloat(item.relevance ?? 0).toFixed(2)}
            </span>
            <span className="digest-card__metric-lbl">relevance</span>
          </div>
        </div>

        {/* Footer */}
        <footer className="digest-card__footer">
          <div className="digest-card__sources">
            {sources.slice(0, 3).map((s, i) => (
              <span key={i} className="source-chip">{s}</span>
            ))}
            {sources.length > 3 && (
              <span className="source-chip source-chip--more">+{sources.length - 3}</span>
            )}
          </div>
          <div className="digest-card__footer-right">
            <span className="digest-card__time">{ago}</span>
            {sourceUrl ? (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="read-source-btn"
                style={{ '--btn-color': color }}
                title={sourceTitle || `Read from ${sourceName}`}
                onClick={e => e.stopPropagation()}
              >
                Read source
                <svg width="10" height="10" viewBox="0 0 12 12" fill="none" aria-hidden>
                  <path d="M1 11L11 1M11 1H4M11 1V8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                </svg>
              </a>
            ) : (
              <span className="read-source-btn read-source-btn--unavailable">
                No link yet
              </span>
            )}
          </div>
        </footer>
      </div>
    </article>
  )
}