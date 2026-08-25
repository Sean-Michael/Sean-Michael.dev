// Hydrates the homepage GitHub widget with real contribution data.
// Uses the public contributions API (same source as react-github-calendar);
// the widget stays hidden unless real data actually loads.

const USERNAME = "sean-michael";

interface Contribution {
  date: string;
  count: number;
  level: 0 | 1 | 2 | 3 | 4;
}
interface ApiResponse {
  contributions: Contribution[];
}

export async function initGithubWidget(): Promise<void> {
  const root = document.querySelector<HTMLElement>("[data-gh-widget]");
  if (!root) return;

  let days: Contribution[];
  try {
    const res = await fetch(`https://github-contributions-api.jogruber.de/v4/${USERNAME}?y=last`);
    if (!res.ok) return;
    const data = (await res.json()) as ApiResponse;
    days = data.contributions;
  } catch {
    return;
  }
  if (days.length === 0) return;

  const grid = root.querySelector<HTMLElement>("[data-gh-grid]");
  if (!grid) return;

  // The grid auto-flows down each column (a week), like GitHub's profile graph.
  // Pad the first column so day-of-week rows line up (row 0 = Sunday).
  const offset = new Date(`${days[0].date}T00:00:00`).getDay();
  for (let i = 0; i < offset; i++) {
    const pad = document.createElement("div");
    pad.className = "hw-gh-cell";
    pad.style.visibility = "hidden";
    grid.appendChild(pad);
  }
  for (const day of days) {
    const cell = document.createElement("div");
    cell.className = `hw-gh-cell hw-gh-l${day.level}`;
    cell.title = `${day.count} contributions on ${day.date}`;
    grid.appendChild(cell);
  }

  const total = days.reduce((sum, d) => sum + d.count, 0);
  const totalEl = root.querySelector<HTMLElement>("[data-gh-total]");
  if (totalEl) totalEl.textContent = `${total} total`;

  let longest = 0;
  let run = 0;
  for (const d of days) {
    run = d.count > 0 ? run + 1 : 0;
    if (run > longest) longest = run;
  }
  const metaEl = root.querySelector<HTMLElement>("[data-gh-meta]");
  if (metaEl) metaEl.textContent = `longest streak: ${longest} days`;

  root.hidden = false;
}
