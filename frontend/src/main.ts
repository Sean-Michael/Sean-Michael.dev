import { initGithubWidget } from "./githubWidget";
import { initTidesWidget } from "./tidesWidget";

document.addEventListener("DOMContentLoaded", () => {
  void initTidesWidget();
  void initGithubWidget();
});
