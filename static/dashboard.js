document.addEventListener("DOMContentLoaded", () => {
  const detailsBlocks = Array.from(document.querySelectorAll(".layer-toggle"));
  detailsBlocks.forEach((block, index) => {
    const key = `dashboard:details:${index}`;
    try {
      const saved = window.localStorage.getItem(key);
      if (saved === "open") {
        block.open = true;
      }
    } catch (error) {
      // Ignore storage errors; the dashboard should still work without persistence.
    }

    block.addEventListener("toggle", () => {
      try {
        window.localStorage.setItem(key, block.open ? "open" : "closed");
      } catch (error) {
        // Ignore storage errors; the dashboard should still work without persistence.
      }
    });
  });

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
