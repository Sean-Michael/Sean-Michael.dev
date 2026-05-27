import type { Bootstrap } from './types'

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      /* keep status text */
    }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

/** Load station metadata + real NOAA hi/lo predictions + sun/moon in one call. */
export async function fetchBootstrap(signal?: AbortSignal): Promise<Bootstrap> {
  return json<Bootstrap>(await fetch('/api/tides/bootstrap', { signal }))
}
