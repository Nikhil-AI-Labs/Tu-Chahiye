# -*- coding: utf-8 -*-
"""
Tu Chahiye — build the downloadable PDFs.

    pip install playwright
    python -m playwright install chromium
    python tools/make-pdfs.py

Writes into  Tu-Chahiye/pdf/ :
    notes-<key>.pdf     the whole subject, every chapter, figures included
    papers-<key>.pdf    the past papers and the predicted paper, solutions open
    quiz-<key>.pdf      the 40 questions as a printable paper, answer key at the back

Everything is rendered from the same HTML and the same stylesheets the site
uses, with assets/print.css doing the paper layout, so the PDF and the page
are the same document.  Re-run this after editing any page.
"""
from __future__ import print_function
import io, os, sys, json, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, os.pardir))
OUT = os.path.join(APP, 'pdf')
TMP = os.path.join(HERE, '_tmp')

KEYS = ['dcn', 'dcomm', 'dsp', 'dip', 'oops']

SUBJECT = {
    'dcn':   ('EC321', 'Communication Networks',        'dcn'),
    'dcomm': ('EC301', 'Digital Communication',         'dcomm'),
    'dsp':   ('EC303', 'Digital Signal Processing',     'dsp'),
    'dip':   ('EC341', 'Digital Image Processing',      'dip'),
    'oops':  ('C++',   'Object Oriented Programming',   'oops'),
}

TODAY = datetime.date.today().strftime('%d %B %Y')

HDR = ('<div style="font-family:Arial,sans-serif;font-size:7px;letter-spacing:.14em;'
       'text-transform:uppercase;color:#8a8a92;width:100%;padding:0 14mm;'
       'display:flex;justify-content:space-between">'
       '<span>Tu Chahiye</span><span>{label}</span></div>')

FTR = ('<div style="font-family:Arial,sans-serif;font-size:7px;letter-spacing:.14em;'
       'text-transform:uppercase;color:#8a8a92;width:100%;padding:0 14mm;'
       'display:flex;justify-content:space-between">'
       '<span>' + TODAY + '</span>'
       '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>'
       '</div>')

OPEN_ALL = """() => {
  document.querySelectorAll('details').forEach(d => d.open = true);
  document.querySelectorAll('[data-rv],.tc-rv').forEach(e => {
    e.classList.add('in'); e.classList.add('tc-in');
  });
  document.querySelectorAll('img').forEach(i => { i.loading = 'eager'; });
  return document.querySelectorAll('details').length;
}"""

WAIT_IMAGES = """() => Promise.all(
  [].map.call(document.images, i => i.complete ? 1 :
    new Promise(r => { i.onload = i.onerror = r; }))
).then(() => document.images.length)"""


# ---------------------------------------------------------------- quiz paper
QUIZ_HEAD = u"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{name} &mdash; the quiz on paper</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@500;600;700;800;900&family=Familjen+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap">
<link rel="stylesheet" href="{app}/assets/press.css">
<link rel="stylesheet" href="{app}/assets/paper.css">
<link rel="stylesheet" href="{app}/assets/print.css">
<style>
:root{{--spot:var(--{ink});--spot-wash:var(--{ink}-wash)}}
body{{background:#fff}}
.qz{{border-top:6px solid var(--ink);border-bottom:6px solid var(--ink);padding:16px 0 8px;margin:0 0 22px}}
.qz h1{{font-family:var(--display);font-weight:900;font-size:44pt;line-height:.84;
  letter-spacing:-.024em;text-transform:uppercase;margin:0 0 6px}}
.qz .code{{font-family:var(--mono);font-size:8pt;letter-spacing:.2em;text-transform:uppercase;
  color:var(--spot);font-weight:700;margin:0 0 6px}}
.qz .bar{{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
  border-top:1px solid var(--hair);border-bottom:1px solid var(--hair);padding:7px 0;margin:10px 0 0;
  font-family:var(--mono);font-size:8pt;letter-spacing:.13em;text-transform:uppercase;color:var(--ink-2)}}
.qz p.rule{{font-size:10pt;line-height:1.45;color:var(--ink-2);margin:10px 0 0}}
.mq{{display:grid;grid-template-columns:38px minmax(0,1fr) 52px;gap:12px;
  border-bottom:1px solid var(--hair);padding:11px 0;break-inside:avoid;page-break-inside:avoid}}
.mq .n{{font-family:var(--display);font-weight:800;font-size:19pt;line-height:1;color:var(--ink-3)}}
.mq .s{{font-size:10.5pt;line-height:1.45}}
.mq .p{{font-family:var(--mono);font-size:7.5pt;letter-spacing:.12em;text-transform:uppercase;
  color:var(--ink-3);text-align:right;white-space:nowrap}}
.mq ol{{list-style:none;margin:7px 0 0;padding:0;
  display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2px 18px}}
.mq ol li{{font-size:10pt;line-height:1.4;padding:2px 0}}
.mq ol li b{{font-family:var(--mono);font-size:8.5pt;font-weight:700;color:var(--spot);
  margin-right:7px;letter-spacing:.06em}}
.mq pre{{font-family:var(--mono);font-size:8.4pt;line-height:1.6;background:var(--stock-2);
  padding:8px 11px;margin:8px 0 0;white-space:pre-wrap;border-left:2pt solid var(--spot)}}
.keyhead{{break-before:page;page-break-before:always}}
.key{{border-top:3px solid var(--ink)}}
.key .k{{display:grid;grid-template-columns:34px 30px minmax(0,1fr);gap:10px;
  border-bottom:1px solid var(--hair-2);padding:7px 0;break-inside:avoid;page-break-inside:avoid}}
.key .k .n{{font-family:var(--mono);font-size:8.5pt;color:var(--ink-3);padding-top:2px}}
.key .k .a{{font-family:var(--display);font-weight:800;font-size:15pt;line-height:1;color:var(--spot)}}
.key .k .w{{font-size:9.2pt;line-height:1.45;color:var(--ink-2)}}
.tot{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
  border-top:3px solid var(--ink);border-bottom:1px solid var(--hair);margin:0 0 20px}}
.tot > div{{padding:9px 12px;border-left:1px solid var(--hair)}}
.tot > div:first-child{{border-left:0;padding-left:0}}
.tot b{{font-family:var(--display);font-weight:800;font-size:22pt;line-height:1;display:block}}
.tot span{{font-family:var(--mono);font-size:7pt;letter-spacing:.15em;text-transform:uppercase;
  color:var(--ink-3);display:block;margin-top:4px}}
</style>
</head>
<body>
<div class="wrap">
<div class="qz">
  <p class="code">{code} &middot; SVNIT Surat &middot; the Tu Chahiye quiz, on paper</p>
  <h1>{title}</h1>
  <div class="bar"><span>40 questions</span><span>90 marks</span><span>45 minutes</span><span>answer key at the back</span></div>
  <p class="rule"><b>How the marks work.</b> Ten easy questions at 1 mark, ten medium at 2, and twenty hard at 3 &mdash; ninety in total, two thirds of them in the hard twenty. One option is right in every question. <b>The answer key, with a short explanation for every question, starts on the last section of this document.</b></p>
</div>

<div class="tot">
  <div><b>40</b><span>questions</span></div>
  <div><b>90</b><span>marks</span></div>
  <div><b>45:00</b><span>on the clock</span></div>
  <div><b>1</b><span>attempt online</span></div>
</div>
"""

QUIZ_FOOT = u"""
<div class="colo" style="margin-top:34px;padding-top:12px;border-top:4px solid var(--ink);
  font-family:var(--mono);font-size:7.5pt;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-3);line-height:2">
  <b style="color:var(--ink-2);font-weight:400">{code} &middot; {name}</b> &middot; printed from Tu Chahiye<br>
  the live version keeps a leaderboard and allows one attempt per name
</div>
</div>
</body>
</html>
"""


def esc(s):
    return (s.replace(u'&', u'&amp;').replace(u'<', u'&lt;').replace(u'>', u'&gt;'))


def fmt(s):
    """the page's own mini-markdown: **bold** and `code`"""
    out, i, n = [], 0, len(s)
    s = esc(s)
    while True:
        a = s.find(u'**')
        if a < 0:
            break
        b = s.find(u'**', a + 2)
        if b < 0:
            break
        s = s[:a] + u'<b>' + s[a + 2:b] + u'</b>' + s[b + 2:]
    while True:
        a = s.find(u'`')
        if a < 0:
            break
        b = s.find(u'`', a + 1)
        if b < 0:
            break
        s = s[:a] + u'<code>' + s[a + 1:b] + u'</code>' + s[b + 1:]
    return s


LETTERS = ['A', 'B', 'C', 'D', 'E', 'F']
PTS = {'easy': 1, 'medium': 2, 'hard': 3}


def quiz_html(key, bank):
    code, name, ink = SUBJECT[key]
    title = name.replace(u' ', u'<br>')
    h = [QUIZ_HEAD.format(name=name, code=code, ink=ink, title=name,
                          app=APP.replace('\\', '/'))]
    order = ([q for q in bank if q['d'] == 'easy'] +
             [q for q in bank if q['d'] == 'medium'] +
             [q for q in bank if q['d'] == 'hard'])
    for i, q in enumerate(order):
        opts = u''.join(u'<li><b>%s</b>%s</li>' % (LETTERS[j], fmt(o))
                        for j, o in enumerate(q['o']))
        code_block = (u'<pre>%s</pre>' % esc(q['code'])) if q.get('code') else u''
        h.append(u'<div class="mq"><div class="n">%02d</div><div class="s">%s%s<ol>%s</ol></div>'
                 u'<div class="p">%s</div></div>'
                 % (i + 1, fmt(q['s']), code_block, opts,
                    u'%d&nbsp;%s' % (PTS[q['d']], 'mark' if PTS[q['d']] == 1 else 'marks')))

    h.append(u'<div class="keyhead"><h2 class="sec" style="font-size:26pt;margin:0 0 4px">'
             u'The answer key</h2>'
             u'<p class="note" style="margin:0 0 14px;font-size:10pt">The letter, then why. '
             u'Read the explanation even where you got it right &mdash; that is where most of '
             u'the revision value is.</p></div>')
    h.append(u'<div class="key">')
    for i, q in enumerate(order):
        h.append(u'<div class="k"><div class="n">%02d</div><div class="a">%s</div>'
                 u'<div class="w">%s</div></div>'
                 % (i + 1, LETTERS[q['a']], fmt(q.get('e', u''))))
    h.append(u'</div>')
    h.append(QUIZ_FOOT.format(code=code, name=name))
    return u'\n'.join(h)


# ------------------------------------------------------------------- driver
def main():
    from playwright.sync_api import sync_playwright

    for d in (OUT, TMP):
        if not os.path.isdir(d):
            os.makedirs(d)

    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1200, 'height': 1600})
        pg = ctx.new_page()

        def render(src_path, out_name, label, landscape=False):
            url = 'file:///' + src_path.replace('\\', '/')
            pg.goto(url, wait_until='load')
            pg.wait_for_timeout(900)
            pg.evaluate(OPEN_ALL)
            try:
                pg.evaluate(WAIT_IMAGES)
            except Exception:
                pass
            pg.wait_for_timeout(700)
            dst = os.path.join(OUT, out_name)
            pg.pdf(path=dst, format='A4', print_background=True,
                   landscape=landscape,
                   display_header_footer=True,
                   header_template=HDR.format(label=label),
                   footer_template=FTR,
                   margin={'top': '16mm', 'bottom': '16mm',
                           'left': '13mm', 'right': '13mm'})
            kb = os.path.getsize(dst) / 1024.0
            made.append((out_name, kb))
            print('  %-22s %8.0f KB' % (out_name, kb))

        print('papers')
        for k in KEYS:
            code, name, _ = SUBJECT[k]
            render(os.path.join(APP, 'papers', k + '.html'),
                   'papers-%s.pdf' % k, '%s &middot; papers' % code)

        print('quizzes')
        for k in KEYS:
            code, name, _ = SUBJECT[k]
            pg.goto('file:///' + os.path.join(APP, 'quiz', k + '.html').replace('\\', '/'),
                    wait_until='load')
            pg.wait_for_timeout(500)
            bank = pg.evaluate('BANK')
            tmp = os.path.join(TMP, 'quiz-%s.html' % k)
            io.open(tmp, 'w', encoding='utf-8').write(quiz_html(k, bank))
            render(tmp, 'quiz-%s.pdf' % k, '%s &middot; quiz' % code)

        print('notes')
        for k in KEYS:
            code, name, _ = SUBJECT[k]
            render(os.path.join(APP, 'notes', k + '.html'),
                   'notes-%s.pdf' % k, '%s &middot; notes' % code)

        ctx.close()
        b.close()

    total = sum(kb for _, kb in made)
    print('\n%d files, %.1f MB' % (len(made), total / 1024.0))
    io.open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8').write(
        json.dumps([{'file': f, 'kb': int(round(kb))} for f, kb in made], indent=1))


if __name__ == '__main__':
    main()
