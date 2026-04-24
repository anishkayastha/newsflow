import { useState } from 'react'

export default function SettingsPage({ user, signOut, theme, toggleTheme, onBack }) {
  const email    = user?.signInDetails?.loginId ?? user?.username ?? ''
  const initials = email ? email[0].toUpperCase() : 'U'

  const [displayName, setDisplayName] = useState(
    email.split('@')[0].split('.').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
  )
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="settings-page">
      <header className="app-header">
        <div className="app-header__inner">
          <div className="app-header__brand">
            <button className="back-btn" onClick={onBack}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5M12 5l-7 7 7 7"/>
              </svg>
              Back
            </button>
            <span className="app-header__logo">News<span className="app-header__logo-accent">Flow</span></span>
          </div>
          <div className="app-header__right">
            <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </header>

      <main className="settings-main">
        <div className="settings-content">
          <h1 className="settings-title">Settings</h1>
          <p className="settings-sub">Manage your account and preferences</p>

          {/* Profile section */}
          <div className="settings-card">
            <h2 className="settings-card__title">Profile</h2>

            <div className="settings-avatar-row">
              <div className="settings-avatar">{initials}</div>
              <div>
                <p className="settings-avatar-name">{displayName}</p>
                <p className="settings-avatar-email">{email}</p>
              </div>
            </div>

            <div className="settings-field">
              <label className="settings-label">Display name</label>
              <input
                className="settings-input"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                placeholder="Your name"
              />
            </div>

            <div className="settings-field">
              <label className="settings-label">Email</label>
              <input className="settings-input settings-input--readonly"
                value={email} readOnly />
              <p className="settings-hint">Email is managed by your Cognito account</p>
            </div>

            <button className="settings-save-btn" onClick={handleSave}>
              {saved ? '✓ Saved' : 'Save changes'}
            </button>
          </div>

          {/* Appearance */}
          <div className="settings-card">
            <h2 className="settings-card__title">Appearance</h2>
            <div className="settings-row">
              <div>
                <p className="settings-row__label">Theme</p>
                <p className="settings-row__sub">Currently {theme} mode</p>
              </div>
              <button className="theme-toggle-btn" onClick={toggleTheme}>
                {theme === 'dark' ? '☀️ Light mode' : '🌙 Dark mode'}
              </button>
            </div>
          </div>

          {/* Account */}
          <div className="settings-card">
            <h2 className="settings-card__title">Account</h2>
            <div className="settings-row">
              <div>
                <p className="settings-row__label">Sign out</p>
                <p className="settings-row__sub">Sign out from all devices</p>
              </div>
              <button className="settings-signout-btn" onClick={signOut}>
                Sign out
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
