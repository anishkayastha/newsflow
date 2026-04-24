import { useMemo } from 'react'

export default function KPIBar({ items, selectedTopics, lastUpdated }) {
  const stats = useMemo(() => {
    const totalSources = items.reduce((sum, item) => {
      return sum + (Array.isArray(item.sources) ? item.sources.length : 0)
    }, 0)
    const uniqueSources = new Set(
      items.flatMap(item => Array.isArray(item.sources) ? item.sources : [])
    ).size
    const topicsWithData = selectedTopics.filter(t =>
      items.some(i => i.topic === t)
    ).length

    const avgScore = items.length
      ? (items.reduce((s, i) => s + parseFloat(i.score || 0), 0) / items.length).toFixed(3)
      : '0.000'

    return {
      stories:     items.length,
      sources:     uniqueSources,
      topics:      topicsWithData,
      avgScore,
    }
  }, [items, selectedTopics])

  const nextRun = useMemo(() => {
    if (!lastUpdated) return '—'
    const next = new Date(lastUpdated)
    next.setHours(next.getHours() + 12)
    return next.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }, [lastUpdated])

  const kpis = [
    { label: 'Stories today',    value: stats.stories,  sub: 'event clusters',      accent: 'teal' },
    { label: 'Topics active',    value: stats.topics,   sub: `of ${selectedTopics.length} selected`, accent: 'orange' },
    { label: 'Sources monitored',value: stats.sources,  sub: 'unique outlets',      accent: 'purple' },
    { label: 'Next digest',      value: nextRun,        sub: 'approx. refresh time',accent: 'green' },
  ]

  return (
    <div className="kpi-bar">
      {kpis.map(({ label, value, sub, accent }) => (
        <div key={label} className={`kpi-card kpi-card--${accent}`}>
          <div className="kpi-card__value">{value}</div>
          <div className="kpi-card__label">{label}</div>
          <div className="kpi-card__sub">{sub}</div>
        </div>
      ))}
    </div>
  )
}