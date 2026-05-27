// Interactive wrapper around BigChart: hover/drag for a point-in-time readout
// (like NOAA's tide page) and click-drag to zoom into a time window. Works with
// mouse and touch. Measures its own width so pointer-x maps 1:1 to chart time.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { Extremum } from '../types'
import { fmtTime, heightAt } from '../tides'
import { BigChart, type SunMarks } from './Charts'

const PAD_L = 38
const PAD_R = 14
const MIN_SPAN = 10 * 60 * 1000 // don't zoom tighter than 10 minutes

export function InteractiveChart({
  series,
  from,
  to,
  now,
  resetKey,
  height = 280,
  showGrid = true,
  showSun = true,
  sun,
  style = 'area',
  showEvents = true,
}: {
  series: { extrema: Extremum[]; code?: string }[]
  from: number
  to: number
  now: number
  // Changing this clears any zoom (e.g. the selected time range). Without it the
  // live clock would constantly change `from`/`to` and wipe the user's zoom.
  resetKey: string
  height?: number
  showGrid?: boolean
  showSun?: boolean
  sun?: SunMarks
  style?: 'line' | 'area'
  showEvents?: boolean
}) {
  const ref = useRef<HTMLDivElement>(null)
  // null until measured — we don't render the chart at a guessed width (which
  // would briefly render tiny/letterboxed before correcting).
  const [width, setWidth] = useState<number | null>(null)
  // null = follow the live [from, to] window; otherwise a pinned absolute window.
  const [zoom, setZoom] = useState<{ from: number; to: number } | null>(null)
  const [cursorPx, setCursorPx] = useState<number | null>(null)
  const dragStart = useRef<number | null>(null)
  const dragNowRef = useRef<number | null>(null)
  const [dragNow, setDragNow] = useState<number | null>(null)

  // Clear the zoom only when the range changes — not on every clock tick.
  useEffect(() => {
    setZoom(null)
  }, [resetKey])

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth)
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const winFrom = zoom ? zoom.from : from
  const winTo = zoom ? zoom.to : to
  const plotW = Math.max(1, (width ?? 600) - PAD_L - PAD_R)
  const single = series.length === 1
  const zoomed = zoom != null

  const tOfX = (px: number) => winFrom + ((px - PAD_L) / plotW) * (winTo - winFrom)

  const pxFromEvent = (clientX: number) => {
    const rect = ref.current!.getBoundingClientRect()
    return clientX - rect.left
  }

  const onPointerDown = (e: React.PointerEvent) => {
    ;(e.target as Element).setPointerCapture?.(e.pointerId)
    const px = pxFromEvent(e.clientX)
    dragStart.current = px
    dragNowRef.current = px
    setDragNow(px)
    setCursorPx(px)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    const px = pxFromEvent(e.clientX)
    setCursorPx(px)
    if (dragStart.current != null) {
      dragNowRef.current = px
      setDragNow(px)
    }
  }
  const endDrag = () => {
    if (dragStart.current != null && dragNowRef.current != null) {
      const a = Math.min(dragStart.current, dragNowRef.current)
      const b = Math.max(dragStart.current, dragNowRef.current)
      if (b - a > 6) {
        let nf = Math.max(winFrom, tOfX(a))
        let nt = Math.min(winTo, tOfX(b))
        if (nt - nf < MIN_SPAN) nt = nf + MIN_SPAN
        if (nt - nf >= MIN_SPAN) setZoom({ from: nf, to: nt })
      }
    }
    dragStart.current = null
    dragNowRef.current = null
    setDragNow(null)
  }
  const onLeave = () => {
    if (dragStart.current == null) setCursorPx(null)
  }

  const cursorT = cursorPx != null ? tOfX(cursorPx) : null
  const cursorClamped = cursorT != null ? Math.max(winFrom, Math.min(winTo, cursorT)) : null
  const cursorH = cursorClamped != null && single ? heightAt(series[0].extrema, cursorClamped) : null

  const dragging = dragStart.current != null && dragNow != null
  const bandLeft = dragging ? Math.min(dragStart.current!, dragNow!) : 0
  const bandWidth = dragging ? Math.abs(dragNow! - dragStart.current!) : 0

  // Readout box position, kept inside the plot.
  const readoutLeft = useMemo(() => {
    if (cursorPx == null) return 0
    return Math.max(PAD_L, Math.min((width ?? 0) - 96, cursorPx + 8))
  }, [cursorPx, width])

  return (
    <div className="tic-wrap">
      <div
        className="tic-plot"
        ref={ref}
        style={{ touchAction: 'none', minHeight: height }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={onLeave}
      >
        {width != null && (
          <BigChart
            series={series}
            from={winFrom}
            to={winTo}
            now={now}
            w={width}
            h={height}
            showGrid={showGrid}
            showSun={showSun}
            sun={sun}
            style={style}
            showEvents={showEvents}
            hoverT={cursorClamped}
          />
        )}
        {dragging && bandWidth > 1 && (
          <div className="tic-band" style={{ left: bandLeft, width: bandWidth, top: 0, bottom: 0 }} />
        )}
        {cursorClamped != null && cursorH != null && (
          <div className="tic-readout" style={{ left: readoutLeft }}>
            <span className="tic-readout-t">{fmtTime(cursorClamped)}</span>
            <span className="tic-readout-h">
              {cursorH.toFixed(2)}
              <i>ft</i>
            </span>
          </div>
        )}
      </div>
      <div className="tic-bar">
        <span className="tic-hint">{zoomed ? 'zoomed in' : 'drag across to zoom · hover to read'}</span>
        {zoomed && (
          <button className="tic-reset" onClick={() => setZoom(null)}>
            reset zoom ⤢
          </button>
        )}
      </div>
    </div>
  )
}
