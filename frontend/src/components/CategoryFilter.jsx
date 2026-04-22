const CATEGORIES = [
  'All',
  'World Politics',
  'Technology',
  'Business',
  'Science',
  'Health',
  'Environment',
  'Sports',
  'Entertainment',
]

/**
 * Horizontal pill-button category filter.
 *
 * Props:
 *   active   — currently selected category string
 *   onChange — callback(category: string)
 *   counts   — optional object mapping category → item count
 */
export default function CategoryFilter({ active, onChange, counts = {} }) {
  return (
    <div className="filter-bar" role="toolbar" aria-label="Filter by category">
      {CATEGORIES.map(cat => {
        const count = cat === 'All'
          ? Object.values(counts).reduce((a, b) => a + b, 0)
          : counts[cat]

        return (
          <button
            key={cat}
            className={`filter-btn${active === cat ? ' active' : ''}`}
            onClick={() => onChange(cat)}
            aria-pressed={active === cat}
          >
            {cat}
            {count > 0 && (
              <span style={{ marginLeft: 5, opacity: 0.55, fontSize: 10 }}>
                {count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
