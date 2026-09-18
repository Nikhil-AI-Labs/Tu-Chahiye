# -*- coding: utf-8 -*-
"""
Fix the notation that lives inside running prose.

Two different jobs need two different answers, and this is the second one.

A formula that stands on its own -- in a monospace block or a <code> span
-- gets typeset, by mathpass.py. But a sentence like "each level needs b
bits, so L = 2^b" is prose with notation in it. Setting `2^b` in Computer
Modern in the middle of that sentence puts two typefaces inside one
expression and reads worse than what it replaced.

So prose gets the symbols and nothing else: a real superscript, a real
multiplication sign, a real pi. That is the actual complaint -- names
written where symbols belong -- and it costs nothing, breaks no layout,
and cannot mangle a sentence.

    python tools/prosemath.py            # quiz banks
    python tools/prosemath.py --report   # show what would change

It runs over the quiz question banks, which are JavaScript string
literals dropped into the page with innerHTML, so <sup> and <sub> are
available and land as real typography.
"""
from __future__ import print_function

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)

GREEK = {
    'alpha': u'α', 'beta': u'β', 'gamma': u'γ',
    'delta': u'δ', 'epsilon': u'ε', 'eta': u'η',
    'theta': u'θ', 'lambda': u'λ', 'mu': u'μ',
    'pi': u'π', 'rho': u'ρ', 'sigma': u'σ',
    'tau': u'τ', 'phi': u'φ', 'omega': u'ω',
    'Delta': u'Δ', 'Gamma': u'Γ', 'Omega': u'Ω',
    'Phi': u'Φ', 'Sigma': u'Σ', 'Theta': u'Θ',
    'Lambda': u'Λ', 'Pi': u'Π',
}


def protect(t):
    """hide the things that must not be touched, so nothing else can"""
    keep = []

    def stash(m):
        keep.append(m.group(0))
        return '\x00%d\x00' % (len(keep) - 1)

    # already-set maths, any markup, and HTML entities
    t = re.sub(r'<[^>]+>', stash, t)
    t = re.sub(r'&[a-zA-Z#0-9]+;', stash, t)
    # backticks mark code, and in C++ `->` is the arrow operator, not an
    # arrow. Nothing inside them is notation to be prettified.
    t = re.sub(r'`[^`]*`', stash, t)
    return t, keep


def restore(t, keep):
    # a stashed span can contain another stash, so unwind until it stops
    for _ in range(8):
        out = re.sub(r'\x00(\d+)\x00',
                     lambda m: keep[int(m.group(1))], t)
        if out == t:
            return out
        t = out
    return t


def superscript(t):
    """x^2, z^-1, 10^(-3), 2^b  ->  a real superscript"""
    t = re.sub(r'(?<=[A-Za-z0-9\)\]])\^\(([^()]{1,12})\)',
               lambda m: '<sup>%s</sup>' % m.group(1).replace('-', u'−'),
               t)
    t = re.sub(r'(?<=[A-Za-z0-9\)\]])\^(-?[A-Za-z0-9]{1,4})\b',
               lambda m: '<sup>%s</sup>' % m.group(1).replace('-', u'−'),
               t)
    return t


def subscript(t):
    """T_b, F_s, x_(a)  ->  a real subscript"""
    t = re.sub(r'(?<=[A-Za-z])_\(([A-Za-z0-9]{1,6})\)',
               lambda m: '<sub>%s</sub>' % m.group(1), t)
    t = re.sub(r'(?<=[A-Za-z])_\{([A-Za-z0-9]{1,6})\}',
               lambda m: '<sub>%s</sub>' % m.group(1), t)
    t = re.sub(r'(?<=[A-Za-z])_([A-Za-z0-9])\b',
               lambda m: '<sub>%s</sub>' % m.group(1), t)
    return t


def symbols(t, code_heavy=False):
    t = re.sub(r'\blog\s*2\b|\blog2\b', u'log₂', t)
    t = re.sub(r'\blog\s*10\b|\blog10\b', u'log₁₀', t)
    t = re.sub(r'\bsqrt\s*\(([^()]{1,24})\)', u'√(\\1)', t)
    t = re.sub(r'\bsqrt\s+', u'√', t)
    for name, ch in GREEK.items():
        t = re.sub(r'(?<![A-Za-z])%s(?![A-Za-z])' % name, ch, t)
    # a convolution star between two signals is not an asterisk
    t = re.sub(r'(\w\([^()]{0,14}\))\s*\*\s*(?=\w\()', u'\\1 ∗ ', t)
    t = t.replace('<=', u'≤').replace('>=', u'≥')
    t = t.replace('!=', u'≠')
    if not code_heavy:
        t = re.sub(r'(?<![<-])->(?!>)', u'→', t)
    t = t.replace('+/-', u'±')
    t = re.sub(r'(?<![A-Za-z])inf(?:inity)?(?![A-Za-z])', u'∞', t)
    t = re.sub(r'(?<=\d)\s*[x]\s*(?=\d)', u' × ', t)
    t = re.sub(r'(?<=\d)\s*\*\s*(?=\d)', u' × ', t)
    return t


def fix(t, code_heavy=False):
    t, keep = protect(t)
    t = superscript(t)
    if not code_heavy:
        t = subscript(t)
    t = symbols(t, code_heavy)
    return restore(t, keep)


STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def bank_of(src):
    i = src.find('var BANK')
    if i < 0:
        return None, None
    j = src.find('\n];', i)
    if j < 0:
        return None, None
    return i, j


def run(report_only=False):
    changed = total = 0
    for name in ('dcn', 'dcomm', 'dsp', 'dip', 'oops'):
        path = os.path.join(APP, 'quiz', '%s.html' % name)
        if not os.path.exists(path):
            continue
        src = io.open(path, encoding='utf-8', errors='replace').read()
        i, j = bank_of(src)
        if i is None:
            print('  !! no question bank in quiz/%s.html' % name)
            continue
        bank = src[i:j]
        hits = [0]

        def one(m):
            body = m.group(1)
            out = fix(body, code_heavy=(name == 'oops'))
            if out != body:
                hits[0] += 1
                if report_only and hits[0] <= 3:
                    print('    %s\n      -> %s' % (body[:96], out[:110]))
            return '"%s"' % out

        new = STRING.sub(one, bank)
        total += hits[0]
        print('quiz/%s.html  %d strings reset' % (name, hits[0]))
        if hits[0] and not report_only:
            io.open(path, 'w', encoding='utf-8').write(
                src[:i] + new + src[j:])
            changed += 1
    print('\n%d strings across %d pages' % (total, changed))
    return 0


if __name__ == '__main__':
    sys.exit(run('--report' in sys.argv))
