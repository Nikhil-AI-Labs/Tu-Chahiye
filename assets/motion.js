/* ==========================================================================
   TU CHAHIYE — motion
   Four small behaviours, no library, no dependencies, ~2 KB.
     1. the masthead sets itself letter by letter on load
     2. sections arrive from 14px below as you reach them, in short bursts
     3. the tally numbers roll up once
     4. the clock in the press strip runs on Surat time
   Everything checks prefers-reduced-motion first and does nothing if it is set.
   ========================================================================== */
(function () {
  "use strict";

  var still = window.matchMedia && window.matchMedia("(prefers-reduced-motion:reduce)").matches;
  var io = "IntersectionObserver" in window;

  /* ====================================================== 1. the masthead */
  /* Split each word into letters without breaking how the word wraps: the
     word stays one inline-block, the letters sit inside it. */
  function esc(ch) {
    return ch === "&" ? "&amp;" : ch === "<" ? "&lt;" : ch === ">" ? "&gt;" : ch;
  }

  function cut(text, start) {
    /* one <span class="ltr"> per glyph; spaces stay as spaces so the word
       still wraps where it always wrapped */
    var out = "", n = start;
    for (var c = 0; c < text.length; c++) {
      var ch = text.charAt(c);
      if (ch === " " || ch === " " || ch === "\n" || ch === "\t") { out += ch; continue; }
      out += '<span class="ltr" style="--i:' + (n++) + '">' + esc(ch) + "</span>";
    }
    return { html: out, n: n };
  }

  function setType(host) {
    if (!host || host.getAttribute("data-set")) return 0;
    host.setAttribute("data-set", "1");
    var words = host.querySelectorAll("span"), n = 0, r;
    if (words.length) {
      /* the markup already carries one span per line — keep that structure */
      for (var w = 0; w < words.length; w++) {
        r = cut(words[w].textContent, n);
        words[w].innerHTML = r.html;
        n = r.n;
      }
    } else {
      r = cut(host.textContent, 0);
      host.innerHTML = r.html;
      n = r.n;
    }
    return n;
  }

  var mis = document.querySelector(".mislay") || document.querySelector(".mast");
  if (mis && !still) {
    var hosts = mis.querySelectorAll("h1, .ghost");
    var count = 0;
    for (var i = 0; i < hosts.length; i++) count = Math.max(count, setType(hosts[i]));
    if (count) {
      mis.classList.add("setting");
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          mis.classList.remove("setting");
          mis.classList.add("set");
          /* the off-register plates slide in — but only where they are not
             already carrying a slow slip of their own */
          [".g1", ".g2"].forEach(function (s) {
            var g = mis.querySelector(s);
            if (!g) return;
            var running = getComputedStyle(g).animationName;
            if (!running || running === "none") g.classList.add("plate-in");
          });
        });
      });
    }
  }

  /* ================================================ 2. sections on approach */
  var SEL = [
    ".row", ".qclip", ".qcard", ".prow", ".trio > div",
    ".sechead", ".tally > div", ".steps > div", ".band > .note",
    ".band > .caveat", ".freq", ".bets", ".qp", ".pgrid"
  ].join(",");

  var marked = [];
  if (!still && io) {
    var list = document.querySelectorAll(SEL);
    var groups = {};
    for (var k = 0; k < list.length; k++) {
      var el = list[k];
      /* never animate something already inside something that animates */
      var p = el.parentNode, nested = false;
      while (p && p.nodeType === 1) {
        if (p.hasAttribute && p.hasAttribute("data-rv")) { nested = true; break; }
        p = p.parentNode;
      }
      if (nested) continue;
      el.setAttribute("data-rv", "");
      /* stagger by position among siblings, capped so nothing waits long */
      var key = el.parentNode ? (el.parentNode.className || "x") : "x";
      groups[key] = (groups[key] || 0);
      el.style.setProperty("--d", String(Math.min(groups[key]++, 4)));
      marked.push(el);
    }

    /* the heavy rules draw themselves across rather than simply being there */
    var rules = document.querySelectorAll(".rule-heavy, .rule-mid");
    for (var u = 0; u < rules.length; u++) {
      rules[u].setAttribute("data-rule", "");
      marked.push(rules[u]);
    }

    if (marked.length) {
      var obs = new IntersectionObserver(function (entries) {
        for (var j = 0; j < entries.length; j++) {
          if (!entries[j].isIntersecting) continue;
          entries[j].target.classList.add("in");
          obs.unobserve(entries[j].target);
        }
      }, { rootMargin: "0px 0px -6% 0px", threshold: 0.03 });

      marked.forEach(function (m) { obs.observe(m); });

      /* whatever is already on screen should be there, not fade in late */
      requestAnimationFrame(function () {
        var h = window.innerHeight;
        marked.forEach(function (m) {
          if (m.getBoundingClientRect().top < h * 0.92) {
            m.classList.add("in"); obs.unobserve(m);
          }
        });
      });
    }
  }

  /* ========================================================= 3. the tallies */
  var rolls = document.querySelectorAll("[data-count]");
  if (rolls.length) {
    var run = function (el) {
      var to = parseInt(el.getAttribute("data-count"), 10);
      if (isNaN(to)) return;
      if (still) { el.textContent = String(to); return; }
      var t0 = 0, dur = 780;
      var step = function (t) {
        if (!t0) t0 = t;
        var k = Math.min(1, (t - t0) / dur);
        /* the same easing as everything else, expressed as a number */
        var e = 1 - Math.pow(1 - k, 3);
        el.textContent = String(Math.round(to * e));
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    if (io && !still) {
      var ro = new IntersectionObserver(function (es) {
        for (var q = 0; q < es.length; q++) {
          if (!es[q].isIntersecting) continue;
          run(es[q].target); ro.unobserve(es[q].target);
        }
      }, { threshold: 0.4 });
      for (var r = 0; r < rolls.length; r++) { rolls[r].textContent = "0"; ro.observe(rolls[r]); }
    } else {
      for (var r2 = 0; r2 < rolls.length; r2++) run(rolls[r2]);
    }
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

  /* =========================================================== 4. the clock */
  var clk = document.querySelector("[data-clock]");
  if (clk) {
    var fmt = null;
    try {
      fmt = new Intl.DateTimeFormat("en-GB", {
        timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: false
      });
    } catch (e) {}
    var tick = function () {
      var s;
      if (fmt) {
        s = fmt.format(new Date());
      } else {
        var d = new Date(Date.now() + (330 + new Date().getTimezoneOffset()) * 60000);
        s = ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
      }
      var bits = s.split(":");
      clk.innerHTML = "Surat " + bits[0] + '<span class="sep">:</span>' + bits[1];
    };
    tick();
    setInterval(tick, 15000);
  }
})();
