# -*- coding: utf-8 -*-
"""
Turn the plain-text mathematics written across this app into LaTeX.

The app was written with ASCII stand-ins: `sum_{n=0}^{N-1}`, `sqrt(2)`,
`e^(-j*2*pi/N)`, `<=`, `Rb/2`, `alpha`. A reader has to decode that before
they can read it, which is exactly backwards. This module parses that
dialect and emits LaTeX, so KaTeX can set it the way a textbook would.

It is a tokeniser and a recursive-descent parser, not a pile of regular
expressions, because the interesting rewrites need to know where an operand
starts and stops. `a/b` only becomes \\frac{a}{b} if you know what `a` and
`b` are, and `2/255^2` has to come out as a fraction whose denominator is
the whole power -- no amount of search-and-replace gets that right.

    tex.line('X(k) = sum_{n=0}^{N-1} x(n) W_N^(n*k)', subject='dsp')
    -> {'math': 'X(k) = \\sum_{n=0}^{N-1} x(n) W_N^{nk}', ...}

Anything it cannot parse confidently raises TexError, and the caller leaves
the original monospace block alone. Degrading to what we had is fine;
printing a half-converted expression is not.
"""
from __future__ import print_function

import re

BS = chr(92)

try:
    unichr
except NameError:
    unichr = chr


class TexError(Exception):
    pass


# --------------------------------------------------------------- entities
ENT = {
    'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"', 'apos': "'",
    'nbsp': ' ', 'ensp': ' ', 'emsp': ' ', 'thinsp': ' ',
    'minus': '-', 'ndash': '-', 'mdash': ' -- ', 'shy': '',
    'middot': ' . ', 'sdot': ' . ', 'times': ' x ', 'divide': '/',
    'le': '<=', 'ge': '>=', 'ne': '!=', 'asymp': '~=', 'equiv': '==',
    'rarr': '->', 'larr': '<-', 'harr': '<->', 'rArr': '=>',
    'plusmn': '+/-', 'infin': ' inf ', 'deg': ' deg',
    'hellip': '...', 'lowast': '*', 'radic': ' sqrt ', 'sum': 'sum',
    'prod': 'prod', 'int': 'integral', 'part': 'd', 'nabla': 'grad',
    'sup2': '^2', 'sup3': '^3', 'frac12': '1/2', 'frac14': '1/4',
    'ldquo': '"', 'rdquo': '"', 'lsquo': "'", 'rsquo': "'", 'prime': "'",
    'bull': ' . ', 'lowbar': '_',
    'oplus': ' xor ', 'otimes': ' * ', 'ominus': ' - ',
    'cap': ' cap ', 'cup': ' cup ', 'isin': ' isin ', 'ni': ' isin ',
    'notin': ' notin ', 'sube': ' subset ', 'sub': ' subset ',
    'empty': ' emptyset ', 'forall': ' forall ', 'exist': ' exists ',
    'ang': ' /_ ', 'perp': ' perp ', 'and': ' and ', 'or': ' or ',
    'lowast': '*', 'lceil': '[', 'rceil': ']', 'lfloor': '[',
    'rfloor': ']', 'larr': '<-', 'uarr': ' uparrow ', 'darr': ' downarrow ',
}
for _g in ('alpha beta gamma delta epsilon zeta eta theta iota kappa lambda '
           'mu nu xi rho sigma tau upsilon phi chi psi omega Delta Gamma '
           'Omega Phi Sigma Theta Lambda Pi Psi Xi').split():
    ENT[_g] = ' %s ' % _g
ENT['pi'] = ' pi '

UNI = {
    u'−': '-', u'–': '-', u'—': ' -- ', u'×': ' x ',
    u'÷': '/', u'≤': '<=', u'≥': '>=', u'≠': '!=',
    u'≈': '~=', u'≡': '==', u'→': '->', u'←': '<-',
    u'↔': '<->', u'⇒': '=>', u'±': '+/-', u'∞': ' inf ',
    u'°': ' deg', u'…': '...', u'∗': '*', u'√': ' sqrt ',
    u'∑': 'sum', u'∏': 'prod', u'∫': 'integral',
    u'∂': 'd', u'∇': 'grad', u'·': ' . ', u' ': ' ',
    u'′': "'", u'✓': ' -- ok', u'✗': ' -- no', u'∠': ' /_ ',
    u'↑': ' uparrow ', u'↓': ' downarrow ',
    u'≡': '==', u'∅': ' emptyset ', u'∈': ' isin ', u'∉': ' notin ',
    u'α': ' alpha ', u'β': ' beta ', u'γ': ' gamma ',
    u'δ': ' delta ', u'ε': ' epsilon ', u'θ': ' theta ',
    u'λ': ' lambda ', u'μ': ' mu ', u'π': ' pi ',
    u'ρ': ' rho ', u'σ': ' sigma ', u'τ': ' tau ',
    u'φ': ' phi ', u'ϕ': ' phi ', u'ω': ' omega ',
    u'Δ': ' Delta ', u'Γ': ' Gamma ', u'Ω': ' Omega ',
    u'Φ': ' Phi ', u'Σ': ' Sigma ', u'Θ': ' Theta ',
    u'Λ': ' Lambda ', u'Π': ' Pi ',
    u'²': '^(2)', u'³': '^(3)', u'½': '(1/2)',
    u'¼': '(1/4)', u'¾': '(3/4)', u'⅓': '(1/3)',
    u'⅔': '(2/3)', u'⅕': '(1/5)', u'⅙': '(1/6)',
    u'⅛': '(1/8)',
}


def unescape(t):
    """HTML back to the ASCII dialect, so the parser sees one language."""
    def ent(m):
        name = m.group(1)
        if name.startswith('#'):
            try:
                ch = (unichr(int(name[2:], 16)) if name[1] in 'xX'
                      else unichr(int(name[1:])))
            except Exception:
                return m.group(0)
            return UNI.get(ch, ch)
        return ENT.get(name, m.group(0))
    t = re.sub(r'&([a-zA-Z][a-zA-Z0-9]*|#x?[0-9a-fA-F]+);', ent, t)
    for k, v in UNI.items():
        t = t.replace(k, v)
    return t


# --------------------------------------------------------------- symbols
GREEK = ('alpha beta gamma delta epsilon eta theta lambda mu pi rho sigma tau '
         'phi omega Delta Gamma Omega Phi Sigma Theta Lambda Pi').split()

FUNC = {
    'sin': BS + 'sin', 'cos': BS + 'cos', 'tan': BS + 'tan',
    'sinh': BS + 'sinh', 'cosh': BS + 'cosh', 'tanh': BS + 'tanh',
    'sinc': BS + 'operatorname{sinc}', 'exp': BS + 'exp',
    'ln': BS + 'ln', 'log': BS + 'log',
    'max': BS + 'max', 'min': BS + 'min',
    'sgn': BS + 'operatorname{sgn}',
    'arg': BS + 'arg', 'det': BS + 'det', 'gcd': BS + 'gcd',
    'mod': BS + 'bmod',
    'arctan': BS + 'arctan', 'arcsin': BS + 'arcsin',
    'arccos': BS + 'arccos', 'atan': BS + 'arctan',
    'cot': BS + 'cot', 'sec': BS + 'sec', 'csc': BS + 'csc',
    'erfc': BS + 'operatorname{erfc}', 'rect': BS + 'operatorname{rect}',
    'tri': BS + 'operatorname{tri}', 'var': BS + 'operatorname{var}',
}

# Names this corpus uses for quantities. Without this table `Rb` is two
# letters multiplied together; with it, it is the bit rate.
COMMON = {
    'Rb': 'R_b', 'Tb': 'T_b', 'Ts': 'T_s', 'Tp': 'T_p', 'Fs': 'F_s',
    'Tfr': 'T_{fr}',
    'fs': 'f_s', 'fm': 'f_m', 'fc': 'f_c', 'fb': 'f_b', 'fB': 'f_B',
    'fN': 'f_N', 'BT': 'B_T', 'Bw': 'B_W',
    'Vmax': 'V_{' + BS + 'max}', 'Vmin': 'V_{' + BS + 'min}',
    'Vrms': 'V_{' + BS + 'mathrm{rms}}', 'Vp': 'V_p', 'Vpp': 'V_{pp}',
    'Eb': 'E_b', 'No': 'N_0', 'N0': 'N_0', 'Pe': 'P_e', 'Pb': 'P_b',
    'SNR': BS + 'mathrm{SNR}', 'SQNR': BS + 'mathrm{SQNR}',
    'PDR': BS + 'mathrm{PDR}', 'BER': BS + 'mathrm{BER}',
    'ISI': BS + 'mathrm{ISI}', 'AWGN': BS + 'mathrm{AWGN}',
    'MSB': BS + 'mathrm{MSB}', 'LSB': BS + 'mathrm{LSB}',
    'DFT': BS + 'mathrm{DFT}', 'IDFT': BS + 'mathrm{IDFT}',
    'FFT': BS + 'mathrm{FFT}', 'DTFT': BS + 'mathrm{DTFT}',
    'ROC': BS + 'mathrm{ROC}', 'MSE': BS + 'mathrm{MSE}',
    'RMS': BS + 'mathrm{RMS}', 'LCM': BS + 'mathrm{LCM}',
    'HCF': BS + 'mathrm{HCF}', 'CRC': BS + 'mathrm{CRC}',
    'inf': BS + 'infty', 'infinity': BS + 'infty',
}

# per subject, because the same letter is not the same quantity everywhere:
# in DSP `w` is angular frequency, in DIP it is a mask weight.
SUBJECT = {
    'dsp': {'w': BS + 'omega', 'w0': BS + 'omega_0', 'wc': BS + 'omega_c',
            'wn': BS + 'omega_n', 'th': BS + 'theta', 'W': 'W',
            'jw': 'j' + BS + 'omega', 'jw0': 'j' + BS + 'omega_0',
            'jwn': 'j' + BS + 'omega n', 'jwk': 'j' + BS + 'omega k'},
    'dcomm': {'a': BS + 'alpha', 'w': BS + 'omega', 'wc': BS + 'omega_c'},
    'dip': {'N4': 'N_4', 'N8': 'N_8', 'ND': 'N_D', 'Nd': 'N_D',
            'D4': 'D_4', 'D8': 'D_8', 'De': 'D_e', 'Dm': 'D_m'},
    'dcn': {},
    'oops': {},
}

UNITS = set(('Hz kHz MHz GHz THz dB dBm bps kbps Mbps Gbps ms us ns ps '
             'bit bits byte bytes Kb Mb Gb KB MB GB nats hartleys symbols '
             'samples Msamples MSamples pixels frames sec V mV mA mW '
             'ohm rad Baud baud kHz nats').split())

UNIT_PHRASE = re.compile(
    r'(?:M?b/s|k?b/s|bits?/s(?:ymbol)?|M?Samples?/s|bits?/pixel|'
    r'bit/s/Hz|samples?/s|symbols?/s|cycles?/s|bits?/sample)')

WORDY = re.compile(r'^[A-Za-z][a-z]{2,}$')

NOT_WORDS = set('sum prod integral lim sqrt log ln exp sin cos tan sgn max '
                'min inf deg mod abs cosh sinh tanh sinc erfc rect tri var '
                'arg det gcd'.split())

TEXTY = set('vs no ok yes all any one two per up down out off by'.split())

# words the entity tables produce for symbols that have no ASCII spelling
SYMWORD = {
    'isin': BS + 'in', 'notin': BS + 'notin', 'subset': BS + 'subset',
    'emptyset': BS + 'emptyset', 'forall': BS + 'forall',
    'exists': BS + 'exists', 'cap': BS + 'cap', 'cup': BS + 'cup',
    'perp': BS + 'perp', 'xor': BS + 'oplus',
    'uparrow': BS + 'uparrow', 'downarrow': BS + 'downarrow',
}

# what a unit may be "per": bits/second, rad/s, samples/symbol
UNIT_DENOM = set('s sec second seconds sample samples symbol symbols Hz '
                 'pixel bit bits'.split())
CONN_RUN = re.compile(r'^' + re.escape(BS) + r'quad' + re.escape(BS)
                      + r'text\{[^{}]*\}' + re.escape(BS) + r'quad$')

STOPWORD = set('of in on is to at by or if as per the a an and for with '
               'than from that its it be are was were no not'.split())

CONNECTIVE = set('for where when if with and or otherwise else then so at '
                 'to per since because all every each of in on is as'.split())

ABBREV = ('i.e.', 'e.g.', 'etc.', 'vs.', 'cf.', 'viz.')


def wordish(p):
    """an English word, as opposed to a name for a quantity: `round` and
       `Level` are words, `Rb`, `SNR` and `cos` are not"""
    if p in COMMON or p in FUNC or p in GREEK or p in UNITS or len(p) < 2:
        return False
    return p.islower() or (p[0].isupper() and p[1:].islower() and len(p) >= 3)


def hyphen_word(w):
    """`round-trip`, `non-zero`, `z-transform`, `4-point`, `radix-2`, `k-th`
       are single words with a hyphen in them; `n-k` and `N-1` are not"""
    parts = w.split('-')
    if len(parts) < 2 or any(not p for p in parts):
        return False
    a, rest = parts[0], parts[1:]
    if a.isdigit():
        return all(p.isalpha() and (len(p) >= 2 or p == 'D') for p in rest)
    if not a.isalpha():
        return False
    if len(parts) == 2 and rest[0].isdigit():
        return wordish(a) and len(a) >= 3
    if not all(p.isalpha() for p in rest):
        return False
    if all(wordish(p) for p in parts):
        return True
    if len(parts) == 2 and len(a) == 1:
        b = rest[0]
        return (wordish(b) and len(b) >= 3) or b in ('th', 'st', 'nd', 'rd')
    return False


# --------------------------------------------------------------- tokeniser
class Tok(object):
    __slots__ = ('k', 'v', 'g')

    def __init__(self, k, v, g=False):
        self.k, self.v, self.g = k, v, g      # g: glued to the token before

    def __repr__(self):
        return '%s(%s)' % (self.k, self.v)


REL = ['<-->', '<->', '-->', '<--', '<=>', '==', '<=', '>=', '!=', '~=',
       '->', '<-', '=>', '=', '<', '>']
NUM = re.compile(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?'
                 r'|\d+(?:\.\d+)?(?:[eE][-+]?\d+)?')
IDENT = re.compile(r'[A-Za-z][A-Za-z0-9]*')
HYPH = re.compile(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+')
OPCH = '+-*/^_(){}[]|,;:!%&#.@'


def abbrev_at(s, i):
    for ab in ABBREV:
        if s.startswith(ab, i) and (i + len(ab) >= len(s)
                                    or not s[i + len(ab)].isalnum()):
            return ab
    return None


def tokenize(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in ' \t':
            j = i
            while j < n and s[j] in ' \t':
                j += 1
            # two spaces or more is a column break, and the parser needs to
            # know: `= 4    x(1) = ...` is two statements, not 4 times x(1)
            wide = (j - i >= 2) or ('\t' in s[i:j])
            if out and out[-1].k != 'ws':
                out.append(Tok('ws', '  ' if wide else ' '))
            elif out and wide:
                out[-1].v = '  '
            i = j
            continue
        if c.isalpha() or c.isdigit():
            ab = abbrev_at(s, i)
            if ab:
                out.append(Tok('id', ab))
                i += len(ab)
                continue
            m = HYPH.match(s, i)
            if m and hyphen_word(m.group(0)):
                out.append(Tok('id', m.group(0)))
                i = m.end()
                continue
        m = UNIT_PHRASE.match(s, i)
        if m and (i + len(m.group(0)) >= n or not s[i + len(m.group(0))].isalnum()):
            out.append(Tok('unit', m.group(0)))
            i = m.end()
            continue
        if s.startswith('/_', i):
            out.append(Tok('op', 'angle'))
            i += 2
            continue
        if s.startswith('+/-', i) or s.startswith('-/+', i):
            out.append(Tok('op', '+/-'))
            i += 3
            continue
        if s.startswith('...', i):
            out.append(Tok('op', '...'))
            i += 3
            continue
        if s.startswith('..', i):
            out.append(Tok('op', '...'))
            i += 2
            continue
        hit = None
        for r in REL:
            if s.startswith(r, i):
                hit = r
                break
        if hit:
            out.append(Tok('rel', hit))
            i += len(hit)
            continue
        m = NUM.match(s, i)
        if m:
            v, end = m.group(0), m.end()
            # `50 000` and `1 000 000`: thousands written with spaces
            if re.match(r'^\d{1,3}$', v):
                while True:
                    mm = re.match(r' (\d{3})(?![\d.,])', s[end:])
                    if not mm:
                        break
                    v += ',' + mm.group(1)
                    end += mm.end()
            out.append(Tok('num', v))
            i = end
            continue
        # `.35` is 0.35 when nothing numeric comes before the point
        if (c == '.' and i + 1 < n and s[i + 1].isdigit()
                and (i == 0 or not s[i - 1].isalnum())):
            m = re.match(r'\.\d+', s[i:])
            out.append(Tok('num', '0' + m.group(0)))
            i += m.end()
            continue
        m = IDENT.match(s, i)
        if m:
            v, end = m.group(0), m.end()
            # `j0.3536` is j times 0.3536, not a symbol called j0
            mm = re.match(r'^([A-Za-z]+)(\d+)$', v)
            if mm and end + 1 < n and s[end] == '.' and s[end + 1].isdigit():
                v = mm.group(1)
                end = i + len(v)
            # `j2pi` is j times 2 times pi (but d2f is a derivative)
            mm = re.match(r'^([A-Za-z])(\d{1,2})([A-Za-z]+)$', v)
            if mm and v[0] != 'd':
                out.append(Tok('id', mm.group(1)))
                out.append(Tok('num', mm.group(2), True))
                out.append(Tok('id', mm.group(3), True))
                i = end
                continue
            out.append(Tok('id', v))
            i = end
            continue
        if c in OPCH:
            out.append(Tok('op', c))
            i += 1
            continue
        raise TexError('stray character %r' % c)
    while out and out[-1].k == 'ws':
        out.pop()
    return out


# --------------------------------------------------------------- parser
RELTEX = {
    '=': '=', '<': '<', '>': '>', '<=': BS + 'le', '>=': BS + 'ge',
    '!=': BS + 'ne', '~=': BS + 'approx', '==': BS + 'equiv',
    '->': BS + 'to', '<-': BS + 'leftarrow', '<->': BS + 'leftrightarrow',
    '-->': BS + 'longrightarrow', '<--': BS + 'longleftarrow',
    '<-->': BS + 'longleftrightarrow',
    '=>': BS + 'Rightarrow', '<=>': BS + 'Leftrightarrow',
}

IDENTLIKE = re.compile(
    r'^(?:[A-Za-z]|%(b)smathrm\{[^{}]*\}|%(b)soperatorname\{[^{}]*\}|'
    r'%(b)s[a-zA-Z]+)(?:_(?:\{[^{}]*\}|[A-Za-z0-9]))?$' % {'b': re.escape(BS)})


class P(object):
    def __init__(self, toks, sym, mats=None):
        self.t, self.i, self.sym = toks, 0, sym
        self.mats = mats or []
        self.inbar = 0

    # -- cursor
    def peek(self):
        i = self.i
        while i < len(self.t) and self.t[i].k == 'ws':
            i += 1
        return self.t[i] if i < len(self.t) else None

    def peek_raw(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        while self.i < len(self.t) and self.t[self.i].k == 'ws':
            self.i += 1
        if self.i >= len(self.t):
            return None
        t = self.t[self.i]
        self.i += 1
        return t

    def done(self):
        return self.peek() is None

    def script_next(self):
        """is the next non-space token a sub/superscript marker?"""
        i = self.i
        while i < len(self.t) and self.t[i].k == 'ws':
            i += 1
        return (i < len(self.t) and self.t[i].k == 'op'
                and self.t[i].v in '_^')

    def spaced_both(self):
        """is the next token free-standing, with space on either side?"""
        i = self.i
        if i >= len(self.t) or self.t[i].k != 'ws':
            return False
        i += 1
        while i < len(self.t) and self.t[i].k == 'ws':
            i += 1
        return i + 1 < len(self.t) and self.t[i + 1].k == 'ws'

    def gap_next(self):
        """two or more spaces before the next token: a column, not a product"""
        t = self.peek_raw()
        return t is not None and t.k == 'ws' and len(t.v) >= 2

    def statement_ahead(self, t):
        """after a column gap, is what follows a statement of its own?
           `= 4    x(1) = ...` yes; `mu  sum a_k p(t)` no, that is a product;
           `N   log2 N = 24` no, a function never opens a statement"""
        if t.k == 'op':
            if t.v not in '([{':
                return False
        elif t.k == 'id':
            v = t.v
            if (v in CONNECTIVE or v in STOPWORD or v in TEXTY or v in UNITS
                    or v in FUNC or v in ABBREV or '-' in v
                    or v.lower() in ('sum', 'prod', 'integral', 'int', 'sqrt',
                                     'lim')
                    or v.startswith('log')):
                return False
            # a name opens a statement only with its arguments, a subscript
            # or a relation right behind it (`x, y = position` counts too)
            j = self.i
            while j < len(self.t) and self.t[j].k == 'ws':
                j += 1
            k = j + 1
            while k < len(self.t) and self.t[k].k == 'ws':
                k += 1
            if k >= len(self.t):
                return False
            n2 = self.t[k]
            if n2.k == 'op' and n2.v == ',':
                rest = [x for x in self.t[k + 1:k + 6] if x.k != 'ws'][:2]
                return (len(rest) == 2 and rest[0].k == 'id'
                        and rest[1].k == 'rel')
            if not ((n2.k == 'op' and n2.v in '([_') or n2.k == 'rel'):
                return False
        elif t.k != 'num':
            return False
        # and a relation has to come before the clause ends
        depth = 0
        for x in self.t[self.i:]:
            if x.k == 'op' and x.v in '([{':
                depth += 1
            elif x.k == 'op' and x.v in ')]}':
                depth -= 1
                if depth < 0:
                    return False
            elif depth == 0 and x.k == 'op' and x.v in ',;':
                return False
            elif depth == 0 and x.k == 'rel':
                return True
        return False

    def upcoming(self, k):
        """the k-th non-space token ahead, or None"""
        i, seen = self.i, 0
        while i < len(self.t):
            if self.t[i].k != 'ws':
                seen += 1
                if seen == k:
                    return self.t[i]
            i += 1
        return None

    def function_word(self, k):
        """is the k-th token ahead `and`, `of`, `the`...? then a lone `x`
           before it is a variable (`lengths of x and h`), not a times sign"""
        t = self.upcoming(k)
        return (t is not None and t.k == 'id'
                and (t.v in STOPWORD or t.v in CONNECTIVE or t.v in TEXTY))

    def is_word(self, t, strict=False):
        """an English word, so that a lone `a` next to it is the article"""
        if t is None or t.k != 'id' or len(t.v) < 2:
            return False
        if '-' in t.v:
            return True
        if strict:
            return (WORDY.match(t.v) is not None and t.v not in NOT_WORDS
                    and t.v not in STOPWORD and self.sym_of(t.v) is None)
        return t.v in STOPWORD or self.sym_of(t.v) is None

    def starts_factor(self, t):
        if t.k in ('num', 'id', 'unit'):
            return True
        if t.k == 'op':
            if t.v in '([{':
                return True
            if t.v == '|' and self.inbar == 0:
                return True
            if t.v == 'angle':
                return True                 # 0.7367 /_ 28.68 deg
        return False

    # -- symbols
    def sym_of(self, name, script=False):
        if '-' in name or name in ABBREV:
            return None                     # round-trip, i.e. -- prose
        if name in self.sym:
            return self.sym[name]
        if name in COMMON:
            return COMMON[name]
        if name in GREEK:
            return BS + name
        if name in FUNC:
            return FUNC[name]
        if len(name) == 1:
            return name
        m = re.match(r'^([A-Za-z])(\d+)$', name)
        if m and m.group(1) not in ('j', 'i', 'e'):
            return '%s_{%s}' % (m.group(1), m.group(2))
        if m:
            return '%s %s' % (m.group(1), m.group(2))
        if script and name.isalpha():
            return BS + 'mathrm{%s}' % name  # V_in, V_out, x_max
        low = name.lower()
        if name in TEXTY or name in STOPWORD or name in CONNECTIVE:
            return None
        # `In`, `If`, `The` at the start of a sentence; not `aN`, not `NOT`
        if name.istitle() and (low in STOPWORD or low in CONNECTIVE):
            return None
        if name.isupper() or name in UNITS:
            return BS + 'mathrm{%s}' % name
        # two letters with no meaning of their own are two variables side
        # by side: `kn` is k times n, `kF` is k times F, and italic is right
        if len(name) == 2 and name.isalpha():
            return name
        if script:
            return BS + 'mathrm{%s}' % name
        if WORDY.match(name) and name not in NOT_WORDS:
            return None                     # prose -- caller makes \text{}
        return BS + 'mathrm{%s}' % name

    # -- grammar
    def relation(self):
        parts = self.relation_parts()
        return ' '.join(x for x in parts if x != '')

    def relation_parts(self):
        t = self.peek()
        if t is not None and t.k == 'rel':
            self.next()
            parts = ['', RELTEX[t.v], self.expr()]
        else:
            parts = [self.expr()]
        while True:
            t = self.peek()
            if t is None:
                break
            if t.k == 'rel':
                self.next()
                parts.append(RELTEX[t.v])
                parts.append(self.expr())
                continue
            if t.k == 'op' and t.v in ',;':
                self.next()
                parts.append(t.v)
                parts.append(self.expr())
                continue
            if t.k == 'op' and t.v == ':':
                self.next()
                parts.append('{:}' + BS + 'quad')
                parts.append(self.expr())
                continue
            break
        return parts

    def expr(self):
        out = []
        t = self.peek()
        if t and t.k == 'op' and t.v in '+-':
            self.next()
            out.append(t.v)
        out.append(self.term())
        while True:
            t = self.peek()
            if t is None or t.k != 'op' or t.v not in '+-':
                break
            self.next()
            out.append(t.v)
            out.append(self.term())
        left = ' '.join(x for x in out if x != '')
        # `A   /   B` written with wide spaces: the whole of A over the
        # whole of B, which a tight `a/b` never means
        t = self.peek()
        if t and t.k == 'op' and t.v == '/' and self.gap_next():
            self.next()
            return BS + 'frac{%s}{%s}' % (bare(left), bare(self.expr()))
        # `... SNR is Eb/N0`: a connective starts a fresh term
        if t and t.k == 'id' and t.v in CONNECTIVE and not self.script_next():
            rest = self.expr()
            sep = BS + ', ' if rest.startswith(BS + 'text{') else ' '
            return left + sep + rest
        return left

    def term(self):
        left = self.factor()
        # a connective (`so`, `where`) never binds to what follows it:
        # `so Eb/N0 = 124` is `so` and then a fraction
        if CONN_RUN.match(left):
            t = self.peek()
            if t is not None and self.starts_factor(t):
                return left + ' ' + self.term()
            return left
        last = left
        while True:
            t = self.peek()
            if t is None:
                break
            # a connective ends the term: `... SNR is Eb/N0`
            if (t.k == 'id' and t.v in CONNECTIVE and left
                    and not self.script_next()):
                break
            # `0 .. N/2 - 1`, `n = -3 .. 0`: a range
            if t.k == 'op' and t.v == '...':
                self.next()
                nxt = self.peek()
                if nxt is not None and self.starts_factor(nxt):
                    return left + ' ' + BS + 'dots ' + self.expr()
                return left + ' ' + BS + 'dots'
            if t.k == 'op' and t.v == '/':
                if self.gap_next():
                    break                   # expr() sets the wide fraction
                den = self.upcoming(2)
                after = self.upcoming(3)
                if (is_unitish(last) and den is not None and den.k == 'id'
                        and den.v in UNIT_DENOM
                        and not (after is not None and after.k == 'id'
                                 and self.is_word(after))):
                    self.next()
                    self.next()             # bits/second, rad/s: one unit
                    left = left + '/' + BS + 'mathrm{%s}' % den.v
                    last = ''
                    continue
                self.next()
                right = self.tight_chain()
                if is_unitish(left) and is_unitish(right):
                    left = left + '/' + right
                else:
                    left = BS + 'frac{%s}{%s}' % (bare(left), bare(right))
                last = left
                continue
            if t.k == 'op' and t.v in '*.':
                self.next()
                right = self.factor()
                left = (join_conv(left, right) if t.v == '*'
                        else left + ' ' + BS + 'cdot ' + right)
                last = right
                continue
            if (t.k == 'id' and t.v == 'x' and times_ok(left)
                    and self.spaced_both() and not self.function_word(2)):
                save = self.i
                self.next()
                nxt = self.peek()
                if nxt and self.starts_factor(nxt):
                    right = self.factor()
                    left = left + ' ' + BS + 'times ' + right
                    last = right
                    continue
                self.i = save
                break
            if self.starts_factor(t):
                if (self.gap_next() and self.statement_ahead(t)
                        and not left.rstrip().endswith(BS + 'quad')):
                    sep = BS + 'quad ' if ends_with_text(left) else BS + 'qquad '
                    right = self.factor()
                    left = left + ' ' + sep + right
                else:
                    right = self.factor()
                    left = join_implicit(left, right)
                last = right
                continue
            break
        return left

    def tight_chain(self):
        """the denominator, plus any factor written hard against it:
           `8w^5 / 2w^3` is one fraction, but `(2/255^2) [t]` is not"""
        out = self.factor()
        while True:
            t = self.peek_raw()
            if t is None or t.k == 'ws':
                break
            if not self.starts_factor(t):
                break
            out = join_implicit(out, self.factor())
        # `frame bits / bit rate`: the word after a unit completes the name
        t = self.peek()
        if (is_unitish(out) and t is not None and self.is_word(t, strict=True)
                and not self.gap_next()):
            self.next()
            out = out + BS + ', ' + BS + 'text{%s}' % textify(t.v)
        return out

    def factor(self):
        t = self.peek()
        if t and t.k == 'op' and t.v in '+-':
            self.next()
            return t.v + self.factor()
        return self.power()

    def power(self):
        base = self.postfix()
        t = self.peek()
        if t and t.k == 'op' and t.v == '^':
            self.next()
            return '%s^{%s}' % (base, self.script())
        return base

    def script(self):
        """what follows ^ or _ -- a brace group, a signed atom, or one atom"""
        t = self.peek()
        if t is None:
            raise TexError('dangling script')
        if t.k == 'op' and t.v == '{':
            self.next()
            return self.until('}')
        if t.k == 'op' and t.v == '(':
            self.next()
            return self.until(')')
        if t.k == 'op' and t.v in '+-':
            self.next()
            return t.v + self.script()
        if t.k == 'id':
            self.next()
            out = self.sym_of(t.v, script=True)
            # e^(-j2w): the pieces of a split name stay in the exponent
            while self.peek_raw() is not None and self.peek_raw().g:
                nt = self.next()
                out += ' ' + (nt.v if nt.k == 'num' else self.sym_of(nt.v, script=True))
            return out
        if t.k == 'num':
            self.next()
            out = t.v
            nt = self.peek_raw()            # W_N^2k: the k belongs up there,
            nt2 = self.upcoming(2)          # but a^2y(-1) is a squared times y(-1)
            if (nt is not None and nt.k == 'id' and len(nt.v) == 1
                    and not (nt2 is not None and nt2.k == 'op' and nt2.v == '(')):
                self.next()
                out += nt.v
            return out
        return self.postfix()

    def postfix(self):
        node = self.atom()
        while True:
            t = self.peek_raw()
            if t is None:
                break
            if t.k == 'ws' and self.script_next():
                self.i += 1
                continue
            if t.k == 'op' and t.v == '_':
                self.i += 1
                node = add_sub(node, self.script())
                continue
            if t.k == 'op' and t.v == "'":
                self.i += 1
                node += "'"
                continue
            if t.k == 'op' and t.v == '%':
                self.i += 1
                node += BS + '%'
                continue
            if t.k == 'op' and t.v == '(' and IDENTLIKE.match(node):
                self.i += 1
                node = node + wrap(self.until(')'), '(', ')')
                continue
            break
        return node

    def atom(self):
        t = self.next()
        if t is None:
            raise TexError('unexpected end')
        if t.k == 'num':
            m = re.match(r'^(\d+(?:\.\d+)?)[eE]([-+]?\d+)$', t.v)
            if m:
                return '%s %stimes 10^{%s}' % (m.group(1), BS,
                                               m.group(2).lstrip('+'))
            # a thousands comma takes no space after it, which is what
            # {,} means to LaTeX
            return t.v.replace(',', '{,}')
        if t.k == 'unit':
            return BS + 'mathrm{%s}' % t.v
        if t.k == 'op':
            return self.op_atom(t)
        return self.ident_atom(t)

    def op_atom(self, t):
        if t.v == '(':
            return wrap(self.until(')'), '(', ')')
        if t.v == '[':
            return wrap(self.until(']'), '[', ']')
        if t.v == '{':
            return wrap(self.until('}'), BS + '{', BS + '}')
        if t.v == '|':
            self.inbar += 1
            try:
                inner = self.until('|')
            finally:
                self.inbar -= 1
            return BS + 'lvert ' + inner + ' ' + BS + 'rvert'
        if t.v == '...':
            return BS + 'dots'
        if t.v == '+/-':
            return BS + 'pm'
        if t.v == 'angle':
            return BS + 'angle'
        if t.v in ',;':
            return t.v
        if t.v in '&#':
            return BS + t.v
        if t.v == '!':
            return '!'
        raise TexError('unexpected %r' % t.v)

    def ident_atom(self, t):
        name = t.v
        if name.lower() in ('sum', 'prod'):
            nxt = self.upcoming(1)
            if (name == 'sum' and nxt is not None and nxt.k == 'id'
                    and nxt.v != 'over'
                    and (nxt.v in ('of', 'is', 'and', 'the', 'to')
                         or self.is_word(nxt, strict=True))):
                return self.text_run(name)  # `the sum of the mask coefficients`
            return self.bigop(name.lower())
        if name in ('integral', 'int', 'INT'):
            return self.bigop('integral')
        if name in SYMWORD:
            return SYMWORD[name]
        if name.startswith('MATRIX') and name[6:].isdigit():
            return self.mats[int(name[6:])]
        if name == 'a' and self.is_word(self.upcoming(1), strict=True):
            return self.text_run(name)      # `a random number`, not a times
        if name == 'lim':
            return self.limit()
        if name == 'sqrt':
            return self.sqrt()
        if name in ('log2', 'log10', 'lg'):
            sub = {'log2': '2', 'log10': '10', 'lg': '2'}[name]
            return BS + 'log_{%s}' % sub
        m = re.match(r'^log(\d+)([A-Za-z]?)$', name)
        if m:                               # log3, or log2N written flat
            return BS + 'log_{%s}%s' % (m.group(1), (' ' + m.group(2)) if m.group(2) else '')
        if name == 'grad':
            return self.grad()
        if name == 'deg':
            return '^' + BS + 'circ'
        d = self.deriv(name)
        if d is not None:
            return d
        if len(name) == 1 and name in self.sym and self.script_next():
            return name
        s = self.sym_of(name)
        if s is None:
            return self.text_run(name)
        return s

    def text_run(self, first):
        """a run of English words becomes one \\text{...}"""
        words = [first]
        while True:
            t = self.peek()
            if t is None or t.k != 'id':
                break
            # a single letter is a symbol, never a word in a phrase --
            # except `a` with a word on either side of it
            if len(t.v) < 2:
                if t.v == 'a' and self.is_word(self.upcoming(2)):
                    self.next()
                    words.append('a')
                    continue
                break
            # `discrete sum S_D = ...`: after a word, `sum` is a noun unless
            # a summand follows it directly
            if t.v == 'sum':
                after = self.upcoming(2)
                if after is None or after.k == 'rel' or (
                        after.k == 'id' and after.v[:1].isupper()):
                    self.next()
                    words.append('sum')
                    continue
            if self.sym_of(t.v) is not None and t.v not in STOPWORD:
                break
            self.next()
            words.append(t.v)
        run = ' '.join(words)
        if len(words) == 1 and first.lower() in CONNECTIVE:
            return BS + 'quad' + BS + 'text{%s}' % textify(run) + BS + 'quad'
        return BS + 'text{%s}' % textify(run)

    # -- specials
    def until(self, close):
        out = []
        while True:
            t = self.peek()
            if t is None:
                raise TexError('unclosed %r' % close)
            if t.k == 'op' and t.v == close:
                self.next()
                break
            if t.k == 'op' and t.v in ')]}' and t.v != close:
                raise TexError('mismatched %r' % t.v)
            if t.k == 'op' and t.v == ',':
                self.next()
                out.append(',')
                continue
            if t.k == 'op' and t.v == ':':
                self.next()
                out.append('{:}')
                continue
            before = self.i
            out.append(self.relation())
            if self.i == before:
                raise TexError('stuck inside %r' % close)
        return ' '.join(x for x in out if x).replace(' ,', ',')

    def bigop(self, name):
        tex = {'sum': BS + 'sum', 'prod': BS + 'prod',
               'integral': BS + 'int', 'int': BS + 'int'}[name]
        lo = hi = None
        t = self.peek_raw()
        if t and t.k == 'op' and t.v == '_':
            self.i += 1
            lo = self.script()
        t = self.peek_raw()
        if t and t.k == 'op' and t.v == '^':
            self.i += 1
            hi = self.script()
        t = self.peek()
        if lo is None and t and t.k == 'id' and t.v == 'over':
            self.next()
            lo = self.script()
            t = self.peek()
            if t and t.k == 'id' and t.v in ('of', 'from'):
                self.next()
        if lo:
            tex += '_{%s}' % lo
        if hi:
            tex += '^{%s}' % hi
        t = self.peek()
        if t is None or not self.starts_factor(t):
            return tex
        body = self.term()
        if name in ('integral', 'int'):
            body = re.sub(re.escape(BS) + r'mathrm\{d([a-zA-Z])\}\s*$',
                          lambda m: BS + ', d' + m.group(1), body)
        return tex + ' ' + body

    def limit(self):
        t = self.peek_raw()
        if t and t.k == 'op' and t.v == '_':
            self.i += 1
            return BS + 'lim_{%s}' % self.script()
        return BS + 'lim'

    def sqrt(self):
        t = self.peek_raw()
        if t and t.k == 'op' and t.v == '(':
            self.i += 1
            return BS + 'sqrt{%s}' % self.until(')')
        t = self.peek()
        if t and t.k == 'op' and t.v == '(':
            self.next()
            return BS + 'sqrt{%s}' % self.until(')')
        return BS + 'sqrt{%s}' % bare(self.postfix())

    def grad(self):
        t = self.peek_raw()
        if t and t.k == 'op' and t.v == '^':
            self.i += 1
            p = self.script()
            return BS + 'nabla^{%s}' % p
        return BS + 'nabla'

    def deriv(self, name):
        """d2f/dx2, dX(z)/dz, df/dx -- written flat in the source"""
        m = re.match(r'^d(\d?)([A-Za-z][A-Za-z0-9]*)$', name)
        if not m:
            return None
        order, fn = m.group(1), m.group(2)
        save = self.i
        args = ''
        t = self.peek_raw()
        if t and t.k == 'op' and t.v == '(':
            self.i += 1
            try:
                args = '(' + self.until(')') + ')'
            except TexError:
                self.i = save
                return None
        t = self.peek()
        if not (t and t.k == 'op' and t.v == '/'):
            self.i = save
            return None
        self.next()
        t2 = self.peek()
        if not (t2 and t2.k == 'id'):
            self.i = save
            return None
        m2 = re.match(r'^d([A-Za-z])(\d?)$', t2.v)
        if not m2:
            self.i = save
            return None
        self.next()
        var, o2 = m2.group(1), m2.group(2)
        o = order or o2
        sup = ('^%s' % o) if o else ''
        top = BS + 'partial' + sup + ' ' + self.sym_of(fn) + args
        bot = BS + 'partial ' + var + sup
        return BS + 'frac{%s}{%s}' % (top, bot)


# --------------------------------------------------------------- helpers
def add_sub(node, sub):
    """N_0 with a further _dBm is one subscript with two parts in it,
       not two subscripts, which LaTeX will not accept at all"""
    m = re.search(r'_\{([^{}]*)\}$', node)
    if m:
        return node[:m.start()] + '_{%s,%s}' % (m.group(1), sub)
    m = re.search(r'_([A-Za-z0-9])$', node)
    if m:
        return node[:m.start()] + '_{%s,%s}' % (m.group(1), sub)
    return '%s_{%s}' % (node, sub)


def times_ok(s):
    """a lone `x` between two operands is a multiplication sign"""
    return bool(s.strip())


def looks_numeric(s):
    return re.match(r'^[-+]?[\d.]+$', s.strip()) is not None


def is_unitish(s):
    return re.match(r'^' + re.escape(BS) + r'mathrm\{[A-Za-z]+\}$',
                    s.strip()) is not None


def bare(s):
    s = s.strip()
    if s.startswith('(') and s.endswith(')') and balanced(s[1:-1]):
        return s[1:-1].strip()
    lo, hi = BS + 'left(', BS + 'right)'
    if s.startswith(lo) and s.endswith(hi):
        inner = s[len(lo):-len(hi)]
        if balanced(inner):
            return inner.strip()
    return s


def balanced(s):
    d = 0
    for c in s:
        if c == '(':
            d += 1
        elif c == ')':
            d -= 1
            if d < 0:
                return False
    return d == 0


def wrap(inner, lo, hi):
    tall = any(k in inner for k in (BS + 'frac', BS + 'sum', BS + 'int',
                                    BS + 'prod', BS + 'sqrt'))
    if tall:
        return BS + 'left' + lo + ' ' + inner + ' ' + BS + 'right' + hi
    return lo + inner + hi


FUNCISH = re.compile(r'^[a-zA-Z](?:_\{[^{}]*\})?\([^()]*\)$')


def join_conv(a, b):
    """an explicit * between two signals is convolution, not a product"""
    a, b = a.strip(), b.strip()
    if FUNCISH.match(a) and FUNCISH.match(b):
        return a + ' ' + BS + 'ast ' + b
    if a.endswith(BS + '}') and b.startswith(BS + '{'):
        return a + ' ' + BS + 'ast ' + b    # {1, 2, 3} * {1, 1}
    if a[-1:].isdigit() and b[:1].isdigit():
        return a + ' ' + BS + 'cdot ' + b   # 2 * 600
    return join_implicit(a, b)


def ends_with_text(s):
    return re.search(re.escape(BS) + r'text\{[^{}]*\}\s*$', s) is not None


def join_implicit(a, b):
    a, b = a.strip(), b.strip()
    if not a:
        return b
    if not b:
        return a
    if a[-1:].isdigit() and b[:1].isdigit():
        # `31 713` is thirty-one thousand; any other pair of numbers side
        # by side is a list, never a product (products are written 2*3)
        if re.match(r'^\d+$', a) and re.match(r'^\d{3}$', b):
            return a + '{,}' + b
        return a + ' ' + BS + 'quad ' + b
    if b.startswith(BS + 'mathrm{') and a[-1:].isdigit():
        return a + BS + ', ' + b            # 9 bits, 4.2 MHz
    if re.search(re.escape(BS) + r'text\{[^{}]*\}$', a):
        return a + BS + ', ' + b
    if b.startswith(BS + 'text{') and a[-1:] not in ' ':
        return a + BS + ', ' + b
    return a + ' ' + b


def textify(s):
    s = s.replace(BS, '')
    for a, b in (('{', BS + '{'), ('}', BS + '}'), ('%', BS + '%'),
                 ('&', BS + '&'), ('#', BS + '#'), ('$', BS + '$'),
                 ('_', BS + '_'), ('^', BS + 'textasciicircum ')):
        s = s.replace(a, b)
    return s.replace(' -- ', ' --- ')


# --------------------------------------------------------------- line level
LABEL = re.compile(r'^([A-Za-z][A-Za-z0-9 ,\'()/+-]{0,46}?)\s*:\s+(\S.*)$')
LISTNUM = re.compile(r'^\s*(\d{1,2})[.)]\s+(?=[A-Za-z])')
LISTLET = re.compile(r'^\s*\(([a-z])\)\s+')
REMARK = re.compile(r'^\s*--\s*(.*)$')
_CELL = r'[-+]?\d+(?:\.\d+)?'
MAT = re.compile(r'\[\s*(' + _CELL + r'(?:[ \t]+' + _CELL + r')*'
                 r'(?:\s*;\s*' + _CELL + r'(?:[ \t]+' + _CELL + r')*)+)\s*\]')


def pull_matrices(body):
    """`[2 1 3 1; 1 2 1 3]` -- rows of numbers split by semicolons -- is a
       matrix; it is set aside and put back as one bracketed block"""
    mats = []

    def sub(m):
        rows = [r.split() for r in m.group(1).split(';')]
        if len(rows) < 2 or len(set(len(r) for r in rows)) != 1:
            return m.group(0)
        body = (' ' + BS + BS + ' ').join(' & '.join(r) for r in rows)
        mats.append(BS + 'begin{bmatrix} ' + body + ' ' + BS + 'end{bmatrix}')
        return ' MATRIX%d ' % (len(mats) - 1)
    return MAT.sub(sub, body), mats


def split_comment(s):
    """`X = 3        the answer` -> ('X = 3', 'the answer')"""
    m = re.search(r'\s+--\s+(.+)$', s)
    if m and s[:m.start()].strip():
        return s[:m.start()], m.group(1).strip()
    # `d : 1 0 1 1 0 1   <-- the original sequence`
    m = re.search(r'\s+<--\s+([A-Za-z].+)$', s)
    if (m and s[:m.start()].strip() and not re.search(r'[=<>^_]', m.group(1))
            and len(re.findall(r'[A-Za-z]{3,}', m.group(1))) >= 2):
        return s[:m.start()], m.group(1).strip()
    m = re.search(r'\s{3,}(.+)$', s)
    if not m or not s[:m.start()].strip():
        return s, None
    tail, head = m.group(1).strip(), s[:m.start()]
    if tail.startswith('(') and tail.endswith(')'):
        return head, tail[1:-1].strip()
    if re.search(r'[=<>^_]|\d\s*/\s*\d', tail):
        return s, None
    words = re.findall(r'[A-Za-z]{3,}', tail)
    if len(words) >= 2:
        return head, tail
    return s, None


def split_label(s):
    """`bits :  I = -log2(0.2)` -> ('bits', 'I = -log2(0.2)')"""
    m = LABEL.match(s)
    if not m:
        return None, s
    lab, rest = m.group(1).strip(), m.group(2)
    if re.search(r'[=<>^]', lab):
        return None, s
    if not re.search(r'[A-Za-z]', lab):
        return None, s
    return lab, rest


def tidy(s):
    s = re.sub(r'\s+([,;])', r'\1', s)
    # a comma between digits is a thousands separator, not a list: it takes
    # no space after it, which {,} is the LaTeX way of saying
    for _ in range(4):
        out = re.sub(r'(?<=\d),\s*(?=\d{3}\b)', '{,}', s)
        if out == s:
            break
        s = out
    s = re.sub(r'[ ]{2,}', ' ', s)
    return s.strip()


def is_prose(s):
    """a line with no operators and three or more words is a sentence"""
    if re.search(r'[=<>^_*]', s):
        return False
    if s.rstrip().endswith(':') and re.findall(r'[A-Za-z]{2,}', s):
        return True
    if re.search(r'\d\s*/\s*\d', s):
        return False
    return len(re.findall(r'[A-Za-z]{3,}', s)) >= 3


def line(src, subject=''):
    """one source line -> {'label', 'math', 'note'}; raises TexError"""
    src = src.rstrip()
    if not src.strip():
        return {'label': None, 'math': '', 'note': None}
    src = re.sub(r'(?<=[0-9])\s*[xX]\s*(?=[0-9])', ' x ', src)
    src = LISTNUM.sub('', src)
    # a line that opens with a dash is a remark, unless it is a bullet in
    # front of an equation: `-- a = 0.5, N = 4:` is still mathematics
    m = REMARK.match(src)
    if m:
        rest = m.group(1).strip()
        if not re.search(r'[=<>]|->|=>', rest):
            return {'label': None, 'math': '', 'note': rest, 'parts': []}
        src = rest
    # `(a) x(n) = ...`: the letter numbers the line, it is not a symbol
    enum = None
    m = LISTLET.match(src)
    if m:
        enum = '(%s)' % m.group(1)
        src = src[m.end():]
    head, note = split_comment(src)
    label, body = split_label(head.strip())
    if enum:
        label = enum + (' ' + label if label else '')
    body, mats = pull_matrices(body)
    toks = tokenize(body)
    if not toks:
        raise TexError('empty after tokenising')
    p = P(toks, SUBJECT.get(subject, {}), mats)
    parts = p.relation_parts()
    if not p.done():
        raise TexError('trailing tokens at %d (%r)' % (p.i, p.t[p.i].v))
    parts = [tidy(x) for x in parts]
    out = tidy(' '.join(x for x in parts if x != ''))
    return {'label': label, 'math': out, 'note': note, 'parts': parts}
