import { timeAgo } from '../utils/time.js'

export default function Header({ user, signOut, theme, toggleTheme, lastUpdated, totalStories, onOpenPrefs, onOpenSettings }) {
  const email    = user?.signInDetails?.loginId ?? user?.username ?? ''
  const initials = email ? email[0].toUpperCase() : 'U'

  return (
    <header className="app-header">
      <div className="app-header__inner">
        <div className="app-header__brand">
          <span className="app-header__logo">
            News<span className="app-header__logo-accent">Flow</span>
          </span>
          {lastUpdated && (
            <span className="app-header__pulse">
              <span className="pulse-dot" />
              Updated {timeAgo(lastUpdated.toISOString())}
            </span>
          )}
        </div>

        <nav className="app-header__nav">
          <button className="nav-btn nav-btn--active">Dashboard</button>
          <button className="nav-btn" onClick={onOpenPrefs}>Topics</button>
          <button className="nav-btn" onClick={onOpenSettings}>Settings</button>
        </nav>

        <div className="app-header__right">
          {totalStories > 0 && (
            <span className="app-header__count">{totalStories} stories</span>
          )}

          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === 'dark' ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="5"/>
                <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            )}
          </button>

          <div className="header-avatar" title={email}>{initials}</div>

          <button className="header-btn--signout" onClick={signOut}>Sign out</button>
        </div>
      </div>
    </header>
  )
}