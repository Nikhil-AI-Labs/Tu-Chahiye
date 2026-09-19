# Tu Chahiye

Everything for the B.Tech EC Semester V mid-sem at SVNIT Surat, on one desk: five subjects
written out in full, five quizzes with live leaderboards, and every past paper we could find
worked out question by question — plus a predicted paper for each subject.

Static HTML. No build step, no framework, no bundler. Open `index.html` and it works.

---

## 1. Before you deploy — run the SQL, once

The leaderboards talk to Supabase. Two of the five tables already existed; three were created
for this app, and there is **one clean-up line you should run**.

1. Supabase dashboard → project `trlbvgevoznwnbbihigk` → **SQL Editor** → **New query**
2. Paste the whole of [`supabase.sql`](supabase.sql) and press **Run**

It is safe to run twice. It creates the three new tables if they are missing, applies the three
row-level-security policies to each, and at the bottom removes a probe row.

> **The probe row.** While checking that the three new boards actually accept a score, one row
> (`slug = 'zz-selftest'`, name `zz selftest`, score 7) was written to each of the DCN, DComm and
> DSP tables. It confirmed that a score can be submitted, that a finished score **cannot** be
> edited afterwards, and that nothing can be deleted from the page — which also means the page
> cannot take it back out. The last three lines of `supabase.sql` do. Until you run them, those
> three boards each show one junk entry.

### What the policies actually do

The key in the quiz pages is Supabase's **publishable** key. It is meant to be public — it is in
the HTML, and that is fine. The protection is the three policies, not the key:

| policy | what it allows |
| --- | --- |
| `tc_read` | anyone may read the board |
| `tc_claim` | anyone may insert their row once — the primary key on `slug` blocks a second attempt |
| `tc_finish` | a row may be updated **only while `status = 'playing'`**, so a submitted score is frozen |

There is deliberately no delete policy. Nothing the page can do removes a score; only you can,
from the SQL editor.

---

## 2. Deploy to Vercel

Any one of these. The project is static, so there is nothing to configure — `vercel.json` only
sets a few headers.

**Drag and drop (easiest).** Go to [vercel.com/new](https://vercel.com/new), drop the
`Tu-Chahiye` folder onto the page, deploy.

**CLI.**

```bash
npm i -g vercel
cd Tu-Chahiye
vercel            # preview URL
vercel --prod     # the real one
```

**From Git.** Push this folder to a repo and import it on Vercel. When it asks:

- Framework preset: **Other**
- Build command: *leave empty*
- Output directory: *leave empty* (or `.` if it insists)

Then send your friends the URL. Nothing else needs to happen.

---

## 3. Installing it on a phone

It is a progressive web app, so on Android it installs as a real app — its own icon in the
drawer, no address bar, and it appears in the app switcher like anything else. Chrome builds a
WebAPK for it behind the scenes. Nothing goes near a store.

**On Android (Chrome, Edge, Samsung Internet).** Open the site, scroll to *Take it offline*, and
press **Install the app**. If that panel does not appear, the browser has not offered it yet —
open the ⋮ menu and choose **Install app**. Either way you get the installed version, not a
bookmark.

**On iPhone.** Safari has no install prompt. Tap **Share → Add to Home Screen**. It opens
without Safari's chrome and works offline, but iOS does not give it a place in the app library
the way Android does. That is Apple's limit, not the site's.

### Why it was only making a shortcut before

A browser will only offer a real install when all three of these are true. The site had none of
them; it has all three now.

| | file |
|---|---|
| a web app manifest, with 192px and 512px icons | `manifest.webmanifest`, `icons/` |
| a registered service worker **with a fetch handler** | `sw.js`, registered by `assets/pwa.js` |
| served over HTTPS | Vercel already does this |

Without the manifest and the worker, "Add to Home Screen" only ever writes a bookmark that opens
in a browser tab. That is what was happening.

### What the service worker does

Two things. It is what makes the install offer appear at all, and it makes every page you have
already opened work with no signal — which matters, because the library has none.

| | strategy |
|---|---|
| pages | network first, falling back to the copy from last time |
| CSS, JS, fonts | cache first, refreshed in the background |
| figures | cache first — they never change once published |
| PDFs and the scanned papers | never cached; 32 MB has no business in a cache |
| Supabase | never touched, so a leaderboard is never served stale |

A page you have never opened, with no connection, gets `offline.html` instead of a browser error.

**After you change a page**, the worker serves the new one on the next load automatically. If you
change `sw.js` itself, bump `VERSION` at the top — that throws away every old cache.

---

## 4. What is in here

```
Tu-Chahiye/
├── index.html              the dashboard — subjects, quizzes, papers, downloads, countdown
├── downloads.html          every PDF in one place
├── revision/
│   └── {dcn,dcomm,dsp,dip,oops}.html     the short version, with a summaries-only mode
├── notes/
│   ├── dcn.html            EC321  Communication Networks
│   ├── dcomm.html          EC301  Digital Communication
│   ├── dip.html            EC341  Digital Image Processing  (6.5 MB — the slide figures)
│   ├── dsp.html            EC303  Digital Signal Processing
│   └── oops.html           C++    Object Oriented Programming
├── quiz/
│   └── {dcn,dcomm,dsp,dip,oops}.html     40 questions, 90 points, one attempt each
├── papers/
│   ├── index.html          the hub — what each prediction bets on, and the method
│   ├── archive.html        the previous year papers, as the original scans
│   ├── archive/            13 scanned question papers, 2022–2025, one PDF each
│   ├── fig/                figures cropped off the original papers
│   └── {dcn,dcomm,dsp,dip,oops}.html     past papers solved + the predicted paper
├── pdf/                    20 generated PDFs — revision, notes, papers and quizzes
├── assets/
│   ├── press.css           the house style
│   ├── paper.css           the question-paper pages
│   ├── print.css           the print / PDF layout for the app pages
│   ├── revision.css        the revision sheets
│   ├── revision.js         the summaries-only switch, the index, the theme
│   ├── notes-theme.css     puts the five older note pages on the house theme, screen and print
│   ├── notes-theme.js      shared theme switch, chapter reveals, print helper
│   ├── fig/                37 computed figures, generated by tools/make-figures.py
│   ├── math.css            the typeset mathematics, on this stock and at this measure
│   ├── katex/              KaTeX stylesheet and faces, self-hosted, woff2 only
│   ├── pwa.js              registers the worker, drives the install button
│   ├── motion.css          the motion layer
│   └── motion.js           masthead, reveals, tallies, clock, print helper
├── tools/
│   ├── make-pdfs.py        rebuilds everything in pdf/ — run it after editing a page
│   ├── make-figures.py     the 37 computed figures, simulated rather than drawn
│   ├── tex.py              reads the ASCII maths dialect, writes LaTeX
│   ├── mathpass.py         typesets every equation on every page, at build time
│   ├── prosemath.py        real symbols for the notation inside running prose
│   ├── render-math.js      KaTeX, called once with the whole batch
│   └── vendor/katex.min.js build-time only — it is never served to a browser
├── supabase.sql            run this once
└── vercel.json
```

**120** solved paper answers across **11** past papers, **5** predicted papers, **200** quiz
questions, roughly 200 chapters of notes, **60** revision chapters with **320** summary lines,
**87** diagrams, **1,150** typeset expressions, **20** generated PDFs and **13** original
scans.

---

## 5. The revision sheets

Four things now exist for every subject: the course, the quiz, the papers, and **the revision
sheet**. They are not the same thing as the course.

The course explains. The revision sheet reminds. Each subject gets nine to twelve chapters, each
a screen or two — a short opening, numbered sections, a comparison table wherever two things are
being told apart, one diagram where a diagram settles it, a worked example with the arithmetic
shown, and then a box of four to six lines that *are* the whole chapter.

**The switch in the margin is the point.** "Just the summaries" hides every chapter body and
leaves nothing but those boxes. That is the last hour before a paper, and the choice is
remembered in `tc.revmode`.

The content lives in `scratchpad/rev_<key>.py` as a plain data file and is rendered by
`scratchpad/revgen.py`. A chapter is a list of blocks — `h`, `p`, `num`, `bul`, `call`, `tip`,
`warn`, `tab`, `eqn`, `fig`, `scan`, `work` — plus its `glance` lines. To change a chapter, edit
the data file and run it.

The diagrams are SVG, generated by `scratchpad/fig_*.py` and collected in `svgfig.py`. They use
`currentColor` and `var(--spot)`, so every one of them inherits the page's ink and flips with the
theme without a second copy existing. A figure whose id has not been drawn renders as nothing
rather than as a hole.

---

## 6. The figures

Three different kinds, and it is worth knowing which is which, because they are
labelled differently on the page.

**Computed** — `assets/fig/`, 37 files, made by `tools/make-figures.py`. These are
*simulations*, not drawings. The sine gratings really are `0.5 + 0.5*np.sin(2*np.pi*8*x/N)`;
their spectra really are `np.fft.fft2` of those gratings; the median-filtered image really has
been through a 3×3 median. Nothing is an artist's impression of what the maths would do, which
means the numbers printed on them — the measured standard deviation before and after
equalisation, the mean error of each smoother, the simulated ALOHA throughput — are measurements
rather than claims.

```bash
pip install numpy scipy matplotlib pillow
python tools/make-figures.py            # all of them
python tools/make-figures.py histeq     # or just the ones whose name matches
```

Fourteen of them belong to the DSP course's Unit 6 and DFT sections: the four linear-phase families, the zeros of an 11-tap low-pass found with `np.roots`, the window family with every side lobe measured, Gibbs at 11, 61 and 101 taps, the Kaiser window, the two worked designs, frequency sampling with and without a transition sample, the differentiator and Hilbert transformer, DFT symmetry, the circular-shift ring, Goertzel against the FFT, and overlap-add / overlap-save on the class example. Every filter in them was designed with the formulas the page states, and every dB figure in a caption was read off the computed response.

They are PNGs, and they sit on a lit plate that does **not** invert in dark mode — inverting a
photograph of a spectrum would show a negative, which would be wrong. A print tipped onto a dark
page stays light.

**Drawn** — SVG, generated by `scratchpad/fig_*.py` and collected in `svgfig.py`. Schematics:
flow charts, timing diagrams, block diagrams, trees. They use `currentColor` and `var(--spot)`,
so every one inherits the page's ink and flips with the theme without a second copy existing.

**From the paper** — `papers/fig/`, crops lifted off the original scans and levelled. Evidence,
framed and labelled as such.

Anywhere in a question, a solution or a worked example you can write
`@@FIG:name|caption@@` and the right kind of figure is substituted at that exact spot —
`@@FIG:img:dip-histeq|…@@` for a computed one, `@@FIG:dcn-walsh|…@@` for a drawn one.

---

## 7. The mathematics

Every expression on these pages is **typeset at build time**. The browser is sent
finished markup and a stylesheet, and no maths JavaScript at all — which is why an
equation still sets itself correctly when it is printed, when it is exported to PDF,
and on a phone with no signal.

1038 expressions are set this way: 720 display blocks and 318 inline.

### How it is done

The pages were written with ASCII stand-ins — `sum_{n=0}^{N-1}`, `sqrt(2)`,
`e^(-j*2*pi/N)`, `<=`, `Rb/2`, `alpha`. A reader had to decode that before they could
read it, which is exactly backwards. Three pieces fix it.

**`tools/tex.py`** parses that dialect and emits LaTeX. It is a tokeniser and a
recursive-descent parser rather than a pile of regular expressions, because the
interesting rewrites need to know where an operand starts and stops: `a/b` only becomes
a fraction if you know what `a` and `b` are, and `2/255^2` has to come out as a fraction
whose denominator is the whole power. It also carries a dictionary of what this corpus's
names mean, per subject — `Rb` is the bit rate, not R times b; in DSP `w` is angular
frequency, in DIP it is a mask weight; `a_n` in Digital Communication is the nth symbol
even though a bare `a` there is the roll-off factor. It reads the dialect the way the
notes were actually written: `round-trip` and `non-zero` are words, not subtractions;
`i.e.` is an abbreviation, not i times e; `j0.3536` is j times a decimal; `50 000` is
fifty thousand; `SUM SUM w(s,t)` with `s t` written underneath is a double sum with its
indices; `[2 1 3 1; 1 2 1 3; ...]` is a matrix; two statements set side by side on one
line (`x(0) = ... = 4    x(1) = ...`) stay two statements; and a remark that is really
mathematics (`= A^2/2`, `check: 42 = 6 x 7`) is set as mathematics.

**`tools/mathpass.py`** walks the built pages, decides what is really an equation, and
replaces it. A multi-line derivation becomes one `aligned` block, on its first relation.
A block that is really a matrix — a mask, a pixel window — becomes a bracketed matrix.
An inline `<code>` span that is really an expression becomes inline maths. A line that
is a sentence stays a sentence, set as text within the block, with any formula inside it
still set as a formula.

**`tools/prosemath.py`** handles the quiz banks, which are a different problem. Those are
conversational sentences with notation in them, and setting `2^b` in Computer Modern in
the middle of one puts two typefaces inside a single expression. So prose gets the
symbols and nothing else: a real superscript, a real multiplication sign, a real pi.

```bash
python tools/mathpass.py            # every page
python tools/mathpass.py revision   # one section
python tools/mathpass.py --report   # convert nothing, just list
python tools/prosemath.py
```

Both are idempotent — anything already set is skipped — so they are safe to re-run, and
safe over the imported course pages, which are never regenerated. Run them after
`genpaper` or `revgen`, and rebuild the PDFs afterwards.

### What it deliberately leaves alone

Source code and program output, bit patterns, tables (labelled rows of numbers, whose
columns only line up in monospace), character diagrams, lists of sentences, anything
carrying markup it cannot read, and anything the parser cannot read with confidence. A
monospace block is a
perfectly good fallback; a mangled equation is not. Every skip is counted and every
failure is written to `tools/_math/report.txt`, together with the before-and-after of
every single conversion, so nothing is quietly dropped and the whole run is reviewable.

### The type

KaTeX's Computer Modern — a book face from exactly the era this design is pretending to
be printed in, so it belongs. Words inside an equation are set in the page's own face
instead, because a formula with a label in it should not look like two documents.

`assets/katex/` is self-hosted and trimmed to woff2 only. Twenty faces ship; **six** are
ever actually requested, and those six are precached by the service worker. The rest are
left in place so that no `@font-face` can ever point at a missing file.

### On a phone

A derivation does not reflow — reflowing an equation destroys the alignment that is the
whole reason to set it — so it scrolls, and says so with a 2px bar in the spot ink. Three
things keep that scrolling rare:

* a long remark drops to its own row rather than sitting in a third column, because in an
  `aligned` block the column widths are shared and one long aside widens every line;
* the panel reaches back over the question-number column, which is 15% of a phone screen;
* and it runs to the edge of the sheet, which is another 9%.

Worst case on `papers/dip.html` at 390px went from 443px of overflow to 244px this way.

---

## 8. The quizzes

Each quiz is one self-contained file. The bits you might want to change sit together near the
top of the script block:

```js
var SUPABASE_URL   = "https://trlbvgevoznwnbbihigk.supabase.co";
var SUPABASE_KEY   = "sb_publishable_...";
var SUPABASE_TABLE = "dcn_quiz_scores";
```

and a little lower, the key it saves progress under:

```js
var LS_KEY = "dcnquiz.v1";
```

How they behave:

- **40 questions, 90 points** — 10 easy (1), 10 medium (2), 20 hard (3).
- **One attempt per name.** The name becomes a slug (lower-cased, spaces to hyphens) and that
  slug is the primary key, so the second attempt is refused by the database, not by the page.
- **45:00 on the clock**, and it submits for you at zero.
- **Resumable.** Close the tab by accident and the same link puts you back on the same question
  with the time that was left.
- **Shuffled per person.** The question order is seeded from the name, so two people sitting it
  side by side do not see the same order.
- **Answer key** opens after you submit.

To let one person sit a quiz again, delete their row:

```sql
delete from public.dcn_quiz_scores where slug = 'nikhil';
```

To clear a whole board before sharing it around:

```sql
truncate public.dcn_quiz_scores;
```

---

## 9. The PDFs

Everything on the site also exists as a PDF, and there are two different kinds.

**Generated from the pages** — `pdf/`, 20 files, 1,358 pages, 32 MB:

| file | what it is |
| --- | --- |
| `revision-<key>.pdf` | the short version, chapter by chapter, summaries included |
| `notes-<key>.pdf` | the whole subject, every chapter starting on its own sheet, figures included |
| `papers-<key>.pdf` | the past papers and the predicted paper, every solution already open |
| `quiz-<key>.pdf` | the 40 questions as a printable question paper, answer key and explanations at the back |

These are rendered from the same HTML and the same stylesheets the site uses, through
`assets/print.css` — a real print layout, not a screenshot of a web page. The dark sheet becomes
paper, the navigation goes, the halftone comes off, the spot inks stay, and nothing that belongs
together is split across a page break.

`make-pdfs.py` starts a small HTTP server and renders through that rather than from a `file://`
URL. It matters: under `file://` a root-absolute path resolves against the drive root and simply
fails, silently — which is exactly what had been happening to the maths faces and to every
computed figure placed by an `@@FIG:img:…@@` marker. Rendering over HTTP means the PDF is made
from precisely what the deployed site serves.

The printed column is 184 mm wide. On screen a formula or code block wider than its column
scrolls sideways; on paper Chromium's answer is to shrink the *whole document* until the
widest box fits, which is why earlier PDFs came out with 8.5 pt body text instead of the
10.5 pt the stylesheet asks for. So before each page is printed it is laid out at the
printed width, and every box still wider than its column is shrunk to fit — only that
box, and only as much as it needs. Everything else now prints at its designed size, which
is also why the PDFs run to more pages than they used to.

**After you edit any page, rebuild them:**

```bash
pip install playwright pymupdf
python -m playwright install chromium
python tools/make-pdfs.py          # about a minute
```

**The original question papers** — `papers/archive/`, 13 files, 9.3 MB. These are the scans as
they were handed out, not our transcription. They are listed subject by subject on
`papers/archive.html`, with the page count and size of each, and every one of them is worked out
question by question on that subject's own page.

**Or make your own, at any moment.** Press <kbd>Ctrl</kbd>+<kbd>P</kbd> (<kbd>⌘</kbd>+<kbd>P</kbd>
on a Mac) on any page and choose *Save as PDF*; on a phone it is under Share → Print. Every
collapsed solution opens itself before the dialog appears, so what you get is the full document.

---

## 10. Changing things

**The exam date and countdown** — the mid-sem starts 21 September 2026. One line in `index.html`, near the bottom:

```js
var EXAM = new Date(2026, 8, 21, 9, 0, 0);   /* months are 0-based: 8 = September */
```

**An equation** — edit the plain text in the source block and re-run
`python tools/mathpass.py`; it will re-typeset the page. If an expression will not parse it is
left as monospace and named in `tools/_math/report.txt`, which also carries the before and after
of every conversion, so a bad reading is findable rather than invisible. Rebuild the PDFs
afterwards.

**A subject's ink** — `assets/press.css`, in `:root`, with a matching pair in each of the two
dark blocks below it:

```css
--dcn:#1E8A5F;    --dcn-wash:#CDE8DC;
```

Every page that shows that subject picks the colour up from there.

**The note pages' look** — `assets/notes-theme.css`. The five note documents were each written
with their own palette and their own typeface pairing. That file does not touch a word of their
content; it re-points the custom properties they already use at the house tokens, so all five
read as one publication. Delete the `<link>` to it in a note page and that page goes back to
exactly how it was.

**Motion** — `assets/motion.css` / `motion.js`. Everything is small, fast and once-only, and
every rule is switched off under `prefers-reduced-motion: reduce`. Delete both files and the
site still works; it just stops moving.

---

## 11. Notes on the design

- **The syllabus spread** on the dashboard is the one full-bleed block on the site: five subjects
  down, 53 topics across, a solid spot-ink square where that topic was asked that year. It is
  generated by `scratchpad/spread.py` straight from the `pattern=[...]` lists inside the paper
  generators, so it can never drift from the solutions. Re-run it after editing a pattern list.
- **The masthead is three impressions, not one.** Pink and blue plates sit 8px either side of the
  black one and overprint with `mix-blend-mode`. They follow the pointer, in whole pixels only.
  They do not animate on their own — a printed sheet does not wobble, and a plate drifting across
  fractional device pixels is what made the title look out of focus in the first place.

- Two house inks — pink `#C21254` and blue `#0B5FC0` — plus one spot ink per subject, printed
  on a warm grey stock `#EAE8E1`. Every ink was picked so that the stock flooded on it clears
  4.5:1, which is why the pink is not the brighter `#DC1F68` it started as.
- **No rounded corners and no shadows anywhere.** Rules and flooded ink fields do the
  separating. That rule is enforced even on the older note pages.
- Type: Big Shoulders Display for headings, Familjen Grotesk for reading, JetBrains Mono for
  labels and data.
- Dark mode follows the system and can be overridden; the choice is remembered in `tc.theme`
  and it follows you across every page in the app.
- Built to the 44px minimum tap target, with `env(safe-area-inset-*)` respected, and answering
  `prefers-reduced-motion`, `prefers-reduced-transparency` and `prefers-contrast` separately.

---

## 12. One honest paragraph about the predicted papers

They are a reading of a pattern, not a leak. Each subject's paper page opens with a grid — topic
down the side, year across the top, a filled square where it appeared — and that table is doing
the predicting. Where a scan was too faint to read, the page says so instead of inventing the
question. C++ has no past paper at all, and its page says so in a section of its own.

Every number in every solution was computed rather than quoted. If you find one that is wrong,
it is wrong — say so and it gets fixed.
