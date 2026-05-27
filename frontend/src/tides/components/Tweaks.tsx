import { useState } from 'react'
import { ACCENTS, type Accent, type SetTweak, type Tweaks } from '../lib/tweaks'
import { RANGE_KEYS } from '../tides'

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="tw-row">
      <span className="tw-row-lbl">{label}</span>
      <div className="tw-row-ctl">{children}</div>
    </div>
  )
}

function Seg<T extends string>({ value, options, onChange }: { value: T; options: readonly T[]; onChange: (v: T) => void }) {
  return (
    <div className="tw-seg">
      {options.map((o) => (
        <button key={o} className={`tw-seg-btn ${value === o ? 'is-on' : ''}`} onClick={() => onChange(o)}>
          {o}
        </button>
      ))}
    </div>
  )
}

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button className={`tw-toggle ${value ? 'is-on' : ''}`} onClick={() => onChange(!value)} role="switch" aria-checked={value}>
      <span className="tw-toggle-knob" />
    </button>
  )
}

export function TweaksPanel({ t, setTweak }: { t: Tweaks; setTweak: SetTweak }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button className="tw-fab" onClick={() => setOpen((o) => !o)} title="Tweaks" aria-label="Tweaks">
        ⚙
      </button>
      {open && (
        <div className="tw-panel">
          <header className="tw-panel-hd">
            <span>TWEAKS</span>
            <button className="tw-close" onClick={() => setOpen(false)}>
              ✕
            </button>
          </header>

          <div className="tw-sec">Layout</div>
          <Row label="Density">
            <Seg value={t.density} options={['dense', 'compact', 'comfortable', 'spacious'] as const} onChange={(v) => setTweak('density', v)} />
          </Row>
          <Row label="Range">
            <Seg value={t.range} options={RANGE_KEYS} onChange={(v) => setTweak('range', v)} />
          </Row>
          <Row label="Chart">
            <Seg value={t.chartStyle} options={['line', 'area'] as const} onChange={(v) => setTweak('chartStyle', v)} />
          </Row>
          <Row label="Group by">
            <Seg value={t.groupBy} options={['none', 'region', 'trend'] as const} onChange={(v) => setTweak('groupBy', v)} />
          </Row>
          <Row label="Sort by">
            <Seg value={t.sortBy} options={['name', 'height', 'range', 'trend'] as const} onChange={(v) => setTweak('sortBy', v)} />
          </Row>

          <div className="tw-sec">Overlays</div>
          <Row label="Grid lines">
            <Toggle value={t.showGrid} onChange={(v) => setTweak('showGrid', v)} />
          </Row>
          <Row label="Sun">
            <Toggle value={t.showSun} onChange={(v) => setTweak('showSun', v)} />
          </Row>
          <Row label="Moon">
            <Toggle value={t.showMoon} onChange={(v) => setTweak('showMoon', v)} />
          </Row>

          <div className="tw-sec">Panels</div>
          <Row label="Focus drilldown">
            <Toggle value={t.showFocus} onChange={(v) => setTweak('showFocus', v)} />
          </Row>
          <Row label="Compare overlay">
            <Toggle value={t.showCompare} onChange={(v) => setTweak('showCompare', v)} />
          </Row>

          <div className="tw-sec">Theme</div>
          <Row label="Accent">
            <div className="tw-accents">
              {(Object.keys(ACCENTS) as Accent[]).map((a) => (
                <button
                  key={a}
                  className={`tw-accent ${t.accent === a ? 'is-on' : ''}`}
                  style={{ background: ACCENTS[a] }}
                  onClick={() => setTweak('accent', a)}
                  title={a}
                />
              ))}
            </div>
          </Row>
          <Row label="Shuksan photo">
            <Toggle value={t.photoBg} onChange={(v) => setTweak('photoBg', v)} />
          </Row>
          <Row label="Auto-refresh">
            <Toggle value={t.autoRefresh} onChange={(v) => setTweak('autoRefresh', v)} />
          </Row>
        </div>
      )}
    </>
  )
}
