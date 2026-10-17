/* Animate only visible, public reading surfaces. Forms and focus stay native. */
(() => {
  'use strict';
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const storageKey = 'bbmod-reduce-motion';
  let manualReduction = false;
  try { manualReduction = localStorage.getItem(storageKey) === 'true'; } catch { /* Private browsing still works. */ }
  const animations = new Set();
  const reduced = () => manualReduction || preference.matches;
  let observer;

  const update = () => {
    document.documentElement.dataset.motion = reduced() ? 'reduce' : 'full';
    if (reduced()) {
      animations.forEach(animation => animation.cancel());
      animations.clear();
      observer?.disconnect();
    }
    document.querySelectorAll('[data-motion-toggle]').forEach(button => {
      button.hidden = false;
      button.disabled = preference.matches;
      button.setAttribute('aria-pressed', String(reduced()));
      button.textContent = preference.matches ? '系统已减少动态效果' : '减少动态效果';
    });
  };

  const bind = (root = document) => {
    root.querySelectorAll('[data-motion-toggle]').forEach(button => {
      if (button.dataset.motionBound) return;
      button.dataset.motionBound = 'true';
      button.addEventListener('click', () => {
        manualReduction = !manualReduction;
        try { localStorage.setItem(storageKey, String(manualReduction)); } catch { /* Session preference is enough. */ }
        update();
      });
    });
    update();
    if (reduced() || !window.IntersectionObserver || !Element.prototype.animate) return;
    observer ??= new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        if (reduced()) return;
        const animation = entry.target.animate([
          { opacity: .35, transform: 'translateY(12px)' },
          { opacity: 1, transform: 'translateY(0)' },
        ], { duration: 360, delay: Number(entry.target.dataset.motionOrder || 0) * 45,
          easing: 'cubic-bezier(.22, 1, .36, 1)' });
        animations.add(animation);
        animation.finished.then(() => animations.delete(animation), () => animations.delete(animation));
      });
    }, { threshold: .08 });
    root.querySelectorAll('.camp-banner, .page-head, .start-links > a, .mod-card, .download-feature, .software-shots > figure').forEach((element, index) => {
      if (element.dataset.motionSeen) return;
      element.dataset.motionSeen = 'true';
      element.dataset.motionOrder = String(index % 3);
      observer.observe(element);
    });
  };

  preference.addEventListener('change', () => { update(); if (!reduced()) bind(); });
  window.BBMODPresentation = { bind };
})();
