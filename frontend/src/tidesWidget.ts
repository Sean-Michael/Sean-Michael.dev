// Hydrates the homepage "tides" carousel widget from /api/tides/widget.
// Real Bellingham Bay data; falls back silently (leaves placeholders) on error.

interface WidgetSample {
  t: number;
  v: number;
}
interface WidgetData {
  time_label: string;
  height: number;
  trend: "rising" | "falling" | "slack";
  next_high: { height: number; t: number } | null;
  next_low: { height: number; t: number } | null;
  day_start: number;
  day_end: number;
  now: number;
  samples: WidgetSample[];
}

const W = 280;
const H = 80;

const timeFmt = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/Los_Angeles",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function fmt(ms: number): string {
  return timeFmt.format(ms).replace("24:", "00:");
}

export async function initTidesWidget(): Promise<void> {
  const root = document.querySelector<HTMLElement>("[data-tides-widget]");
  if (!root) return;

  let data: WidgetData;
  try {
    const res = await fetch("/api/tides/widget");
    if (!res.ok) return;
    data = (await res.json()) as WidgetData;
  } catch {
    return;
  }

  const set = (sel: string, text: string) => {
    const el = root.querySelector<HTMLElement>(sel);
    if (el) el.textContent = text;
  };

  set("[data-tides-time]", data.time_label);
  set("[data-tides-h]", data.height.toFixed(1));
  set("[data-tides-arrow]", data.trend === "rising" ? "↗" : data.trend === "falling" ? "↘" : "→");
  set("[data-tides-state]", data.trend);

  const next = data.trend === "falling" ? data.next_low : data.next_high;
  const nextLabel = data.trend === "falling" ? "low" : "high";
  if (next) set("[data-tides-next]", `${nextLabel} ${next.height.toFixed(1)}ft @ ${fmt(next.t)}`);

  const pts = data.samples;
  if (pts.length > 1) {
    let lo = Infinity;
    let hi = -Infinity;
    for (const p of pts) {
      if (p.v < lo) lo = p.v;
      if (p.v > hi) hi = p.v;
    }
    lo -= 0.4;
    hi += 0.4;
    const span = hi - lo || 1;
    const span_t = data.day_end - data.day_start || 1;
    const xOf = (t: number) => ((t - data.day_start) / span_t) * W;
    const yOf = (v: number) => H - ((v - lo) / span) * H;

    const line = pts.map((p) => `${xOf(p.t).toFixed(1)},${yOf(p.v).toFixed(1)}`).join(" ");
    const fill = `0,${H} ${line} ${W},${H}`;

    root.querySelector("[data-tides-line]")?.setAttribute("points", line);
    root.querySelector("[data-tides-fill]")?.setAttribute("points", fill);

    const nowX = Math.max(0, Math.min(W, xOf(data.now)));
    const nowY = yOf(data.height);
    const nowLine = root.querySelector("[data-tides-nowline]");
    nowLine?.setAttribute("x1", String(nowX));
    nowLine?.setAttribute("x2", String(nowX));
    const dot = root.querySelector("[data-tides-nowdot]");
    dot?.setAttribute("cx", String(nowX));
    dot?.setAttribute("cy", String(nowY.toFixed(1)));
  }
}
