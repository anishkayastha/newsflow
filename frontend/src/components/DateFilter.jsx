import { useMemo, useState, useRef, useEffect } from 'react'

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function formatFull(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  })
}

function formatDisplay(dateStr) {
  if (!dateStr) return ''
  const d     = new Date(dateStr + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diff = Math.round((today - d) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return d.toLocaleDateString('en', { month: 'short', day: 'numeric' })
}

const MONTHS = ['January','February','March','April','May','June',
                'July','August','September','October','November','December']
const DAYS   = ['Su','Mo','Tu','We','Th','Fr','Sa']

export default function DateFilter({ selected, availDates, onChange }) {
  const [open,      setOpen]      = useState(false)
  const [viewYear,  setViewYear]  = useState(() => new Date().getFullYear())
  const [viewMonth, setViewMonth] = useState(() => new Date().getMonth())
  const wrapRef = useRef(null)
  const today   = todayStr()

  const availSet = useMemo(() => new Set(availDates), [availDates])

  // Close on outside click
  useEffect(() => {
    const h = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  // When opening, jump to the month of the selected date
  const handleOpen = () => {
    if (selected) {
      const d = new Date(selected + 'T00:00:00')
      setViewYear(d.getFullYear())
      setViewMonth(d.getMonth())
    }
    setOpen(o => !o)
  }

  // Build calendar grid for current view month
  const calendarDays = useMemo(() => {
    const firstDay = new Date(viewYear, viewMonth, 1).getDay()
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate()
    const cells = []
    for (let i = 0; i < firstDay; i++) cells.push(null)
    for (let d = 1; d <= daysInMonth; d++) {
      const mm  = String(viewMonth + 1).padStart(2, '0')
      const dd  = String(d).padStart(2, '0')
      cells.push(`${viewYear}-${mm}-${dd}`)
    }
    return cells
  }, [viewYear, viewMonth])

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1) }
    else setViewMonth(m => m - 1)
  }
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1) }
    else setViewMonth(m => m + 1)
  }

  // Disable future months
  const now = new Date()
  const isNextDisabled = viewYear > now.getFullYear() ||
    (viewYear === now.getFullYear() && viewMonth >= now.getMonth())

  const availSorted = useMemo(() =>
    [...availDates].sort((a, b) => b.localeCompare(a)), [availDates])

  return (
    <div className="date-filter">
      {/* Left: label + selected date text */}
      <div className="date-filter__left">
        <span className="date-filter__label">DIGEST DATE</span>
        <span className="date-filter__selected-display">{formatFull(selected)}</span>
      </div>

      {/* Right: quick chips + calendar trigger */}
      <div className="date-filter__right">
        {/* Quick access chips — only available dates */}
        <div className="date-filter__chips">
          {availSorted.slice(0, 5).map(day => (
            <button
              key={day}
              className={`date-chip ${day === selected ? 'date-chip--active' : ''}`}
              onClick={() => onChange(day)}
            >
              {formatDisplay(day)}
              <span className="date-chip__dot" />
            </button>
          ))}
        </div>

        {/* Calendar trigger */}
        <div className="cal-wrap" ref={wrapRef}>
          <button className="cal-trigger" onClick={handleOpen} aria-label="Open calendar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" aria-hidden>
              <rect x="3" y="4" width="18" height="18" rx="2"/>
              <path d="M16 2v4M8 2v4M3 10h18"/>
            </svg>
          </button>

          {open && (
            <div className="cal-panel">
              {/* Month navigation */}
              <div className="cal-header">
                <button className="cal-nav" onClick={prevMonth} aria-label="Previous month">‹</button>
                <span className="cal-month-label">{MONTHS[viewMonth]} {viewYear}</span>
                <button
                  className="cal-nav"
                  onClick={nextMonth}
                  disabled={isNextDisabled}
                  aria-label="Next month"
                >›</button>
              </div>

              {/* Day headers */}
              <div className="cal-grid">
                {DAYS.map(d => (
                  <span key={d} className="cal-day-header">{d}</span>
                ))}

                {/* Day cells */}
                {calendarDays.map((dateStr, i) => {
                  if (!dateStr) return <span key={`empty-${i}`} />

                  const isAvail   = availSet.has(dateStr)
                  const isSelected = dateStr === selected
                  const isFuture  = dateStr > today

                  return (
                    <button
                      key={dateStr}
                      className={[
                        'cal-day',
                        isSelected ? 'cal-day--selected' : '',
                        !isAvail || isFuture ? 'cal-day--disabled' : '',
                        isAvail && !isFuture ? 'cal-day--available' : '',
                      ].join(' ')}
                      onClick={() => {
                        if (isAvail && !isFuture) {
                          onChange(dateStr)
                          setOpen(false)
                        }
                      }}
                      disabled={!isAvail || isFuture}
                      title={isAvail ? formatFull(dateStr) : 'No digest for this date'}
                    >
                      {parseInt(dateStr.slice(8))}
                      {isAvail && !isFuture && (
                        <span className="cal-day__dot" />
                      )}
                    </button>
                  )
                })}
              </div>

              {/* Footer */}
              <div className="cal-footer">
                <span className="cal-legend">
                  <span className="cal-legend__dot" /> has digest
                </span>
                <button
                  className="cal-today-btn"
                  onClick={() => {
                    if (availSet.has(today)) { onChange(today); setOpen(false) }
                  }}
                  disabled={!availSet.has(today)}
                >
                  Today
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}