/* ==========================================================================
   TU CHAHIYE — install and offline
   Registers the service worker, and turns the browser's install offer into a
   button in the page rather than a banner the reader has to go looking for.
   ========================================================================== */
(function () {
  "use strict";

  /* ------------------------------------------------------ the worker */
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).then(function (reg) {
        /* a new version is waiting: take it on the next load, quietly */
        if (reg.waiting) reg.waiting.postMessage("skip-waiting");
        reg.addEventListener("updatefound", function () {
          var w = reg.installing;
          if (!w) return;
          w.addEventListener("statechange", function () {
            if (w.state === "installed" && navigator.serviceWorker.controller) {
              w.postMessage("skip-waiting");
            }
          });
        });
      })["catch"](function () { /* no worker is not a broken site */ });
    });
  }

  /* ------------------------------------------------------ the install */
  var deferred = null;
  var btn = document.querySelector("[data-install]");
  var row = document.querySelector("[data-install-row]");

  function show(state) {
    if (!row) return;
    row.setAttribute("data-state", state);
    row.hidden = false;
  }

  function installed() {
    return window.matchMedia("(display-mode: standalone)").matches ||
           window.navigator.standalone === true;
  }

  if (installed()) {
    show("done");
  }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    show("ready");
  });

  if (btn) {
    btn.addEventListener("click", function () {
      if (!deferred) { show("how"); return; }
      deferred.prompt();
      deferred.userChoice.then(function (r) {
        deferred = null;
        show(r && r.outcome === "accepted" ? "done" : "ready");
      });
    });
  }

  window.addEventListener("appinstalled", function () {
    deferred = null;
    show("done");
  });

  /* iOS never fires beforeinstallprompt, so say how it is done there */
  var ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  if (ios && !installed()) show("ios");
})();
