import { useEffect, useState } from 'react'
import { fetchBootstrap } from './api'
import type { Bootstrap } from './types'
import { Dashboard } from './Dashboard'
import { MobileApp } from './mobile/MobileApp'

// Below this width the desktop Ganglia grid is unusable; render the phone app.
const MOBILE_QUERY = '(max-width: 768px)'

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia(MOBILE_QUERY).matches)
  useEffect(() => {
    const mq = window.matchMedia(MOBILE_QUERY)
    const onChange = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return isMobile
}

export default function App() {
  const [data, setData] = useState<Bootstrap | null>(null)
  const [error, setError] = useState<string | null>(null)
  const isMobile = useIsMobile()

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

  return isMobile ? <MobileApp data={data} /> : <Dashboard data={data} />
}
