// Phone-optimized tides observatory — ported from the design's tides-mobile.jsx,
// driven by real NOAA data. Single-column list, hero card, drilldown, filters
// sheet, saved views, and a bottom tab bar. Rendered below the desktop breakpoint.
import { useEffect, useMemo, useState } from 'react'
import type { Bootstrap, StationData } from '../types'
import {
  RANGE_KEYS,
  fmtClock,
  fmtTime,
  heightAt,
  pacificWallMs,
  rateAt,
  RANGES,
  stationSnapshot,
} from '../tides'
import { BigChart, Spark, TideDial, type SunMarks } from '../components/Charts'

const MIN = 60 * 1000

type View = 'stations' | 'drill' | 'filters' | 'saved'
type SortBy = 'name' | 'height' | 'range' | 'trend'
type GroupBy = 'none' | 'region' | 'trend'

const trendGlyph = (t: string) => (t === 'rising' ? '↗' : t === 'falling' ? '↘' : '→')

// ── Header ────────────────────────────────────────────────────────────────
function Header({ view, clock, onSearch, onSetting }: { view: View; clock: string; onSearch: () => void; onSetting: () => void }) {
  const title = view === 'stations' ? 'Stations' : view === 'drill' ? 'Drilldown' : view === 'saved' ? 'Saved' : 'Filters'
  return (
    <div className="tm-hd">
      <div className="tm-hd-l">
        <div className="tm-hd-eyebrow">~/TIDES · BELLINGHAM</div>
        <div className="tm-hd-title">{title}</div>
      </div>
      <div className="tm-hd-r">
        <span className="tm-live is-live">
          <span className="tm-live-dot" />
          <span>{clock}</span>
        </span>
        <button className="tm-icbtn" onClick={onSearch} aria-label="Stations">⌕</button>
        <button className="tm-icbtn" onClick={onSetting} aria-label="Filters">▤</button>
      </div>
    </div>
  )
}

// ── Range pills ─────────────────────────────────────────────────────────────
function RangePills({ value, onChange }: { value: string; onChange: (r: string) => void }) {
  return (
    <div className="tm-range">
      <span className="tm-range-lbl">RANGE</span>
      <div className="tm-range-pills">
        {RANGE_KEYS.map((r) => (
          <button key={r} className={`tm-range-pill ${value === r ? 'is-on' : ''}`} onClick={() => onChange(r)}>
            {r}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Hero card ────────────────────────────────────────────────────────────────
function Hero({ stn, now, onTap }: { stn: StationData; now: number; onTap: () => void }) {
  const snap = useMemo(() => stationSnapshot(stn, now), [stn, now])
  const from = now - 6 * 60 * MIN
  const to = now + 12 * 60 * MIN
  return (
    <div className="tm-hero" onClick={onTap}>
      <div className="tm-hero-top">
        <div>
          <div className="tm-hero-code">{stn.code} · NOW</div>
          <div className="tm-hero-name">{stn.name}</div>
        </div>
        <span className={`tm-pin tm-pin-${snap.trend}`}>
          <span className="tm-pin-dot" />
          <span>{snap.trend}</span>
        </span>
      </div>
      <div className="tm-hero-figrow">
        <TideDial rate={snap.rate} trend={snap.trend} size={88} />
        <div className="tm-hero-figs">
          <div className="tm-hero-h">
            <span>{snap.height.toFixed(1)}</span>
            <i>ft</i>
          </div>
          <div className="tm-hero-rate">
            {trendGlyph(snap.trend)}&nbsp;{Math.abs(snap.rate).toFixed(2)}
            <i>ft/h</i>
          </div>
          <div className="tm-hero-sub">
            {stn.predictions.toLowerCase()} · range {(snap.dayMax - snap.dayMin).toFixed(1)}ft
          </div>
        </div>
      </div>
      <div className="tm-hero-chart">
        <Spark extrema={stn.extrema} from={from} to={to} now={now} h={66} style="area" />
        <div className="tm-hero-axis">
          <span>{fmtTime(from)}</span>
          <span className="tm-now-pip">now</span>
          <span>{fmtTime(to)}</span>
        </div>
      </div>
      <div className="tm-hero-events">
        {snap.nextHigh && (
          <div className="tm-evt-chip">
            <span className="tm-evt-glyph tm-h">▲</span>
            <div>
              <div className="tm-evt-k">next high</div>
              <div className="tm-evt-v">
                {snap.nextHigh.height.toFixed(1)}
                <i>ft</i> · {fmtTime(snap.nextHigh.t)}
              </div>
            </div>
          </div>
        )}
        {snap.nextLow && (
          <div className="tm-evt-chip">
            <span className="tm-evt-glyph tm-l">▼</span>
            <div>
              <div className="tm-evt-k">next low</div>
              <div className="tm-evt-v">
                {snap.nextLow.height.toFixed(1)}
                <i>ft</i> · {fmtTime(snap.nextLow.t)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── KPI chips ────────────────────────────────────────────────────────────────
function Kpis({ data, now }: { data: Bootstrap; now: number }) {
  const cells = useMemo(() => {
    const snaps = data.stations.map((s) => stationSnapshot(s, now))
    const meanH = snaps.reduce((a, b) => a + b.height, 0) / snaps.length
    const rising = snaps.filter((s) => s.trend === 'rising').length
    const falling = snaps.filter((s) => s.trend === 'falling').length
    const slack = snaps.filter((s) => s.trend === 'slack').length
    const dayMin = Math.min(...snaps.map((s) => s.dayMin))
    const dayMax = Math.max(...snaps.map((s) => s.dayMax))
    const nextH = snaps.map((s) => s.nextHigh).filter((e): e is NonNullable<typeof e> => !!e).sort((a, b) => a.t - b.t)[0]
    const nextL = snaps.map((s) => s.nextLow).filter((e): e is NonNullable<typeof e> => !!e).sort((a, b) => a.t - b.t)[0]
    const sm = data.sun_moon
    return [
      { k: 'MEAN', v: meanH.toFixed(1), u: 'ft', s: `${snaps.length} stns` },
      { k: 'RANGE', v: (dayMax - dayMin).toFixed(1), u: 'ft', s: `${dayMin.toFixed(0)}–${dayMax.toFixed(0)}` },
      { k: 'NEXT ▲', v: nextH ? fmtTime(nextH.t) : '—', u: '', s: nextH ? `${nextH.height.toFixed(1)}ft` : '' },
      { k: 'NEXT ▼', v: nextL ? fmtTime(nextL.t) : '—', u: '', s: nextL ? `${nextL.height.toFixed(1)}ft` : '' },
      { k: 'MOON', v: sm.moon_glyph, u: '', s: `${Math.round(sm.moon_illum * 100)}%`, glyph: true },
      { k: 'SUN', v: sm.sunrise, u: '↗', s: `set ${sm.sunset}` },
      { k: 'TREND', v: `${rising}↗`, u: '', s: `${falling}↘ ${slack}·` },
    ]
  }, [data, now])
  return (
    <div className="tm-kpis">
      {cells.map((c, i) => (
        <div className="tm-kpi" key={i}>
          <div className="tm-kpi-k">{c.k}</div>
          <div className={`tm-kpi-v ${c.glyph ? 'is-glyph' : ''}`}>
            <span>{c.v}</span>
            {c.u && <i>{c.u}</i>}
          </div>
          <div className="tm-kpi-s">{c.s}</div>
        </div>
      ))}
    </div>
  )
}

// ── Station row ──────────────────────────────────────────────────────────────
function StationRow({ stn, range, now, isFocus, onTap }: { stn: StationData; range: string; now: number; isFocus: boolean; onTap: (id: string) => void }) {
  const snap = useMemo(() => stationSnapshot(stn, now), [stn, now])
  const mins = RANGES[range].mins
  const from = now - mins * 0.6 * MIN
  const to = now + mins * 0.4 * MIN
  return (
    <button className={`tm-row tm-row-${snap.trend} ${isFocus ? 'is-focus' : ''}`} onClick={() => onTap(stn.id)}>
      <div className="tm-row-l">
        <div className="tm-row-code">
          <span className={`tm-pin-dot tm-pin-${snap.trend}-d`} />
          <span>{stn.code}</span>
        </div>
        <div className="tm-row-name">{stn.name}</div>
        <div className="tm-row-area">{stn.area}</div>
      </div>
      <div className="tm-row-m">
        <Spark extrema={stn.extrema} from={from} to={to} now={now} h={28} w={120} style="line" />
      </div>
      <div className="tm-row-r">
        <div className="tm-row-h">
          {snap.height.toFixed(1)}
          <i>ft</i>
        </div>
        <div className="tm-row-rate">
          {trendGlyph(snap.trend)} {Math.abs(snap.rate).toFixed(2)}
        </div>
      </div>
    </button>
  )
}

const REGION_ORDER = ['central', 'south', 'islands', 'north'] as const

function sortStations(stations: StationData[], now: number, sortBy: SortBy): StationData[] {
  const arr = stations.map((s) => [s, stationSnapshot(s, now)] as const)
  arr.sort((a, b) => {
    if (sortBy === 'name') return a[0].name.localeCompare(b[0].name)
    if (sortBy === 'height') return b[1].height - a[1].height
    if (sortBy === 'range') return b[1].dayMax - b[1].dayMin - (a[1].dayMax - a[1].dayMin)
    const order = { rising: 0, slack: 1, falling: 2 }
    return order[a[1].trend] - order[b[1].trend]
  })
  return arr.map(([s]) => s)
}

// ── Stations screen ─────────────────────────────────────────────────────────
function StationsScreen({ data, now, range, setRange, sortBy, groupBy, focusId, onTapStation }: { data: Bootstrap; now: number; range: string; setRange: (r: string) => void; sortBy: SortBy; groupBy: GroupBy; focusId: string; onTapStation: (id: string) => void }) {
  const focusStn = data.stations.find((s) => s.id === focusId) ?? data.stations[0]
  const minuteBucket = Math.floor(now / 60000)
  const groups = useMemo(() => {
    const sorted = sortStations(data.stations, now, sortBy)
    if (groupBy === 'region') {
      const map: Record<string, StationData[]> = {}
      for (const s of sorted) (map[s.group] ||= []).push(s)
      return REGION_ORDER.map((k) => ({ label: k.toUpperCase(), items: map[k] || [] })).filter((g) => g.items.length)
    }
    if (groupBy === 'trend') {
      const map: Record<string, StationData[]> = { rising: [], slack: [], falling: [] }
      for (const s of sorted) map[stationSnapshot(s, now).trend].push(s)
      return (['rising', 'slack', 'falling'] as const).map((k) => ({ label: k.toUpperCase(), items: map[k] })).filter((g) => g.items.length)
    }
    return [{ label: null as string | null, items: sorted }]
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data.stations, sortBy, groupBy, minuteBucket])

  return (
    <div className="tm-screen">
      <Hero stn={focusStn} now={now} onTap={() => onTapStation(focusStn.id)} />
      <RangePills value={range} onChange={setRange} />
      <div className="tm-sec-hd">
        <span className="tm-sec-lbl">KPI · ALL STATIONS</span>
        <span className="tm-sec-meta">scroll →</span>
      </div>
      <Kpis data={data} now={now} />
      {groups.map((g, gi) => (
        <div key={gi}>
          <div className="tm-sec-hd">
            <span className="tm-sec-lbl">{g.label ? g.label : `STATIONS · ${g.items.length}`}</span>
            <span className="tm-sec-meta">tap to drill</span>
          </div>
          <div className="tm-list">
            {g.items.map((s) => (
              <StationRow key={s.id} stn={s} range={range} now={now} isFocus={s.id === focusId} onTap={onTapStation} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Drill screen ─────────────────────────────────────────────────────────────
function DrillScreen({ data, stn, now, range, setRange, sun, showSun, showGrid, showMoon, compare, onBack }: { data: Bootstrap; stn: StationData; now: number; range: string; setRange: (r: string) => void; sun: SunMarks; showSun: boolean; showGrid: boolean; showMoon: boolean; compare: boolean; onBack: () => void }) {
  const snap = useMemo(() => stationSnapshot(stn, now), [stn, now])
  const mins = RANGES[range].mins
  const from = now - mins * 0.4 * MIN
  const to = now + mins * 0.6 * MIN
  const minuteBucket = Math.floor(now / 60000)

  const rows = useMemo(() => {
    const out = []
    for (let i = 0; i < 8; i++) {
      const t = now + i * 60 * MIN
      out.push({ t, h: heightAt(stn.extrema, t), r: rateAt(stn.extrema, t), isNow: i === 0 })
    }
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stn, minuteBucket])
  const hi = Math.max(...rows.map((r) => r.h))
  const lo = Math.min(...rows.map((r) => r.h))
  const span = hi - lo || 1
  const sm = data.sun_moon
  const series = compare ? data.stations : [stn]

  return (
    <div className="tm-screen">
      <div className="tm-back">
        <button className="tm-back-btn" onClick={onBack}>← stations</button>
        <button className="tm-back-pick" onClick={onBack}>switch station ⇅</button>
      </div>

      <div className="tm-drill-hd">
        <div className="tm-drill-code">{stn.code}</div>
        <div className="tm-drill-name">{stn.name}</div>
        <div className="tm-drill-loc">{stn.lat}, {stn.lon} · {stn.area}</div>
        <div className="tm-drill-figrow">
          <TideDial rate={snap.rate} trend={snap.trend} size={92} />
          <div>
            <div className="tm-drill-h">
              <span>{snap.height.toFixed(2)}</span>
              <i>ft</i>
            </div>
            <div className="tm-drill-state">
              {trendGlyph(snap.trend)} {snap.trend} · {Math.abs(snap.rate).toFixed(2)}ft/h
            </div>
            <div className="tm-drill-sub">
              day range {(snap.dayMax - snap.dayMin).toFixed(1)}ft · {stn.predictions.toLowerCase()}
            </div>
          </div>
        </div>
      </div>

      <RangePills value={range} onChange={setRange} />

      <div className="tm-drill-chart">
        <BigChart series={series} from={from} to={to} now={now} showGrid={showGrid} showSun={showSun && showMoon} sun={sun} style={compare ? 'line' : 'area'} showEvents={!compare} h={210} w={368} />
      </div>

      <div className="tm-sec-hd">
        <span className="tm-sec-lbl">UPCOMING · 8H</span>
        <span className="tm-sec-meta">{fmtTime(now)} →</span>
      </div>
      <div className="tm-hours">
        {rows.map((r, i) => {
          const pct = ((r.h - lo) / span) * 100
          const g = Math.abs(r.r) < 0.15 ? '—' : r.r > 0 ? '↗' : '↘'
          return (
            <div key={i} className={`tm-hr ${r.isNow ? 'is-now' : ''}`}>
              <span className="tm-hr-t">{r.isNow ? 'now' : fmtTime(r.t)}</span>
              <span className="tm-hr-spark">
                <span style={{ width: `${pct.toFixed(0)}%` }} />
              </span>
              <span className="tm-hr-h">
                {r.h.toFixed(2)}
                <i>ft</i>
              </span>
              <span className="tm-hr-r">
                {g} {Math.abs(r.r).toFixed(2)}
              </span>
            </div>
          )
        })}
      </div>

      <div className="tm-sec-hd">
        <span className="tm-sec-lbl">SUN · MOON</span>
        <span className="tm-sec-meta">{sm.moon_glyph} today</span>
      </div>
      <div className="tm-sol">
        <div className="tm-sol-col">
          <div className="tm-sol-k">SUN</div>
          <div className="tm-sol-row"><span>↑ rise</span><span>{sm.sunrise}</span></div>
          <div className="tm-sol-row"><span>☀ noon</span><span>{sm.noon}</span></div>
          <div className="tm-sol-row"><span>↓ set</span><span>{sm.sunset}</span></div>
        </div>
        <div className="tm-sol-col">
          <div className="tm-sol-k">MOON</div>
          <div className="tm-sol-row"><span>phase</span><span>{sm.moon_glyph}</span></div>
          <div className="tm-sol-row"><span>illum</span><span>{Math.round(sm.moon_illum * 100)}%</span></div>
          <div className="tm-sol-row"><span>{sm.moon_phase}</span><span /></div>
        </div>
      </div>

      <div className="tm-sec-hd">
        <span className="tm-sec-lbl">STATION</span>
        <span className="tm-sec-meta">{stn.id}</span>
      </div>
      <div className="tm-wx">
        {[
          ['datum', data.datum, 'ref'],
          ['type', stn.predictions === 'Harmonic' ? 'harm' : 'sub', stn.predictions.toLowerCase()],
          ['lat', stn.lat.toFixed(3), '°N'],
          ['lon', stn.lon.toFixed(3), '°W'],
          ['next ▲', snap.nextHigh ? snap.nextHigh.height.toFixed(1) : '—', snap.nextHigh ? fmtTime(snap.nextHigh.t) : ''],
          ['next ▼', snap.nextLow ? snap.nextLow.height.toFixed(1) : '—', snap.nextLow ? fmtTime(snap.nextLow.t) : ''],
        ].map((c, i) => (
          <div key={i} className="tm-wx-cell">
            <div className="tm-wx-k">{c[0]}</div>
            <div className="tm-wx-v">{c[1]}</div>
            <div className="tm-wx-s">{c[2]}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Filters screen ───────────────────────────────────────────────────────────
function FiltersScreen(props: {
  range: string; setRange: (r: string) => void
  sortBy: SortBy; setSortBy: (s: SortBy) => void
  groupBy: GroupBy; setGroupBy: (g: GroupBy) => void
  showCompare: boolean; setShowCompare: (v: boolean) => void
  showSun: boolean; setShowSun: (v: boolean) => void
  showMoon: boolean; setShowMoon: (v: boolean) => void
  showGrid: boolean; setShowGrid: (v: boolean) => void
}) {
  const { range, setRange, sortBy, setSortBy, groupBy, setGroupBy } = props
  return (
    <div className="tm-screen">
      <div className="tm-sec-hd"><span className="tm-sec-lbl">TIME RANGE</span></div>
      <div className="tm-grid-2">
        {RANGE_KEYS.map((r) => (
          <button key={r} className={`tm-bigbtn ${range === r ? 'is-on' : ''}`} onClick={() => setRange(r)}>
            <span className="tm-bigbtn-v">{r}</span>
            <span className="tm-bigbtn-s">{RANGES[r].label}</span>
          </button>
        ))}
      </div>

      <div className="tm-sec-hd"><span className="tm-sec-lbl">SORT BY</span></div>
      <div className="tm-grid-2">
        {([['name', 'alphabetical'], ['height', 'current ft, high → low'], ['range', 'tidal range, big → small'], ['trend', 'rising · slack · falling']] as const).map(([k, s]) => (
          <button key={k} className={`tm-bigbtn ${sortBy === k ? 'is-on' : ''}`} onClick={() => setSortBy(k)}>
            <span className="tm-bigbtn-v">{k}</span>
            <span className="tm-bigbtn-s">{s}</span>
          </button>
        ))}
      </div>

      <div className="tm-sec-hd"><span className="tm-sec-lbl">GROUP BY</span></div>
      <div className="tm-grid-2">
        {([['none', 'one big list'], ['region', 'central · islands · north'], ['trend', 'rising · slack · falling']] as const).map(([k, s], i) => (
          <button key={k} className={`tm-bigbtn ${groupBy === k ? 'is-on' : ''}`} style={i === 2 ? { gridColumn: '1 / -1' } : undefined} onClick={() => setGroupBy(k)}>
            <span className="tm-bigbtn-v">{k}</span>
            <span className="tm-bigbtn-s">{s}</span>
          </button>
        ))}
      </div>

      <div className="tm-sec-hd"><span className="tm-sec-lbl">OVERLAYS</span></div>
      <div className="tm-toggles">
        {([
          ['compare overlay', props.showCompare, props.setShowCompare, 'all stations on one chart'],
          ['sun rise/set', props.showSun, props.setShowSun, 'shaded daylight, dawn/dusk markers'],
          ['moon markers', props.showMoon, props.setShowMoon, 'lunar phase in drilldown'],
          ['grid lines', props.showGrid, props.setShowGrid, 'subtle background grid'],
        ] as const).map(([lbl, val, on, sub], i) => (
          <button key={i} className={`tm-tog ${val ? 'is-on' : ''}`} onClick={() => on(!val)}>
            <div>
              <div className="tm-tog-v">{lbl}</div>
              <div className="tm-tog-s">{sub}</div>
            </div>
            <span className="tm-tog-switch"><span /></span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Saved screen ─────────────────────────────────────────────────────────────
interface SavedView {
  name: string
  meta: string
  desc: string
  glyph: string
  apply: () => void
}
function SavedScreen({ views }: { views: SavedView[] }) {
  return (
    <div className="tm-screen">
      <div className="tm-sec-hd"><span className="tm-sec-lbl">SAVED VIEWS</span><span className="tm-sec-meta">tap to load</span></div>
      <div className="tm-saved">
        {views.map((v, i) => (
          <button key={i} className="tm-saved-row" onClick={v.apply}>
            <span className="tm-saved-g">{v.glyph}</span>
            <div className="tm-saved-body">
              <div className="tm-saved-name">{v.name}</div>
              <div className="tm-saved-desc">{v.desc}</div>
            </div>
            <span className="tm-saved-meta">{v.meta}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Bottom tabs ──────────────────────────────────────────────────────────────
function Tabs({ view, setView }: { view: View; setView: (v: View) => void }) {
  const tabs: { id: View; icon: string; lbl: string }[] = [
    { id: 'stations', icon: '▦', lbl: 'Stations' },
    { id: 'drill', icon: '◉', lbl: 'Drilldown' },
    { id: 'filters', icon: '⚑', lbl: 'Filters' },
    { id: 'saved', icon: '★', lbl: 'Saved' },
  ]
  return (
    <nav className="tm-tabs">
      {tabs.map((t) => (
        <button key={t.id} className={`tm-tab ${view === t.id ? 'is-on' : ''}`} onClick={() => setView(t.id)}>
          <span className="tm-tab-icon">{t.icon}</span>
          <span className="tm-tab-lbl">{t.lbl}</span>
        </button>
      ))}
    </nav>
  )
}

// ── App ──────────────────────────────────────────────────────────────────────
export function MobileApp({ data }: { data: Bootstrap }) {
  const [view, setView] = useState<View>('stations')
  const [range, setRange] = useState('24H')
  const [focusId, setFocusId] = useState(data.stations[0]?.id ?? '')
  const [sortBy, setSortBy] = useState<SortBy>('name')
  const [groupBy, setGroupBy] = useState<GroupBy>('none')
  const [showCompare, setShowCompare] = useState(false)
  const [showSun, setShowSun] = useState(true)
  const [showMoon, setShowMoon] = useState(true)
  const [showGrid, setShowGrid] = useState(true)
  const [now, setNow] = useState(data.now)

  useEffect(() => {
    const id = setInterval(() => setNow((n) => n + 1000), 1000)
    return () => clearInterval(id)
  }, [])

  const focusStn = data.stations.find((s) => s.id === focusId) ?? data.stations[0]
  const sun: SunMarks = useMemo(
    () => ({
      rise: pacificWallMs(data.date.iso, data.sun_moon.sunrise),
      set: pacificWallMs(data.date.iso, data.sun_moon.sunset),
      riseLabel: data.sun_moon.sunrise,
      setLabel: data.sun_moon.sunset,
    }),
    [data.date.iso, data.sun_moon],
  )

  const openDrill = (id: string) => {
    setFocusId(id)
    setView('drill')
  }

  const savedViews: SavedView[] = [
    { name: 'All stations · 24h', meta: 'default', desc: 'everything on the inner bay, last day', glyph: '▦', apply: () => { setRange('24H'); setGroupBy('none'); setShowCompare(false); setView('stations') } },
    { name: 'Bellingham · 7d', meta: 'focus', desc: 'main waterfront, week trend', glyph: '◉', apply: () => { setRange('7D'); setShowCompare(false); openDrill('9449211') } },
    { name: 'San Juans compare', meta: 'compare', desc: 'all stations stacked on one chart', glyph: '▭▭', apply: () => { setRange('24H'); setShowCompare(true); openDrill(focusId) } },
    { name: 'By region', meta: 'group', desc: 'central · islands · north', glyph: '⊞', apply: () => { setGroupBy('region'); setView('stations') } },
    { name: 'Biggest tides', meta: 'events', desc: 'sort by tidal range', glyph: '△', apply: () => { setSortBy('range'); setView('stations') } },
  ]

  return (
    <div className="tm-app">
      <div className="tm-bg" />
      <div className="tm-bg-tint" />
      <Header view={view} clock={fmtClock(now)} onSearch={() => setView('stations')} onSetting={() => setView('filters')} />
      <div className="tm-scroll">
        {view === 'stations' && (
          <StationsScreen data={data} now={now} range={range} setRange={setRange} sortBy={sortBy} groupBy={groupBy} focusId={focusId} onTapStation={openDrill} />
        )}
        {view === 'drill' && focusStn && (
          <DrillScreen data={data} stn={focusStn} now={now} range={range} setRange={setRange} sun={sun} showSun={showSun} showGrid={showGrid} showMoon={showMoon} compare={showCompare} onBack={() => setView('stations')} />
        )}
        {view === 'filters' && (
          <FiltersScreen
            range={range} setRange={setRange}
            sortBy={sortBy} setSortBy={setSortBy}
            groupBy={groupBy} setGroupBy={setGroupBy}
            showCompare={showCompare} setShowCompare={setShowCompare}
            showSun={showSun} setShowSun={setShowSun}
            showMoon={showMoon} setShowMoon={setShowMoon}
            showGrid={showGrid} setShowGrid={setShowGrid}
          />
        )}
        {view === 'saved' && <SavedScreen views={savedViews} />}
      </div>
      <Tabs view={view} setView={setView} />
    </div>
  )
}
