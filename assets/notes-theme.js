/* ==========================================================================
   TU CHAHIYE — the small amount of behaviour the note pages share.
   Three things, and nothing else: the light/dark switch is remembered across
   the whole app, chapters arrive as you reach them, and the app bar knows
   when it has left the top of the page.
   ========================================================================== */
(function () {
  "use strict";

  var KEY = "tc.theme";
  var root = document.documentElement;
  var still = window.matchMedia && window.matchMedia("(prefers-reduced-motion:reduce)").matches;

  /* ---------------------------------------------------- the theme switch */
  function read() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function write(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  function nowDark() {
    var set = root.getAttribute("data-theme");
    if (set) return set === "dark";
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme:dark)").matches);
  }

  var btn = document.querySelector(".tcb-tog");
  function label() {
    if (!btn) return;
    var d = nowDark();
    btn.textContent = d ? "Light" : "Dark";
    btn.setAttribute("aria-label", d ? "Switch to the light sheet" : "Switch to the dark sheet");
  }
  if (btn) {
    btn.addEventListener("click", function () {
      var next = nowDark() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      write(next);
      label();
    });
    label();
    if (window.matchMedia) {
      try {
        window.matchMedia("(prefers-color-scheme:dark)").addEventListener("change", label);
      } catch (e) {}
    }
  }

  /* DSP carries a switch of its own from before the app existed. Let it keep
     working, but mirror whatever it does into the shared key so the choice
     survives the walk back to the dashboard. */
  if (window.MutationObserver) {
    new MutationObserver(function () {
      var v = root.getAttribute("data-theme");
      if (v && v !== read()) write(v);
      label();
    }).observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  }

  /* ------------------------------------------------- the bar leaves the top */
  var bar = document.querySelector(".tcbar");
  if (bar) {
    var stuck = false;
    var onScroll = function () {
      var s = window.scrollY > 4;
      if (s !== stuck) { stuck = s; bar.classList.toggle("off-top", s); }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }


  /* ==================================================== 5. on the way to paper */
  /* A closed <details> prints as a title with nothing under it, so every
     solution is opened for the print dialog and shut again afterwards. */
  function openAll() {
    var d = document.querySelectorAll("details");
    for (var i = 0; i < d.length; i++) {
      if (!d[i].open) { d[i].setAttribute("data-was-shut", "1"); d[i].open = true; }
    }
  }
  function shutBack() {
    var d = document.querySelectorAll("details[data-was-shut]");
    for (var i = 0; i < d.length; i++) {
      d[i].open = false; d[i].removeAttribute("data-was-shut");
    }
  }
  window.addEventListener("beforeprint", openAll);
  window.addEventListener("afterprint", shutBack);
  if (window.matchMedia) {
    try {
      window.matchMedia("print").addEventListener("change", function (e) {
        if (e.matches) openAll(); else shutBack();
      });
    } catch (e) {}
  }

  /* anything marked data-print asks the browser for the print dialog, which
     is where "Save as PDF" lives on every platform including a phone */
  var pb = document.querySelectorAll("[data-print]");
  for (var z = 0; z < pb.length; z++) {
    pb[z].addEventListener("click", function (ev) {
      ev.preventDefault(); openAll(); window.print();
    });
  }

  /* --------------------------------------------- chapters arrive on approach */
  if (still || !("IntersectionObserver" in window)) return;

  var sel = "section.ch, section.module, section.unithead, article.ch, figure, h2[id], h3[id]";
  var all = [].slice.call(document.querySelectorAll(sel), 0, 600);

  /* never animate something that already sits inside something animating */
  var targets = [];
  for (var i = 0; i < all.length; i++) {
    var el = all[i], nested = false, p = el.parentNode;
    while (p && p.nodeType === 1) {
      if (p.classList && p.classList.contains("tc-rv")) { nested = true; break; }
      p = p.parentNode;
    }
    if (!nested) { el.classList.add("tc-rv"); targets.push(el); }
  }
  if (!targets.length) return;

  var io = new IntersectionObserver(function (entries) {
    for (var j = 0; j < entries.length; j++) {
      var e = entries[j];
      if (!e.isIntersecting) continue;
      e.target.classList.add("tc-in");
      io.unobserve(e.target);
    }
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.02 });

  targets.forEach(function (t) { io.observe(t); });

  /* anything already on screen at load should not fade in after the fact */
  requestAnimationFrame(function () {
    var h = window.innerHeight;
    targets.forEach(function (t) {
      if (t.getBoundingClientRect().top < h) { t.classList.add("tc-in"); io.unobserve(t); }
    });
  });
})();
