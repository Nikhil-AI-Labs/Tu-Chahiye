# -*- coding: utf-8 -*-
"""
Bring the page counts and file sizes on downloads.html back in line with
what is actually in pdf/.

The numbers are printed next to every download, and a PDF's length changes
whenever the pages it is built from change — typesetting the mathematics
moved most of them. Rather than regenerate the page and risk losing
anything that was added to it since, this edits the two numbers in place,
matching each entry by the file it links to.

    python tools/make-pdfs.py
    python tools/refresh-downloads.py
"""
from __future__ import print_function

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
PDF = os.path.join(APP, 'pdf')

try:
    import fitz
except ImportError:
    print('needs PyMuPDF:  pip install pymupdf')
    sys.exit(2)


def meta(path):
    d = fitz.open(path)
    n = d.page_count
    d.close()
    kb = int(round(os.path.getsize(path) / 1024.0))
    return n, kb


def size(kb):
    return ('%.1f MB' % (kb / 1024.0)) if kb >= 1024 else ('%d KB' % kb)


# <span>62 pages &middot; 1.5 MB &middot; A4 PDF</span> ... href="pdf/x.pdf"
ENTRY = re.compile(
    r'<span>(\d+)\s*pages?\s*&middot;\s*([\d.]+\s*[KM]B)\s*&middot;\s*A4 PDF'
    r'</span>(.*?)href="(?:\.\./)?pdf/([a-z0-9-]+\.pdf)"', re.S)


def main():
    page = os.path.join(APP, 'downloads.html')
    src = io.open(page, encoding='utf-8').read()
    changed = [0]
    missing = []

    def one(m):
        old_pages, old_size, middle, fname = m.groups()
        path = os.path.join(PDF, fname)
        if not os.path.exists(path):
            missing.append(fname)
            return m.group(0)
        n, kb = meta(path)
        new = size(kb)
        if str(n) != old_pages or new != old_size.replace(' ', ''):
            changed[0] += 1
            print('  %-24s %s pages, %s  ->  %d pages, %s'
                  % (fname, old_pages, old_size, n, new))
        return ('<span>%d pages &middot; %s &middot; A4 PDF</span>%shref="%s"'
                % (n, new, middle,
                   re.search(r'href="([^"]*)"',
                             m.group(0)[m.group(0).rfind('href='):]).group(1)))

    out = ENTRY.sub(one, src)
    if missing:
        print('  no such PDF: %s' % ', '.join(sorted(set(missing))))
    if changed[0]:
        io.open(page, 'w', encoding='utf-8').write(out)
    print('%d entries updated in downloads.html' % changed[0])
    return 0


if __name__ == '__main__':
    sys.exit(main())
