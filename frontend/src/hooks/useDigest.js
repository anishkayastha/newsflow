import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchAuthSession } from 'aws-amplify/auth'
import axios from 'axios'
import { API_URL } from '../config.js'

const REFRESH_INTERVAL_MS = 30 * 60 * 1_000  // 30 minutes — matches pipeline cadence

/**
 * Fetches the full digest from API Gateway with a Cognito JWT.
 * Returns all clusters unsorted — DigestPage handles category filtering client-side.
 *
 * Returns: { items, loading, error, lastUpdated, refresh }
 */
export function useDigest() {
  const [items,       setItems]       = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const timerRef = useRef(null)

  const fetchDigest = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Get the current Cognito session token
      const session = await fetchAuthSession()
      const token   = session.tokens?.idToken?.toString()

      const res = await axios.get(`${API_URL}/digest`, {
        headers: { Authorization: `Bearer ${token}` },
        params:  { limit: 200 },          // fetch up to 200 clusters
        timeout: 15_000,
      })

      // Sort by score descending — DynamoDB scan order is undefined
      const sorted = (res.data.digest ?? []).sort(
        (a, b) => parseFloat(b.score) - parseFloat(a.score)
      )
      setItems(sorted)
      setLastUpdated(new Date())
    } catch (err) {
      console.error('[useDigest] fetch failed:', err)
      setError(err.response?.data?.message ?? err.message ?? 'Failed to load digest')
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial fetch + auto-refresh every 30 min
  useEffect(() => {
    fetchDigest()
    timerRef.current = setInterval(fetchDigest, REFRESH_INTERVAL_MS)
    return () => clearInterval(timerRef.current)
  }, [fetchDigest])

  return { items, loading, error, lastUpdated, refresh: fetchDigest }
}
