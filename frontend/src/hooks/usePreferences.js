import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchAuthSession } from 'aws-amplify/auth'
import axios from 'axios'
import { API_URL } from '../config.js'

const STORAGE_KEY = 'newsflow_prefs_v1'

export const ALL_TOPICS = [
  'World Politics',
  'Technology',
  'Business',
  'Science',
  'Health',
  'Environment',
  'Sports',
  'Entertainment',
]

export const TOPIC_META = {
  'World Politics': {
    icon: '🌍',
    desc: 'Global affairs, diplomacy & elections',
    color: '#e05a4a',
    glow: 'rgba(224,90,74,0.3)',
    bg: 'rgba(224,90,74,0.08)',
  },
  'Technology': {
    icon: '⚡',
    desc: 'AI, software, gadgets & startups',
    color: '#4a9ef5',
    glow: 'rgba(74,158,245,0.3)',
    bg: 'rgba(74,158,245,0.08)',
  },
  'Business': {
    icon: '📈',
    desc: 'Markets, companies & economics',
    color: '#f5a623',
    glow: 'rgba(245,166,35,0.3)',
    bg: 'rgba(245,166,35,0.08)',
  },
  'Science': {
    icon: '🔬',
    desc: 'Research, discoveries & space',
    color: '#9b6cf5',
    glow: 'rgba(155,108,245,0.3)',
    bg: 'rgba(155,108,245,0.08)',
  },
  'Health': {
    icon: '🩺',
    desc: 'Medicine, wellness & public health',
    color: '#4cbf7c',
    glow: 'rgba(76,191,124,0.3)',
    bg: 'rgba(76,191,124,0.08)',
  },
  'Environment': {
    icon: '🌿',
    desc: 'Climate, nature & sustainability',
    color: '#3db870',
    glow: 'rgba(61,184,112,0.3)',
    bg: 'rgba(61,184,112,0.08)',
  },
  'Sports': {
    icon: '🏆',
    desc: 'Scores, events & athlete stories',
    color: '#f56338',
    glow: 'rgba(245,99,56,0.3)',
    bg: 'rgba(245,99,56,0.08)',
  },
  'Entertainment': {
    icon: '🎬',
    desc: 'Film, music, culture & arts',
    color: '#e05f9e',
    glow: 'rgba(224,95,158,0.3)',
    bg: 'rgba(224,95,158,0.08)',
  },
}

// ── localStorage helpers ─────────────────────────────────────────────────
function loadLocal() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const p = JSON.parse(raw)
      if (p && Array.isArray(p.topics)) return p
    }
  } catch {}
  return null
}

function saveLocal(prefs) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)) } catch {}
}

// ── API helpers ──────────────────────────────────────────────────────────
async function getToken() {
  const session = await fetchAuthSession()
  return session.tokens?.idToken?.toString()
}

async function fetchPrefsFromAPI(userId) {
  try {
    const token = await getToken()
    const res = await axios.get(`${API_URL}/preferences`, {
      params:  { user_id: userId },
      headers: { Authorization: `Bearer ${token}` },
      timeout: 5_000,
    })
    const data = res.data
    if (data && typeof data.onboarded === 'boolean' && Array.isArray(data.topics)) {
      return data
    }
  } catch (err) {
    console.warn('[usePreferences] API fetch failed, using local cache:', err.message)
  }
  return null
}

async function savePrefsToAPI(userId, prefs) {
  try {
    const token = await getToken()
    await axios.put(
      `${API_URL}/preferences`,
      { user_id: userId, topics: prefs.topics, onboarded: prefs.onboarded },
      { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, timeout: 5_000 },
    )
  } catch (err) {
    console.warn('[usePreferences] API save failed, preferences only saved locally:', err.message)
  }
}

// ── Hook ─────────────────────────────────────────────────────────────────
/**
 * Manages topic preferences with:
 *   - Instant reads from localStorage (no flash on warm visits)
 *   - Server-side sync via DynamoDB /preferences endpoint (persists across devices)
 *   - Optimistic local updates (saves to localStorage immediately, API in background)
 *
 * @param {string|null} userId  Cognito sub (user.userId from Amplify Authenticator)
 */
export function usePreferences(userId) {
  const local = loadLocal()

  // If localStorage has data we start ready; otherwise show loading until server responds
  const [prefs, setPrefs]             = useState(local ?? { onboarded: false, topics: [] })
  const [prefsLoading, setPrefsLoading] = useState(!local)
  const syncedRef = useRef(false)

  useEffect(() => {
    if (!userId || syncedRef.current) return
    syncedRef.current = true

    fetchPrefsFromAPI(userId).then(serverPrefs => {
      if (serverPrefs) {
        // Server is the source of truth — overwrite local cache
        const merged = { onboarded: serverPrefs.onboarded, topics: serverPrefs.topics }
        setPrefs(merged)
        saveLocal(merged)
      }
      // If server returned nothing, keep whatever was in localStorage (or the default)
      setPrefsLoading(false)
    })
  }, [userId])

  const completeOnboarding = useCallback((topics) => {
    const next = { onboarded: true, topics }
    setPrefs(next)
    saveLocal(next)
    if (userId) savePrefsToAPI(userId, next)
  }, [userId])

  const updateTopics = useCallback((topics) => {
    setPrefs(prev => {
      const next = { ...prev, topics }
      saveLocal(next)
      if (userId) savePrefsToAPI(userId, next)
      return next
    })
  }, [userId])

  return {
    onboarded: prefs.onboarded,
    topics:    prefs.topics,
    prefsLoading,
    completeOnboarding,
    updateTopics,
  }
}
