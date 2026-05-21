export function initCarousel(): void {
  const widgets = Array.from(document.querySelectorAll<HTMLElement>(".carousel-widget"));
  const tabs = Array.from(document.querySelectorAll<HTMLButtonElement>(".hcr-tab"));

  if (widgets.length === 0 || tabs.length === 0) return;

  let current = 0;
  let timer: ReturnType<typeof setInterval>;

  function go(idx: number): void {
    widgets[current].classList.remove("active");
    tabs[current].classList.remove("active");
    current = ((idx % widgets.length) + widgets.length) % widgets.length;
    widgets[current].classList.add("active");
    tabs[current].classList.add("active");
  }

  function startTimer(): void {
    timer = setInterval(() => go(current + 1), 6000);
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

  startTimer();
}
