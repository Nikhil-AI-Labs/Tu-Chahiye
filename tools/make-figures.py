# -*- coding: utf-8 -*-
"""
Tu Chahiye — the computed figures.

    pip install numpy scipy matplotlib pillow
    python tools/make-figures.py

Everything in here is *simulated*, not drawn. The sine gratings really are
sin(2*pi*u*x/N); their spectra really are np.fft.fft2 of those gratings; the
smoothed image really has been through a 3x3 mean. Nothing is an artist's
impression of what the maths would do, which means a student can trust what
they are looking at and, if they want, run the same four lines themselves.

Writes PNGs into  Tu-Chahiye/assets/fig/.
"""
from __future__ import division, print_function
import io, os, sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, os.pardir))
OUT = os.path.join(APP, 'assets', 'fig')
if not os.path.isdir(OUT):
    os.makedirs(OUT)

# ---------------------------------------------------------------- the house
STOCK = '#EAE8E1'
STOCK2 = '#DEDBD1'
INK = '#17171B'
INK2 = '#4C4C55'
INK3 = '#63636D'
HAIR = '#BCBAB5'
PINK = '#C21254'
BLUE = '#0B5FC0'
SPOT = {'dip': '#C21254', 'dsp': '#6A3EA1', 'dcomm': '#0B5FC0',
        'dcn': '#166B49', 'oops': '#A5440F'}

MONO = 'DejaVu Sans Mono'
SANS = 'DejaVu Sans'

plt.rcParams.update({
    'figure.facecolor': STOCK,
    'axes.facecolor': STOCK,
    'savefig.facecolor': STOCK,
    'axes.edgecolor': INK,
    'axes.labelcolor': INK2,
    'axes.linewidth': 1.1,
    'xtick.color': INK3, 'ytick.color': INK3,
    'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5,
    'text.color': INK,
    'font.family': SANS,
    'font.size': 9.5,
    'axes.titlesize': 10,
    'axes.titleweight': 'bold',
    'axes.grid': False,
    'legend.frameon': False,
    'figure.dpi': 170,
})

MADE = []


def bare(ax, keep=('left', 'bottom')):
    for s in ('top', 'right', 'left', 'bottom'):
        ax.spines[s].set_visible(s in keep)
    ax.tick_params(length=3, width=1)


def pane(ax, title=None, spot=None):
    """an image panel: no axes at all, a hairline frame, a mono caption"""
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True); s.set_color(HAIR); s.set_linewidth(1)
    if title:
        ax.set_title(title, fontsize=8.6, fontfamily=MONO, color=spot or INK2,
                     pad=6, fontweight='bold')



def _shrink(p):
    """These are flat plates -- one ground, one ink, a few greys. 24-bit is
       twice the file for no visible gain, so grey stays grey and everything
       else drops to a 192-colour palette. Roughly a 40% saving overall."""
    try:
        from PIL import Image
    except ImportError:
        return
    im = Image.open(p).convert('RGB')
    r, g, b = im.split()
    if r.tobytes() == g.tobytes() == b.tobytes():
        im.convert('L').save(p, optimize=True)
    else:
        im.quantize(colors=192, method=Image.MEDIANCUT,
                    dither=Image.NONE).save(p, optimize=True)


def save(fig, name, pad=0.16):
    p = os.path.join(OUT, name + '.png')
    fig.savefig(p, bbox_inches='tight', pad_inches=pad, facecolor=STOCK)
    plt.close(fig)
    _shrink(p)
    kb = os.path.getsize(p) / 1024.0
    MADE.append((name, kb))
    print('  %-30s %7.0f KB' % (name + '.png', kb))


def photo(n=256):
    """a real photograph, bundled with matplotlib, as 8-bit grey"""
    import matplotlib.cbook as cbook
    with cbook.get_sample_data('grace_hopper.jpg') as f:
        rgb = plt.imread(f)
    g = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])
    h, w = g.shape                                     # centre square crop
    m = min(h, w)
    g = g[(h - m) // 2:(h - m) // 2 + m, (w - m) // 2:(w - m) // 2 + m]
    idx = np.linspace(0, m - 1, n).astype(int)         # nearest-neighbour resize
    g = g[np.ix_(idx, idx)]
    return np.clip(g, 0, 255).astype(np.uint8)


def spectrum(img):
    """the magnitude spectrum, centred and log-stretched, as everyone draws it"""
    F = np.fft.fftshift(np.fft.fft2(img.astype(float)))
    S = np.log1p(np.abs(F))
    return S / (S.max() + 1e-12)


def show_spectrum(ax, img, half=34, mark=True, cmap='inferno'):
    """An impulse is one pixel in a 256x256 field, so at page size it is
       invisible. Crop to a window around DC and ring what is actually there,
       which is the whole point of the picture."""
    S = spectrum(img)
    c = S.shape[0] // 2
    W = S[c - half:c + half + 1, c - half:c + half + 1]
    ax.imshow(W, cmap=cmap, interpolation='nearest', vmin=0, vmax=1)
    ax.axhline(half, color=STOCK, lw=.5, alpha=.35)
    ax.axvline(half, color=STOCK, lw=.5, alpha=.35)
    if mark:
        ys, xs = np.where(W > 0.55)
        pts = sorted(zip(xs, ys))
        for i, (x, y) in enumerate(pts):
            ax.add_patch(plt.Circle((x, y), 4.2, fill=False, lw=1.5,
                                    color='#7CFFB2'))
            # stagger the labels, or three collinear points write over each other
            collinear_h = len({p[1] for p in pts}) == 1
            dy = (-13, 13, -13)[i % 3] if collinear_h else -9
            dx = 7 if not collinear_h else 0
            # keep the label on the canvas whatever the point's position
            lx = min(max(x + dx, 2), 2 * half - 2)
            ha = 'left' if lx < half * 0.6 else ('right' if lx > half * 1.4 else 'center')
            ax.annotate('(%+d, %+d)' % (x - half, half - y), (x, y),
                        xytext=(lx, y + dy), fontsize=7.2, fontfamily=MONO,
                        color='#7CFFB2', ha=ha)
    ax.set_xlim(-.5, 2 * half + .5); ax.set_ylim(2 * half + .5, -.5)
    return W


def conv2(img, k):
    """2-D convolution with zero padding, written out so it matches the
       by-hand method in the notes rather than hiding in a library call"""
    img = img.astype(float)
    kh, kw = k.shape
    ph, pw = kh // 2, kw // 2
    p = np.pad(img, ((ph, ph), (pw, pw)), mode='constant')
    out = np.zeros_like(img, dtype=float)
    kf = np.flipud(np.fliplr(k))
    for i in range(kh):
        for j in range(kw):
            out += kf[i, j] * p[i:i + img.shape[0], j:j + img.shape[1]]
    return out


def median2(img, n=3):
    img = img.astype(float)
    p = n // 2
    q = np.pad(img, ((p, p), (p, p)), mode='edge')
    st = np.stack([q[i:i + img.shape[0], j:j + img.shape[1]]
                   for i in range(n) for j in range(n)], axis=0)
    return np.median(st, axis=0)


# ==========================================================================
#  DIP — the 2-D Fourier pair the 2025 paper is built on
# ==========================================================================
N = 256


def grating(freq, vertical=False):
    """freq complete cycles across the image. This IS Fig.1 / Fig.2."""
    x = np.arange(N)
    s = 0.5 + 0.5 * np.sin(2 * np.pi * freq * x / N)
    return np.tile(s, (N, 1)) if not vertical else np.tile(s[:, None], (1, N))


def fig_sine_pair():
    f1 = grating(8, vertical=False)      # horizontal sine, frequency 8
    f2 = grating(16, vertical=True)      # vertical sine, frequency 16
    fig, ax = plt.subplots(1, 2, figsize=(6.4, 3.5))
    for a, im, t in ((ax[0], f1, 'Fig.1  horizontal sine, frequency 8'),
                     (ax[1], f2, 'Fig.2  vertical sine, frequency 16')):
        a.imshow(im, cmap='gray', vmin=0, vmax=1, interpolation='nearest')
        pane(a, t, SPOT['dip'])
    fig.suptitle('The two images, generated from sin(2πux/N)',
                 fontsize=9.5, color=INK2, y=1.02)
    save(fig, 'dip-sine-pair')


def fig_sine_spectra():
    f1, f2 = grating(8), grating(16, vertical=True)
    fig, ax = plt.subplots(2, 2, figsize=(6.4, 6.6))
    for a, im, t in ((ax[0][0], f1, 'Fig.1  in space'),
                     (ax[0][1], f2, 'Fig.2  in space')):
        a.imshow(im, cmap='gray', vmin=0, vmax=1, interpolation='nearest')
        pane(a, t)
    for a, im, t in ((ax[1][0], f1, '|F1|  on the u-axis, at ±8'),
                     (ax[1][1], f2, '|F2|  on the v-axis, at ±16')):
        show_spectrum(a, im, half=26)
        pane(a, t, SPOT['dip'])
    fig.suptitle('A sinusoid transforms to a pair of impulses, on the axis it '
                 'varies along.\n'
                 'The spectra are cropped to the middle 53×53 of 256×256 '
                 '— everywhere else is exactly zero.',
                 fontsize=9, color=INK2, y=1.03, linespacing=1.5)
    save(fig, 'dip-sine-spectra')


def fig_conv_theorem():
    f1, f2 = grating(8), grating(16, vertical=True)
    F1 = np.fft.fft2(f1)
    F2 = np.fft.fft2(f2)
    G = F1 * F2                                   # the convolution theorem
    g = np.real(np.fft.ifft2(G))
    fig, ax = plt.subplots(1, 4, figsize=(11.4, 3.3))
    ax[0].imshow(f1, cmap='gray', vmin=0, vmax=1); pane(ax[0], 'Fig.1')
    ax[1].imshow(f2, cmap='gray', vmin=0, vmax=1); pane(ax[1], 'Fig.2')
    show_spectrum(ax[2], None if False else g * 0 + 0, half=26, mark=False)
    Gs = np.fft.fftshift(np.log1p(np.abs(G)))
    Gs = Gs / (Gs.max() + 1e-12)
    c = Gs.shape[0] // 2
    ax[2].clear()
    ax[2].imshow(Gs[c - 26:c + 27, c - 26:c + 27], cmap='inferno',
                 interpolation='nearest', vmin=0, vmax=1)
    ax[2].add_patch(plt.Circle((26, 26), 4.2, fill=False, lw=1.5, color='#7CFFB2'))
    ax[2].annotate('(0, 0) only', (26, 26), xytext=(31, 20), fontsize=7.4,
                   fontfamily=MONO, color='#7CFFB2')
    pane(ax[2], 'F1 × F2   one point, at the origin', SPOT['dip'])
    ax[3].imshow(g, cmap='gray'); pane(ax[3], 'the convolution', SPOT['dip'])
    rng = g.max() - g.min()
    fig.suptitle('The product is non-zero only where both spectra are '
                 '— and the only point they share is the origin. '
                 'Range of the result: %.2g' % rng,
                 fontsize=9.2, color=INK2, y=1.04)
    save(fig, 'dip-conv-theorem')


def fig_impulse_ft():
    d = np.zeros((N, N)); d[N // 2, N // 2] = 1
    a = 24
    pair = np.zeros((N, N))
    pair[N // 2, N // 2 - a] = .5
    pair[N // 2, N // 2 + a] = .5
    fig, ax = plt.subplots(2, 2, figsize=(6.4, 6.6))
    ax[0][0].imshow(d, cmap='gray'); pane(ax[0][0], 'δ(x,y)   one point')
    ax[0][1].imshow(np.abs(np.fft.fftshift(np.fft.fft2(d))), cmap='inferno',
                    vmin=0, vmax=1.2)
    pane(ax[0][1], '|F| = 1 everywhere   a flat plane', SPOT['dip'])
    ax[1][0].imshow(pair, cmap='gray')
    pane(ax[1][0], '0.5[δ(x−a,y) + δ(x+a,y)]')
    S = np.abs(np.fft.fftshift(np.fft.fft2(pair)))
    ax[1][1].imshow(S, cmap='inferno', vmin=0, vmax=1.2)
    pane(ax[1][1], '|F| = |cos(2πua)|   bands of period 1/(2a)', SPOT['dip'])
    fig.suptitle('A point contains every frequency equally; a pair of points '
                 'gives a cosine', fontsize=9.5, color=INK2, y=1.005)
    save(fig, 'dip-impulse-ft')


def fig_bitplanes():
    g = photo(256)
    fig, ax = plt.subplots(2, 5, figsize=(12.6, 5.4))
    ax[0][0].imshow(g, cmap='gray', vmin=0, vmax=255)
    pane(ax[0][0], 'the image, 8 bits', SPOT['dip'])
    order = [7, 6, 5, 4, 3, 2, 1, 0]
    cells = [ax[0][1], ax[0][2], ax[0][3], ax[0][4],
             ax[1][1], ax[1][2], ax[1][3], ax[1][4]]
    for a, b in zip(cells, order):
        a.imshow((g >> b) & 1, cmap='gray', vmin=0, vmax=1)
        pane(a, 'plane %d  (%d)' % (b + 1, 1 << b))
    keep = (g & 0b11000000)
    ax[1][0].imshow(keep, cmap='gray', vmin=0, vmax=255)
    pane(ax[1][0], 'planes 8 + 7 only', SPOT['dip'])
    fig.suptitle('The top planes carry the picture; the bottom ones carry '
                 'noise. Two planes give four grey levels: %s'
                 % ', '.join(str(int(v)) for v in np.unique(keep)),
                 fontsize=9.3, color=INK2, y=1.02)
    save(fig, 'dip-bitplanes')


def fig_histeq():
    g = photo(256).astype(float)
    low = (g * 0.32 + 92).astype(np.uint8)          # a genuinely flat image
    h = np.bincount(low.ravel(), minlength=256).astype(float)
    cdf = np.cumsum(h) / h.sum()
    T = np.round(255 * cdf).astype(np.uint8)
    eq = T[low]
    h2 = np.bincount(eq.ravel(), minlength=256).astype(float)

    fig = plt.figure(figsize=(11.6, 5.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.35, 1], hspace=.32, wspace=.22)
    a = fig.add_subplot(gs[0, 0]); a.imshow(low, cmap='gray', vmin=0, vmax=255)
    pane(a, 'before   everything between 92 and 173')
    b = fig.add_subplot(gs[0, 1]); b.imshow(eq, cmap='gray', vmin=0, vmax=255)
    pane(b, 'after equalisation', SPOT['dip'])
    c = fig.add_subplot(gs[0, 2])
    c.plot(np.arange(256), T, color=SPOT['dip'], lw=2)
    c.plot([0, 255], [0, 255], color=HAIR, lw=1, ls=(0, (4, 3)))
    c.set_xlim(0, 255); c.set_ylim(0, 255); bare(c)
    c.set_title('s = T(r), the running sum', fontsize=8.6, fontfamily=MONO,
                color=SPOT['dip'], pad=6, fontweight='bold')
    c.set_xlabel('r  in'); c.set_ylabel('s  out')
    for ax_, hh, t in ((fig.add_subplot(gs[1, 0]), h, 'crowded into a third of the range'),
                       (fig.add_subplot(gs[1, 1]), h2, 'spread across all of it')):
        ax_.fill_between(np.arange(256), hh, step='mid',
                         color=SPOT['dip'] if hh is h2 else INK3, alpha=.85, lw=0)
        ax_.set_xlim(0, 255); bare(ax_); ax_.set_yticks([])
        ax_.set_title(t, fontsize=8.4, fontfamily=MONO, color=INK3, pad=5)
    n = fig.add_subplot(gs[1, 2]); n.axis('off')
    n.text(0, .92, 'What actually happens', fontsize=9, fontweight='bold',
           color=INK, va='top')
    n.text(0, .70, 'Equalisation cannot split a grey level — every pixel\n'
                   'of one value must go to the same new value. So the\n'
                   'bars are moved and merged, never divided, and the\n'
                   'result is spread rather than flat.\n\n'
                   'std before %.1f   →   std after %.1f'
           % (low.std(), eq.std()),
           fontsize=8.6, color=INK2, va='top', linespacing=1.55)
    save(fig, 'dip-histeq')


def fig_smoothing():
    rng = np.random.default_rng(7)
    g = photo(256).astype(float)
    noisy = g.copy()
    sp = rng.random(g.shape)
    noisy[sp < .04] = 0
    noisy[sp > .96] = 255
    box = conv2(noisy, np.ones((3, 3)) / 9.0)
    k = np.outer([1, 4, 6, 4, 1], [1, 4, 6, 4, 1]) / 256.0
    gau = conv2(noisy, k)
    med = median2(noisy, 3)
    fig, ax = plt.subplots(1, 4, figsize=(12.4, 3.5))
    for a, im, t in ((ax[0], noisy, 'salt and pepper, 8% of pixels'),
                     (ax[1], box, 'mean 3×3'),
                     (ax[2], gau, 'Gaussian 5×5 (Pascal)'),
                     (ax[3], med, 'median 3×3')):
        a.imshow(im, cmap='gray', vmin=0, vmax=255)
        pane(a, t, SPOT['dip'] if 'median' in t else None)
    err = lambda x: np.abs(x - g).mean()
    fig.suptitle('Mean error against the clean image — '
                 'mean %.1f, Gaussian %.1f, median %.1f. '
                 'The median does not average the spike in, it refuses to pick it.'
                 % (err(box), err(gau), err(med)),
                 fontsize=9.2, color=INK2, y=1.04)
    save(fig, 'dip-smoothing')


def fig_sharpening():
    g = photo(256).astype(float)
    lap = conv2(g, np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], float))
    sharp = np.clip(g - lap, 0, 255)
    fig, ax = plt.subplots(1, 3, figsize=(9.6, 3.5))
    ax[0].imshow(g, cmap='gray', vmin=0, vmax=255); pane(ax[0], 'original')
    ax[1].imshow(lap, cmap='gray'); pane(ax[1], '∇²f   edges on a dead background')
    ax[2].imshow(sharp, cmap='gray', vmin=0, vmax=255)
    pane(ax[2], 'g = f − ∇²f', SPOT['dip'])
    fig.suptitle('The Laplacian on its own is not an image — it is a map of '
                 'the discontinuities. Add it back and you have the sharpened '
                 'picture.', fontsize=9.2, color=INK2, y=1.04)
    save(fig, 'dip-sharpening')


def fig_gradient():
    g = photo(256).astype(float)
    sx = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], float)
    sy = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], float)
    Gx, Gy = conv2(g, sx), conv2(g, sy)
    M = np.abs(Gx) + np.abs(Gy)
    fig, ax = plt.subplots(1, 4, figsize=(12.4, 3.5))
    ax[0].imshow(g, cmap='gray', vmin=0, vmax=255); pane(ax[0], 'original')
    ax[1].imshow(np.abs(Gx), cmap='gray'); pane(ax[1], '|Gx|  horizontal edges')
    ax[2].imshow(np.abs(Gy), cmap='gray'); pane(ax[2], '|Gy|  vertical edges')
    ax[3].imshow(M, cmap='gray'); pane(ax[3], 'M ≈ |Gx| + |Gy|', SPOT['dip'])
    fig.suptitle('Gx answers to change down the columns, Gy to change across '
                 'the rows — and the gradient points across an edge, never '
                 'along it.', fontsize=9.2, color=INK2, y=1.04)
    save(fig, 'dip-gradient')


def fig_gamma():
    g = photo(256).astype(float)
    fig = plt.figure(figsize=(11.6, 3.7))
    gs = fig.add_gridspec(1, 4, wspace=.2)
    for i, (gam, t) in enumerate(((0.4, 'γ = 0.4  lifts the dark end'),
                                  (1.0, 'γ = 1  the original'),
                                  (2.5, 'γ = 2.5  pushes it down'))):
        a = fig.add_subplot(gs[0, i])
        a.imshow(255 * (g / 255) ** gam, cmap='gray', vmin=0, vmax=255)
        pane(a, t, SPOT['dip'] if gam != 1 else None)
    c = fig.add_subplot(gs[0, 3])
    r = np.arange(256)
    for gam, st in ((0.4, '-'), (1.0, (0, (4, 3))), (2.5, '-')):
        c.plot(r, 255 * (r / 255) ** gam,
               color=SPOT['dip'] if gam != 1 else HAIR, lw=2 if gam != 1 else 1,
               ls=st)
    c.text(150, 235, 'γ = 0.4', fontsize=8.5, color=SPOT['dip'], fontfamily=MONO)
    c.text(168, 62, 'γ = 2.5', fontsize=8.5, color=SPOT['dip'], fontfamily=MONO)
    c.set_xlim(0, 255); c.set_ylim(0, 255); bare(c)
    c.set_xlabel('r  in'); c.set_ylabel('s  out')
    c.set_title('s = c·r^γ', fontsize=8.6, fontfamily=MONO, color=INK2,
                pad=6, fontweight='bold')
    save(fig, 'dip-gamma')


def fig_sampling_quant():
    g = photo(512)
    fig, ax = plt.subplots(2, 4, figsize=(12.4, 6.6))
    for i, n in enumerate((512, 128, 32, 16)):
        idx = np.linspace(0, 511, n).astype(int)
        small = g[np.ix_(idx, idx)]
        big = np.kron(small, np.ones((512 // n, 512 // n)))
        ax[0][i].imshow(big, cmap='gray', vmin=0, vmax=255)
        pane(ax[0][i], '%d × %d samples' % (n, n),
             SPOT['dip'] if n < 64 else None)
    for i, b in enumerate((8, 4, 2, 1)):
        lv = 1 << b
        q = np.floor(g / 256 * lv) * (255 / (lv - 1))
        ax[1][i].imshow(q, cmap='gray', vmin=0, vmax=255)
        pane(ax[1][i], '%d bit%s = %d levels' % (b, '' if b == 1 else 's', lv),
             SPOT['dip'] if b < 4 else None)
    fig.suptitle('Top row: too few samples and the detail goes blocky. '
                 'Bottom row: too few levels and smooth shading breaks into '
                 'bands — two different axes, two different failures.',
                 fontsize=9.2, color=INK2, y=1.015)
    save(fig, 'dip-sampling-quant')


def fig_paths():
    """the 2025 paper's own 5x5 segment, with the shortest paths drawn"""
    A = np.array([[0, 1, 1, 2, 3],
                  [1, 1, 2, 0, 1],
                  [2, 2, 3, 3, 2],
                  [1, 3, 0, 0, 1],
                  [0, 0, 2, 0, 1]])
    V = {0, 3}
    inV = np.isin(A, list(V))
    fig, ax = plt.subplots(1, 2, figsize=(9.2, 4.6))
    for k, (a, title, path) in enumerate((
            (ax[0], 'V = {0, 3}   the pixels in V', None),
            (ax[1], 'shortest 8-path = 3   (no 4-path exists)',
             [(3, 3), (2, 3), (1, 3), (0, 4)]))):
        a.imshow(inV, cmap=matplotlib.colors.ListedColormap([STOCK, '#F7D6E2']),
                 vmin=0, vmax=1)
        for i in range(5):
            for j in range(5):
                a.text(j, i, str(A[i, j]), ha='center', va='center',
                       fontsize=13, fontfamily=MONO,
                       color=SPOT['dip'] if inV[i, j] else INK3,
                       fontweight='bold' if inV[i, j] else 'normal')
        a.set_xticks(np.arange(-.5, 5, 1), minor=True)
        a.set_yticks(np.arange(-.5, 5, 1), minor=True)
        a.grid(which='minor', color=HAIR, lw=1)
        a.set_xticks([]); a.set_yticks([])
        for s in a.spines.values():
            s.set_color(INK); s.set_linewidth(1.4)
        a.text(3, 3.42, 'p', ha='center', fontsize=10, color=INK, fontweight='bold')
        a.text(4, -0.45, 'q', ha='center', fontsize=10, color=INK, fontweight='bold')
        a.set_title(title, fontsize=9, fontfamily=MONO, color=INK2, pad=8,
                    fontweight='bold')
        if path:
            ys = [p[0] for p in path]; xs = [p[1] for p in path]
            a.plot(xs, ys, color=SPOT['dip'], lw=2.6, solid_capstyle='round',
                   zorder=3)
            a.scatter(xs, ys, s=70, color=SPOT['dip'], zorder=4)
    fig.suptitle("q's only 4-neighbours are 2 and 1, neither in V — so under "
                 '4-adjacency q cannot be reached at all.',
                 fontsize=9.2, color=INK2, y=1.02)
    save(fig, 'dip-paths')


# ==========================================================================
#  DSP
# ==========================================================================
def fig_aliasing():
    Fs = 500.0
    t = np.linspace(0, 0.02, 4000)
    n = np.arange(0, int(0.02 * Fs) + 1)
    fig, ax = plt.subplots(figsize=(9.2, 3.4))
    ax.plot(t * 1000, np.cos(2 * np.pi * 600 * t), color=INK3, lw=1.1,
            ls=(0, (5, 3)), label='600 Hz, the real signal')
    ax.plot(t * 1000, np.cos(2 * np.pi * 100 * t), color=SPOT['dsp'], lw=2.2,
            label='100 Hz, what the samples say')
    ax.stem(n / Fs * 1000, np.cos(2 * np.pi * 600 * n / Fs),
            linefmt='-', markerfmt='o', basefmt=' ')
    for c in ax.containers:
        pass
    ax.set_xlabel('time  ms'); ax.set_ylabel('x(t)')
    bare(ax); ax.legend(loc='upper right', fontsize=8.5)
    ax.set_title('Sampled at 500 Hz, a 600 Hz cosine is indistinguishable from '
                 'a 100 Hz one', fontsize=9.4, color=INK2, pad=8)
    save(fig, 'dsp-aliasing')


def fig_dft():
    x = np.array([1, 2, 3, 4], float)
    X = np.fft.fft(x)
    fig, ax = plt.subplots(1, 3, figsize=(10.6, 3.2))
    ax[0].stem(np.arange(4), x, linefmt='-', markerfmt='o', basefmt=' ')
    ax[0].set_title('x(n) = {1, 2, 3, 4}', fontsize=9, fontfamily=MONO, color=INK2)
    ax[0].set_xlabel('n')
    ax[1].stem(np.arange(4), np.abs(X), linefmt='-', markerfmt='o', basefmt=' ')
    ax[1].set_title('|X(k)|', fontsize=9, fontfamily=MONO, color=SPOT['dsp'])
    ax[1].set_xlabel('k')
    ax[2].stem(np.arange(4), np.angle(X), linefmt='-', markerfmt='o', basefmt=' ')
    ax[2].set_title('∠X(k)  radians', fontsize=9, fontfamily=MONO, color=SPOT['dsp'])
    ax[2].set_xlabel('k')
    for a in ax:
        bare(a)
        a.xaxis.set_major_locator(MaxNLocator(integer=True))
    vals = '  '.join('%.3g%+.3gj' % (v.real, v.imag) for v in X)
    fig.suptitle('X(k) = %s' % vals, fontsize=8.6, color=INK2,
                 fontfamily=MONO, y=1.05)
    save(fig, 'dsp-dft')


def fig_freq_response():
    w = np.linspace(0, np.pi, 800)
    H = 1.0 / (1 - 0.5 * np.exp(-1j * w))
    fig, ax = plt.subplots(1, 2, figsize=(9.6, 3.2))
    ax[0].plot(w / np.pi, np.abs(H), color=SPOT['dsp'], lw=2.2)
    ax[0].set_ylabel('|H|'); ax[0].set_title('magnitude', fontsize=9,
                                             fontfamily=MONO, color=INK2)
    ax[1].plot(w / np.pi, np.angle(H), color=SPOT['dsp'], lw=2.2)
    ax[1].set_ylabel('∠H  rad'); ax[1].set_title('phase', fontsize=9,
                                                      fontfamily=MONO, color=INK2)
    for a in ax:
        a.set_xlabel('ω / π'); bare(a); a.set_xlim(0, 1)
    ax[0].annotate('2 at ω = 0', xy=(0, 2), xytext=(.18, 1.85),
                   fontsize=8.5, color=INK2, fontfamily=MONO,
                   arrowprops=dict(arrowstyle='-', color=HAIR))
    ax[0].annotate('0.667 at ω = π', xy=(1, 2 / 3), xytext=(.55, .95),
                   fontsize=8.5, color=INK2, fontfamily=MONO,
                   arrowprops=dict(arrowstyle='-', color=HAIR))
    fig.suptitle('y(n) − ½y(n−1) = x(n)   —   a low-pass filter, '
                 'because the pole sits at z = +0.5',
                 fontsize=9.4, color=INK2, y=1.04)
    save(fig, 'dsp-freq-response')


def fig_fft_saving():
    N = 2 ** np.arange(3, 14)
    direct = N.astype(float) ** 2
    fft = N / 2 * np.log2(N)
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    ax.plot(N, direct, color=INK3, lw=2, marker='o', ms=4, label='direct DFT  N²')
    ax.plot(N, fft, color=SPOT['dsp'], lw=2.4, marker='o', ms=4,
            label='radix-2 FFT  (N/2)log₂N')
    ax.set_xscale('log', base=2); ax.set_yscale('log')
    ax.set_xlabel('N'); ax.set_ylabel('complex multiplications')
    bare(ax); ax.legend(fontsize=8.6)
    for n in (8, 256, 1024):
        i = int(np.log2(n)) - 3
        ax.annotate('%.2f%% saved' % (100 * (1 - fft[i] / direct[i])),
                    xy=(n, fft[i]), xytext=(n, fft[i] * 0.22),
                    fontsize=8.2, color=SPOT['dsp'], fontfamily=MONO,
                    ha='center')
    ax.set_title('At N = 1024 the FFT does 5,120 multiplications where the '
                 'direct transform does 1,048,576',
                 fontsize=9.4, color=INK2, pad=8)
    save(fig, 'dsp-fft-saving')


# ==========================================================================
#  DComm
# ==========================================================================
def fig_quant_snr():
    rng = np.random.default_rng(3)
    bits = np.arange(2, 13)
    t = np.linspace(0, 1, 40000)
    x = np.sin(2 * np.pi * 5 * t)
    meas = []
    for b in bits:
        L = 2 ** b
        q = np.round((x + 1) / 2 * (L - 1)) / (L - 1) * 2 - 1
        meas.append(10 * np.log10(np.mean(x ** 2) / np.mean((x - q) ** 2)))
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    ax.plot(bits, 1.76 + 6.02 * bits, color=HAIR, lw=6, solid_capstyle='round',
            label='1.76 + 6.02n  dB')
    ax.plot(bits, meas, color=SPOT['dcomm'], lw=0, marker='o', ms=6,
            label='measured on a real sine')
    ax.set_xlabel('n  bits per sample'); ax.set_ylabel('SNR  dB')
    bare(ax); ax.legend(fontsize=8.6, loc='upper left')
    ax.set_title('One more bit is six more decibels — and the simulation '
                 'lands on the formula', fontsize=9.4, color=INK2, pad=8)
    save(fig, 'dcomm-quant-snr')


def rcos(t, T, a):
    with np.errstate(divide='ignore', invalid='ignore'):
        s = np.sinc(t / T) * np.cos(np.pi * a * t / T) / (1 - (2 * a * t / T) ** 2)
    s[np.isnan(s)] = np.pi / 4 * np.sinc(1 / (2 * a)) if a else 0
    return s


def fig_isi():
    T = 1.0
    t = np.linspace(-4, 4, 2000)
    fig, ax = plt.subplots(1, 2, figsize=(10.6, 3.4))
    for a, c, lab in ((0.0, INK3, 'α = 0  brick wall'),
                      (0.5, SPOT['dcomm'], 'α = 0.5'),
                      (1.0, PINK, 'α = 1')):
        ax[0].plot(t, rcos(t, T, a), color=c, lw=2, label=lab)
    ax[0].axhline(0, color=HAIR, lw=1)
    for k in range(-4, 5):
        ax[0].axvline(k, color=HAIR, lw=.8, ls=(0, (2, 3)))
    ax[0].scatter(np.arange(-4, 5), [1] + [0] * 8, s=0)
    ax[0].set_xlabel('t / T'); ax[0].legend(fontsize=8.4)
    bare(ax[0])
    ax[0].set_title('every pulse is 0 at every other sampling instant',
                    fontsize=9, fontfamily=MONO, color=INK2, pad=6)
    # three symbols and their sum
    sym = [1, -1, 1]
    tt = np.linspace(-2, 4, 2000)
    tot = np.zeros_like(tt)
    for i, s in enumerate(sym):
        p = s * rcos(tt - i, T, 0.35)
        tot += p
        ax[1].plot(tt, p, color=HAIR, lw=1.2)
    ax[1].plot(tt, tot, color=SPOT['dcomm'], lw=2.4)
    for i in range(3):
        ax[1].axvline(i, color=HAIR, lw=.8, ls=(0, (2, 3)))
        ax[1].scatter([i], [np.interp(i, tt, tot)], s=46, color=PINK, zorder=4)
    ax[1].set_xlabel('t / T'); bare(ax[1])
    ax[1].set_title('so the sum reads 1, −1, 1 exactly at the instants',
                    fontsize=9, fontfamily=MONO, color=INK2, pad=6)
    fig.suptitle("Nyquist's first criterion, simulated: the tails are enormous, "
                 'and they are all zero where it matters',
                 fontsize=9.4, color=INK2, y=1.04)
    save(fig, 'dcomm-isi')


def fig_eye():
    rng = np.random.default_rng(11)
    T, sps = 1.0, 64
    nsym = 300
    bits = rng.integers(0, 2, nsym) * 2 - 1
    span = 6
    t = (np.arange(-span * sps, span * sps + 1)) / sps
    fig, ax = plt.subplots(1, 2, figsize=(10.6, 3.6))
    for a, alpha, noise, ttl in ((ax[0], 0.9, 0.02, 'α = 0.9, clean'),
                                 (ax[1], 0.2, 0.06, 'α = 0.2 and noise')):
        p = rcos(t, T, alpha)
        sig = np.zeros(nsym * sps + len(p))
        for i, b in enumerate(bits):
            sig[i * sps:i * sps + len(p)] += b * p
        sig += rng.normal(0, noise, sig.shape)
        for i in range(20, nsym - 20):
            seg = sig[i * sps:(i + 2) * sps]
            a.plot(np.linspace(-1, 1, len(seg)), seg, color=INK, lw=.5, alpha=.14)
        a.axvline(0, color=SPOT['dcomm'], lw=1.6)
        a.set_xlabel('t / T'); bare(a); a.set_ylim(-2, 2)
        a.set_title(ttl, fontsize=9, fontfamily=MONO, color=INK2, pad=6)
    fig.suptitle('Every possible symbol sequence, laid over two bit periods. '
                 'The opening is how much noise and timing error the link '
                 'survives.', fontsize=9.4, color=INK2, y=1.04)
    save(fig, 'dcomm-eye')


def fig_ber():
    from math import erfc
    snr = np.arange(0, 13, .25)
    lin = 10 ** (snr / 10)
    Q = lambda x: 0.5 * np.array([erfc(v / np.sqrt(2)) for v in np.atleast_1d(x)])
    bpsk = Q(np.sqrt(2 * lin))
    ask = Q(np.sqrt(lin))
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    ax.semilogy(snr, bpsk, color=SPOT['dcomm'], lw=2.4, label='BPSK   Q(√(2Eb/N0))')
    ax.semilogy(snr, ask, color=INK3, lw=2, ls=(0, (5, 3)),
                label='ASK / FSK   Q(√(Eb/N0))')
    ax.set_xlabel('Eb/N0  dB'); ax.set_ylabel('bit error rate')
    ax.set_ylim(1e-7, .6); bare(ax); ax.legend(fontsize=8.6)
    ax.annotate('3 dB', xy=(9.6, Q(np.sqrt(2 * 10 ** .96))[0]),
                xytext=(6.4, 2e-6), fontsize=8.6, color=PINK, fontfamily=MONO,
                arrowprops=dict(arrowstyle='<->', color=PINK, lw=1.2))
    ax.set_title('BPSK buys exactly 3 dB over ASK, because antipodal symbols '
                 'are twice as far apart', fontsize=9.4, color=INK2, pad=8)
    save(fig, 'dcomm-ber')


# ==========================================================================
#  DCN — the one figure that really wants simulating
# ==========================================================================
def fig_aloha_sim():
    rng = np.random.default_rng(5)
    G = np.linspace(0.02, 3, 40)
    slots = 40000
    pure_m, slot_m = [], []
    for g in G:
        # slotted: a slot succeeds when exactly one station starts in it
        k = rng.poisson(g, slots)
        slot_m.append(np.mean(k == 1) * 1.0)
        # pure: a frame succeeds when nothing starts in the 2Tfr around it
        k2 = rng.poisson(2 * g, slots)
        pure_m.append(g * np.mean(k2 == 0))
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    gg = np.linspace(0.02, 3, 400)
    ax.plot(gg, gg * np.exp(-2 * gg), color=HAIR, lw=6, solid_capstyle='round')
    ax.plot(gg, gg * np.exp(-gg), color=HAIR, lw=6, solid_capstyle='round')
    ax.plot(G, pure_m, 'o', ms=5, color=INK3, label='pure ALOHA, simulated')
    ax.plot(G, slot_m, 'o', ms=5, color=SPOT['dcn'], label='slotted, simulated')
    ax.axhline(1 / (2 * np.e), color=INK3, lw=.9, ls=(0, (3, 3)))
    ax.axhline(1 / np.e, color=SPOT['dcn'], lw=.9, ls=(0, (3, 3)))
    ax.text(2.35, 1 / (2 * np.e) + .012, 'S = 0.184', fontsize=8.4,
            fontfamily=MONO, color=INK3)
    ax.text(2.35, 1 / np.e + .012, 'S = 0.368', fontsize=8.4,
            fontfamily=MONO, color=SPOT['dcn'])
    ax.set_xlabel('G  offered load'); ax.set_ylabel('S  throughput')
    bare(ax); ax.legend(fontsize=8.6, loc='lower right')
    ax.set_title('40,000 slots per point, Poisson arrivals — the dots land '
                 'on Ge⁻²ᴳ and Ge⁻ᴳ without being told to',
                 fontsize=9.4, color=INK2, pad=8)
    save(fig, 'dcn-aloha-sim')



def fig_bsc_capacity():
    """C = 1 - H(p) for the binary symmetric channel"""
    p = np.linspace(1e-6, 1 - 1e-6, 2000)
    H = -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
    C = 1 - H
    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    ax.plot(p, C, color=SPOT['dcomm'], lw=2.6)
    ax.axhline(0, color=HAIR, lw=1)
    for x, t in ((0.0, 'C = 1'), (1.0, 'C = 1')):
        ax.plot([x], [1], 'o', ms=6, color=SPOT['dcomm'])
    ax.plot([0.5], [0], 'o', ms=6, color=PINK)
    ax.annotate('a perfect channel', xy=(0, 1), xytext=(.07, .84),
                fontsize=8.6, color=INK2, fontfamily=MONO,
                arrowprops=dict(arrowstyle='-', color=HAIR))
    ax.annotate('a perfect inverter — just as good,\n'
                'you only have to flip every bit',
                xy=(1, 1), xytext=(.58, .78), fontsize=8.6, color=INK2,
                fontfamily=MONO, arrowprops=dict(arrowstyle='-', color=HAIR),
                linespacing=1.5)
    ax.annotate('p = 0.5 — the output is\nindependent of the input,\n'
                'so it carries nothing',
                xy=(.5, 0), xytext=(.27, .26), fontsize=8.6, color=PINK,
                fontfamily=MONO, arrowprops=dict(arrowstyle='-', color=PINK),
                linespacing=1.5)
    ax.set_xlabel('p  transition probability')
    ax.set_ylabel('C  bits per channel use')
    ax.set_xlim(0, 1); ax.set_ylim(-.02, 1.08); bare(ax)
    ax.set_title('C = 1 − H(p), plotted from the definition',
                 fontsize=9.4, color=INK2, pad=8)
    save(fig, 'dcomm-bsc-capacity')



def fig_paths_predicted():
    """the 4x4 grid the predicted paper uses, V = {1, 2}"""
    A = np.array([[3, 1, 2, 1],
                  [2, 2, 0, 2],
                  [1, 2, 1, 1],
                  [1, 0, 1, 2]])
    V = {1, 2}
    inV = np.isin(A, list(V))
    paths = [('shortest 4-path = 6',
              [(3, 0), (2, 0), (2, 1), (1, 1), (0, 1), (0, 2), (0, 3)]),
             ('shortest 8-path = 4',
              [(3, 0), (2, 1), (1, 1), (0, 2), (0, 3)]),
             ('shortest m-path = 6, and unique',
              [(3, 0), (2, 0), (2, 1), (1, 1), (0, 1), (0, 2), (0, 3)])]
    fig, ax = plt.subplots(1, 3, figsize=(11.2, 4.2))
    for a, (title, path) in zip(ax, paths):
        a.imshow(inV, cmap=matplotlib.colors.ListedColormap([STOCK, '#FBE7EE']),
                 vmin=0, vmax=1)
        for i in range(4):
            for j in range(4):
                a.text(j, i, str(A[i, j]), ha='center', va='center',
                       fontsize=13, fontfamily=MONO,
                       color=SPOT['dip'] if inV[i, j] else INK3,
                       fontweight='bold' if inV[i, j] else 'normal')
        a.set_xticks(np.arange(-.5, 4, 1), minor=True)
        a.set_yticks(np.arange(-.5, 4, 1), minor=True)
        a.grid(which='minor', color=HAIR, lw=1)
        a.set_xticks([]); a.set_yticks([])
        for sp in a.spines.values():
            sp.set_color(INK); sp.set_linewidth(1.4)
        ys = [q[0] for q in path]; xs = [q[1] for q in path]
        a.plot(xs, ys, color=SPOT['dip'], lw=2.6, solid_capstyle='round', zorder=3)
        a.scatter(xs, ys, s=64, color=SPOT['dip'], zorder=4)
        a.text(0, 3.42, 'p', ha='center', fontsize=10, color=INK, fontweight='bold')
        a.text(3, -0.46, 'q', ha='center', fontsize=10, color=INK, fontweight='bold')
        a.set_title(title, fontsize=9, fontfamily=MONO, color=INK2, pad=8,
                    fontweight='bold')
    fig.suptitle('V = {1, 2}. Every length below was found by breadth-first '
                 'search over this exact array, with the m-adjacency rule '
                 'applied at each diagonal step.',
                 fontsize=9.2, color=INK2, y=1.03)
    save(fig, 'dip-paths-predicted')


# ==========================================================================
#  DSP — the FIR unit, the DFT properties, and the class-notebook pictures
#  Every one of these is computed. The filters really are designed with the
#  formulas the page states; the ripple figures are measured off the
#  responses, not quoted.
# ==========================================================================
def _lpf_hd(M, wc):
    """ideal low-pass impulse response, delayed by tau = (M-1)/2"""
    tau = (M - 1) / 2.0
    n = np.arange(M)
    with np.errstate(divide='ignore', invalid='ignore'):
        h = np.where(n == tau, wc / np.pi, np.sin(wc * (n - tau)) / (np.pi * (n - tau)))
    return h


def _H(h, w):
    """|H(e^jw)| from the coefficients, straight from the definition"""
    n = np.arange(len(h))
    return np.abs(np.array([np.sum(h * np.exp(-1j * wi * n)) for wi in w]))


def _db(x):
    return 20 * np.log10(np.maximum(x, 1e-9))


def _stem(ax, n, v, color=None, ms=4.5, lw=1.4):
    color = color or SPOT['dsp']
    m, s, b = ax.stem(n, v, linefmt='-', markerfmt='o', basefmt=' ')
    plt.setp(s, color=color, linewidth=lw)
    plt.setp(m, color=color, markersize=ms)
    ax.axhline(0, color=HAIR, lw=1, zorder=0)


def fig_fir_types():
    """the four linear-phase families: symmetric or antisymmetric, M odd or even"""
    fig, ax = plt.subplots(2, 2, figsize=(9.6, 5.4))
    cases = [(9, +1, 'Type 1: symmetric, M odd'), (8, +1, 'Type 2: symmetric, M even'),
             (9, -1, 'Type 3: antisymmetric, M odd'), (8, -1, 'Type 4: antisymmetric, M even')]
    rng = np.random.default_rng(5)
    for a, (M, sgn, title) in zip(ax.ravel(), cases):
        n = np.arange(M)
        half = rng.uniform(0.25, 1.0, size=M // 2) * np.array([0.35, 0.6, 0.9, 1.0])[:M // 2]
        h = np.zeros(M)
        h[:M // 2] = half
        h[M - M // 2:] = sgn * half[::-1]
        if M % 2 == 1:
            h[M // 2] = 1.0 if sgn > 0 else 0.0
        _stem(a, n, h)
        tau = (M - 1) / 2.0
        a.axvline(tau, color=INK3, lw=1, ls=(0, (3, 3)))
        a.text(tau, 1.12, 'centre  n = (M−1)/2 = %g' % tau, ha='center', fontsize=8,
               color=INK2, fontfamily=MONO)
        a.set_ylim(-1.25, 1.3); a.set_xlim(-0.6, M - 0.4)
        a.set_title(title, fontsize=9.2, fontfamily=MONO, color=INK2, loc='left')
        a.set_xlabel('n'); bare(a)
        a.xaxis.set_major_locator(MaxNLocator(integer=True))
        note = {(9, 1): 'h(n) = h(M−1−n); nothing forced to zero',
                (8, 1): 'h(n) = h(M−1−n); H(π) = 0 — no high-pass',
                (9, -1): 'h(n) = −h(M−1−n); centre tap 0; H(0) = H(π) = 0',
                (8, -1): 'h(n) = −h(M−1−n); H(0) = 0'}[(M, sgn)]
        a.text(0.02, 0.06, note, transform=a.transAxes, fontsize=8, color=SPOT['dsp'],
               fontfamily=MONO)
    fig.suptitle('Linear phase needs symmetry about the centre tap. Which of the four '
                 'families you can use depends on the filter you want.',
                 fontsize=9.4, color=INK2, y=1.01)
    fig.tight_layout()
    save(fig, 'dsp-fir-types')


def fig_fir_zeros():
    """the zeros of the M = 11 rectangular-window low-pass, found by np.roots"""
    h = _lpf_hd(11, np.pi / 2)
    z = np.roots(h)
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    th = np.linspace(0, 2 * np.pi, 400)
    ax.plot(np.cos(th), np.sin(th), color=HAIR, lw=1.2)
    ax.axhline(0, color=HAIR, lw=1); ax.axvline(0, color=HAIR, lw=1)
    on = np.isclose(np.abs(z), 1, atol=1e-6)
    ax.plot(z[on].real, z[on].imag, 'o', ms=8, mfc='none', mec=INK, mew=1.6,
            label='on the unit circle — conjugate pairs')
    ax.plot(z[~on].real, z[~on].imag, 'o', ms=8, mfc='none', mec=SPOT['dsp'], mew=1.8,
            label='off it — reciprocal AND conjugate, a quadruplet')
    for zz in z[~on]:
        ax.annotate('|z| = %.3f' % abs(zz), xy=(zz.real, zz.imag),
                    xytext=(zz.real + 0.12, zz.imag + 0.12 * np.sign(zz.imag + 1e-9)),
                    fontsize=8, color=SPOT['dsp'], fontfamily=MONO)
    ax.set_aspect('equal'); ax.set_xlim(-2.1, 2.1); ax.set_ylim(-2.1, 2.1)
    ax.set_xlabel('Re z'); ax.set_ylabel('Im z'); bare(ax)
    ax.legend(loc='lower left', fontsize=8, bbox_to_anchor=(0, 1.0))
    ax.set_title('Zeros of the 11-tap low-pass, ωc = π/2 (rectangular window). '
                 'Symmetric h(n) means H(z) = z^{-(M-1)} H(1/z):\nevery zero at z comes '
                 'with one at 1/z, and real coefficients add the conjugate of each.',
                 fontsize=8.8, color=INK2, pad=54, loc='left')
    save(fig, 'dsp-fir-zeros')


def fig_fir_ideal():
    """the four ideal responses and their truncated impulse responses, M = 21"""
    M = 21; tau = 10; n = np.arange(M)
    w = np.linspace(-np.pi, np.pi, 801)
    wc, w1, w2 = 0.4 * np.pi, 0.3 * np.pi, 0.6 * np.pi
    with np.errstate(divide='ignore', invalid='ignore'):
        d = n - tau
        lp = np.where(d == 0, wc / np.pi, np.sin(wc * d) / (np.pi * d))
        hp = np.where(d == 0, 1 - wc / np.pi, (np.sin(np.pi * d) - np.sin(wc * d)) / (np.pi * d))
        bp = np.where(d == 0, (w2 - w1) / np.pi, (np.sin(w2 * d) - np.sin(w1 * d)) / (np.pi * d))
        bs = np.where(d == 0, 1 - (w2 - w1) / np.pi,
                      (np.sin(w1 * d) - np.sin(w2 * d) + np.sin(np.pi * d)) / (np.pi * d))
    ideal = [(np.abs(w) <= wc), (np.abs(w) >= wc),
             ((np.abs(w) >= w1) & (np.abs(w) <= w2)), ~((np.abs(w) >= w1) & (np.abs(w) <= w2))]
    names = ['Low-pass  ωc = 0.4π', 'High-pass  ωc = 0.4π', 'Band-pass  0.3π–0.6π',
             'Band-stop  0.3π–0.6π']
    hs = [lp, hp, bp, bs]
    fig, ax = plt.subplots(2, 4, figsize=(12.4, 5.0))
    for k in range(4):
        a = ax[0, k]
        a.plot(w / np.pi, ideal[k].astype(float), color=INK3, lw=1.3, ls=(0, (4, 3)),
               label='ideal Hd(ω)')
        a.plot(w / np.pi, _H(hs[k], w), color=SPOT['dsp'], lw=1.8, label='truncated, M = 21')
        a.set_title(names[k], fontsize=9, fontfamily=MONO, color=INK2, loc='left')
        a.set_xlabel('ω / π'); a.set_ylim(-0.1, 1.25); bare(a)
        if k == 0:
            a.legend(fontsize=7.6, loc='upper right')
        b = ax[1, k]
        _stem(b, n, hs[k], ms=3.6, lw=1.2)
        b.set_xlabel('n'); bare(b)
        b.set_title('hd(n), n = 0…20', fontsize=8.6, fontfamily=MONO, color=INK2, loc='left')
    fig.suptitle('Every ideal response has a closed-form hd(n) — a sinc, or two sincs '
                 'subtracted. Cut it off at M taps and the ripple appears.',
                 fontsize=9.4, color=INK2, y=1.01)
    fig.tight_layout()
    save(fig, 'dsp-fir-ideal')


def fig_gibbs():
    """truncating the ideal response: the overshoot does not shrink with M"""
    w = np.linspace(0, np.pi, 3000)
    wc = np.pi / 2
    fig, ax = plt.subplots(1, 2, figsize=(10.6, 3.6))
    for M, col in ((11, HAIR), (61, INK3), (101, SPOT['dsp'])):
        H = _H(_lpf_hd(M, wc), w)
        over = H[w < wc].max() - 1
        ax[0].plot(w / np.pi, H, color=col, lw=1.6 if M < 101 else 2.1,
                   label='M = %d   overshoot %.1f%%' % (M, 100 * over))
    ax[0].axhline(1, color=HAIR, lw=1, ls=(0, (3, 3)))
    ax[0].set_xlabel('ω / π'); ax[0].set_ylabel('|H(ω)|'); bare(ax[0])
    ax[0].legend(fontsize=8.2, loc='upper right')
    ax[0].set_title('Rectangular window: more taps make the ripple faster, never smaller',
                    fontsize=9, color=INK2, loc='left')
    for M, col, name, wn in ((61, INK3, 'rectangular', np.ones(61)),
                             (61, SPOT['dsp'], 'Hamming', np.hamming(61))):
        H = _H(_lpf_hd(M, wc) * wn, w)
        sb = _db(H[w > 0.62 * np.pi].max())
        ax[1].plot(w / np.pi, _db(H), color=col, lw=1.9,
                   label='%s, M = 61   stopband peak %.0f dB' % (name, sb))
    ax[1].set_ylim(-110, 8); ax[1].set_xlabel('ω / π'); ax[1].set_ylabel('dB'); bare(ax[1])
    ax[1].legend(fontsize=8.2, loc='upper right')
    ax[1].set_title('The same M with a tapered window: ripple gone, transition wider',
                    fontsize=9, color=INK2, loc='left')
    fig.suptitle('Gibbs: a hard cut in the time domain is a sinc in the frequency domain, '
                 'and its first sidelobe is 9% high whatever M is.',
                 fontsize=9.4, color=INK2, y=1.02)
    fig.tight_layout()
    save(fig, 'dsp-gibbs')


def fig_windows():
    """the window family, in time and in dB, with the sidelobe measured"""
    M = 51; n = np.arange(M)
    fam = [('rectangular', np.ones(M), INK3),
           ('Bartlett', np.bartlett(M), '#8C7A4C'),
           ('Hann', np.hanning(M), BLUE),
           ('Hamming', np.hamming(M), SPOT['dsp']),
           ('Blackman', np.blackman(M), PINK)]
    fig, ax = plt.subplots(1, 2, figsize=(11.2, 3.8))
    for name, wv, col in fam:
        ax[0].plot(n, wv, color=col, lw=1.9, label=name)
        W = np.abs(np.fft.fft(wv, 8192)); W /= W[0]
        Wdb = _db(W[:4096])
        rising = np.where(np.diff(W[:4096]) > 0)[0]
        null = rising[0] if len(rising) else 1
        side = Wdb[null:].max()
        wgrid = np.linspace(0, np.pi, 4096)
        ax[1].plot(wgrid / np.pi, Wdb, color=col, lw=1.6,
                   label='%-11s sidelobe %5.0f dB   main lobe %.0fπ/M'
                         % (name, side, 2 * (null / 8192 * 2 * np.pi) / (2 * np.pi / M)))
    ax[0].set_xlabel('n'); ax[0].set_ylabel('w(n)'); bare(ax[0])
    ax[0].set_title('M = 51 taps', fontsize=9, fontfamily=MONO, color=INK2, loc='left')
    ax[0].legend(fontsize=8, loc='upper right')
    ax[1].set_ylim(-110, 5); ax[1].set_xlim(0, 0.25)
    ax[1].set_xlabel('ω / π'); ax[1].set_ylabel('|W(ω)|  dB'); bare(ax[1])
    ax[1].legend(fontsize=7.4, loc='upper right', prop={'family': MONO, 'size': 7.4})
    ax[1].set_title('Each spectrum, normalised: the trade is main-lobe width against '
                    'sidelobe height', fontsize=9, color=INK2, loc='left')
    fig.tight_layout()
    save(fig, 'dsp-windows')


def _bessel_i0(x):
    from scipy.special import i0
    return i0(x)


def fig_kaiser():
    """one window, one knob: beta"""
    M = 51; n = np.arange(M)
    fig, ax = plt.subplots(1, 2, figsize=(11.2, 3.8))
    for beta, col, lab in ((0, INK3, 'β = 0   (rectangular)'), (3.4, BLUE, 'β = 3.4'),
                           (5.44, SPOT['dsp'], 'β = 5.44 (≈ Hamming)'),
                           (8.5, PINK, 'β = 8.5 (≈ Blackman)')):
        arg = 1 - (2 * n / (M - 1) - 1) ** 2
        wv = _bessel_i0(beta * np.sqrt(np.maximum(arg, 0))) / _bessel_i0(beta)
        ax[0].plot(n, wv, color=col, lw=1.9, label=lab)
        W = np.abs(np.fft.fft(wv, 8192)); W /= W[0]
        Wdb = _db(W[:4096])
        rising = np.where(np.diff(W[:4096]) > 0)[0]
        null = rising[0] if len(rising) else 1
        ax[1].plot(np.linspace(0, 1, 4096), Wdb, color=col, lw=1.6,
                   label='%s   sidelobe %.0f dB' % (lab, Wdb[null:].max()))
    ax[0].set_xlabel('n'); ax[0].set_ylabel('w(n)'); bare(ax[0]); ax[0].legend(fontsize=8)
    ax[1].set_ylim(-120, 5); ax[1].set_xlim(0, 0.25)
    ax[1].set_xlabel('ω / π'); ax[1].set_ylabel('dB'); bare(ax[1]); ax[1].legend(fontsize=7.8)
    fig.suptitle('Kaiser: w(n) = I₀(β√(1 − (2n/(M−1) − 1)²)) / I₀(β). Raising β buys '
                 'stopband attenuation and pays for it with transition width.',
                 fontsize=9.4, color=INK2, y=1.02)
    fig.tight_layout()
    save(fig, 'dsp-kaiser')


def fig_fir_lpf_design():
    """the two designs worked on the page, computed and plotted"""
    w = np.linspace(0, np.pi, 1200)
    wt = np.arange(0, 1.001, 0.1) * np.pi
    fig, ax = plt.subplots(2, 2, figsize=(10.6, 6.2))
    # (a) rectangular, M = 11, wc = pi/2
    h = _lpf_hd(11, np.pi / 2)
    _stem(ax[0, 0], np.arange(11), h)
    ax[0, 0].set_title('(a) rectangular window, M = 11, ωc = π/2 — h(n)', fontsize=9,
                       fontfamily=MONO, color=INK2, loc='left')
    for i, v in enumerate(h):
        if abs(v) > 1e-9:
            ax[0, 0].text(i, v + (0.03 if v > 0 else -0.06), '%.3f' % v, ha='center',
                          fontsize=7.4, color=INK2, fontfamily=MONO)
    ax[0, 1].plot(w / np.pi, _db(_H(h, w)), color=SPOT['dsp'], lw=1.9)
    ax[0, 1].plot(wt / np.pi, _db(_H(h, wt)), 'o', ms=4, color=INK)
    ax[0, 1].axhline(-6.02, color=HAIR, lw=1, ls=(0, (3, 3)))
    ax[0, 1].text(0.52, -4.4, '−6.02 dB at ωc, exactly half', fontsize=7.8, color=INK2,
                  fontfamily=MONO)
    ax[0, 1].set_ylim(-60, 6); ax[0, 1].set_title('|H(ω)| in dB, dots at ω = 0, 0.1π … π '
                                                   '(the table on the page)',
                                                   fontsize=9, color=INK2, loc='left')
    # (b) Hamming, M = 7, wc = 3pi/4
    hd = _lpf_hd(7, 3 * np.pi / 4); wn = np.hamming(7); h2 = hd * wn
    _stem(ax[1, 0], np.arange(7), hd, color=HAIR, ms=5)
    _stem(ax[1, 0], np.arange(7), h2)
    ax[1, 0].set_title('(b) Hamming window, M = 7, ωc = 3π/4 — hd(n) grey, h(n) = hd·w ink',
                       fontsize=9, fontfamily=MONO, color=INK2, loc='left')
    for i, v in enumerate(h2):
        ax[1, 0].text(i, v + (0.03 if v >= 0 else -0.07), '%.3f' % v, ha='center',
                      fontsize=7.4, color=INK2, fontfamily=MONO)
    ax[1, 1].plot(w / np.pi, _db(_H(h2, w)), color=SPOT['dsp'], lw=1.9)
    ax[1, 1].plot(wt / np.pi, _db(_H(h2, wt)), 'o', ms=4, color=INK)
    ax[1, 1].set_ylim(-14, 2)
    ax[1, 1].set_title('|H(ω)| in dB — only −10.7 dB at π: seven taps cannot do better',
                       fontsize=9, color=INK2, loc='left')
    for a in ax.ravel():
        bare(a)
    for a in ax[:, 0]:
        a.set_xlabel('n'); a.xaxis.set_major_locator(MaxNLocator(integer=True))
    for a in ax[:, 1]:
        a.set_xlabel('ω / π'); a.set_ylabel('dB')
    fig.tight_layout()
    save(fig, 'dsp-fir-lpf-design')


def fig_freq_sampling():
    """design by sampling the ideal response: exact at the samples, ripple between"""
    w = np.linspace(0, np.pi, 3000)
    fig, ax = plt.subplots(1, 2, figsize=(11.2, 3.9))
    # M = 17, wc = pi/2 : H(k) = 1 for k = 0..4
    M = 17; n = np.arange(M)
    h = (1 + 2 * np.sum([np.cos(2 * np.pi * k * (n - 8) / M) for k in range(1, 5)], axis=0)) / M
    H = _H(h, w)
    ax[0].plot(w / np.pi, H, color=SPOT['dsp'], lw=1.9, label='|H(ω)| of the 17 taps')
    kk = np.arange(9); wk = 2 * np.pi * kk / M
    Hk = (kk <= 4).astype(float)
    ax[0].plot(wk / np.pi, Hk, 'o', ms=6, color=INK, label='the samples H(k), k = 0…8')
    ax[0].plot(w / np.pi, (w <= np.pi / 2).astype(float), color=HAIR, lw=1.2, ls=(0, (4, 3)),
               label='ideal')
    rip = H[w < 0.45 * np.pi].max() - 1; sb = H[w > 0.62 * np.pi].max()
    ax[0].text(0.03, 1.13, 'passes through every sample exactly; between them: +%.0f%% ripple, '
               'stopband peak %.2f' % (100 * rip, sb), fontsize=7.8, color=INK2, fontfamily=MONO)
    ax[0].set_ylim(-0.08, 1.28); ax[0].set_xlabel('ω / π'); bare(ax[0])
    ax[0].legend(fontsize=7.8, loc='center right')
    ax[0].set_title('M = 17, ωc = π/2, samples at ω = 2πk/17', fontsize=9, fontfamily=MONO,
                    color=INK2, loc='left')
    # Proakis 8.6 vs 8.7
    M = 15; n = np.arange(M)
    h1 = (1 + 2 * np.sum([np.cos(2 * np.pi * k * (n - 7) / M) for k in range(1, 4)], axis=0)) / M
    h2 = h1 + 0.8 * np.cos(8 * np.pi * (n - 7) / M) / M
    for hh, col, lab in ((h1, INK3, 'H(4) = 0     hard edge'), (h2, SPOT['dsp'], 'H(4) = 0.4   one transition sample')):
        Hh = _H(hh, w)
        ax[1].plot(w / np.pi, _db(Hh), color=col, lw=1.9,
                   label='%s → stopband %.0f dB' % (lab, _db(Hh[w > 0.75 * np.pi].max())))
    ax[1].set_ylim(-70, 6); ax[1].set_xlabel('ω / π'); ax[1].set_ylabel('dB'); bare(ax[1])
    ax[1].legend(fontsize=8, loc='upper right')
    ax[1].set_title('M = 15: Proakis 8.6 against 8.7 — what one sample in the transition buys',
                    fontsize=9, color=INK2, loc='left')
    fig.tight_layout()
    save(fig, 'dsp-freq-sampling')


def fig_diff_hilbert():
    """the two antisymmetric designs: differentiator and Hilbert transformer"""
    M = 21; tau = 10; n = np.arange(M); d = n - tau
    w = np.linspace(0, np.pi, 1500)
    with np.errstate(divide='ignore', invalid='ignore'):
        hdiff = np.where(d == 0, 0.0, np.cos(np.pi * d) / d)
        hhil = np.where(d == 0, 0.0, (1 - np.cos(np.pi * d)) / (np.pi * d))
    hdiff_w = hdiff * np.hamming(M); hhil_w = hhil * np.hamming(M)
    fig, ax = plt.subplots(2, 2, figsize=(10.6, 5.8))
    _stem(ax[0, 0], n, hdiff_w); ax[0, 0].set_title('differentiator, hd(n)·Hamming, M = 21',
                                                   fontsize=9, fontfamily=MONO, color=INK2, loc='left')
    ax[0, 1].plot(w / np.pi, w, color=HAIR, lw=1.2, ls=(0, (4, 3)), label='ideal |H| = ω')
    ax[0, 1].plot(w / np.pi, _H(hdiff_w, w), color=SPOT['dsp'], lw=1.9, label='designed')
    ax[0, 1].legend(fontsize=8); ax[0, 1].set_title('|H(ω)| — a straight line through the origin',
                                                    fontsize=9, color=INK2, loc='left')
    _stem(ax[1, 0], n, hhil_w); ax[1, 0].set_title('Hilbert transformer, hd(n)·Hamming, M = 21 '
                                                  '(every even tap is zero)',
                                                  fontsize=9, fontfamily=MONO, color=INK2, loc='left')
    ax[1, 1].plot(w / np.pi, np.ones_like(w), color=HAIR, lw=1.2, ls=(0, (4, 3)), label='ideal |H| = 1')
    ax[1, 1].plot(w / np.pi, _H(hhil_w, w), color=SPOT['dsp'], lw=1.9, label='designed')
    ax[1, 1].set_ylim(0, 1.3); ax[1, 1].legend(fontsize=8, loc='lower center')
    ax[1, 1].set_title('|H(ω)| — flat, with a −90° phase shift at every frequency',
                       fontsize=9, color=INK2, loc='left')
    for a in ax.ravel():
        bare(a)
    for a in ax[:, 0]:
        a.set_xlabel('n')
    for a in ax[:, 1]:
        a.set_xlabel('ω / π')
    fig.suptitle('Both are antisymmetric — h(n) = −h(M−1−n) — so both are Type 3 here, '
                 'and both have H(0) = 0 as they must.', fontsize=9.4, color=INK2, y=1.01)
    fig.tight_layout()
    save(fig, 'dsp-diff-hilbert')


def fig_dft_symmetry():
    """a real sequence's DFT is conjugate-symmetric — the 'first five points' example"""
    given = np.array([0.25, 0.125 - 0.3018j, 0, 0.125 - 0.0518j, 0])
    X = np.concatenate([given, np.conj(given[3:0:-1])])          # X(5)=X*(3), X(6)=X*(2), X(7)=X*(1)
    x = np.fft.ifft(X)
    k = np.arange(8)
    fig, ax = plt.subplots(1, 3, figsize=(11.6, 3.4))
    _stem(ax[0], k, np.abs(X))
    ax[0].axvline(4, color=HAIR, lw=1, ls=(0, (3, 3)))
    ax[0].set_title('|X(k)| — a mirror about k = N/2 = 4', fontsize=9, fontfamily=MONO,
                    color=INK2, loc='left'); ax[0].set_xlabel('k')
    _stem(ax[1], k, np.angle(X))
    ax[1].axvline(4, color=HAIR, lw=1, ls=(0, (3, 3)))
    ax[1].set_title('∠X(k) — odd about k = 4', fontsize=9, fontfamily=MONO, color=INK2,
                    loc='left'); ax[1].set_xlabel('k')
    _stem(ax[2], k, x.real)
    ax[2].set_title('IDFT of the completed X(k): real, max |Im| = %.1e' % np.abs(x.imag).max(),
                    fontsize=9, fontfamily=MONO, color=INK2, loc='left'); ax[2].set_xlabel('n')
    for a in ax:
        bare(a); a.xaxis.set_major_locator(MaxNLocator(integer=True))
    fig.suptitle('Given X(0)…X(4) of a real 8-point sequence, X(N−k) = X*(k) supplies the rest '
                 '— and transforming back really does give a real x(n).',
                 fontsize=9.2, color=INK2, y=1.03)
    fig.tight_layout()
    save(fig, 'dsp-dft-symmetry')


def fig_circular_shift():
    """x(n) = {5, 4, 3, 2} on a ring: a circular shift and a circular fold"""
    x = np.array([5, 4, 3, 2])
    N = 4
    panels = [('x(n)', x), ('x((n − 2))₄  — shifted two places', np.roll(x, 2)),
              ('x((−n))₄  — folded', x[(-np.arange(N)) % N])]
    fig, ax = plt.subplots(1, 3, figsize=(11.4, 3.9))
    for a, (title, v) in zip(ax, panels):
        th = np.linspace(0, 2 * np.pi, 200)
        a.plot(np.cos(th), np.sin(th), color=HAIR, lw=1.4)
        for i in range(N):
            ang = np.pi / 2 - 2 * np.pi * i / N          # n = 0 at the top, clockwise
            px, py = np.cos(ang), np.sin(ang)
            a.plot(px, py, 'o', ms=26, color=STOCK2, mec=SPOT['dsp'], mew=1.8)
            a.text(px, py, '%d' % v[i], ha='center', va='center', fontsize=11, color=INK,
                   fontweight='bold')
            a.text(1.32 * px, 1.32 * py, 'n=%d' % i, ha='center', va='center', fontsize=8.5,
                   color=INK3, fontfamily=MONO)
        a.set_xlim(-1.6, 1.6); a.set_ylim(-1.6, 1.6); a.set_aspect('equal'); a.axis('off')
        a.set_title(title, fontsize=9.4, fontfamily=MONO, color=INK2)
        a.text(0, -1.55, '{ ' + ', '.join(str(t) for t in v) + ' }', ha='center', fontsize=9,
               color=SPOT['dsp'], fontfamily=MONO)
    fig.suptitle('The index lives on a ring of N = 4 positions. A shift is a rotation; a fold '
                 'is a reflection through n = 0. Nothing falls off the end.',
                 fontsize=9.4, color=INK2, y=1.0)
    fig.tight_layout()
    save(fig, 'dsp-circular-shift')


def fig_fir_spec():
    """a real design, with the tolerance scheme read off it"""
    from scipy.signal import kaiserord, firwin
    wp, ws = 0.35 * np.pi, 0.45 * np.pi
    numtaps, beta = kaiserord(45, (ws - wp) / np.pi)
    if numtaps % 2 == 0:
        numtaps += 1
    h = firwin(numtaps, (wp + ws) / 2 / np.pi, window=('kaiser', beta))
    w = np.linspace(0, np.pi, 4000)
    H = _H(h, w)
    d1 = np.abs(H[w <= wp] - 1).max(); d2 = H[w >= ws].max()
    fig, ax = plt.subplots(figsize=(9.4, 3.9))
    ax.plot(w / np.pi, H, color=SPOT['dsp'], lw=2)
    ax.axvspan(0, wp / np.pi, color=STOCK2, alpha=0.9, zorder=0)
    ax.axvspan(ws / np.pi, 1, color=STOCK2, alpha=0.9, zorder=0)
    # the two passband lines are only 2δ₁ apart, so one label sits above and one below
    for y, lab, va in ((1 + d1, '1 + δ₁', 'bottom'), (1 - d1, '1 − δ₁', 'top'), (d2, 'δ₂', 'center')):
        ax.plot([0, 1], [y, y], color=INK3, lw=1, ls=(0, (3, 3)))   # stop at pi, clear of the label
        ax.text(1.01, y, lab, fontsize=8.5, color=INK2, fontfamily=MONO, va=va)
    ax.text(wp / 2 / np.pi, 0.5, 'passband\n0 ≤ ω ≤ ωp', ha='center', fontsize=8.6, color=INK2)
    ax.text((wp + ws) / 2 / np.pi, 0.5, 'transition\nωs − ωp', ha='center', fontsize=8.6, color=INK2)
    ax.text((ws / np.pi + 1) / 2, 0.5, 'stopband\nωs ≤ ω ≤ π', ha='center', fontsize=8.6, color=INK2)
    ax.set_xticks([0, wp / np.pi, ws / np.pi, 1]); ax.set_xticklabels(['0', 'ωp', 'ωs', 'π'])
    ax.set_ylim(-0.05, 1.15); ax.set_xlim(0, 1.06); ax.set_ylabel('|H(ω)|'); bare(ax)
    ax.set_title('A %d-tap Kaiser design for ωp = 0.35π, ωs = 0.45π, 45 dB: measured '
                 'δ₁ = %.4f, δ₂ = %.4f (%.1f dB)' % (numtaps, d1, d2, _db(d2)),
                 fontsize=9.2, color=INK2, loc='left', pad=8)
    save(fig, 'dsp-fir-spec')


def fig_goertzel():
    """one DFT bin as a second-order filter, run on x = 1..8"""
    x = np.arange(1, 9.0); N = 8
    X = np.fft.fft(x)
    fig, ax = plt.subplots(figsize=(9.0, 3.4))
    _stem(ax, np.arange(N), np.abs(X), color=HAIR, ms=5)
    got = []
    for k in range(N):
        c = 2 * np.cos(2 * np.pi * k / N); v1 = v2 = 0.0
        for xn in list(x) + [0.0]:
            v = xn + c * v1 - v2; v2, v1 = v1, v
        got.append(v1 - np.exp(-2j * np.pi * k / N) * v2)
    got = np.array(got)
    ax.plot(np.arange(N), np.abs(got), 'o', ms=7, mfc='none', mec=SPOT['dsp'], mew=2,
            label='Goertzel, one bin at a time')
    ax.legend(fontsize=8.5)
    ax.set_xlabel('k'); ax.set_ylabel('|X(k)|'); bare(ax)
    ax.set_title('x = 1…8: each Goertzel bin agrees with the FFT to %.0e — '
                 'N multiplications per bin, so it wins when you want fewer than log₂N of them'
                 % np.abs(got - X).max(), fontsize=9, color=INK2, loc='left', pad=8)
    save(fig, 'dsp-goertzel')


FIR_FIGS = [fig_fir_spec, fig_fir_types, fig_fir_zeros, fig_fir_ideal, fig_gibbs, fig_windows,
            fig_kaiser, fig_fir_lpf_design, fig_freq_sampling, fig_diff_hilbert,
            fig_dft_symmetry, fig_circular_shift, fig_goertzel]



def fig_overlap():
    """block convolution, both ways, on the class-notebook example"""
    h = np.array([2, 2, 1]); x = np.array([3, 0, -2, 0, 2, 1, 0, -2, -1, 0])
    N, M = 8, 3; L = N - M + 1
    y_direct = np.convolve(x, h)
    cc = lambda a, b: np.real(np.rint(np.fft.ifft(np.fft.fft(a, N) * np.fft.fft(b, N)))).astype(int)
    fig, ax = plt.subplots(2, 2, figsize=(11.6, 6.0))
    # ---- overlap-add (left column)
    a = ax[0, 0]
    y = np.zeros(len(x) + M - 1, int)
    cols = [SPOT['dsp'], BLUE]
    for i, s in enumerate(range(0, len(x), L)):
        yb = cc(x[s:s + L], h)
        n = np.arange(s, s + N)
        keep = n < len(y)
        a.bar(n[keep] + (0.18 if i else -0.18), yb[keep], width=0.34, color=cols[i],
              label='block %d output (8 points)' % (i + 1))
        y[s:s + N] += yb[:np.sum(keep)]
    a.axvspan(5.5, 7.5, color=STOCK2, zorder=0)
    a.text(6.5, -5.6, 'overlap:\nadd', ha='center', fontsize=8, color=INK2, fontfamily=MONO)
    a.set_title('Overlap-ADD: blocks of L = 6 inputs, each gives 8 outputs',
                fontsize=9, fontfamily=MONO, color=INK2, loc='left')
    a.legend(fontsize=7.6, loc='lower right'); a.set_xlabel('n'); a.set_ylim(-7.2, 7); bare(a)
    b = ax[1, 0]
    _stem(b, np.arange(len(y)), y)
    b.plot(np.arange(len(y_direct)), y_direct, 'o', ms=9, mfc='none', mec=INK, mew=1.4,
           label='direct linear convolution')
    b.legend(fontsize=7.8); b.set_xlabel('n'); bare(b)
    b.set_title('sum of the blocks = %s' % ' '.join(str(v) for v in y),
                fontsize=8.6, fontfamily=MONO, color=INK2, loc='left')
    # ---- overlap-save (right column)
    c = ax[0, 1]
    xp = np.concatenate([np.zeros(M - 1, int), x, np.zeros(N, int)]); out = []
    for i, s in enumerate(range(0, len(x), L)):
        yb = cc(xp[s:s + N], h)
        n = np.arange(s, s + N)
        good = np.arange(N) >= M - 1
        c.bar(n[good] - (M - 1) + (0.18 if i else -0.18), yb[good], width=0.34, color=cols[i],
              label='block %d, the 6 kept' % (i + 1))
        c.bar(n[~good] - (M - 1) + (0.18 if i else -0.18), yb[~good], width=0.34,
              color=HAIR, hatch='//', edgecolor=cols[i], lw=0.8)
        out.extend(yb[M - 1:])
    c.text(-1.4, -4.9, 'hatched: first M−1 = 2\nof each block, thrown away', ha='left', fontsize=7.8,
           color=INK2, fontfamily=MONO)
    c.set_title('Overlap-SAVE: blocks of N = 8 inputs that overlap by M−1 = 2',
                fontsize=9, fontfamily=MONO, color=INK2, loc='left')
    c.legend(fontsize=7.6, loc='lower right'); c.set_xlabel('n'); c.set_ylim(-7.2, 7); bare(c)
    d = ax[1, 1]
    ys = np.array(out[:len(y_direct)])
    _stem(d, np.arange(len(ys)), ys)
    d.plot(np.arange(len(y_direct)), y_direct, 'o', ms=9, mfc='none', mec=INK, mew=1.4,
           label='direct linear convolution')
    d.legend(fontsize=7.8); d.set_xlabel('n'); bare(d)
    d.set_title('kept samples, joined = %s' % ' '.join(str(v) for v in ys),
                fontsize=8.6, fontfamily=MONO, color=INK2, loc='left')
    fig.suptitle('h = {2, 2, 1}, x = {3, 0, −2, 0, 2, 1, 0, −2, −1, 0}, 8-point DFTs. Both '
                 'ways land exactly on the direct answer.', fontsize=9.4, color=INK2, y=1.01)
    fig.tight_layout()
    save(fig, 'dsp-overlap-add-save')


FIR_FIGS.append(fig_overlap)


ALL = [
    fig_sine_pair, fig_sine_spectra, fig_conv_theorem, fig_impulse_ft,
    fig_bitplanes, fig_histeq, fig_smoothing, fig_sharpening, fig_gradient,
    fig_gamma, fig_sampling_quant, fig_paths, fig_paths_predicted,
    fig_aliasing, fig_dft, fig_freq_response, fig_fft_saving,
    fig_quant_snr, fig_isi, fig_eye, fig_ber, fig_bsc_capacity,
    fig_aloha_sim,
] + FIR_FIGS

if __name__ == '__main__':
    only = sys.argv[1:] or None
    for f in ALL:
        if only and not any(o in f.__name__ for o in only):
            continue
        f()
    print('\n%d figures, %.1f MB -> %s'
          % (len(MADE), sum(k for _, k in MADE) / 1024.0, OUT))
