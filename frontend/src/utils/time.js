/**
 * Converts an ISO 8601 timestamp to a human-readable relative string.
 * e.g. "2026-04-13T10:30:00Z" → "3h ago"
 */
export function timeAgo(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  if (isNaN(date)) return ''
  const diffMs  = Date.now() - date.getTime()
  const diffMin = Math.floor(diffMs / 60_000)
  if (diffMin < 1)  return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24)   return `${diffH}h ago`
  const diffD = Math.floor(diffH / 24)
  return `${diffD}d ago`
}

/**
 * Maps a topic string from the DynamoDB record to a CSS class suffix.
 * Used for category badge colour classes (cat-wp, cat-sci, etc.)
 */
export function topicClass(topic = '') {
  const map = {
    'World Politics': 'wp',
    'Science':        'sci',
    'Business':       'biz',
    'Technology':     'tec',
    'Health':         'hlt',
    'Environment':    'env',
    'Sports':         'spo',
    'Entertainment':  'ent',
  }
  return `cat-${map[topic] ?? 'biz'}`
}
