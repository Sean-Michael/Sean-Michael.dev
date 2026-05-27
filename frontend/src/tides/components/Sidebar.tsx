import type { StationData } from '../types'
import { stationSnapshot } from '../tides'

const NAV = [
  { icon: '~', label: 'Home', href: '/' },
  { icon: '/', label: 'Blog', href: '/blog' },
  { icon: '%', label: 'Digests', href: '/digest' },
  { icon: '#', label: 'Projects', href: '/projects' },
  { icon: '@', label: 'About', href: '/about' },
]

export interface SavedView {
  id: string
  name: string
  meta: string
}

export function Sidebar({
  stations,
  focusId,
  now,
  savedViews,
  onSelect,
  onLoadView,
}: {
  stations: StationData[]
  focusId: string
  now: number
  savedViews: SavedView[]
  onSelect: (id: string) => void
  onLoadView: (id: string) => void
}) {
  return (
    <aside className="gs-sidebar tt-sidebar">
      <div className="gs-sidebar-head">
        <div className="gs-brand">
          <span className="gs-brand-mark">◆</span>
          <span className="gs-brand-name">sean-michael</span>
        </div>
        <div className="gs-brand-sub">tidal observatory · v0.3</div>
      </div>

      <div className="gs-sb-section">PAGES</div>
      {NAV.map((n) => (
        <a key={n.label} className="gs-sb-link" href={n.href}>
          <span className="gs-sb-glyph">{n.icon}</span>
          <span className="gs-sb-name">{n.label}</span>
        </a>
      ))}
      <a className="gs-sb-link active" href="#">
        <span className="gs-sb-glyph">~</span>
        <span className="gs-sb-name">Tides</span>
        <span className="gs-sb-caret">→</span>
      </a>

      <div className="gs-sb-section" style={{ marginTop: 20 }}>STATIONS · {stations.length}</div>
      <div className="tt-sb-list">
        {stations.map((s) => {
          const snap = stationSnapshot(s, now)
          return (
            <button key={s.id} className={`tt-sb-stn ${focusId === s.id ? 'is-focus' : ''}`} onClick={() => onSelect(s.id)}>
              <span className={`tt-sb-dot tt-pin-${snap.trend}`}>
                <span className="tt-pin-dot" />
              </span>
              <span className="tt-sb-code">{s.code}</span>
              <span className="tt-sb-h">{snap.height.toFixed(1)}</span>
            </button>
          )
        })}
      </div>

      <div className="gs-sb-section" style={{ marginTop: 22 }}>SAVED VIEWS</div>
      {savedViews.map((v) => (
        <button key={v.id} className="gs-sb-link gs-sb-link-sm tt-sb-view" onClick={() => onLoadView(v.id)}>
          <span className="gs-sb-name">{v.name}</span>
          <span className="tt-sb-view-meta">{v.meta}</span>
        </button>
      ))}

      <div className="gs-sb-foot">
        <a href="https://github.com/sean-michael" className="gs-sb-foot-link">github ↗</a>
        <a href="https://api.tidesandcurrents.noaa.gov/api/prod/" className="gs-sb-foot-link">data: noaa coops ↗</a>
        <div className="gs-sb-avail">
          <span className="gs-sb-pulse" />
          <span>live · noaa predictions</span>
        </div>
      </div>
    </aside>
  )
}
