# -*- coding: utf-8 -*-
"""
Set the mathematics across the whole app properly.

Run after the pages are generated:

    python tools/mathpass.py            # every page
    python tools/mathpass.py revision   # one section
    python tools/mathpass.py --report   # convert nothing, just list

What it does, per page:

  * every monospace block that is really an equation becomes display maths,
    aligned on its first relation, with any trailing remark kept as a note
    in its own column;
  * a block that is really a matrix -- a mask, a pixel window, a Walsh
    table -- becomes a bracketed matrix;
  * every inline <code> span that is really an expression becomes inline
    maths.

What it deliberately leaves alone: source code, bit patterns, ASCII
tables, and anything the parser cannot read with confidence. A monospace
block is a perfectly good fallback; a mangled equation is not. Every skip
is counted and every failure is written to the report, so nothing is
quietly dropped.

The pass is idempotent -- a block that already carries rendered maths is
skipped -- so it is safe to run twice, and safe to run over the imported
course pages that are never regenerated.
"""
from __future__ import print_function

import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tex                                                    # noqa: E402

BS = chr(92)
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
SCRATCH = os.environ.get('TC_SCRATCH', os.path.join(HERE, '_math'))

PAGES = ([os.path.join('papers', f) for f in
          ('dcn.html', 'dcomm.html', 'dsp.html', 'dip.html', 'oops.html')] +
         [os.path.join('revision', f) for f in
          ('dcn.html', 'dcomm.html', 'dsp.html', 'dip.html', 'oops.html')] +
         [os.path.join('notes', f) for f in
          ('dcn.html', 'dcomm.html', 'dsp.html', 'dip.html', 'oops.html')] +
         [os.path.join('quiz', f) for f in
          ('dcn.html', 'dcomm.html', 'dsp.html', 'dip.html', 'oops.html')])

# OOPS is a programming course: its monospace blocks are C++, not algebra.
NO_INLINE = ('oops',)


def subject_of(path):
    return os.path.splitext(os.path.basename(path))[0]


# --------------------------------------------------------------- guards
CODE = re.compile(
    r'(?m)(#include|using namespace|std::|::|->\s*\w+\s*\(|\bclass\s+\w|'
    r'\bpublic\s*:|\bprivate\s*:|\bprotected\s*:|\bvirtual\b|\bcout\b|'
    r'\bcin\b|\bprintf\b|\bSystem\.|\bvoid\s+\w+\s*\(|\bint\s+main\b|'
    r'\breturn\s+\w+;|;\s*$|\{\s*$|^\s*\}|//|/\*|\bnew\s+\w+|\bdelete\b)')

ART = re.compile(r'(\+--|--\+|\|__|__\||/' + re.escape(BS) + r'|'
                 + re.escape(BS) + r'/|###|\^\^\^|\.--|--\.|___|'
                 r'-{3,}&gt;|-{3,}>|&lt;-{3,}|-->\s*\||\|\s*<--)', re.M)

# A bar is part of a drawing when it is one of a column of bars, or when a
# line is fenced by them. A bar wrapped round an expression is a magnitude,
# and |z| > 3 is algebra, not a picture.
FENCED = re.compile(r'^\s*\|[^|]*\|\s*$')


def bars_are_drawn(t):
    lines = [l for l in t.split('\n') if l.strip()]
    if len(lines) < 2:
        return False
    if sum(1 for l in lines if FENCED.match(l)) >= 2:
        return True              # fenced rows are a table
    cols = {}
    for l in lines:
        for i, ch in enumerate(l):
            if ch == '|':
                cols[i] = cols.get(i, 0) + 1
    return any(v >= 3 for v in cols.values())   # a column of bars is an axis

BINARY = re.compile(r'\b[01]{5,}\b')
# a byte written out with spaces between the bits is a bit pattern too, and
# so are nibble pairs like `0000 0001`
BITS = re.compile(r'(?<![\d.])[01](?:\s+[01]){6,}(?![\d.])|\b[01]{4}\s+[01]{4}\b')
XOR = re.compile(r'(?i)\bx?or\b|\bxor\b')
TAGS = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*>')
SAFE_TAGS = set(['b', 'i', 'em', 'strong', 'code', 'sup', 'sub', 'span', 'br'])


# The imported course pages build their maths out of nested spans. Those
# carry real structure -- a fraction is a numerator over a denominator, a
# summation has limits above and below -- so they are translated, never
# flattened. Flattening turns a summation into the product `N` times
# `Sigma` times `i=1`, which is worse than leaving it alone.
FRAC = re.compile(r'<span class="frac">\s*<span>(.*?)</span>\s*'
                  r'<span>(.*?)</span>\s*</span>', re.S)
SUM3 = re.compile(r'<span class="sum">\s*<span class="l">(.*?)</span>\s*'
                  r'<span class="s">(.*?)</span>\s*'
                  r'<span class="l">(.*?)</span>\s*</span>', re.S)
SUM2 = re.compile(r'<span class="sum">\s*<span class="s">(.*?)</span>\s*'
                  r'<span class="l">(.*?)</span>\s*</span>', re.S)
CNOTE = re.compile(r'<span class="c">(.*?)</span>', re.S)

BIGOP = {'sum': 'sum', 'prod': 'prod', 'integral': 'integral'}


def _bigop(glyph):
    return BIGOP.get(tex.unescape(glyph).strip(), 'sum')


def structures(t):
    """nested-span maths -> the flat dialect the parser reads"""
    for _ in range(6):
        before = t
        t = FRAC.sub(lambda m: '((%s)/(%s))' % (m.group(1), m.group(2)), t)
        t = SUM3.sub(lambda m: '%s_(%s)^(%s)' % (_bigop(m.group(2)),
                                                 m.group(3), m.group(1)), t)
        t = SUM2.sub(lambda m: '%s_(%s)' % (_bigop(m.group(1)), m.group(2)), t)
        if t == before:
            break
    return CNOTE.sub(lambda m: '   -- ' + m.group(1), t)


def strip_tags(t):
    """<sup>2</sup> carries meaning; <b> does not. Keep the meaning."""
    t = structures(t)
    t = re.sub(r'<sup>(.*?)</sup>', lambda m: '^(' + m.group(1) + ')', t)
    t = re.sub(r'<sub>(.*?)</sub>', lambda m: '_(' + m.group(1) + ')', t)
    t = re.sub(r'<br\s*/?>', '\n', t)
    t = re.sub(r'</?(?:b|i|em|strong|code)[^>]*>', '', t)
    return re.sub(r'</?span[^>]*>', '', t)


def has_foreign_tags(t):
    """after structures(): a classed span left over is one we cannot read"""
    t = structures(t)
    for m in TAGS.finditer(t):
        if m.group(2).lower() not in SAFE_TAGS:
            return True
    # a span carrying any attribute at all is somebody else's markup
    return re.search(r'<span\s+[^>]*=', t) is not None


def skip_reason(raw):
    if 'katex' in raw:
        return 'already set'
    if has_foreign_tags(raw):
        return 'markup'
    t = tex.unescape(strip_tags(raw))
    if CODE.search(t):
        return 'code'
    if ART.search(t) or bars_are_drawn(t):
        return 'diagram'
    if BINARY.search(t) or XOR.search(t) or BITS.search(t):
        return 'bit pattern'
    # an entity the table does not know would be typeset as its own name
    left = re.search(r'&[a-zA-Z][a-zA-Z0-9]*;', t)
    if left:
        return 'unknown entity'
    lines = [l for l in t.split('\n') if l.strip()]
    if not lines:
        return 'empty'
    if len(lines) > 26:
        return 'too long'
    return None


DATA_CELL = r'[-+]?\d+(?:\.\d+)?(?:\s?(?:pi|deg|dB|%))?'
DATA_ROW = re.compile(r'^\s*' + DATA_CELL + r'(?:\s+' + DATA_CELL + r'){2,}\s*$')
LABELLED = re.compile(r'^\s*[A-Za-z][A-Za-z0-9 _()\'.]{0,26}[:=]\s*')
SENTENCE = re.compile(r'[a-z]{2,}\.\s+[A-Z]')
INDEX_LINE = re.compile(r'^\s*(?:[A-Za-z]\d?\s+)*[A-Za-z]\d?\s*$')
BIGWORD = re.compile(r'\b(SUM|sum|PROD|prod)\b(?![_^])')
_N = r'[-+]?\d+(?:\.\d+)?(?:/\d+)?'
NUMRUN = re.compile(r'(?<![\w.])' + _N + r'(?:\s+' + _N + r'){2,}(?![\w.])')
TABLE2 = re.compile(r'^\s*[A-Za-z][\w()]*\s+' + _N + r'(?:\s+' + _N + r')+\s*$')
BARE = re.compile(r'^(?:' + re.escape(BS) + r'text\{[^{}]*\}|'
                  + re.escape(BS) + r'mathrm\{[^{}]*\}|[A-Za-z])$')
WORDS_ONLY = re.compile(re.escape(BS) + r'(?:text|mathrm)\{[^{}]*\}|[()\s]|' + re.escape(BS) + r',')
MATHY = re.compile(r'[\^_<>=]|^[A-Za-z]\(')


def is_data_row(l):
    return DATA_ROW.match(l) is not None


def is_table_row(l):
    """`index :  0  1  2  3`, `z4 z5 z6 = 10 10 10`, `A : +1 -1 +1 -1` -- a
       row of numbers with nothing computed in it is a table row"""
    l = tex.split_comment(l.rstrip())[0]
    head = LABELLED.sub('', l, 1)
    if DATA_ROW.match(head) or TABLE2.match(head):
        return True
    if not NUMRUN.search(head):
        return False
    rest = NUMRUN.sub(' ', head)
    rest = re.sub(r'\([A-Za-z0-9 ]*\)', ' ', rest)     # a label like Pz (zq)
    return (re.search(r'[+*/^()\[\]{}<>|]', rest) is None and '->' not in rest
            and re.search(r'[A-Za-z]\s*-\s*[A-Za-z0-9]', rest) is None)


def has_rel(r):
    """does the row state a relation? commas and colons do not count"""
    return any(p.startswith(BS) or p in ('=', '<', '>')
               for p in r['parts'][1::2])


def prose_tex(t, subject=''):
    """words as text, with the formulas that sit among them set as maths:
       `entry (k, n) is W_N^(kn)` keeps its W_N^(kn)"""
    t = tex.LISTNUM.sub('', ' '.join(t.split()))
    if t.startswith('--'):
        t = t[2:].strip()
    out = []
    for w in t.split(' '):
        m = re.match(r'^(.*?)([,.;:]*)$', w)
        core, tail = m.group(1), m.group(2)
        # a closing bracket that closes nothing belongs to the sentence
        while core.endswith(')') and core.count(')') > core.count('('):
            core, tail = core[:-1], ')' + tail
        # the dialect's names for symbols: theta, ->, <=, inf
        if core in tex.GREEK:
            out.append('$' + BS + core + '$' + tex.textify(tail))
            continue
        if core in tex.RELTEX:
            out.append('$' + tex.RELTEX[core] + '$' + tex.textify(tail))
            continue
        if core in ('inf', 'infinity'):
            out.append('$' + BS + 'infty$' + tex.textify(tail))
            continue
        if MATHY.search(core) and 1 < len(core) <= 24 and '--' not in core:
            try:
                r = tex.line(core, subject)
            except tex.TexError:
                r = None
            if r and r['math'].strip() and not r['label'] and not r['note']:
                out.append('$' + r['math'] + '$' + tex.textify(tail))
                continue
        out.append(tex.textify(w))
    return ' '.join(out)


def attach_sum_indices(lines):
    """`SUM SUM w(s,t)` with `s   t` written on the line below: the letters
       are the summation indices, so put them where the parser reads them"""
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ''
        k = len(BIGWORD.findall(l))
        if k and INDEX_LINE.match(nxt) and len(nxt.split()) == k:
            idx = iter(nxt.split())
            l = BIGWORD.sub(lambda m: m.group(1).lower() + '_' + next(idx), l)
            out.append(l)
            i += 2
            continue
        out.append(l)
        i += 1
    return out


RELCH = re.compile(r'[=<>]|->|=>|<->')


def split_middots(lines):
    """`E = ...  .  P = ...  .  energy signal => P = 0`: a line that strings
       statements together with wide-spaced middle dots is one statement
       per row (`n . x(n)`, a product, has single spaces)"""
    out = []
    for l in lines:
        parts = re.split(r'\s{2,}\.\s{2,}', l)
        if len(parts) >= 2 and all(RELCH.search(p) for p in parts):
            out.extend(parts)
        else:
            out.append(l)
    return out


def texty(r, line):
    """a sentence that happens to parse is still a sentence: one with a
       full stop in it, or with no relation and only words, or a bare word
       with a remark hanging off it (`PIFS   - point coordination`)"""
    if SENTENCE.search(line):
        return True
    math = r['math'].strip()
    words = ' '.join(re.findall(re.escape(BS) + r'text\{([^{}]*)\}', math))
    if has_rel(r):
        # a sentence with an equation inside it is still a sentence
        return len(words.split()) > 12
    if BARE.match(math):
        return True                         # nothing but words
    if r['note'] and len(r['note']) >= 12 and WORDS_ONLY.sub('', math) == '':
        return True                         # `DIFS (longest)   - ordinary data`
    if re.search(r'[\^_]|' + re.escape(BS) + r'(?:frac|sqrt|sum|int)', math):
        return False                        # there is structure worth setting
    return len(words.split()) >= 6


def simple_row(r):
    """a word and a number, a name -- nothing a formula would be made of"""
    rest = re.sub(re.escape(BS) + r'(?:text|mathrm)\{[^{}]*\}', '', r['math'])
    rest = re.sub(re.escape(BS) + r'[A-Za-z]+', '', rest)
    return (len(re.findall(r'[A-Za-z0-9.]+', rest)) <= 2
            and not re.search(r'[\^_()]', rest))


def merge_note(r, l, subject):
    """`Step 1 -- rewrite: x(-n-2) = x(-(n+2))` -- the mathematics is in
       the remark, so set the remark and keep the head as its label"""
    try:
        rn = tex.line(r['note'], subject)
    except tex.TexError:
        return None
    if not rn['math'].strip() or not has_rel(rn):
        return None
    head = ' '.join(tex.split_comment(l.rstrip())[0].split())
    head = tex.LISTNUM.sub('', head)
    if not head or len(head) > 30 or re.search(r'[=<>^_]', head):
        return None
    rn['label'] = head + (' -- ' + rn['label'] if rn['label'] else '')
    return rn


def note_latex(note, subject=''):
    """a remark that is really mathematics (`= A^2/2`, `check: 42 = 6 x 7`)
       is set as mathematics; anything else is text. Returns (latex, is_math)"""
    if re.search(r'[=<>^_]|\d\s*/\s*\d|\w\(', note):
        try:
            r = tex.line(note, subject)
        except tex.TexError:
            r = None
        if r and r['math'].strip():
            out = r['math']
            if r['label']:
                out = BS + 'text{%s}:' % tex.textify(r['label']) + BS + '; ' + out
            if r['note']:
                out += BS + ';' + BS + 'text{%s}' % prose_tex(r['note'], subject)
            return out, True
    return BS + 'text{%s}' % prose_tex(note, subject), False


# --------------------------------------------------------------- matrices
def as_matrix(lines):
    """rows of bare numbers become a bracketed matrix"""
    heads, notes = [], []
    for l in lines:
        h, n = tex.split_comment(l)
        heads.append(h.strip())
        notes.append(n)
    rows = [h.split() for h in heads if h]
    if len(rows) < 2:
        return None
    w = len(rows[0])
    if w < 2 or any(len(r) != w for r in rows):
        return None
    if len(rows) < 3 and w < 3:
        return None
    for r in rows:
        for c in r:
            if not re.match(r'^[-+]?\d+(?:\.\d+)?$', c):
                return None
    body = (' ' + BS + BS + ' ').join(' & '.join(r) for r in rows)
    out = BS + 'begin{bmatrix} ' + body + ' ' + BS + 'end{bmatrix}'
    tail = [n for n in notes if n]
    if tail:
        out += BS + 'quad' + BS + 'text{%s}' % tex.textify('; '.join(tail))
    return out


# --------------------------------------------------------------- blocks
def build_block(raw, subject):
    """decoded monospace text -> display LaTeX, or None to leave it alone"""
    t = tex.unescape(strip_tags(raw))
    t = t.replace('\t', '    ')
    lines = t.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None

    lines = attach_sum_indices(lines)
    lines = split_middots(lines)
    live = [l for l in lines if l.strip()]
    # a matrix needs to look like one: OOPS blocks are program output
    if subject != 'oops':
        m = as_matrix(live)
        if m:
            return m

    # a run of bare-number rows is data, not algebra; two labelled rows of
    # numbers are a table, whose columns only line up in monospace
    if sum(1 for l in live if is_data_row(l)) >= 2:
        return None
    if sum(1 for l in live if is_table_row(l)) >= 2:
        return None

    rows = []                               # ('math', row) / ('prose', text) / ('gap', None)
    for l in lines:
        if not l.strip() or re.match(r'^\s*[-=_.]{3,}\s*$', l):
            rows.append(('gap', None))
            continue
        if is_data_row(l):
            return None
        if is_table_row(l):
            rows.append(('prose', l.strip()))
            continue
        try:
            r = tex.line(l, subject)
        except tex.TexError:
            if tex.is_prose(l):
                rows.append(('prose', l.strip()))
                continue
            return None
        if not r['math'].strip():
            if r['note']:
                rows.append(('prose', r['note']))
            else:
                rows.append(('gap', None))
            continue
        if not has_rel(r) and r['note'] and not r['label']:
            r = merge_note(r, l, subject) or r
        if texty(r, l):
            rows.append(('prose', l.strip()))
            continue
        rows.append(('math', r))

    maths = [r for k, r in rows if k == 'math']
    prose = len([r for k, r in rows if k == 'prose'])
    if not maths:
        return None
    # a block that is mostly prose belongs in a paragraph, not in a formula
    if 3 * len(maths) < prose:
        return None
    # rows of names and numbers with no relation anywhere: program output
    if len(rows) > 1 and not any(has_rel(r) for r in maths) and all(simple_row(r) for r in maths):
        return None

    single = len(rows) == 1 and rows[0][0] == 'math'
    if single and not rows[0][1]['note'] and not rows[0][1]['label']:
        return rows[0][1]['math']

    out = []
    for kind, r in rows:
        if kind == 'gap':
            if out:
                out[-1] = out[-1] + BS + BS + '[5pt]'
            continue
        if kind == 'prose':
            out.extend(note_rows(r, subject))
            continue
        out.extend(aligned_row(r, subject))
    body = (' ' + BS + BS + ' ').join(out)
    body = body.replace(BS + BS + '[5pt] ' + BS + BS + ' ', BS + BS + '[5pt] ')
    return BS + 'begin{aligned} ' + body + ' ' + BS + 'end{aligned}'


# A remark up to this many characters still reads beside its line.
SHORT_NOTE = 18
# Beyond this one a remark is split across two rows of its own.
WRAP_NOTE = 46


def tex_block(raw):
    """a block the author wrote in LaTeX: only the HTML escaping comes off"""
    t = raw.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    t = re.sub(r'<br\s*/?>', '\n', t)
    return t.strip()


def aligned_row(r, subject=''):
    """lhs &= rhs && note -- the alignment point is the first relation"""
    parts = r['parts']
    lhs = parts[0]
    if r['label']:
        lhs = BS + 'text{%s}:' % tex.textify(r['label']) + BS + '; ' + lhs
    if len(parts) >= 3:
        cell = '%s &%s' % (lhs, ' '.join(parts[1:]))
    else:
        cell = '%s &' % lhs
    cell = tex.tidy(cell)
    note = r['note']
    if not note:
        return [cell]
    latex, is_math = note_latex(note, subject)
    if is_math:
        if len(note) <= WRAP_NOTE:
            return [cell + ' && ' + latex]
        return [cell, '&' + BS + 'quad ' + latex]
    if len(note) <= SHORT_NOTE:
        return [cell + ' && ' + latex]
    return [cell] + note_rows(note, subject)


def note_rows(text, subject=''):
    """a remark on its own row, in the second column, split if very long"""
    rows = []
    for piece in split_words(' '.join(text.split()), WRAP_NOTE):
        rows.append('&' + BS + 'quad ' + BS + 'text{%s}' % prose_tex(piece, subject))
    return rows


def split_words(text, limit):
    """break a long remark, but never inside a bracket: splitting
       "A sin(2 pi fm t)" across two rows reads as two broken things"""
    if len(text) <= limit:
        return [text]
    def delta(w):
        return w.count('(') + w.count('[') - w.count(')') - w.count(']')

    out, line, depth = [], '', 0
    for w in text.split(' '):
        # depth is how many brackets the line so far leaves open
        if line and depth <= 0 and len(line) + 1 + len(w) > limit:
            out.append(line)
            line, depth = w, max(0, delta(w))
        else:
            line = (line + ' ' + w) if line else w
            depth += delta(w)
    if line:
        out.append(line)
    return out


# --------------------------------------------------------------- inline
INLINE_BAD = re.compile(
    r'(std::|::|#include|\bclass\b|\bpublic\b|\bprivate\b|\bvirtual\b|'
    r'\bcout\b|\bcin\b|\bvoid\b|\breturn\b|\bnew\b|\bdelete\b|\bthis\b|'
    r'\bnullptr\b|\btrue\b|\bfalse\b|[;{}]|<<|>>|&&|\|\||\+\+|--\w|'
    r'\.h\b|\.cpp\b|\bstatic\b|\bconst\b|\bstruct\b|\benum\b|\btypedef\b)')

INLINE_GOOD = re.compile(r'[\^_=/*+]|&lt;=|&gt;=|\(.*\)|&[a-z]+;')


def inline_candidate(txt):
    if 'katex' in txt:
        return False
    if len(txt) > 120 or not txt.strip():
        return False
    if has_foreign_tags(txt):
        return False
    if INLINE_BAD.search(txt):
        return False
    if not INLINE_GOOD.search(txt):
        return False
    t = tex.unescape(strip_tags(txt))
    if '\n' in t:
        return False
    # must contain at least one operator or a function application
    if not re.search(r'[\^_=/*+<>-]|\w\(', t):
        return False
    return True


def build_inline(txt, subject):
    t = tex.unescape(strip_tags(txt)).strip()
    if not t:
        return None
    try:
        r = tex.line(t, subject)
    except tex.TexError:
        return None
    out = r['math']
    if r['label'] or r['note']:
        return None
    if not out.strip():
        return None
    # if nothing was gained, keep the <code> span
    if out == t and BS not in out:
        return None
    return out


# --------------------------------------------------------------- driver
BLOCK_RE = re.compile(r'<(div|p) class="(eqn|eq)( tex)?">(.*?)</\1>', re.S)
CODE_RE = re.compile(r'<code>(.*?)</code>', re.S)
SCRIPT_RE = re.compile(r'<(script|style)\b.*?</\1>', re.S | re.I)


def dead_zones(src):
    """Ranges no replacement may touch.

    The quiz banks are JavaScript string literals that happen to contain
    HTML, so a <code> span in there looks exactly like one in the page.
    Rendered maths carries double quotes, which close the string and break
    the whole script -- which is precisely what happened the first time
    this ran.
    """
    return [(m.start(), m.end()) for m in SCRIPT_RE.finditer(src)]


def in_dead(zones, a, b):
    for x, y in zones:
        if a >= x and b <= y:
            return True
    return False


def collect(paths, do_inline=True):
    jobs, sites, stats = [], [], {}
    for rel in paths:
        path = os.path.join(APP, rel)
        if not os.path.exists(path):
            continue
        subject = subject_of(rel)
        src = io.open(path, encoding='utf-8', errors='replace').read()
        zones = dead_zones(src)
        st = stats.setdefault(rel, {'block': 0, 'skip': {}, 'inline': 0,
                                    'fail': 0})

        for m in BLOCK_RE.finditer(src):
            if in_dead(zones, m.start(), m.end()):
                st['skip']['in script'] = st['skip'].get('in script', 0) + 1
                continue
            raw = m.group(4)
            if m.group(3):
                # written as LaTeX already: render it exactly as given
                if 'katex' in raw:
                    st['skip']['already set'] = st['skip'].get('already set', 0) + 1
                    continue
                latex = tex_block(raw)
                jobs.append({'id': len(jobs), 'tex': latex, 'display': True})
                sites.append((rel, m.start(), m.end(), 'block', raw))
                st['block'] += 1
                continue
            why = skip_reason(raw)
            if why:
                st['skip'][why] = st['skip'].get(why, 0) + 1
                continue
            latex = build_block(raw, subject)
            if latex is None:
                st['skip']['unparsed'] = st['skip'].get('unparsed', 0) + 1
                continue
            # nothing is gained by setting a block that comes out as itself
            if latex.strip() == tex.unescape(strip_tags(raw)).strip():
                st['skip']['nothing to set'] = \
                    st['skip'].get('nothing to set', 0) + 1
                continue
            jobs.append({'id': len(jobs), 'tex': latex, 'display': True})
            sites.append((rel, m.start(), m.end(), 'block', raw))
            st['block'] += 1

        if do_inline and subject not in NO_INLINE:
            for m in CODE_RE.finditer(src):
                if in_dead(zones, m.start(), m.end()):
                    continue
                raw = m.group(1)
                if not inline_candidate(raw):
                    continue
                latex = build_inline(raw, subject)
                if latex is None:
                    continue
                jobs.append({'id': len(jobs), 'tex': latex, 'display': False})
                sites.append((rel, m.start(), m.end(), 'inline', raw))
                st['inline'] += 1
    return jobs, sites, stats


def render(jobs):
    if not jobs:
        return {}
    if not os.path.isdir(SCRATCH):
        os.makedirs(SCRATCH)
    jp = os.path.join(SCRATCH, 'jobs.json')
    op = os.path.join(SCRATCH, 'out.json')
    io.open(jp, 'w', encoding='utf-8').write(
        json.dumps(jobs, ensure_ascii=False))
    r = subprocess.call(['node', os.path.join(HERE, 'render-math.js'), jp, op])
    if r != 0:
        raise SystemExit('render-math.js failed (%d)' % r)
    out = json.loads(io.open(op, encoding='utf-8').read())
    return dict((o['id'], o) for o in out)


def apply(sites, jobs, done, stats):
    by_file = {}
    for i, (rel, a, b, kind, raw) in enumerate(sites):
        by_file.setdefault(rel, []).append((a, b, kind, i, raw))
    fails = []
    for rel, items in by_file.items():
        path = os.path.join(APP, rel)
        src = io.open(path, encoding='utf-8', errors='replace').read()
        items.sort(key=lambda x: x[0], reverse=True)
        n = 0
        for a, b, kind, i, raw in items:
            res = done.get(i)
            if not res or res.get('err'):
                stats[rel]['fail'] += 1
                fails.append((rel, kind, jobs[i]['tex'], raw,
                              res['err'] if res else 'missing'))
                if kind == 'block':
                    stats[rel]['block'] -= 1
                else:
                    stats[rel]['inline'] -= 1
                continue
            if kind == 'block':
                rep = ('<div class="mathblock"><div class="mrow">%s</div></div>'
                       % res['html'])
            else:
                rep = '<span class="minline">%s</span>' % res['html']
            src = src[:a] + rep + src[b:]
            n += 1
        if n:
            io.open(path, 'w', encoding='utf-8').write(src)
    return fails


def main(argv):
    only = [a for a in argv if not a.startswith('-')]
    report_only = '--report' in argv
    paths = PAGES
    if only:
        paths = [p for p in PAGES
                 if any(o in p.replace(BS, '/') for o in only)]
    jobs, sites, stats = collect(paths)
    print('%d expressions found across %d pages'
          % (len(jobs), len([p for p in stats if stats[p]['block'] or
                             stats[p]['inline']])))
    if report_only:
        dump(stats, [], jobs, sites)
        return 0
    done = render(jobs)
    fails = apply(sites, jobs, done, stats)
    dump(stats, fails, jobs, sites)
    tot_b = sum(s['block'] for s in stats.values())
    tot_i = sum(s['inline'] for s in stats.values())
    print('\nset %d display blocks and %d inline expressions; %d failed'
          % (tot_b, tot_i, len(fails)))
    return 0


def dump(stats, fails, jobs, sites):
    if not os.path.isdir(SCRATCH):
        os.makedirs(SCRATCH)
    p = os.path.join(SCRATCH, 'report.txt')
    with io.open(p, 'w', encoding='utf-8') as f:
        f.write(u'%-22s %6s %7s %6s   %s\n'
                % ('page', 'blocks', 'inline', 'failed', 'left alone'))
        f.write(u'-' * 92 + u'\n')
        for rel in sorted(stats):
            s = stats[rel]
            if not (s['block'] or s['inline'] or s['skip']):
                continue
            sk = ', '.join('%s %d' % (k, v)
                           for k, v in sorted(s['skip'].items()))
            f.write(u'%-22s %6d %7d %6d   %s\n'
                    % (rel.replace(BS, '/'), s['block'], s['inline'],
                       s['fail'], sk))
        if fails:
            f.write(u'\n\nFAILURES (left as monospace)\n' + u'=' * 70 + u'\n')
            for rel, kind, latex, raw, err in fails:
                f.write(u'\n%s  [%s]  %s\n  src: %s\n  tex: %s\n'
                        % (rel, kind, err, raw.strip()[:200],
                           latex[:300]))
        f.write(u'\n\nEVERY CONVERSION\n' + u'=' * 70 + u'\n')
        for i, (rel, a, b, kind, raw) in enumerate(sites):
            f.write(u'\n--- %s [%s]\n%s\n==>\n%s\n'
                    % (rel.replace(BS, '/'), kind,
                       tex.unescape(strip_tags(raw)).strip(), jobs[i]['tex']))
    print('report: %s' % p)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
