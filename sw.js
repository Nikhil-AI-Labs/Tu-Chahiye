/* ==========================================================================
   TU CHAHIYE — service worker
   --------------------------------------------------------------------------
   Two jobs. It is what makes Android offer a real install rather than a
   bookmark, and it makes every page you have already opened work with no
   signal — which is the point, because the library has none.

   The strategy, per kind of file:

     HTML          network first, fall back to the copy from last time.
                   You always get the current page when there is a
                   connection, and the page you read yesterday when there
                   is not.
     CSS/JS/fonts  cache first, refreshed in the background. These change
                   rarely and blocking on them is what makes a page feel slow.
                   The maths fonts live here too, which is what lets an
                   equation still set itself with no signal.
     figures       cache first. They never change once published.
     PDFs, scans   never cached. They are 30 MB and the browser already
                   handles a download.

   Bump VERSION to invalidate everything.
   ========================================================================== */

var VERSION = 'tc-v2';   /* v2: the maths is typeset, so the stylesheets changed */
var SHELL = VERSION + '-shell';
var PAGES = VERSION + '-pages';
var MEDIA = VERSION + '-media';

/* the smallest set that makes the app usable cold */
var PRECACHE = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.webmanifest',
  '/assets/press.css',
  '/assets/motion.css',
  '/assets/motion.js',
  '/assets/pwa.js',
  '/assets/print.css',
  '/assets/math.css',
  '/assets/katex/katex.css',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  /* The six faces the expressions on these pages actually call for.
     KaTeX ships twenty; the other fourteen are never asked for, so they
     are left to load on demand if a future page ever needs one. */
  '/assets/katex/fonts/KaTeX_Main-Regular.woff2',
  '/assets/katex/fonts/KaTeX_Math-Italic.woff2',
  '/assets/katex/fonts/KaTeX_Size1-Regular.woff2',
  '/assets/katex/fonts/KaTeX_Size2-Regular.woff2',
  '/assets/katex/fonts/KaTeX_Size3-Regular.woff2',
  '/assets/katex/fonts/KaTeX_Size4-Regular.woff2'
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(SHELL).then(function (c) {
      /* one bad URL must not fail the whole install */
      return Promise.all(PRECACHE.map(function (u) {
        return c.add(new Request(u, { cache: 'reload' }))['catch'](function () {});
      }));
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k.indexOf(VERSION) !== 0) return caches['delete'](k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

function isMedia(p) {
  return /\.(png|jpe?g|gif|svg|webp|woff2?)$/i.test(p);
}
function neverCache(p) {
  return /\.pdf$/i.test(p) || p.indexOf('/pdf/') === 0 || p.indexOf('/papers/archive/') === 0;
}

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;

  var url;
  try { url = new URL(req.url); } catch (err) { return; }

  /* leave Supabase, Google Fonts and anything else off-origin alone —
     the leaderboard must never be served from a cache */
  if (url.origin !== self.location.origin) return;
  if (neverCache(url.pathname)) return;

  /* ---------------------------------------------------------- documents */
  if (req.mode === 'navigate' ||
      (req.headers.get('accept') || '').indexOf('text/html') > -1) {
    e.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(PAGES).then(function (c) { c.put(req, copy); });
        return res;
      })['catch'](function () {
        return caches.match(req).then(function (hit) {
          return hit || caches.match('/offline.html') || caches.match('/index.html');
        });
      })
    );
    return;
  }

  /* ------------------------------------------------- styles, scripts, art */
  var bucket = isMedia(url.pathname) ? MEDIA : SHELL;
  e.respondWith(
    caches.match(req).then(function (hit) {
      var live = fetch(req).then(function (res) {
        if (res && res.status === 200 && res.type === 'basic') {
          var copy = res.clone();
          caches.open(bucket).then(function (c) { c.put(req, copy); });
        }
        return res;
      })['catch'](function () { return hit; });
      return hit || live;
    })
  );
});

/* the page can ask for the new worker straight away after an update */
self.addEventListener('message', function (e) {
  if (e.data === 'skip-waiting') self.skipWaiting();
});
