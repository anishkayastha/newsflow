import { useState } from 'react'
import { Authenticator, View, Heading, Text } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'
import DigestPage     from './pages/DigestPage.jsx'
import OnboardingPage from './pages/OnboardingPage.jsx'
import SettingsPage   from './pages/SettingsPage.jsx'
import { usePreferences } from './hooks/usePreferences.js'
import { useTheme } from './hooks/useTheme.js'

function AuthHeader() {
  return (
    <View textAlign="center" padding="1.5rem 0 0.5rem">
      <Heading level={3} style={{ fontFamily: 'Fraunces, serif', fontWeight: 700,
        letterSpacing: '-0.02em', color: 'var(--text-1)' }}>
        NewsFlow
      </Heading>
      <Text variation="tertiary" style={{ fontSize: '13px', marginTop: 4, color: 'var(--text-3)' }}>
        Sign in to access your digest
      </Text>
    </View>
  )
}

function AppContent({ user, signOut }) {
  const userId = user?.userId ?? null
  const [page, setPage] = useState('digest') // 'digest' | 'settings'
  const { theme, toggleTheme } = useTheme()
  const { onboarded, topics, prefsLoading, completeOnboarding, updateTopics } =
    usePreferences(userId)

  if (prefsLoading) {
    return (
      <div className="prefs-loading">
        <div className="prefs-loading__spinner" />
        <p className="prefs-loading__text">Loading your preferences…</p>
      </div>
    )
  }

  if (!onboarded) {
    return <OnboardingPage onComplete={completeOnboarding} />
  }

  if (page === 'settings') {
    return (
      <SettingsPage
        user={user}
        signOut={signOut}
        theme={theme}
        toggleTheme={toggleTheme}
        onBack={() => setPage('digest')}
      />
    )
  }

  return (
    <DigestPage
      user={user}
      signOut={signOut}
      theme={theme}
      toggleTheme={toggleTheme}
      selectedTopics={topics}
      onUpdateTopics={updateTopics}
      onOpenSettings={() => setPage('settings')}
    />
  )
}

export default function App() {
  return (
    <Authenticator components={{ Header: AuthHeader }} variation="modal">
      {({ signOut, user }) => <AppContent user={user} signOut={signOut} />}
    </Authenticator>
  )
}