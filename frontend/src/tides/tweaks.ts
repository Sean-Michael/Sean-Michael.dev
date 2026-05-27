import { useCallback, useState } from 'react'

export type Density = 'dense' | 'compact' | 'comfortable' | 'spacious'
export type ChartStyle = 'line' | 'area'
export type SortBy = 'name' | 'height' | 'range' | 'trend'
export type GroupBy = 'none' | 'region' | 'trend'
export type Accent = 'ice' | 'kelp' | 'sand' | 'lilac'

export interface Tweaks {
  density: Density
  range: string
  chartStyle: ChartStyle
  showMoon: boolean
  showSun: boolean
  showGrid: boolean
  showFocus: boolean
  showCompare: boolean
  sortBy: SortBy
  groupBy: GroupBy
  accent: Accent
  autoRefresh: boolean
  photoBg: boolean
}

export const TWEAK_DEFAULTS: Tweaks = {
  density: 'dense',
  range: '24H',
  chartStyle: 'area',
  showMoon: true,
  showSun: true,
  showGrid: true,
  showFocus: true,
  showCompare: false,
  sortBy: 'trend',
  groupBy: 'none',
  accent: 'ice',
  autoRefresh: true,
  photoBg: true,
}

export type SetTweak = {
  <K extends keyof Tweaks>(key: K, value: Tweaks[K]): void
  (patch: Partial<Tweaks>): void
}

export function useTweaks(defaults: Tweaks = TWEAK_DEFAULTS): [Tweaks, SetTweak] {
  const [t, setT] = useState<Tweaks>(defaults)

  const setTweak = useCallback((keyOrPatch: keyof Tweaks | Partial<Tweaks>, value?: unknown) => {
    setT((prev) =>
      typeof keyOrPatch === 'string'
        ? { ...prev, [keyOrPatch]: value }
        : { ...prev, ...keyOrPatch },
    )
  }, [])

  return [t, setTweak as SetTweak]
}

export const ACCENTS: Record<Accent, string> = {
  ice: 'oklch(0.78 0.08 220)',
  kelp: 'oklch(0.74 0.09 165)',
  sand: 'oklch(0.78 0.09 80)',
  lilac: 'oklch(0.74 0.09 300)',
}
