// Tide curve math — ported from the design's tides-data.jsx, but driven by REAL
// NOAA hi/lo extrema (epoch ms) instead of the synthetic M2+K1 model. Between
// consecutive extrema the water follows a half-cosine (the smooth tidal curve).

import type { Extremum, StationData, Trend } from './types'

const MIN = 60 * 1000
const HOUR = 60 * MIN

export interface RangeDef {
  mins: number
  label: string
  ticks: string[]
}

export const RANGES: Record<string, RangeDef> = {
  '1H': { mins: 60, label: '1 hour', ticks: ['−1h', 'now'] },
  '6H': { mins: 360, label: '6 hours', ticks: ['−6h', '−4h', '−2h', 'now'] },
  '24H': { mins: 1440, label: '24 hours', ticks: ['00', '06', '12', '18', '24'] },
  '3D': { mins: 3 * 1440, label: '3 days', ticks: ['d−3', 'd−2', 'd−1', 'today'] },
  '7D': { mins: 7 * 1440, label: '1 week', ticks: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] },
  '30D': { mins: 30 * 1440, label: '1 month', ticks: ['w1', 'w2', 'w3', 'w4'] },
}

export const RANGE_KEYS = ['1H', '6H', '24H', '3D', '7D', '30D'] as const

const PACIFIC = 'America/Los_Angeles'

const _timeFmt = new Intl.DateTimeFormat('en-US', {
  timeZone: PACIFIC,
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})
const _dateKeyFmt = new Intl.DateTimeFormat('en-CA', { timeZone: PACIFIC })

/** Format an epoch-ms instant as HH:MM in Pacific time. */
export function fmtTime(ms: number): string {
  return _timeFmt.format(ms).replace('24:', '00:')
}

/** YYYY-MM-DD key in Pacific time (used to bucket "today"). */
export function pacificDateKey(ms: number): string {
  return _dateKeyFmt.format(ms)
}

const _clockFmt = new Intl.DateTimeFormat('en-US', {
  timeZone: PACIFIC,
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})

/** Format an instant as HH:MM:SS in Pacific time (live clock). */
export function fmtClock(ms: number): string {
  return _clockFmt.format(ms).replace('24:', '00:')
}

/** Convert a Pacific wall-clock (YYYY-MM-DD + HH:MM) to epoch ms. */
export function pacificWallMs(iso: string, hhmm: string): number {
  const [Y, M, D] = iso.split('-').map(Number)
  const [h, m] = hhmm.split(':').map(Number)
  const guess = Date.UTC(Y, M - 1, D, h, m)
  // Offset of Pacific from UTC at that instant (DST-aware enough here).
  const asLocal = new Date(new Date(guess).toLocaleString('en-US', { timeZone: PACIFIC }))
  const offset = asLocal.getTime() - guess
  return guess - offset
}

/** Half-cosine interpolation of height (ft) at an instant. Extrema must be sorted. */
export function heightAt(extrema: Extremum[], t: number): number {
  if (extrema.length === 0) return NaN
  // binary search for first extremum with time > t
  let lo = 0
  let hi = extrema.length
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (extrema[mid].t <= t) lo = mid + 1
    else hi = mid
  }
  if (lo === 0) return extrema[0].height
  if (lo >= extrema.length) return extrema[extrema.length - 1].height
  const a = extrema[lo - 1]
  const b = extrema[lo]
  const frac = b.t !== a.t ? (t - a.t) / (b.t - a.t) : 0
  return (a.height + b.height) / 2 + ((a.height - b.height) / 2) * Math.cos(Math.PI * frac)
}

/** Signed rate of change in ft/hr via centered finite difference. */
export function rateAt(extrema: Extremum[], t: number): number {
  const dt = 5 * MIN
  return ((heightAt(extrema, t + dt) - heightAt(extrema, t - dt)) / (2 * dt)) * HOUR
}

export interface SamplePt {
  t: number
  v: number
}

/** Sample the curve across [from, to] inclusive into n+1 points. */
export function sample(extrema: Extremum[], from: number, to: number, n = 96): SamplePt[] {
  const pts: SamplePt[] = []
  for (let i = 0; i <= n; i++) {
    const t = from + (to - from) * (i / n)
    pts.push({ t, v: heightAt(extrema, t) })
  }
  return pts
}

/** Real extrema falling within [from, to]. */
export function eventsIn(extrema: Extremum[], from: number, to: number): Extremum[] {
  return extrema.filter((e) => e.t >= from && e.t <= to)
}

export interface Snapshot {
  height: number
  rate: number
  trend: Trend
  dayMin: number
  dayMax: number
  nextHigh: Extremum | null
  nextLow: Extremum | null
}

export function snapshot(extrema: Extremum[], now: number): Snapshot {
  const height = heightAt(extrema, now)
  const rate = rateAt(extrema, now)
  const trend: Trend = Math.abs(rate) < 0.15 ? 'slack' : rate > 0 ? 'rising' : 'falling'

  const today = pacificDateKey(now)
  const dayPts = extrema.filter((e) => pacificDateKey(e.t) === today).map((e) => e.height)
  const dayMin = dayPts.length ? Math.min(...dayPts) : height
  const dayMax = dayPts.length ? Math.max(...dayPts) : height

  const upcoming = extrema.filter((e) => e.t >= now)
  const nextHigh = upcoming.find((e) => e.kind === 'H') ?? null
  const nextLow = upcoming.find((e) => e.kind === 'L') ?? null

  return { height, rate, trend, dayMin, dayMax, nextHigh, nextLow }
}

/** Snapshot for a station, memo-friendly. */
export function stationSnapshot(s: StationData, now: number): Snapshot {
  return snapshot(s.extrema, now)
}
