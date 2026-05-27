import { useMemo } from 'react'
import type { Density } from '../lib/tweaks'
import type { StationData } from '../types'
import { fmtTime, RANGES, stationSnapshot } from '../tides'
import { RangeBar, Spark } from './Charts'

const MIN = 60 * 1000

export function StationTile({
  stn,
  density,
  range,
  chartStyle,
  isFocus,
  now,
  onSelect,
}: {
  stn: StationData
  density: Density
  range: string
  chartStyle: 'line' | 'area'
  isFocus: boolean
  now: number
  onSelect: (id: string) => void
}) {
  const snap = useMemo(() => stationSnapshot(stn, now), [stn, now])
  const mins = RANGES[range].mins
  const from = now - mins * 0.6 * MIN
  const to = now + mins * 0.4 * MIN
  const trendGlyph = snap.trend === 'rising' ? '↗' : snap.trend === 'falling' ? '↘' : '→'

  const showAxis = density !== 'dense'
  const showFooter = density !== 'dense'
  const showRangeBar = density === 'comfortable' || density === 'spacious'
  const showMeta = density === 'spacious'
  const sparkH = density === 'dense' ? 34 : density === 'compact' ? 40 : density === 'spacious' ? 64 : 52

  return (
    <button
      className={`tt-tile tt-tile-${density} ${isFocus ? 'is-focus' : ''} tt-tile-${snap.trend}`}
      onClick={() => onSelect(stn.id)}
    >
      <header className="tt-tile-hd">
        <span className="tt-tile-code">{stn.code}</span>
        <span className={`tt-pin tt-pin-${snap.trend}`}>
          <span className="tt-pin-dot" />
          <span className="tt-pin-lbl">{snap.trend}</span>
        </span>
      </header>

      <div className="tt-tile-name">{stn.name}</div>

      <div className="tt-tile-now">
        <span className="tt-tile-h">{snap.height.toFixed(1)}</span>
        <span className="tt-tile-unit">ft</span>
        <span className="tt-tile-trend">
          {trendGlyph}&nbsp;{Math.abs(snap.rate).toFixed(2)}ft/h
        </span>
      </div>

      <Spark extrema={stn.extrema} from={from} to={to} now={now} h={sparkH} style={chartStyle} />

      {showAxis && (
        <div className="tt-tile-axis">
          <span>{fmtTime(from)}</span>
          <span>now</span>
          <span>{fmtTime(to)}</span>
        </div>
      )}

      {showRangeBar && <RangeBar dayMin={snap.dayMin} dayMax={snap.dayMax} height={snap.height} />}

      {showMeta && (
        <div className="tt-tile-meta">
          <span>
            <b>{stn.predictions}</b> pred
          </span>
          <span>{stn.area}</span>
        </div>
      )}

      {showFooter && (
        <footer className="tt-tile-foot">
          {snap.nextHigh && (
            <span className="tt-evt">
              <span className="tt-evt-glyph tt-h">▲</span> {snap.nextHigh.height.toFixed(1)}ft · {fmtTime(snap.nextHigh.t)}
            </span>
          )}
          {snap.nextLow && (
            <span className="tt-evt">
              <span className="tt-evt-glyph tt-l">▼</span> {snap.nextLow.height.toFixed(1)}ft · {fmtTime(snap.nextLow.t)}
            </span>
          )}
        </footer>
      )}
    </button>
  )
}
