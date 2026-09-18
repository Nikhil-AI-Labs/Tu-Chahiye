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
    'hellip': '...', 'lowast': '*', 'radic': 'sqrt', 'sum': 'sum',
    'prod': 'prod', 'int': 'integral', 'part': 'd', 'nabla': 'grad',
    'sup2': '^2', 'sup3': '^3', 'frac12': '1/2', 'frac14': '1/4',
    'ldquo': '"', 'rdquo': '"', 'lsquo': "'", 'rsquo': "'", 'prime': "'",
    'bull': ' . ', 'lowbar': '_',
    'oplus': ' xor ', 'otimes': ' * ', 'ominus': ' - ',
    'cap': ' cap ', 'cup': ' cup ', 'isin': ' in ', 'ni': ' in ',
    'notin': ' notin ', 'sube': ' subset ', 'sub': ' subset ',
    'empty': ' emptyset ', 'forall': ' forall ', 'exist': ' exists ',
    'ang': ' angle ', 'perp': ' perp ', 'and': ' and ', 'or': ' or ',
    'lowast': '*', 'lceil': '[', 'rceil': ']', 'lfloor': '[',
    'rfloor': ']', 'larr': '<-', 'uarr': ' up ', 'darr': ' down ',
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
    u'°': ' deg', u'…': '...', u'∗': '*', u'√': 'sqrt',
    u'∑': 'sum', u'∏': 'prod', u'∫': 'integral',
    u'∂': 'd', u'∇': 'grad', u'·': ' . ', u' ': ' ',
    u'′': "'", u'✓': ' -- ok', u'✗': ' -- no',
    u'≡': '==', u'∅': ' emptyset ', u'∈': ' in ',
    u'α': ' alpha ', u'β': ' beta ', u'γ': ' gamma ',
    u'δ': ' delta ', u'ε': ' epsilon ', u'θ': ' theta ',
    u'λ': ' lambda ', u'μ': ' mu ', u'π': ' pi ',
    u'ρ': ' rho ', u'σ': ' sigma ', u'τ': ' tau ',
    u'φ': ' phi ', u'ϕ': ' phi ', u'ω': ' omega ',
    u'Δ': ' Delta ', u'Γ': ' Gamma ', u'Ω': ' Omega ',
    u'Φ': ' Phi ', u'Σ': ' Sigma ', u'Θ': ' Theta ',
    u'Λ': ' Lambda ', u'Π': ' Pi ',
    u'²': '^2', u'³': '^3', u'½': '(1/2)',
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
    'sgn': BS + 'operatorname{sgn}', 'sign': BS + 'operatorname{sgn}',
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
                'arg det gcd sign'.split())

TEXTY = set('vs no ok yes all any one two per'.split())

STOPWORD = set('of in on is to at by or if as per the a an and for with '
               'than from that its it be are was were no not'.split())

CONNECTIVE = set('for where when if with and or otherwise else then so at '
                 'to per since because all every each of in on is as'.split())


# --------------------------------------------------------------- tokeniser
class Tok(object):
    __slots__ = ('k', 'v')

    def __init__(self, k, v):
        self.k, self.v = k, v

    def __repr__(self):
        return '%s(%s)' % (self.k, self.v)


REL = ['<->', '-->', '<--', '<=>', '==', '<=', '>=', '!=', '~=', '->', '<-',
       '=>', '=', '<', '>']
NUM = re.compile(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?'
                 r'|\d+(?:\.\d+)?(?:[eE][-+]?\d+)?')
IDENT = re.compile(r'[A-Za-z][A-Za-z0-9]*')
OPCH = '+-*/^_(){}[]|,;:!%&#.@'


def tokenize(s):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in ' \t':
            i += 1
            if out and out[-1].k != 'ws':
                out.append(Tok('ws', ' '))
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
            out.append(Tok('num', m.group(0)))
            i = m.end()
            continue
        m = IDENT.match(s, i)
        if m:
            out.append(Tok('id', m.group(0)))
            i = m.end()
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
    '=>': BS + 'Rightarrow', '<=>': BS + 'Leftrightarrow',
}

IDENTLIKE = re.compile(
    r'^(?:[A-Za-z]|%(b)smathrm\{[^{}]*\}|%(b)soperatorname\{[^{}]*\}|'
    r'%(b)s[a-zA-Z]+)(?:_(?:\{[^{}]*\}|[A-Za-z0-9]))?$' % {'b': re.escape(BS)})


class P(object):
    def __init__(self, toks, sym):
        self.t, self.i, self.sym = toks, 0, sym
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

    def starts_factor(self, t):
        if t.k in ('num', 'id', 'unit'):
            return True
        if t.k == 'op':
            if t.v in '([{':
                return True
            if t.v == '|' and self.inbar == 0:
                return True
        return False

    # -- symbols
    def sym_of(self, name, script=False):
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
        if name in TEXTY or name in STOPWORD or name in CONNECTIVE:
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
        return ' '.join(x for x in out if x != '')

    def term(self):
        left = self.factor()
        while True:
            t = self.peek()
            if t is None:
                break
            if t.k == 'op' and t.v == '/':
                self.next()
                right = self.tight_chain()
                if is_unitish(left) and is_unitish(right):
                    left = left + '/' + right
                else:
                    left = BS + 'frac{%s}{%s}' % (bare(left), bare(right))
                continue
            if t.k == 'op' and t.v in '*.':
                self.next()
                right = self.factor()
                left = (join_conv(left, right) if t.v == '*'
                        else left + ' ' + BS + 'cdot ' + right)
                continue
            if (t.k == 'id' and t.v == 'x' and times_ok(left)
                    and self.spaced_both()):
                save = self.i
                self.next()
                nxt = self.peek()
                if nxt and self.starts_factor(nxt):
                    right = self.factor()
                    left = left + ' ' + BS + 'times ' + right
                    continue
                self.i = save
                break
            if self.starts_factor(t):
                left = join_implicit(left, self.factor())
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
            return self.sym_of(t.v, script=True)
        if t.k == 'num':
            self.next()
            return t.v
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
        if name in ('sum', 'prod', 'integral', 'int'):
            return self.bigop(name)
        if name == 'lim':
            return self.limit()
        if name == 'sqrt':
            return self.sqrt()
        if name in ('log2', 'log10', 'lg'):
            sub = {'log2': '2', 'log10': '10', 'lg': '2'}[name]
            return BS + 'log_{%s}' % sub
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
            # a single letter is a symbol, never a word in a phrase
            if len(t.v) < 2:
                break
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
    if FUNCISH.match(a.strip()) and FUNCISH.match(b.strip()):
        return a + ' ' + BS + 'ast ' + b
    return join_implicit(a, b)


def join_implicit(a, b):
    a, b = a.strip(), b.strip()
    if not a:
        return b
    if not b:
        return a
    if a[-1:].isdigit() and b[:1].isdigit():
        return a + ' ' + BS + 'cdot ' + b
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
    return s


# --------------------------------------------------------------- line level
LABEL = re.compile(r'^([A-Za-z][A-Za-z0-9 ,\'()/+-]{0,46}?)\s*:\s+(\S.*)$')
LISTNUM = re.compile(r'^\s*(\d{1,2})[.)]\s+(?=[A-Za-z])')


def split_comment(s):
    """`X = 3        the answer` -> ('X = 3', 'the answer')"""
    m = re.search(r'\s+--\s+(.+)$', s)
    if m and s[:m.start()].strip():
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
    head, note = split_comment(src)
    label, body = split_label(head.strip())
    toks = tokenize(body)
    if not toks:
        raise TexError('empty after tokenising')
    p = P(toks, SUBJECT.get(subject, {}))
    parts = p.relation_parts()
    if not p.done():
        raise TexError('trailing tokens at %d (%r)' % (p.i, p.t[p.i].v))
    parts = [tidy(x) for x in parts]
    out = tidy(' '.join(x for x in parts if x != ''))
    return {'label': label, 'math': out, 'note': note, 'parts': parts}
