import type { SetTweak, Tweaks } from '../lib/tweaks'
import type { Bootstrap } from '../types'
import { RANGE_KEYS } from '../tides'

const DENSITIES = ['dense', 'compact', 'comfortable', 'spacious'] as const
const SORTS = [
  { id: 'name', lbl: 'name' },
  { id: 'height', lbl: 'height' },
  { id: 'range', lbl: 'range' },
  { id: 'trend', lbl: 'trend' },
] as const

const densityGlyph = (d: string) => (d === 'dense' ? '▦▦' : d === 'compact' ? '▦' : d === 'comfortable' ? '▢▢' : '▢')

export function Toolbar({ t, setTweak, data, clock }: { t: Tweaks; setTweak: SetTweak; data: Bootstrap; clock: string }) {
  return (
    <header className="tt-toolbar">
      <div className="tt-tb-head">
        <div className="tt-tb-headline">
          <div className="gs-hero-label">~/TIDES</div>
          <h1 className="tt-title">Bellingham Tidal Observatory</h1>
          <p className="tt-subtitle">
            Real-time tide heights and solunar conditions across <b>{data.stations.length} NOAA stations</b> on the inner Salish Sea — Bellingham Bay, the
            Lummi waters, and the San Juan Islands. Click any station to drill down, or pop on the compare overlay to see them all stacked.
            <span className="tt-kbds">
              <kbd>1</kbd>–<kbd>6</kbd> time · <kbd>[</kbd> <kbd>]</kbd> density · <kbd>c</kbd> compare · <kbd>f</kbd> focus · <kbd>r</kbd> refresh
            </span>
          </p>
        </div>
        <div className="tt-now-card">
          <div className="tt-now-top">
            <span className={`tt-live ${t.autoRefresh ? 'is-live' : 'is-pause'}`}>
              <span className="tt-live-dot" />
              <span>{t.autoRefresh ? 'LIVE' : 'PAUSED'}</span>
            </span>
            <span className="tt-now-time">{clock}</span>
          </div>
          <div className="tt-now-date">{data.date.pretty}</div>
          <div className="tt-now-meta">
            <span>noaa coops</span>
            <span>·</span>
            <span>tz pst</span>
            <span>·</span>
            <span>{data.datum}</span>
          </div>
        </div>
      </div>

      <div className="tt-tb-strip">
        <div className="tt-tb-col">
          <span className="tt-seg-lbl">RANGE</span>
          <div className="tt-seg">
            {RANGE_KEYS.map((r) => (
              <button key={r} className={`tt-seg-btn ${t.range === r ? 'is-on' : ''}`} onClick={() => setTweak('range', r)}>
                {r}
              </button>
            ))}
          </div>
        </div>

        <span className="tt-tb-sep" />

        <div className="tt-tb-col">
          <span className="tt-seg-lbl">DENSITY</span>
          <div className="tt-seg">
            {DENSITIES.map((d) => (
              <button key={d} className={`tt-seg-btn ${t.density === d ? 'is-on' : ''}`} onClick={() => setTweak('density', d)} title={d}>
                {densityGlyph(d)}
              </button>
            ))}
          </div>
        </div>

        <span className="tt-tb-sep" />

        <div className="tt-tb-col">
          <span className="tt-seg-lbl">SORT</span>
          <div className="tt-seg">
            {SORTS.map((s) => (
              <button key={s.id} className={`tt-seg-btn ${t.sortBy === s.id ? 'is-on' : ''}`} onClick={() => setTweak('sortBy', s.id)}>
                {s.lbl}
              </button>
            ))}
          </div>
        </div>

        <span className="tt-tb-sep" />

        <div className="tt-tb-col">
          <span className="tt-seg-lbl">GROUP</span>
          <div className="tt-seg">
            {(['none', 'region', 'trend'] as const).map((g) => (
              <button key={g} className={`tt-seg-btn ${t.groupBy === g ? 'is-on' : ''}`} onClick={() => setTweak('groupBy', g)}>
                {g}
              </button>
            ))}
          </div>
        </div>

        <span className="tt-tb-sep" />

        <div className="tt-tb-col">
          <span className="tt-seg-lbl">VIEW</span>
          <div className="tt-tb-actions">
            <button className={`tt-tb-pill ${t.showCompare ? 'is-on' : ''}`} onClick={() => setTweak('showCompare', !t.showCompare)} title="Compare overlay (c)">
              <span className="tt-tb-pill-g">▭▭</span>
              <span>compare</span>
            </button>
            <button className={`tt-tb-pill ${t.showFocus ? 'is-on' : ''}`} onClick={() => setTweak('showFocus', !t.showFocus)} title="Focus drilldown (f)">
              <span className="tt-tb-pill-g">◉</span>
              <span>focus</span>
            </button>
          </div>
        </div>

        <span className="tt-tb-spacer" />

        <div className="tt-tb-col tt-tb-col-end">
          <span className="tt-seg-lbl">ACTIONS</span>
          <div className="tt-tb-actions">
            <button className={`tt-icon-btn ${t.autoRefresh ? 'is-on' : ''}`} onClick={() => setTweak('autoRefresh', !t.autoRefresh)} title="Auto-refresh (r)">
              ↻
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
