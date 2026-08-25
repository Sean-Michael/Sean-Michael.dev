export function initCarousel(): void {
  const widgets = Array.from(document.querySelectorAll<HTMLElement>(".carousel-widget"));
  const tabs = Array.from(document.querySelectorAll<HTMLButtonElement>(".hcr-tab"));

  if (widgets.length === 0 || tabs.length === 0) return;

  let current = 0;
  let timer: ReturnType<typeof setInterval>;

  // A widget stays `hidden` until its live data loads; don't rotate onto it,
  // and don't show its tab.
  function syncTabs(): void {
    tabs.forEach((tab, i) => {
      tab.style.display = widgets[i]?.hidden ? "none" : "";
    });
  }

  function go(idx: number): void {
    const n = widgets.length;
    let next = ((idx % n) + n) % n;
    for (let hops = 0; widgets[next].hidden && hops < n; hops++) {
      next = (next + 1) % n;
    }
    if (widgets[next].hidden) return;
    widgets[current].classList.remove("active");
    tabs[current].classList.remove("active");
    current = next;
    widgets[current].classList.add("active");
    tabs[current].classList.add("active");
  }

  function startTimer(): void {
    timer = setInterval(() => {
      syncTabs();
      go(current + 1);
    }, 6000);
  }

  function stopTimer(): void {
    clearInterval(timer);
  }

  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => {
      stopTimer();
      go(i);
      startTimer();
    });
  });

  syncTabs();
  startTimer();
}
