window.brand = {
  upIn(tl, targets, at = 0.1, stagger = 0.18) {
    tl.fromTo(targets, { opacity: 0, y: 72 },
      { opacity: 1, y: 0, duration: 0.6, ease: "back.out(1.5)", stagger }, at);
  },

  popIn(tl, targets, at = 0.3, stagger = 0.1) {
    tl.fromTo(targets, { opacity: 0, scale: 0.62 },
      { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2.2)", stagger }, at);
  },

  fadeIn(tl, targets, at = 0.05) {
    tl.fromTo(targets, { opacity: 0 }, { opacity: 1, duration: 0.5, ease: "power1.out" }, at);
  },

  floatIn(tl, target, at = 0.16) {
    tl.fromTo(target, { opacity: 0, y: 220 },
      { opacity: 1, y: 0, duration: 0.8, ease: "back.out(1.2)" }, at);
  },

  counter(tl, el, to, at, duration = 1.2, from = 0, format = window.brand.brl) {
    const node = document.querySelector(el);
    const value = { n: from };
    node.textContent = format(from);
    tl.to(value, {
      n: to, duration, ease: "power2.out",
      onUpdate: () => { node.textContent = format(Math.round(value.n)); },
    }, at);
  },

  brl(n) {
    return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(n);
  },

  typeText(tl, el, text, at, cps = 16) {
    const node = typeof el === "string" ? document.querySelector(el) : el;
    const typed = { n: 0 };
    const duration = text.length / cps;
    node.textContent = "";
    tl.to(typed, {
      n: text.length, duration, ease: "none",
      onUpdate: () => { node.textContent = text.slice(0, Math.round(typed.n)); },
    }, at);
    return at + duration;
  },

  swapText(tl, el, at) {
    const swap = typeof el === "string" ? document.querySelector(el) : el;
    const [from, to] = swap.children;
    tl.set(swap, { width: from.offsetWidth }, 0);
    tl.set(to, { scaleY: 0 }, 0);
    tl.to(from, { scaleY: 0, duration: 0.14, ease: "power2.in" }, at);
    tl.to(swap, { width: to.offsetWidth, duration: 0.3, ease: "power2.out" }, at + 0.14);
    tl.to(to, { scaleY: 1, duration: 0.3, ease: "back.out(2.4)" }, at + 0.14);
  },

  drawLine(tl, el, at, duration = 0.35) {
    tl.fromTo(el, { scaleY: 0 }, { scaleY: 1, duration, ease: "power2.out" }, at);
  },

  camera(tl, scene, zoom, dur) {
    if (!zoom || zoom === 1) return;
    const stage = document.querySelector(`[data-composition-id="${scene}"] .stage`);
    const chrome = stage.querySelectorAll(":scope > .logo, :scope > .logo-pill");
    const cx = stage.offsetWidth / 2;
    const cy = stage.offsetHeight / 2;
    chrome.forEach((el) => {
      gsap.set(el, { transformOrigin: `${cx - el.offsetLeft}px ${cy - el.offsetTop}px` });
    });
    const cam = { scale: 1 };
    tl.to(cam, {
      scale: zoom, duration: dur, ease: "none",
      onUpdate: () => {
        gsap.set(stage, { scale: cam.scale });
        gsap.set(chrome, { scale: 1 / cam.scale });
      },
    }, 0);
  },
};
