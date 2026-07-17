"""
Font scoring v2: rasterize glyphs with FreeType at high resolution and
measure from the actual bitmaps. Works with TrueType and CFF outlines alike.

Metrics:
  1. x-height ratio  (x / H heights)                    optimum 0.72  w20
  2. stroke contrast ('o' side wall / top wall)          optimum 2.5   w20
  3. stem weight     ('n' stem width / em)               optimum 0.085 w15
  4. width economy   (avg lowercase advance / em)        optimum 0.50  w15
  5. counter open    ('o' inner width / outer width)     optimum 0.60  w15
  6. descender depth ('p' depth below baseline / em)     optimum 0.25  w15
"""
import glob
import math

import freetype
import numpy as np

SIZE = 512  # render at 512 px em for precision


def render(face, char):
    face.load_char(char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
    bmp = face.glyph.bitmap
    if bmp.rows == 0:
        return None, None, None
    raw = np.frombuffer(bytes(bmp.buffer), dtype=np.uint8).reshape(bmp.rows, bmp.pitch)
    bits = np.unpackbits(raw, axis=1)[:, :bmp.width].astype(bool)
    top = face.glyph.bitmap_top
    adv = face.glyph.advance.x / 64.0
    return bits, top, adv


def row_runs(row):
    """Return list of (start, end) runs of True in a boolean row."""
    runs = []
    in_run = False
    for i, v in enumerate(row):
        if v and not in_run:
            s = i
            in_run = True
        elif not v and in_run:
            runs.append((s, i))
            in_run = False
    if in_run:
        runs.append((s, len(row)))
    return runs


def col_runs(col):
    return row_runs(col)


def measure(path):
    face = freetype.Face(path)
    face.set_pixel_sizes(0, SIZE)
    m = {}

    # heights
    img_x, top_x, _ = render(face, "x")
    img_H, top_H, _ = render(face, "H")
    if img_x is None or img_H is None:
        return None
    xh = top_x
    ch = top_H
    m["xheight_ratio"] = xh / ch if ch else None

    # 'o' analysis
    img_o, top_o, _ = render(face, "o")
    if img_o is not None:
        h, w = img_o.shape
        mid = h // 2
        runs = row_runs(img_o[mid])
        if len(runs) == 2:
            thick = ((runs[0][1] - runs[0][0]) + (runs[1][1] - runs[1][0])) / 2
            inner = runs[1][0] - runs[0][1]
            outer = runs[1][1] - runs[0][0]
            m["counter"] = inner / outer if outer else None
            # thin stroke: vertical column through center
            cx = (runs[0][1] + runs[1][0]) // 2
            vruns = col_runs(img_o[:, cx])
            if len(vruns) == 2:
                thin = ((vruns[0][1] - vruns[0][0]) + (vruns[1][1] - vruns[1][0])) / 2
                m["contrast"] = thick / thin if thin else None
            else:
                m["contrast"] = None
        else:
            m["counter"] = None
            m["contrast"] = None

    # 'n' stem
    img_n, top_n, _ = render(face, "n")
    if img_n is not None:
        h, w = img_n.shape
        scan_y = int(h * 0.6)  # below arch join
        runs = row_runs(img_n[scan_y])
        if runs:
            m["stem"] = (runs[0][1] - runs[0][0]) / SIZE
        else:
            m["stem"] = None

    # width economy
    advs = []
    for c in "abcdefghijklmnopqrstuvwxyz":
        face.load_char(c)
        advs.append(face.glyph.advance.x / 64.0)
    m["width"] = (sum(advs) / len(advs)) / SIZE if advs else None

    # descender from 'p'
    img_p, top_p, _ = render(face, "p")
    if img_p is not None:
        below = img_p.shape[0] - top_p
        m["descender"] = below / SIZE
    else:
        m["descender"] = None

    return m


OPTIMA = {
    "xheight_ratio": (0.72, 0.06, 20),
    "contrast":      (2.5,  1.0,  20),
    "stem":          (0.085, 0.02, 15),
    "width":         (0.50, 0.05, 15),
    "counter":       (0.60, 0.08, 15),
    "descender":     (0.25, 0.05, 15),
}


def score(metrics):
    total = 0.0
    tw = 0
    detail = {}
    for key, (opt, sigma, weight) in OPTIMA.items():
        v = metrics.get(key)
        if v is None:
            detail[key] = None
            continue
        s = math.exp(-((v - opt) ** 2) / (2 * sigma ** 2))
        detail[key] = s * 100
        total += s * weight
        tw += weight
    return (total / tw * 100) if tw else 0, detail


if __name__ == "__main__":
    results = []
    for path in sorted(glob.glob("fonts/*.ttf")):
        name = path.split("/")[-1].replace(".ttf", "")
        try:
            metrics = measure(path)
            if metrics is None:
                print(f"{name}: could not render")
                continue
            total, detail = score(metrics)
            results.append((name, total, metrics, detail))
        except Exception as e:
            print(f"{name}: ERROR {e}")

    results.sort(key=lambda r: -r[1])

    print()
    hdr = f"{'Font':<20} {'SCORE':>6} | {'x-ht':>6} {'contr':>6} {'stem':>6} {'width':>6} {'countr':>6} {'desc':>6}"
    print(hdr)
    print("-" * len(hdr))
    for name, total, mx, detail in results:
        def fmt(v, prec=3):
            return f"{v:.{prec}f}" if v is not None else "  n/a"
        print(f"{name:<20} {total:>6.1f} | {fmt(mx['xheight_ratio'])} {fmt(mx['contrast'],2)} {fmt(mx['stem'])} {fmt(mx['width'])} {fmt(mx['counter'])} {fmt(mx['descender'])}")

    print()
    print("Per-metric scores (0-100), weighted: x-ht 20, contrast 20, stem 15, width 15, counter 15, descender 15")
    hdr2 = f"{'Font':<20} | {'x-ht':>6} {'contr':>6} {'stem':>6} {'width':>6} {'countr':>6} {'desc':>6}"
    print(hdr2)
    print("-" * len(hdr2))
    for name, total, mx, detail in results:
        def fmts(k):
            v = detail.get(k)
            return f"{v:>6.0f}" if v is not None else "   n/a"
        print(f"{name:<20} | {fmts('xheight_ratio')} {fmts('contrast')} {fmts('stem')} {fmts('width')} {fmts('counter')} {fmts('descender')}")
