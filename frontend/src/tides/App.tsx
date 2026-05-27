import { useEffect, useState } from 'react'
import { fetchBootstrap } from './api'
import type { Bootstrap } from './types'
import { Dashboard } from './Dashboard'

export default function App() {
  const [data, setData] = useState<Bootstrap | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    fetchBootstrap(ctrl.signal)
      .then(setData)
      .catch((e) => {
        if (e.name !== 'AbortError') setError(String(e.message ?? e))
      })
    return () => ctrl.abort()
  }, [])

  if (error) {
    return (
      <div className="bto-splash">
        <div className="bto-splash-mark">◆</div>
        <div className="bto-splash-title">Bellingham Tidal Observatory</div>
        <div className="bto-splash-err">Failed to load NOAA data — {error}</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="bto-splash">
        <div className="bto-splash-mark">◆</div>
        <div className="bto-splash-title">Bellingham Tidal Observatory</div>
        <div className="bto-splash-sub">fetching noaa predictions…</div>
      </div>
    )
  }

  return <Dashboard data={data} />
}
