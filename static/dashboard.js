document.addEventListener("DOMContentLoaded", () => {
  const shells = Array.from(document.querySelectorAll("[data-tab-shell]"));
  if (!shells.length) {
    return;
  }

  shells.forEach((shell) => {
    const tabs = Array.from(shell.querySelectorAll("[data-panel-target]"));
    const panels = Array.from(shell.querySelectorAll("[data-panel]"));
    if (!tabs.length || !panels.length) {
      return;
    }

    const activate = (target) => {
      tabs.forEach((tab) => {
        tab.classList.toggle("is-active", tab.dataset.panelTarget === target);
      });
      panels.forEach((panel) => {
        const visible = panel.dataset.panel === target;
        panel.classList.toggle("is-active", visible);
        panel.hidden = !visible;
      });
    };

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => activate(tab.dataset.panelTarget));
    });

    activate(shell.dataset.defaultPanel || tabs[0].dataset.panelTarget);
  });
});
