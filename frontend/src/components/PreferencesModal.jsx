import { useState, useEffect } from 'react'
import { ALL_TOPICS, TOPIC_META } from '../hooks/usePreferences.js'

export default function PreferencesModal({ currentTopics, onSave, onClose }) {
  const [selected, setSelected] = useState(currentTopics)

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const toggle = (topic) => {
    setSelected(prev =>
      prev.includes(topic)
        ? prev.filter(t => t !== topic)
        : [...prev, topic]
    )
  }

  const handleSave = () => {
    if (selected.length > 0) {
      onSave(selected)
      onClose()
    }
  }

  return (
    <div className="prefs-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label="Edit topic preferences">
      <div className="prefs-panel" onClick={e => e.stopPropagation()}>
        <div className="prefs-panel__header">
          <div>
            <h2 className="prefs-panel__title">Your Topics</h2>
            <p className="prefs-panel__sub">Tap to add or remove topics from your digest</p>
          </div>
          <button className="prefs-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="prefs-topic-grid">
          {ALL_TOPICS.map((topic) => {
            const meta = TOPIC_META[topic]
            const isSelected = selected.includes(topic)
            return (
              <button
                key={topic}
                className={`prefs-topic-card ${isSelected ? 'prefs-topic-card--selected' : ''}`}
                onClick={() => toggle(topic)}
                style={{
                  '--topic-color': meta.color,
                  '--topic-glow': meta.glow,
                  '--topic-bg': meta.bg,
                }}
                aria-pressed={isSelected}
              >
                <span className="prefs-topic-card__icon">{meta.icon}</span>
                <span className="prefs-topic-card__name">{topic}</span>
                {isSelected && <span className="prefs-topic-card__check">✓</span>}
              </button>
            )
          })}
        </div>

        <div className="prefs-panel__footer">
          <span className="prefs-count">
            {selected.length} of {ALL_TOPICS.length} selected
          </span>
          <div className="prefs-actions">
            <button className="prefs-cancel" onClick={onClose}>Cancel</button>
            <button
              className="prefs-save"
              onClick={handleSave}
              disabled={selected.length === 0}
            >
              Save changes
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
