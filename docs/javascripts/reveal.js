/* Scroll-reveal: JS가 직접 클래스를 부여하므로 JS 비활성 시엔 그냥 보인다(graceful). */
(function () {
  if (!("IntersectionObserver" in window)) return;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) return;

  function init() {
    var groups = [
      ".sb-head", ".sb-why__item", ".sb-feature",
      ".sb-steps li", ".sb-proof__card", ".sb-stat", ".sb-cta-final .sb-cta"
    ];
    var els = [];
    groups.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) { els.push(el); });
    });
    if (!els.length) return;

    // 같은 부모 안에서의 순번으로 stagger
    els.forEach(function (el) {
      el.classList.add("js-reveal");
      var sibs = Array.prototype.slice.call(el.parentNode.children);
      var i = sibs.indexOf(el);
      el.style.transitionDelay = Math.min(i, 6) * 70 + "ms";
    });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("is-visible"); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });

    els.forEach(function (el) { io.observe(el); });
  }

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
