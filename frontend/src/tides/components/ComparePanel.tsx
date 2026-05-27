import type { StationData } from '../types'
import { RANGES } from '../tides'
import { BigChart, type SunMarks } from './Charts'

const MIN = 60 * 1000

export function ComparePanel({
  stations,
  now,
  range,
  showSun,
  showGrid,
  sun,
}: {
  stations: StationData[]
  now: number
  range: string
  showSun: boolean
  showGrid: boolean
  sun: SunMarks
}) {
  const mins = RANGES[range].mins
  const from = now - mins * 0.4 * MIN
  const to = now + mins * 0.6 * MIN
  return (
    <section className="tt-compare">
      <header className="tt-sec-hd tt-sec-hd-lg">
        <span className="tt-sec-lbl">COMPARE OVERLAY · all stations</span>
        <span className="tt-sec-meta">{RANGES[range].label} · normalized to MLLW</span>
      </header>
      <BigChart series={stations} from={from} to={to} now={now} showGrid={showGrid} showSun={showSun} sun={sun} style="line" showEvents={false} h={280} w={920} />
      <div className="tt-compare-legend">
        {stations.map((s, i) => {
          const hue = 220 + ((i % 5) - 2) * 22
          return (
            <div key={s.id} className="tt-cmp-leg">
              <span className="tt-cmp-sw" style={{ background: `oklch(0.78 0.10 ${hue})` }} />
              <span className="tt-cmp-code">{s.code}</span>
              <span className="tt-cmp-name">{s.name}</span>
            </div>
          )
        })}
      </div>
    </section>
  )
}
