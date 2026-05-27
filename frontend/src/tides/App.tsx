import { useCallback, useEffect, useRef, useState } from 'react'
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

// NOAA's API is occasionally flaky; auto-retry a few times before giving up.
const MAX_AUTO_RETRIES = 3

export default function App() {
  const [data, setData] = useState<Bootstrap | null>(null)
  const [error, setError] = useState<string | null>(null)
  const isMobile = useIsMobile()
  const attempt = useRef(0)

  const load = useCallback((signal?: AbortSignal) => {
    setError(null)
    fetchBootstrap(signal)
      .then((d) => {
        attempt.current = 0
        setData(d)
      })
      .catch((e) => {
        if (e.name === 'AbortError') return
        if (attempt.current < MAX_AUTO_RETRIES) {
          attempt.current += 1
          setTimeout(() => load(signal), 1200 * attempt.current)
        } else {
          setError(String(e.message ?? e))
        }
      })
  }, [])

  useEffect(() => {
    const ctrl = new AbortController()
    load(ctrl.signal)
    return () => ctrl.abort()
  }, [load])

  if (error) {
    return (
      <div className="bto-splash">
        <div className="bto-splash-mark">◆</div>
        <div className="bto-splash-title">Bellingham Tidal Observatory</div>
        <div className="bto-splash-err">Couldn’t reach NOAA — {error}</div>
        <button className="bto-splash-retry" onClick={() => { attempt.current = 0; load() }}>
          retry
        </button>
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
