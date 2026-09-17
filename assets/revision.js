/* ==========================================================================
   TU CHAHIYE — the revision sheets
   Three behaviours: the theme switch is shared with the rest of the app, the
   index follows where you are, and the mode switch strips the page down to
   nothing but the chapter summaries — which is what the last hour before an
   exam is actually for.
   ========================================================================== */
(function () {
  "use strict";

  var root = document.documentElement;
  var KEY = "tc.theme";
  var MODE = "tc.revmode";

  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  /* ------------------------------------------------------------- the theme */
  function isDark() {
    var s = root.getAttribute("data-theme");
    if (s) return s === "dark";
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme:dark)").matches);
  }
  var tog = document.querySelector(".tcb-tog");
  function label() {
    if (!tog) return;
    var d = isDark();
    tog.textContent = d ? "Light" : "Dark";
    tog.setAttribute("aria-label", d ? "Switch to the light sheet" : "Switch to the dark sheet");
  }
  if (tog) {
    tog.addEventListener("click", function () {
      var next = isDark() ? "light" : "dark";
      root.setAttribute("data-theme", next); set(KEY, next); label();
    });
    label();
    if (window.matchMedia) {
      try { window.matchMedia("(prefers-color-scheme:dark)").addEventListener("change", label); }
      catch (e) {}
    }
  }

  /* --------------------------------------------------------- the bar shadow */
  var bar = document.querySelector(".tcbar"), stuck = false;
  if (bar) {
    var onScroll = function () {
      var s = window.scrollY > 4;
      if (s !== stuck) { stuck = s; bar.classList.toggle("off-top", s); }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ------------------------------------------------------- summaries only */
  var modes = [].slice.call(document.querySelectorAll(".mode"));
  function apply(m, remember) {
    document.body.classList.toggle("glance-only", m === "glance");
    modes.forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-mode") === m); });
    if (remember) set(MODE, m);
  }
  modes.forEach(function (b) {
    b.addEventListener("click", function () {
      var here = nearest();
      apply(b.getAttribute("data-mode"), true);
      /* keep the reader where they were, not wherever the shorter page lands */
      if (here) here.scrollIntoView({ block: "start", behavior: "auto" });
    });
  });
  apply(get(MODE) === "glance" ? "glance" : "all", false);

  /* ------------------------------------------------- the index follows you */
  var links = [].slice.call(document.querySelectorAll(".toc a"));
  var secs = links.map(function (a) {
    return document.querySelector(a.getAttribute("href"));
  });

  function nearest() {
    var y = window.scrollY + 120, best = null;
    for (var i = 0; i < secs.length; i++) {
      if (secs[i] && secs[i].offsetTop <= y) best = secs[i];
    }
    return best;
  }

  var ticking = false;
  function sync() {
    ticking = false;
    var y = window.scrollY + 140, best = 0;
    for (var i = 0; i < secs.length; i++) {
      if (secs[i] && secs[i].offsetTop <= y) best = i;
    }
    for (var j = 0; j < links.length; j++) {
      links[j].classList.toggle("on", j === best);
    }
    /* drag the index along so the current chapter stays in view */
    var rail = document.querySelector(".rail"), on = links[best];
    if (rail && on && rail.scrollHeight > rail.clientHeight) {
      var r = on.getBoundingClientRect(), rr = rail.getBoundingClientRect();
      if (r.top < rr.top + 40 || r.bottom > rr.bottom - 40) {
        rail.scrollTop += (r.top - rr.top) - rail.clientHeight * 0.4;
      }
    }
  }
  if (links.length) {
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(sync); }
    }, { passive: true });
    window.addEventListener("resize", sync, { passive: true });
    sync();
  }

  /* ------------------------------------------------------- on the way to paper */
  function openAll() {
    var d = document.querySelectorAll("details");
    for (var i = 0; i < d.length; i++) {
      if (!d[i].open) { d[i].setAttribute("data-was-shut", "1"); d[i].open = true; }
    }
  }
  function shutBack() {
    var d = document.querySelectorAll("details[data-was-shut]");
    for (var i = 0; i < d.length; i++) { d[i].open = false; d[i].removeAttribute("data-was-shut"); }
  }
  window.addEventListener("beforeprint", openAll);
  window.addEventListener("afterprint", shutBack);
})();
