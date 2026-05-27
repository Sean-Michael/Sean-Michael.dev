export type Kind = 'H' | 'L'
export type Trend = 'rising' | 'falling' | 'slack'

export interface Extremum {
  t: number // epoch ms
  height: number // ft above MLLW
  kind: Kind
}

export interface StationData {
  id: string
  code: string
  name: string
  area: string
  lat: number
  lon: number
  predictions: 'Harmonic' | 'Subordinate'
  group: 'central' | 'south' | 'islands' | 'north'
  extrema: Extremum[]
}

export interface SunMoon {
  sunrise: string
  sunset: string
  noon: string
  moon_phase: string
  moon_illum: number
  moon_glyph: string
}

export interface Bootstrap {
  now: number // epoch ms (server, Pacific)
  tz: string
  datum: string
  units: string
  date: { iso: string; pretty: string }
  sun_moon: SunMoon
  stations: StationData[]
}
