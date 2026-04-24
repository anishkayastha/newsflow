import { useState, useMemo, useEffect } from 'react'
import Header           from '../components/Header.jsx'
import DigestCard       from '../components/DigestCard.jsx'
import LoadingSkeleton  from '../components/LoadingSkeleton.jsx'
import PreferencesModal from '../components/PreferencesModal.jsx'
import KPIBar           from '../components/KPIBar.jsx'
import DateFilter       from '../components/DateFilter.jsx'
import { useDigest }    from '../hooks/useDigest.js'
import { TOPIC_META }   from '../hooks/usePreferences.js'

const INITIAL_LIMIT = 6   // stories shown per topic before "load more"
const LOAD_MORE_N   = 6   // additional stories loaded per click

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

export default function DigestPage({ user, signOut, theme, toggleTheme,
  selectedTopics, onUpdateTopics, onOpenSettings }) {
  const [prefsOpen,  setPrefsOpen]  = useState(false)
  const [dateFilter, setDateFilter] = useState(todayStr)
  // Per-topic visible count  { [topic]: number }
  const [visibleCounts, setVisibleCounts] = useState({})

  const { items, loading, error, lastUpdated, availDates, refresh } = useDigest(dateFilter)

  // As soon as availDates loads, if the current date has no data
  // fall back to the most recent date that does
  useEffect(() => {
    if (availDates.length === 0) return
    const sorted = [...availDates].sort((a, b) => b.localeCompare(a))
    if (!sorted.includes(dateFilter)) {
      setDateFilter(sorted[0])
    }
  }, [availDates])

  // Reset visible counts when date changes
  const handleDateChange = (date) => {
    setDateFilter(date)
    setVisibleCounts({})
  }

  const sections = useMemo(() => {
    return selectedTopics.map(topic => ({
      topic,
      stories: items.filter(i => i.topic === topic)  // no hard cap
    }))
  }, [items, selectedTopics])

  const totalStories = useMemo(
    () => sections.reduce((s, sec) => s + sec.stories.length, 0),
    [sections]
  )

  const email = user?.signInDetails?.loginId ?? user?.username ?? ''

  const getVisible = (topic, total) =>
    visibleCounts[topic] ?? Math.min(INITIAL_LIMIT, total)

  const loadMore = (topic) =>
    setVisibleCounts(prev => ({
      ...prev,
      [topic]: Math.min((prev[topic] ?? INITIAL_LIMIT) + LOAD_MORE_N,
                        sections.find(s => s.topic === topic)?.stories.length ?? INITIAL_LIMIT)
    }))

  const showAll = (topic) =>
    setVisibleCounts(prev => ({
      ...prev,
      [topic]: sections.find(s => s.topic === topic)?.stories.length ?? 999
    }))

  return (
    <div className="dashboard">
      <Header
        user={user}
        signOut={signOut}
        theme={theme}
        toggleTheme={toggleTheme}
        lastUpdated={lastUpdated}
        totalStories={totalStories}
        onOpenPrefs={() => setPrefsOpen(true)}
        onOpenSettings={onOpenSettings}
      />

      <main className="dashboard__main">
        <div className="dashboard__welcome">
          <div className="welcome__left">
            <p className="welcome__date">
              {new Date().toLocaleDateString('en', {
                weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
              }).toUpperCase()}
            </p>
            <h1 className="welcome__heading">
              Good {getTimeOfDay()}, <span className="welcome__name">{firstName(email)}</span>
            </h1>
          </div>
          <div className="welcome__right">
            {lastUpdated && (
              <p className="welcome__meta">
                Next digest delivery: <strong>{nextRun(lastUpdated)}</strong>
              </p>
            )}
          </div>
        </div>

        <KPIBar items={items} selectedTopics={selectedTopics} lastUpdated={lastUpdated} />

        <DateFilter
          selected={dateFilter}
          availDates={availDates}
          onChange={handleDateChange}
        />

        {loading && <LoadingSkeleton count={6} />}

        {!loading && error && (
          <div className="state-empty">
            <span className="state-empty__icon">⚡</span>
            <p>Could not load digest — {error}</p>
            <button className="retry-btn" onClick={refresh}>Try again</button>
          </div>
        )}

        {!loading && !error && totalStories === 0 && (
          <div className="state-empty">
            <span className="state-empty__icon">📋</span>
            <p>No stories found for {dateFilter}.</p>
            <p className="state-empty__sub">Try a different date or run the pipeline.</p>
          </div>
        )}

        {!loading && !error && sections.map(({ topic, stories }) => {
          if (stories.length === 0) return null
          const meta      = TOPIC_META[topic] ?? { icon: '📰', color: 'var(--accent-teal)', bg: 'transparent' }
          const visible   = getVisible(topic, stories.length)
          const remaining = stories.length - visible
          const shown     = stories.slice(0, visible)

          return (
            <section key={topic} className="topic-section"
              style={{ '--section-color': meta.color }}>
              <div className="topic-section__header">
                <div className="topic-section__left">
                  <span className="topic-section__icon">{meta.icon}</span>
                  <h2 className="topic-section__title">{topic}</h2>
                </div>
                <span className="topic-section__count">
                  {shown.length} of {stories.length} stor{stories.length === 1 ? 'y' : 'ies'}
                </span>
              </div>

              <div className="cards-grid">
                {shown.map((item, idx) => (
                  <DigestCard
                    key={item.cluster_id}
                    item={item}
                    rank={idx + 1}
                    topicColor={meta.color}
                  />
                ))}
              </div>

              {remaining > 0 && (
                <div className="load-more-row">
                  <button
                    className="load-more-btn"
                    onClick={() => loadMore(topic)}
                    style={{ '--btn-color': meta.color }}
                  >
                    Read {Math.min(remaining, LOAD_MORE_N)} more {topic.toLowerCase()} stories
                    <span className="load-more-btn__arrow">↓</span>
                  </button>
                  {remaining > LOAD_MORE_N && (
                    <button
                      className="load-more-btn load-more-btn--ghost"
                      onClick={() => showAll(topic)}
                      style={{ '--btn-color': meta.color }}
                    >
                      Show all {stories.length}
                    </button>
                  )}
                </div>
              )}
            </section>
          )
        })}
      </main>

      {prefsOpen && (
        <PreferencesModal
          currentTopics={selectedTopics}
          onSave={onUpdateTopics}
          onClose={() => setPrefsOpen(false)}
        />
      )}
    </div>
  )
}

function getTimeOfDay() {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
}

function firstName(email) {
  const name = email.split('@')[0].split('.')[0]
  return name.charAt(0).toUpperCase() + name.slice(1)
}

function nextRun(lastUpdated) {
  const next = new Date(lastUpdated)
  next.setHours(next.getHours() + 12)
  return next.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}