// SVG chart primitives in the glacier vocabulary — ported from tides-charts.jsx,
// driven by real NOAA extrema (epoch ms).
import { useId } from 'react'
import type { Extremum } from '../types'
import { eventsIn, fmtTime, heightAt, sample } from '../tides'

const STROKE = 'var(--tt-stroke)'
const CURRENT_DOT = 'oklch(0.95 0.02 220)'
const GRID_LINE = 'rgba(170, 210, 245, 0.10)'
const AXIS_LABEL = 'rgba(220, 232, 245, 0.55)'

const DAY = 24 * 60 * 60 * 1000

function niceTicks(lo: number, hi: number, count = 4): number[] {
  const span = hi - lo
  const step0 = span / count
  const mag = Math.pow(10, Math.floor(Math.log10(step0)))
  const norm = step0 / mag
  let step: number
  if (norm < 1.5) step = 1 * mag
  else if (norm < 3) step = 2 * mag
  else if (norm < 7) step = 5 * mag
  else step = 10 * mag
  const ticks: number[] = []
  const start = Math.ceil(lo / step) * step
  for (let v = start; v <= hi; v += step) ticks.push(v)
  return ticks
}

export function Spark({
  extrema,
  from,
  to,
  now,
  w = 220,
  h = 44,
  style = 'area',
}: {
  extrema: Extremum[]
  from: number
  to: number
  now: number
  w?: number
  h?: number
  style?: 'line' | 'area'
}) {
  const gradId = useId()
  const pts = sample(extrema, from, to, Math.max(32, Math.floor(w / 4)))
  let lo = Infinity
  let hi = -Infinity
  for (const p of pts) {
    if (p.v < lo) lo = p.v
    if (p.v > hi) hi = p.v
  }
  lo -= 0.4
  hi += 0.4
  const span = hi - lo || 1
  const xy = pts.map((p, i) => {
    const x = (i / (pts.length - 1)) * w
    const y = h - ((p.v - lo) / span) * h
    return [x, y] as const
  })
  const linePts = xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const fillPts = `0,${h} ${linePts} ${w},${h}`
  const tFrac = (now - from) / (to - from)
  const nowX = Math.max(0, Math.min(1, tFrac)) * w
  const nowY = h - ((heightAt(extrema, now) - lo) / span) * h
  return (
    <svg className="tt-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" width="100%" height={h}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={STROKE} stopOpacity="0.42" />
          <stop offset="1" stopColor={STROKE} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {style === 'area' && <polyline points={fillPts} fill={`url(#${gradId})`} stroke="none" />}
      <polyline points={linePts} fill="none" stroke={STROKE} strokeWidth="1.25" strokeLinejoin="round" />
      <line x1={nowX} y1="0" x2={nowX} y2={h} stroke="rgba(255,255,255,0.22)" strokeDasharray="2 3" strokeWidth="1" />
      <circle cx={nowX} cy={nowY} r="2.6" fill={CURRENT_DOT} stroke={STROKE} strokeWidth="1.2" />
    </svg>
  )
}

export interface SunMarks {
  rise: number | null
  set: number | null
  riseLabel: string
  setLabel: string
}

export function BigChart({
  series,
  from,
  to,
  now,
  w = 880,
  h = 280,
  showGrid = true,
  showSun = true,
  sun,
  showEvents = true,
  showCurrent = true,
  style = 'area',
  hoverT = null,
}: {
  series: { extrema: Extremum[] }[]
  from: number
  to: number
  now: number
  w?: number
  h?: number
  showGrid?: boolean
  showSun?: boolean
  sun?: SunMarks
  showEvents?: boolean
  showCurrent?: boolean
  style?: 'line' | 'area'
  hoverT?: number | null
}) {
  const gradId = useId()
  if (!series || series.length === 0) return null
  const padL = 38
  const padR = 14
  const padT = 12
  const padB = 22
  const innerW = w - padL - padR
  const innerH = h - padT - padB

  let lo = Infinity
  let hi = -Infinity
  const allSamples = series.map((s) => sample(s.extrema, from, to, Math.max(64, Math.floor(innerW / 3))))
  for (const ser of allSamples)
    for (const p of ser) {
      if (p.v < lo) lo = p.v
      if (p.v > hi) hi = p.v
    }
  lo = Math.floor(lo - 0.5)
  hi = Math.ceil(hi + 0.5)
  const spanV = hi - lo || 1
  const xOf = (t: number) => padL + ((t - from) / (to - from)) * innerW
  const yOf = (v: number) => padT + (1 - (v - lo) / spanV) * innerH
  const yTicks = niceTicks(lo, hi, 5)
  const meanV = (lo + hi) / 2

  const colorFor = (i: number) => {
    const hue = 220 + ((i % 5) - 2) * 22
    return `oklch(0.78 0.10 ${hue})`
  }

  const single = series.length === 1
  const spanT = to - from

  // X ticks
  const xTicks: number[] = []
  let step: number
  if (spanT <= 2 * 60 * 60 * 1000) step = 30 * 60 * 1000
  else if (spanT <= 8 * 60 * 60 * 1000) step = 60 * 60 * 1000
  else if (spanT <= DAY * 1.2) step = 3 * 60 * 60 * 1000
  else if (spanT <= DAY * 4) step = 12 * 60 * 60 * 1000
  else if (spanT <= DAY * 9) step = DAY
  else step = DAY * 7
  const first = Math.ceil(from / step) * step
  for (let t = first; t <= to; t += step) xTicks.push(t)

  const sunOverlays: React.ReactNode[] = []
  if (showSun && sun && spanT <= DAY * 1.2) {
    if (sun.rise != null && sun.rise >= from && sun.rise <= to) {
      sunOverlays.push(
        <g key="sr">
          <line x1={xOf(sun.rise)} y1={padT} x2={xOf(sun.rise)} y2={padT + innerH} stroke="rgba(255, 210, 130, 0.30)" strokeWidth="1" strokeDasharray="4 4" />
          <text x={xOf(sun.rise) + 4} y={padT + 10} fill="rgba(255, 210, 130, 0.75)" fontFamily="var(--mono)" fontSize="9">☼ rise {sun.riseLabel}</text>
        </g>,
      )
    }
    if (sun.set != null && sun.set >= from && sun.set <= to) {
      sunOverlays.push(
        <g key="ss">
          <line x1={xOf(sun.set)} y1={padT} x2={xOf(sun.set)} y2={padT + innerH} stroke="rgba(255, 170, 120, 0.30)" strokeWidth="1" strokeDasharray="4 4" />
          <text x={xOf(sun.set) + 4} y={padT + 10} fill="rgba(255, 170, 120, 0.75)" fontFamily="var(--mono)" fontSize="9">☾ set {sun.setLabel}</text>
        </g>,
      )
    }
    if (sun.rise != null && sun.set != null) {
      const dayLo = Math.max(from, sun.rise)
      const dayHi = Math.min(to, sun.set)
      if (dayHi > dayLo)
        sunOverlays.push(<rect key="day" x={xOf(dayLo)} y={padT} width={xOf(dayHi) - xOf(dayLo)} height={innerH} fill="rgba(255, 220, 160, 0.04)" />)
    }
  }

  return (
    <svg className="tt-bigchart" viewBox={`0 0 ${w} ${h}`} width="100%" height={h}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={STROKE} stopOpacity="0.42" />
          <stop offset="1" stopColor={STROKE} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {showGrid && yTicks.map((v, i) => <line key={`yg${i}`} x1={padL} y1={yOf(v)} x2={w - padR} y2={yOf(v)} stroke={GRID_LINE} strokeWidth="1" />)}
      {showGrid && xTicks.map((t, i) => <line key={`xg${i}`} x1={xOf(t)} y1={padT} x2={xOf(t)} y2={padT + innerH} stroke={GRID_LINE} strokeWidth="1" />)}

      <line x1={padL} y1={yOf(meanV)} x2={w - padR} y2={yOf(meanV)} stroke="rgba(220, 232, 245, 0.18)" strokeWidth="1" strokeDasharray="6 4" />
      <text x={w - padR - 4} y={yOf(meanV) - 3} textAnchor="end" fill="rgba(220, 232, 245, 0.45)" fontFamily="var(--mono)" fontSize="9">
        mean {meanV.toFixed(1)}ft
      </text>

      {sunOverlays}

      {allSamples.map((ser, si) => {
        const stroke = single ? STROKE : colorFor(si)
        const linePts = ser.map((p) => `${xOf(p.t).toFixed(1)},${yOf(p.v).toFixed(1)}`).join(' ')
        const fillPts = `${xOf(ser[0].t)},${padT + innerH} ${linePts} ${xOf(ser[ser.length - 1].t)},${padT + innerH}`
        return (
          <g key={`s${si}`}>
            {style === 'area' && single && <polyline points={fillPts} fill={`url(#${gradId})`} stroke="none" />}
            <polyline points={linePts} fill="none" stroke={stroke} strokeWidth={single ? 1.7 : 1.4} strokeLinejoin="round" />
          </g>
        )
      })}

      {showEvents &&
        single &&
        eventsIn(series[0].extrema, from, to).map((e, i) => {
          const x = xOf(e.t)
          const y = yOf(e.height)
          const yOff = e.kind === 'H' ? -8 : 14
          return (
            <g key={`ev${i}`}>
              <circle cx={x} cy={y} r="2.4" fill={STROKE} />
              <text x={x} y={y + yOff} textAnchor="middle" fill="rgba(220, 232, 245, 0.85)" fontFamily="var(--mono)" fontSize="9">
                {e.kind === 'H' ? '▲' : '▼'} {e.height.toFixed(1)}ft · {fmtTime(e.t)}
              </text>
            </g>
          )
        })}

      {showCurrent && single && now >= from && now <= to && (
        <g>
          <line x1={xOf(now)} y1={padT} x2={xOf(now)} y2={padT + innerH} stroke="rgba(255,255,255,0.30)" strokeDasharray="3 3" strokeWidth="1" />
          <circle cx={xOf(now)} cy={yOf(heightAt(series[0].extrema, now))} r="4" fill={CURRENT_DOT} stroke={STROKE} strokeWidth="1.5" />
        </g>
      )}

      {hoverT != null && hoverT >= from && hoverT <= to && (
        <line x1={xOf(hoverT)} y1={padT} x2={xOf(hoverT)} y2={padT + innerH} stroke="rgba(255,255,255,0.45)" strokeWidth="1" />
      )}

      {yTicks.map((v, i) => (
        <text key={`yt${i}`} x={padL - 6} y={yOf(v) + 3} textAnchor="end" fill={AXIS_LABEL} fontFamily="var(--mono)" fontSize="9">
          {v.toFixed(0)}ft
        </text>
      ))}
      {xTicks.map((t, i) => {
        const lbl =
          spanT <= DAY * 1.2 ? fmtTime(t) : spanT <= DAY * 9 ? `d${Math.round((t - from) / DAY)}` : `w${Math.floor((t - from) / (DAY * 7)) + 1}`
        return (
          <text key={`xt${i}`} x={xOf(t)} y={h - 6} textAnchor="middle" fill={AXIS_LABEL} fontFamily="var(--mono)" fontSize="9">
            {lbl}
          </text>
        )
      })}

      <rect x={padL} y={padT} width={innerW} height={innerH} fill="none" stroke="rgba(170, 210, 245, 0.18)" strokeWidth="1" />
    </svg>
  )
}

export function RangeBar({ dayMin, dayMax, height }: { dayMin: number; dayMax: number; height: number }) {
  const span = dayMax - dayMin || 1
  const pct = Math.max(0, Math.min(1, (height - dayMin) / span))
  return (
    <div className="tt-rangebar">
      <span className="tt-rb-lo">{dayMin.toFixed(1)}</span>
      <div className="tt-rb-track">
        <div className="tt-rb-fill" style={{ width: `${(pct * 100).toFixed(1)}%` }} />
        <div className="tt-rb-knob" style={{ left: `${(pct * 100).toFixed(1)}%` }} />
      </div>
      <span className="tt-rb-hi">{dayMax.toFixed(1)}</span>
    </div>
  )
}

export function TideDial({ rate, trend, size = 110 }: { rate: number; trend: string; size?: number }) {
  const cx = size / 2
  const cy = size - 8
  const r = size / 2 - 8
  const norm = Math.max(-1, Math.min(1, rate / 3))
  const angle = -Math.PI / 2 + norm * (Math.PI / 2 - 0.05)
  const x = cx + Math.cos(angle) * r
  const y = cy + Math.sin(angle) * r
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} className="tt-dial">
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} fill="none" stroke="rgba(170, 210, 245, 0.20)" strokeWidth="6" strokeLinecap="round" />
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${x} ${y}`} fill="none" stroke={STROKE} strokeWidth="6" strokeLinecap="round" />
      <line x1={cx} y1={cy} x2={x} y2={y} stroke={CURRENT_DOT} strokeWidth="1.5" />
      <circle cx={cx} cy={cy} r="3" fill={CURRENT_DOT} />
      <text x={cx} y={cy + 14} textAnchor="middle" fill={AXIS_LABEL} fontFamily="var(--mono)" fontSize="9" letterSpacing="0.06em">
        {trend.toUpperCase()}
      </text>
    </svg>
  )
}
