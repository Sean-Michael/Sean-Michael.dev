import { useMemo } from 'react'
import type { Bootstrap } from '../types'
import { fmtTime, stationSnapshot } from '../tides'

export function KpiStrip({ data, now }: { data: Bootstrap; now: number }) {
  const cells = useMemo(() => {
    const snaps = data.stations.map((s) => stationSnapshot(s, now))
    const meanH = snaps.reduce((a, b) => a + b.height, 0) / snaps.length
    const rising = snaps.filter((s) => s.trend === 'rising').length
    const falling = snaps.filter((s) => s.trend === 'falling').length
    const slack = snaps.filter((s) => s.trend === 'slack').length
    const dayMin = Math.min(...snaps.map((s) => s.dayMin))
    const dayMax = Math.max(...snaps.map((s) => s.dayMax))
    const nextH = snaps
      .map((s) => s.nextHigh)
      .filter((e): e is NonNullable<typeof e> => !!e)
      .sort((a, b) => a.t - b.t)[0]
    const nextL = snaps
      .map((s) => s.nextLow)
      .filter((e): e is NonNullable<typeof e> => !!e)
      .sort((a, b) => a.t - b.t)[0]
    const sm = data.sun_moon

    return [
      { lbl: 'MEAN HEIGHT', v: meanH.toFixed(1), u: 'ft', sub: `across ${snaps.length} stations` },
      { lbl: 'TIDE RANGE', v: (dayMax - dayMin).toFixed(1), u: 'ft', sub: `${dayMin.toFixed(1)} → ${dayMax.toFixed(1)} ft today` },
      { lbl: 'NEXT HIGH', v: nextH ? fmtTime(nextH.t) : '—', u: '', sub: nextH ? `${nextH.height.toFixed(1)}ft` : '' },
      { lbl: 'NEXT LOW', v: nextL ? fmtTime(nextL.t) : '—', u: '', sub: nextL ? `${nextL.height.toFixed(1)}ft` : '' },
      { lbl: 'MOON', v: sm.moon_glyph, u: '', sub: `${sm.moon_phase.toLowerCase()} · ${Math.round(sm.moon_illum * 100)}%`, glyph: true },
      { lbl: 'SUN', v: sm.sunrise, u: '↗', sub: `set ${sm.sunset}` },
      { lbl: 'STATIONS', v: String(snaps.length), u: '', sub: `${rising}↗ ${falling}↘ ${slack}∙` },
    ]
  }, [data, now])

  return (
    <section className="tt-kpi">
      {cells.map((c, i) => (
        <div className="tt-kpi-cell" key={i}>
          <div className="tt-kpi-lbl">{c.lbl}</div>
          <div className={`tt-kpi-val ${c.glyph ? 'is-glyph' : ''}`}>
            <span className="tt-kpi-v">{c.v}</span>
            {c.u && <span className="tt-kpi-u">{c.u}</span>}
          </div>
          <div className="tt-kpi-sub">{c.sub}</div>
        </div>
      ))}
    </section>
  )
}
