import { timeAgo } from '../utils/time.js'

/**
 * Top navigation bar.
 *
 * Props:
 *   user        — Cognito user object from Amplify Authenticator
 *   signOut     — Amplify signOut function
 *   itemCount   — total clusters loaded
 *   lastUpdated — Date object of last successful fetch
 */
export default function Header({ user, signOut, itemCount, lastUpdated }) {
  const email = user?.signInDetails?.loginId ?? user?.username ?? ''

  return (
    <header className="topbar">
      <span className="topbar-logo">
        News<span>Flow</span>
      </span>

      <div className="topbar-stats">
        {itemCount > 0 && (
          <>
            <b>{itemCount}</b> events
            <span className="topbar-dot">·</span>
          </>
        )}
        {lastUpdated && (
          <>
            updated <b>{timeAgo(lastUpdated.toISOString())}</b>
          </>
        )}
      </div>

      <div className="topbar-user">
        <span className="topbar-email">{email}</span>
        <button className="signout-btn" onClick={signOut}>
          Sign out
        </button>
      </div>
    </header>
  )
}
