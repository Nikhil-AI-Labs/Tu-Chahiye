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

## 3. What is in here

```
Tu-Chahiye/
├── index.html              the dashboard — subjects, quizzes, papers, downloads, countdown
├── downloads.html          every PDF in one place
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
│   └── {dcn,dcomm,dsp,dip,oops}.html     past papers solved + the predicted paper
├── pdf/                    15 generated PDFs — notes, papers and quizzes, one per subject
├── assets/
│   ├── press.css           the house style
│   ├── paper.css           the question-paper pages
│   ├── print.css           the print / PDF layout for the app pages
│   ├── notes-theme.css     puts the five older note pages on the house theme, screen and print
│   ├── notes-theme.js      shared theme switch, chapter reveals, print helper
│   ├── motion.css          the motion layer
│   └── motion.js           masthead, reveals, tallies, clock, print helper
├── tools/
│   └── make-pdfs.py        rebuilds everything in pdf/ — run it after editing a page
├── supabase.sql            run this once
└── vercel.json
```

**120** solved paper answers across **11** past papers, **5** predicted papers, **200** quiz
questions, roughly 200 chapters of notes, **15** generated PDFs and **13** original scans.

---

## 4. The quizzes

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

## 5. The PDFs

Everything on the site also exists as a PDF, and there are two different kinds.

**Generated from the pages** — `pdf/`, 15 files, about 23 MB:

| file | what it is |
| --- | --- |
| `notes-<key>.pdf` | the whole subject, every chapter starting on its own sheet, figures included |
| `papers-<key>.pdf` | the past papers and the predicted paper, every solution already open |
| `quiz-<key>.pdf` | the 40 questions as a printable question paper, answer key and explanations at the back |

These are rendered from the same HTML and the same stylesheets the site uses, through
`assets/print.css` — a real print layout, not a screenshot of a web page. The dark sheet becomes
paper, the navigation goes, the halftone comes off, the spot inks stay, and nothing that belongs
together is split across a page break.

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

## 6. Changing things

**The exam date and countdown** — `index.html`, near the bottom:

```js
var EXAM = new Date(2026, 8, 22, 9, 0, 0);   /* months are 0-based: 8 = September */
```

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

## 7. Notes on the design

- Two house inks — pink `#DC1F68` and blue `#0B5FC0` — plus one spot ink per subject, printed
  on a warm grey stock `#EAE8E1`. The masthead is set twice more in the two house inks, a hair
  out of register, the way a two-colour riso print misses.
- **No rounded corners and no shadows anywhere.** Rules and flooded ink fields do the
  separating. That rule is enforced even on the older note pages.
- Type: Big Shoulders Display for headings, Familjen Grotesk for reading, JetBrains Mono for
  labels and data.
- Dark mode follows the system and can be overridden; the choice is remembered in `tc.theme`
  and it follows you across every page in the app.
- Built to the 44px minimum tap target, with `env(safe-area-inset-*)` respected, and answering
  `prefers-reduced-motion`, `prefers-reduced-transparency` and `prefers-contrast` separately.

---

## 8. One honest paragraph about the predicted papers

They are a reading of a pattern, not a leak. Each subject's paper page opens with a grid — topic
down the side, year across the top, a filled square where it appeared — and that table is doing
the predicting. Where a scan was too faint to read, the page says so instead of inventing the
question. C++ has no past paper at all, and its page says so in a section of its own.

Every number in every solution was computed rather than quoted. If you find one that is wrong,
it is wrong — say so and it gets fixed.
