document.addEventListener("DOMContentLoaded", () => {
  const hero = document.querySelector("[data-home-hero]");
  const reveals = Array.from(document.querySelectorAll("[data-reveal]"));

  reveals.forEach((element) => {
    const delay = element.getAttribute("data-reveal-delay");
    if (delay) {
      element.style.setProperty("--reveal-delay", `${delay}ms`);
    }
  });

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      {
        threshold: 0.14,
        rootMargin: "0px 0px -10% 0px",
      },
    );

    reveals.forEach((element) => observer.observe(element));
  } else {
    reveals.forEach((element) => element.classList.add("is-visible"));
  }

  const canUseParallax = hero &&
    window.matchMedia("(pointer:fine)").matches &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (!canUseParallax) return;

  const portrait = hero.querySelector(".hero-portrait-frame");
  if (!portrait) return;

  let rafId = null;

  hero.addEventListener("mousemove", (event) => {
    const rect = hero.getBoundingClientRect();
    const offsetX = (event.clientX - rect.left) / rect.width - 0.5;
    const offsetY = (event.clientY - rect.top) / rect.height - 0.5;

    if (rafId) {
      window.cancelAnimationFrame(rafId);
    }

    rafId = window.requestAnimationFrame(() => {
      portrait.style.setProperty("--hero-shift-x", `${offsetX * 14}px`);
      portrait.style.setProperty("--hero-shift-y", `${offsetY * 10}px`);
    });
  });

  hero.addEventListener("mouseleave", () => {
    portrait.style.setProperty("--hero-shift-x", "0px");
    portrait.style.setProperty("--hero-shift-y", "0px");
  });
});
