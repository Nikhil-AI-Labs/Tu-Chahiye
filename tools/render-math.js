/*
 * Render a batch of TeX strings to static HTML, once, at build time.
 *
 * The browser never sees KaTeX's JavaScript. It gets the finished markup and
 * a stylesheet, which is why the maths survives printing, the PDF export and
 * a phone with no network. Output is `htmlAndMathml`: the visual layer for
 * sighted readers, a real <math> element underneath for screen readers and
 * for anyone copying an expression out.
 *
 *     node tools/render-math.js jobs.json out.json
 *
 * jobs.json  [{ id, tex, display }, ...]
 * out.json   [{ id, html, err }, ...]      err is null when it rendered
 *
 * A failure is reported, never swallowed: mathpass.py leaves the original
 * text alone when `err` comes back set, so a bad expression degrades to the
 * monospace block it was before rather than to a red KaTeX error.
 */
'use strict';

const fs = require('fs');
const katex = require('./vendor/katex.min.js');

const [, , jobsPath, outPath] = process.argv;
if (!jobsPath || !outPath) {
  console.error('usage: node tools/render-math.js <jobs.json> <out.json>');
  process.exit(2);
}

const jobs = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
const out = [];
let ok = 0;
let bad = 0;

for (const job of jobs) {
  try {
    const html = katex.renderToString(job.tex, {
      displayMode: !!job.display,
      throwOnError: true,
      strict: (code) => (code === 'unicodeTextInMathMode' ? 'ignore' : 'warn'),
      trust: false,
      output: 'htmlAndMathml',
      // \text{} should sit in the page's own face, not in Computer Modern,
      // so that a word inside an equation matches the words around it.
      macros: {
        '\\deg': '^{\\circ}',
      },
    });
    out.push({ id: job.id, html: html, err: null });
    ok++;
  } catch (e) {
    out.push({ id: job.id, html: null, err: String(e.message || e) });
    bad++;
  }
}

fs.writeFileSync(outPath, JSON.stringify(out), 'utf8');
console.error('rendered ' + ok + ' expressions, ' + bad + ' failed');
