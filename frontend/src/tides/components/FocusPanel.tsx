import { useMemo, useRef, useState } from 'react'
import type { Bootstrap, StationData, SunMoon } from '../types'
import { fmtTime, heightAt, RANGES, rateAt, stationSnapshot } from '../tides'
import { BigChart, type SunMarks, TideDial } from './Charts'

const MIN = 60 * 1000

function HourTable({ stn, now }: { stn: StationData; now: number }) {
  const rows = useMemo(() => {
    const out = []
    for (let i = 0; i < 12; i++) {
      const t = now + i * 60 * MIN
      const h = heightAt(stn.extrema, t)
      const r = rateAt(stn.extrema, t)
      const glyph = Math.abs(r) < 0.15 ? '—' : r > 0 ? '↗' : '↘'
      out.push({ t, h, r, glyph, isNow: i === 0 })
    }
    return out
  }, [stn, now])
  const hi = Math.max(...rows.map((r) => r.h))
  const lo = Math.min(...rows.map((r) => r.h))
  const span = hi - lo || 1
  return (
    <div className="tt-hourtable">
      <header className="tt-ht-hd">
        <span>TIME</span>
        <span>HEIGHT</span>
        <span>RATE</span>
        <span>·</span>
        <span>VISUAL</span>
      </header>
      {rows.map((r, i) => (
        <div className={`tt-ht-row ${r.isNow ? 'is-now' : ''}`} key={i}>
          <span className="tt-ht-t">{r.isNow ? 'now' : fmtTime(r.t)}</span>
          <span className="tt-ht-v">
            {r.h.toFixed(2)}
            <span className="tt-ht-u">ft</span>
          </span>
          <span className="tt-ht-r">
            {r.glyph} {Math.abs(r.r).toFixed(2)}
          </span>
          <span className="tt-ht-spark">
            <span className="tt-ht-fill" style={{ width: `${(((r.h - lo) / span) * 100).toFixed(0)}%` }} />
          </span>
        </div>
      ))}
    </div>
  )
}

function SunMoonPanel({ sm }: { sm: SunMoon }) {
  return (
    <div className="tt-solunar">
      <header className="tt-sec-hd">
        <span className="tt-sec-lbl">SUN · MOON</span>
        <span className="tt-sec-meta">{sm.moon_glyph} today</span>
      </header>
      <div className="tt-solunar-score">
        <div className="tt-ss-bar">
          <div className="tt-ss-fill" style={{ width: `${Math.round(sm.moon_illum * 100)}%` }} />
        </div>
        <div className="tt-ss-num">
          <span>{Math.round(sm.moon_illum * 100)}</span>
          <i>% lit</i>
        </div>
      </div>
      <div className="tt-solunar-grid">
        <div>
          <div className="tt-sl-row-hd">SUN</div>
          <div className="tt-sl-row">
            <span className="tt-sl-t">↑ {sm.sunrise}</span>
          </div>
          <div className="tt-sl-row">
            <span className="tt-sl-t">☀ {sm.noon}</span>
          </div>
          <div className="tt-sl-row">
            <span className="tt-sl-t">↓ {sm.sunset}</span>
          </div>
        </div>
        <div>
          <div className="tt-sl-row-hd">MOON</div>
          <div className="tt-sl-row">
            <span className="tt-sl-t">{sm.moon_glyph} {sm.moon_phase}</span>
          </div>
          <div className="tt-sl-row">
            <span className="tt-sl-t">{Math.round(sm.moon_illum * 100)}% illuminated</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function StationInfo({ stn, datum, now }: { stn: StationData; datum: string; now: number }) {
  const snap = stationSnapshot(stn, now)
  const cells = [
    { k: 'datum', v: datum, s: 'reference' },
    { k: 'type', v: stn.predictions === 'Harmonic' ? 'harm' : 'sub', s: stn.predictions.toLowerCase() },
    { k: 'lat', v: stn.lat.toFixed(3), s: '°N' },
    { k: 'lon', v: stn.lon.toFixed(3), s: '°W' },
    { k: 'next ▲', v: snap.nextHigh ? snap.nextHigh.height.toFixed(1) : '—', s: snap.nextHigh ? fmtTime(snap.nextHigh.t) : '' },
    { k: 'next ▼', v: snap.nextLow ? snap.nextLow.height.toFixed(1) : '—', s: snap.nextLow ? fmtTime(snap.nextLow.t) : '' },
  ]
  return (
    <div className="tt-weather">
      <header className="tt-sec-hd">
        <span className="tt-sec-lbl">STATION</span>
        <span className="tt-sec-meta">{stn.id}</span>
      </header>
      <div className="tt-wx-grid">
        {cells.map((c, i) => (
          <div className="tt-wx-cell" key={i}>
            <div className="tt-wx-k">{c.k}</div>
            <div className="tt-wx-v">{c.v}</div>
            <div className="tt-wx-s">{c.s}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function FocusPanel({
  stn,
  data,
  now,
  range,
  chartStyle,
  showSun,
  showGrid,
  sun,
}: {
  stn: StationData
  data: Bootstrap
  now: number
  range: string
  chartStyle: 'line' | 'area'
  showSun: boolean
  showGrid: boolean
  sun: SunMarks
}) {
  const snap = useMemo(() => stationSnapshot(stn, now), [stn, now])
  const mins = RANGES[range].mins
  const from = now - mins * 0.4 * MIN
  const to = now + mins * 0.6 * MIN
  const trendGlyph = snap.trend === 'rising' ? '↗' : snap.trend === 'falling' ? '↘' : '→'

  const [hoverT, setHoverT] = useState<number | null>(null)
  const chartRef = useRef<HTMLDivElement>(null)
  const onMove = (e: React.MouseEvent) => {
    const r = chartRef.current!.getBoundingClientRect()
    const x = e.clientX - r.left
    const ratio = (x - 38) / (r.width - 38 - 14)
    if (ratio < 0 || ratio > 1) {
      setHoverT(null)
      return
    }
    setHoverT(from + ratio * (to - from))
  }
  const hoverH = hoverT != null ? heightAt(stn.extrema, hoverT) : null

  return (
    <section className="tt-focus">
      <header className="tt-focus-hd">
        <div className="tt-focus-id">
          <div className="tt-focus-code">{stn.code}</div>
          <div className="tt-focus-title">{stn.name}</div>
          <div className="tt-focus-loc">
            {stn.lat}, {stn.lon} · {stn.area}
          </div>
        </div>
        <div className="tt-focus-now">
          <TideDial rate={snap.rate} trend={snap.trend} />
          <div className="tt-focus-now-text">
            <div className="tt-focus-h">
              <span>{snap.height.toFixed(2)}</span>
              <i>ft</i>
            </div>
            <div className="tt-focus-state">
              {trendGlyph}&nbsp;{snap.trend} · {Math.abs(snap.rate).toFixed(2)}ft/h
            </div>
            <div className="tt-focus-sub">
              <span>day range {(snap.dayMax - snap.dayMin).toFixed(1)}ft</span>
              <span>·</span>
              <span>{stn.predictions.toLowerCase()}</span>
            </div>
          </div>
        </div>
      </header>

      <div className="tt-focus-chart" ref={chartRef} onMouseMove={onMove} onMouseLeave={() => setHoverT(null)}>
        <BigChart series={[stn]} from={from} to={to} now={now} showGrid={showGrid} showSun={showSun} sun={sun} style={chartStyle} hoverT={hoverT} h={300} w={920} />
        {hoverT != null && hoverH != null && (
          <div className="tt-focus-hover">
            <span className="tt-fh-t">{fmtTime(hoverT)}</span>
            <span className="tt-fh-h">
              {hoverH.toFixed(2)}
              <i>ft</i>
            </span>
          </div>
        )}
      </div>

      <div className="tt-focus-grid">
        <HourTable stn={stn} now={now} />
        <SunMoonPanel sm={data.sun_moon} />
        <StationInfo stn={stn} datum={data.datum} now={now} />
      </div>
    </section>
  )
}
