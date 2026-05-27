import { initCarousel } from "./carousel";
import { initTidesWidget } from "./tidesWidget";

document.addEventListener("DOMContentLoaded", () => {
  initCarousel();
  void initTidesWidget();
});
