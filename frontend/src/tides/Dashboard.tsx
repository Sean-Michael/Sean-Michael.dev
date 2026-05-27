import { useEffect, useMemo, useState } from 'react'
import type { Bootstrap, StationData } from './types'
import { ACCENTS, type Tweaks, useTweaks } from './lib/tweaks'
import { fmtClock, pacificWallMs, RANGE_KEYS, stationSnapshot } from './tides'
import type { SunMarks } from './components/Charts'
import { Sidebar, type SavedView } from './components/Sidebar'
import { Toolbar } from './components/Toolbar'
import { KpiStrip } from './components/KpiStrip'
import { StationTile } from './components/StationTile'
import { FocusPanel } from './components/FocusPanel'
import { ComparePanel } from './components/ComparePanel'
import { TweaksPanel } from './components/Tweaks'

const DENSITIES = ['dense', 'compact', 'comfortable', 'spacious'] as const
const REGION_ORDER = ['central', 'south', 'islands', 'north'] as const

function regionSub(k: string) {
  if (k === 'central') return 'bellingham bay · main waterfront'
  if (k === 'south') return 'south of fairhaven'
  if (k === 'islands') return 'lummi · lopez · orcas'
  if (k === 'north') return 'lummi bay through blaine'
  return ''
}
function trendSub(k: string) {
  if (k === 'rising') return 'flood tide · water building'
  if (k === 'falling') return 'ebb tide · water dropping'
  if (k === 'slack') return 'near-zero current'
  return ''
}

const SAVED_VIEWS: SavedView[] = [
  { id: 'all-day', name: 'All stations · 24h', meta: 'default' },
  { id: 'bhm-week', name: 'Bellingham · 7d', meta: 'focus' },
  { id: 'islands', name: 'San Juans compare', meta: 'compare' },
  { id: 'north-tides', name: 'North county', meta: 'region' },
]

function GroupHeader({ label, count, sub }: { label: string; count: number; sub?: string }) {
  return (
    <div className="tt-grouphead">
      <span className="tt-gh-bar" />
      <span className="tt-gh-lbl">{label}</span>
      <span className="tt-gh-count">{count}</span>
      {sub && <span className="tt-gh-sub">{sub}</span>}
      <span className="tt-gh-rule" />
    </div>
  )
}

export function Dashboard({ data }: { data: Bootstrap }) {
  const [t, setTweak] = useTweaks()
  const [focusId, setFocusId] = useState(data.stations[0]?.id ?? '')
  // "now" is anchored at the server timestamp and advanced one second per tick
  // while auto-refresh is on (pure: no Date/performance reads during render).
  const [now, setNow] = useState(data.now)

  useEffect(() => {
    if (!t.autoRefresh) return
    const id = setInterval(() => setNow((n) => n + 1000), 1000)
    return () => clearInterval(id)
  }, [t.autoRefresh])

  const minuteBucket = Math.floor(now / 60000)

  // Keyboard shortcuts
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) return
      if (e.key >= '1' && e.key <= '6') setTweak('range', RANGE_KEYS[+e.key - 1])
      else if (e.key === '[') {
        const i = DENSITIES.indexOf(t.density)
        setTweak('density', DENSITIES[Math.max(0, i - 1)])
      } else if (e.key === ']') {
        const i = DENSITIES.indexOf(t.density)
        setTweak('density', DENSITIES[Math.min(DENSITIES.length - 1, i + 1)])
      } else if (e.key === 'c' || e.key === 'C') setTweak('showCompare', !t.showCompare)
      else if (e.key === 'f' || e.key === 'F') setTweak('showFocus', !t.showFocus)
      else if (e.key === 'r' || e.key === 'R') setNow((n) => n + 1000)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [t.density, t.showCompare, t.showFocus, setTweak])

  const focusStn = data.stations.find((s) => s.id === focusId) ?? data.stations[0]

  const sorted = useMemo(() => {
    const snaps = data.stations.map((s) => [s, stationSnapshot(s, now)] as const)
    snaps.sort((a, b) => {
      if (t.sortBy === 'name') return a[0].name.localeCompare(b[0].name)
      if (t.sortBy === 'height') return b[1].height - a[1].height
      if (t.sortBy === 'range') return b[1].dayMax - b[1].dayMin - (a[1].dayMax - a[1].dayMin)
      if (t.sortBy === 'trend') {
        const order = { rising: 0, slack: 1, falling: 2 }
        return order[a[1].trend] - order[b[1].trend]
      }
      return 0
    })
    return snaps.map(([s]) => s)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.stations, t.sortBy, minuteBucket])

  const groups = useMemo(() => {
    if (t.groupBy === 'region') {
      const map: Record<string, StationData[]> = {}
      for (const s of sorted) (map[s.group] ||= []).push(s)
      return REGION_ORDER.map((k) => ({ label: k.toUpperCase(), items: map[k] || [], sub: regionSub(k) })).filter((g) => g.items.length > 0)
    }
    if (t.groupBy === 'trend') {
      const map: Record<string, StationData[]> = { rising: [], falling: [], slack: [] }
      for (const s of sorted) map[stationSnapshot(s, now).trend].push(s)
      return (['rising', 'slack', 'falling'] as const)
        .map((k) => ({ label: k.toUpperCase(), items: map[k] || [], sub: trendSub(k) }))
        .filter((g) => g.items.length > 0)
    }
    return [{ label: null as string | null, items: sorted, sub: undefined }]
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sorted, t.groupBy, minuteBucket])

  function loadView(id: string) {
    if (id === 'all-day') {
      setTweak({ range: '24H', showCompare: false, showFocus: true, groupBy: 'none' })
      setFocusId(data.stations[0].id)
    } else if (id === 'bhm-week') {
      setTweak({ range: '7D', showCompare: false, showFocus: true })
      setFocusId('9449211')
    } else if (id === 'islands') {
      setTweak({ range: '24H', showCompare: true, groupBy: 'region' })
    } else if (id === 'north-tides') {
      setTweak({ range: '24H', showCompare: false, groupBy: 'region' })
    }
  }

  const cols = t.density === 'dense' ? 5 : t.density === 'compact' ? 4 : t.density === 'comfortable' ? 3 : 2

  const sun: SunMarks = useMemo(
    () => ({
      rise: pacificWallMs(data.date.iso, data.sun_moon.sunrise),
      set: pacificWallMs(data.date.iso, data.sun_moon.sunset),
      riseLabel: data.sun_moon.sunrise,
      setLabel: data.sun_moon.sunset,
    }),
    [data.date.iso, data.sun_moon],
  )

  const rootStyle = { '--tt-stroke': ACCENTS[t.accent] } as React.CSSProperties

  return (
    <div className={`tt-root gs-dark ${t.photoBg ? 'tt-has-photo' : ''}`} style={rootStyle}>
      {t.photoBg && <div className="gs-bg tt-bg" />}
      <div className="gs-bg-tint tt-bg-tint" />
      <div className="tt-scanlines" />

      <Sidebar stations={data.stations} focusId={focusId} now={now} savedViews={SAVED_VIEWS} onSelect={setFocusId} onLoadView={loadView} />

      <main className="tt-main">
        <Toolbar t={t} setTweak={setTweak} data={data} clock={fmtClock(now)} />

        <KpiStrip data={data} now={now} />

        {t.showCompare && <ComparePanel stations={sorted} now={now} range={t.range} showSun={t.showSun} showGrid={t.showGrid} sun={sun} />}

        <section className="tt-grid-wrap">
          {groups.map((g, gi) => (
            <div key={gi} className="tt-grid-group">
              {g.label && <GroupHeader label={g.label} count={g.items.length} sub={g.sub} />}
              <div className="tt-grid" style={{ '--tt-cols': cols } as React.CSSProperties}>
                {g.items.map((s) => (
                  <StationTile key={s.id} stn={s} density={t.density} range={t.range} chartStyle={t.chartStyle} isFocus={s.id === focusId} now={now} onSelect={setFocusId} />
                ))}
              </div>
            </div>
          ))}
        </section>

        {t.showFocus && focusStn && (
          <FocusPanel stn={focusStn} data={data} now={now} range={t.range} chartStyle={t.chartStyle} showSun={t.showSun} showGrid={t.showGrid} sun={sun} />
        )}

        <footer className="tt-foot">
          <span>tidal observatory · seanmichael.dev/tides</span>
          <span>·</span>
          <span>built on FastAPI · React · noaa coops feed</span>
          <span>·</span>
          <span>real hi/lo predictions, half-cosine interpolated (Salish Sea mixed semi-diurnal)</span>
          <span>·</span>
          <span>v0.3 · {data.date.iso}</span>
        </footer>
      </main>

      <TweaksPanel t={t as Tweaks} setTweak={setTweak} />
    </div>
  )
}
