if (typeof document !== "undefined") {
  document.documentElement.dataset.iaWidget = "true";
  const baseHeight = typeof window !== "undefined" && window.innerHeight ? window.innerHeight : 720;
  const desiredHeight = Math.max(baseHeight, 920);
  document.documentElement.style.setProperty("--ia-widget-height", `${desiredHeight}px`);
  document.documentElement.style.setProperty("--ia-widget-gutter", "10px");

  const tryResize = () => {
    const api = (window as any)?.openai;
    if (!api) return false;
    const sizePayload = { height: desiredHeight };
    let called = false;
    if (typeof api.setWidgetSize === "function") {
      api.setWidgetSize(sizePayload);
      called = true;
    }
    if (typeof api.resize === "function") {
      api.resize(sizePayload);
      called = true;
    }
    if (typeof api.requestResize === "function") {
      api.requestResize(sizePayload);
      called = true;
    }
    if (typeof api.setWidgetHeight === "function") {
      api.setWidgetHeight(desiredHeight);
      called = true;
    }
    if (typeof api.setFrameHeight === "function") {
      api.setFrameHeight(desiredHeight);
      called = true;
    }
    if (typeof api.setIframeHeight === "function") {
      api.setIframeHeight(desiredHeight);
      called = true;
    }
    return called;
  };

  let attempts = 0;
  const timer = window.setInterval(() => {
    attempts += 1;
    if (tryResize() || attempts > 12) {
      window.clearInterval(timer);
    }
  }, 250);
}

import("../../../client/src/main");
