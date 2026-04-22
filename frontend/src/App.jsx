import { Authenticator, useAuthenticator, View, Heading, Text } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'
import DigestPage from './pages/DigestPage.jsx'

// Custom Authenticator header showing the NewsFlow brand
function AuthHeader() {
  return (
    <View textAlign="center" padding="1.5rem 0 0.5rem">
      <Heading level={3} style={{ fontWeight: 600, letterSpacing: '-0.03em' }}>
        NewsFlow
      </Heading>
      <Text variation="tertiary" style={{ fontSize: '13px', marginTop: 4 }}>
        Sign in to access your digest
      </Text>
    </View>
  )
}

export default function App() {
  return (
    <Authenticator components={{ Header: AuthHeader }} variation="modal">
      {({ signOut, user }) => <DigestPage user={user} signOut={signOut} />}
    </Authenticator>
  )
}
