import { timeAgo, topicClass } from '../utils/time.js'

/**
 * Single event card in the digest grid.
 *
 * DynamoDB item shape (from consumer Lambda):
 * {
 *   cluster_id:    string
 *   summary:       string
 *   score:         string   ("0.9370")
 *   relevance:     string
 *   authority:     string
 *   recency:       string
 *   topic:         string   ("World Politics")
 *   article_count: number
 *   sources:       string[] (source names)
 *   passed_gate:   boolean
 *   generated_at:  string   (ISO timestamp)
 * }
 */
export default function DigestCard({ item, rank }) {
  const score       = parseFloat(item.score ?? 0)
  const scorePct    = Math.round(score * 100)
  const sourceCount = Array.isArray(item.sources) ? item.sources.length : 0
  const catClass    = topicClass(item.topic)
  const ago         = timeAgo(item.generated_at)

  return (
    <article className="digest-card">
      <div className="card-top">
        <span className="card-rank">#{rank}</span>

        <span className={`card-cat-badge ${catClass}`}>
          {item.topic ?? 'General'}
        </span>

        <div className="card-score-bar" title={`Importance score: ${score.toFixed(3)}`}>
          <div className="card-score-fill" style={{ width: `${scorePct}%` }} />
        </div>
      </div>

      <p className="card-summary">{item.summary}</p>

      <footer className="card-footer">
        <span className="card-meta">
          {sourceCount > 0 && `${sourceCount} sources`}
          {sourceCount > 0 && item.article_count > 0 && ' · '}
          {item.article_count > 0 && `${item.article_count} articles`}
        </span>
        <span className="card-score-num">
          {score.toFixed(3)}
          {ago && ` · ${ago}`}
        </span>
      </footer>
    </article>
  )
}
