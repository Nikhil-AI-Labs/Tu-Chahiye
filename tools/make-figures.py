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


ALL = [
    fig_sine_pair, fig_sine_spectra, fig_conv_theorem, fig_impulse_ft,
    fig_bitplanes, fig_histeq, fig_smoothing, fig_sharpening, fig_gradient,
    fig_gamma, fig_sampling_quant, fig_paths,
    fig_aliasing, fig_dft, fig_freq_response, fig_fft_saving,
    fig_quant_snr, fig_isi, fig_eye, fig_ber,
    fig_aloha_sim,
]

if __name__ == '__main__':
    only = sys.argv[1:] or None
    for f in ALL:
        if only and not any(o in f.__name__ for o in only):
            continue
        f()
    print('\n%d figures, %.1f MB -> %s'
          % (len(MADE), sum(k for _, k in MADE) / 1024.0, OUT))
