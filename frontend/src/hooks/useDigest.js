import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchAuthSession } from 'aws-amplify/auth'
import axios from 'axios'
import { API_URL } from '../config.js'

const REFRESH_MS = 30 * 60 * 1_000

export function useDigest(dateFilter) {
  const [items,       setItems]       = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [availDates,  setAvailDates]  = useState([])
  const timerRef = useRef(null)

  const fetchDigest = useCallback(async (date) => {
    setLoading(true)
    setError(null)
    try {
      const session = await fetchAuthSession()
      const token   = session.tokens?.idToken?.toString()
      const params  = { limit: 500 }
      if (date) params.date = date

      const res = await axios.get(`${API_URL}/digest`, {
        headers: { Authorization: `Bearer ${token}` },
        params,
        timeout: 15_000,
      })

      const sorted = (res.data.digest ?? []).sort(
        (a, b) => parseFloat(b.score) - parseFloat(a.score)
      )
      setItems(sorted)
      setLastUpdated(new Date())
      if (res.data.dates) setAvailDates(res.data.dates)
    } catch (err) {
      setError(err.response?.data?.message ?? err.message ?? 'Failed to load digest')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDigest(dateFilter)
    clearInterval(timerRef.current)
    timerRef.current = setInterval(() => fetchDigest(dateFilter), REFRESH_MS)
    return () => clearInterval(timerRef.current)
  }, [fetchDigest, dateFilter])

  return { items, loading, error, lastUpdated, availDates, refresh: () => fetchDigest(dateFilter) }
}