import { useState } from 'react'
import { ALL_TOPICS, TOPIC_META } from '../hooks/usePreferences.js'

export default function OnboardingPage({ onComplete }) {
  const [selected, setSelected] = useState([])

  const toggle = (topic) => {
    setSelected(prev =>
      prev.includes(topic)
        ? prev.filter(t => t !== topic)
        : [...prev, topic]
    )
  }

  const handleStart = () => {
    if (selected.length > 0) onComplete(selected)
  }

  return (
    <div className="onboarding">
      <div className="onboarding-glow" />

      <div className="onboarding-inner">
        <header className="onboarding-header">
          <div className="onboarding-logo">NewsFlow</div>
          <h1 className="onboarding-title">
            What's your<br />
            <em>world?</em>
          </h1>
          <p className="onboarding-sub">
            Choose the topics that shape your daily digest.<br />
            We'll surface the most important stories — just for you.
          </p>
        </header>

        <div className="topic-grid">
          {ALL_TOPICS.map((topic, i) => {
            const meta = TOPIC_META[topic]
            const isSelected = selected.includes(topic)
            return (
              <button
                key={topic}
                className={`topic-card ${isSelected ? 'topic-card--selected' : ''}`}
                onClick={() => toggle(topic)}
                style={{
                  '--topic-color': meta.color,
                  '--topic-glow': meta.glow,
                  '--topic-bg': meta.bg,
                  animationDelay: `${i * 0.07}s`,
                }}
                aria-pressed={isSelected}
              >
                <span className="topic-card__icon">{meta.icon}</span>
                <span className="topic-card__name">{topic}</span>
                <span className="topic-card__desc">{meta.desc}</span>
                <span className="topic-card__check" aria-hidden>
                  {isSelected ? '✓' : ''}
                </span>
              </button>
            )
          })}
        </div>

        <footer className="onboarding-footer">
          <span className="onboarding-count">
            {selected.length === 0
              ? 'Select at least one topic'
              : `${selected.length} topic${selected.length > 1 ? 's' : ''} selected`}
          </span>
          <button
            className="start-btn"
            onClick={handleStart}
            disabled={selected.length === 0}
          >
            Start Reading
            <span className="start-btn__arrow">→</span>
          </button>
        </footer>
      </div>
    </div>
  )
}
