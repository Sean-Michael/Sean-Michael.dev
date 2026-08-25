import { initCarousel } from "./carousel";
import { initGithubWidget } from "./githubWidget";
import { initTidesWidget } from "./tidesWidget";

document.addEventListener("DOMContentLoaded", () => {
  initCarousel();
  void initTidesWidget();
  void initGithubWidget();
});
