import { useState, useMemo } from 'react'
import Header          from '../components/Header.jsx'
import CategoryFilter  from '../components/CategoryFilter.jsx'
import DigestCard      from '../components/DigestCard.jsx'
import LoadingSkeleton from '../components/LoadingSkeleton.jsx'
import { useDigest }   from '../hooks/useDigest.js'

/**
 * Main digest page.
 * - Fetches all passed-gate summaries from API Gateway via useDigest
 * - Filters client-side by selected category (instant, no extra API call)
 * - Shows skeleton while loading, error state on failure, empty state when filtered to zero
 */
export default function DigestPage({ user, signOut }) {
  const [activeCategory, setActiveCategory] = useState('All')
  const { items, loading, error, lastUpdated, refresh } = useDigest()

  // Count per category for filter badge numbers
  const counts = useMemo(() => {
    const map = {}
    items.forEach(item => {
      const t = item.topic ?? 'General'
      map[t] = (map[t] ?? 0) + 1
    })
    return map
  }, [items])

  // Client-side category filter — sorting already done in hook
  const filtered = useMemo(() => {
    if (activeCategory === 'All') return items
    return items.filter(item => item.topic === activeCategory)
  }, [items, activeCategory])

  return (
    <div className="page-shell">
      <Header
        user={user}
        signOut={signOut}
        itemCount={items.length}
        lastUpdated={lastUpdated}
      />

      <CategoryFilter
        active={activeCategory}
        onChange={setActiveCategory}
        counts={counts}
      />

      {/* Loading state */}
      {loading && <LoadingSkeleton count={8} />}

      {/* Error state */}
      {!loading && error && (
        <div className="digest-grid">
          <div className="state-box">
            <p>Could not load digest — {error}</p>
            <button className="retry-btn" onClick={refresh}>Try again</button>
          </div>
        </div>
      )}

      {/* Empty filtered state */}
      {!loading && !error && filtered.length === 0 && (
        <div className="digest-grid">
          <div className="state-box">
            <p>No events in <strong>{activeCategory}</strong> yet.</p>
            <button className="retry-btn" onClick={() => setActiveCategory('All')}>
              Show all categories
            </button>
          </div>
        </div>
      )}

      {/* Digest grid */}
      {!loading && !error && filtered.length > 0 && (
        <div className="digest-grid">
          {filtered.map((item, index) => (
            <DigestCard
              key={item.cluster_id}
              item={item}
              rank={index + 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}
