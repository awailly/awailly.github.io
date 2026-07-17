"""
Font warmth/smoothness/ease scoring based on measurable typographic metrics.

Metrics extracted from actual glyph outlines:
  1. x-height ratio  (x-height / cap-height)   optimum 0.72   weight 20
  2. stroke contrast (thick/thin of 'o')        optimum 2.5    weight 20
  3. stem weight     (n stem / UPM)             optimum 0.085  weight 15
  4. width economy   (avg advance / UPM)        optimum 0.50   weight 15
  5. counter open    ('o' inner/outer width)    optimum 0.60   weight 15
  6. descender depth (|descender| / UPM)        optimum 0.25   weight 15

Score per metric: gaussian falloff from optimum, sigma tuned per metric.
Total = weighted sum, scaled to 100.
"""
import glob
import math
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen


def glyph_bounds(font, glyph_name):
    gs = font.getGlyphSet()
    if glyph_name not in gs:
        return None
    pen = BoundsPen(gs)
    gs[glyph_name].draw(pen)
    return pen.bounds  # (xMin, yMin, xMax, yMax)


def scanline_stroke_widths(font, glyph_name, y):
    """Intersect glyph outline with horizontal line at height y.
    Returns sorted x-crossings, from which stroke widths derive."""
    gs = font.getGlyphSet()
    if glyph_name not in gs:
        return []
    pen = RecordingPen()
    gs[glyph_name].draw(pen)

    # flatten outline to segments (approximating curves)
    pts = []
    crossings = []
    current = None
    start = None

    def flatten_curve(p0, ctrls, p1, steps=24):
        out = []
        n = len(ctrls)
        for i in range(1, steps + 1):
            t = i / steps
            if n == 1:  # quadratic
                x = (1-t)**2*p0[0] + 2*(1-t)*t*ctrls[0][0] + t**2*p1[0]
                y_ = (1-t)**2*p0[1] + 2*(1-t)*t*ctrls[0][1] + t**2*p1[1]
            else:  # cubic
                x = (1-t)**3*p0[0] + 3*(1-t)**2*t*ctrls[0][0] + 3*(1-t)*t**2*ctrls[1][0] + t**3*p1[0]
                y_ = (1-t)**3*p0[1] + 3*(1-t)**2*t*ctrls[0][1] + 3*(1-t)*t**2*ctrls[1][1] + t**3*p1[1]
            out.append((x, y_))
        return out

    segments = []
    for op, args in pen.value:
        if op == "moveTo":
            current = args[0]
            start = args[0]
        elif op == "lineTo":
            segments.append((current, args[0]))
            current = args[0]
        elif op == "qCurveTo":
            # may have implied on-curve points; simple approx pairwise
            pts_seq = [current] + list(args)
            # decompose TrueType qcurves: consecutive off-curves imply midpoints
            i = 0
            prev = current
            ctrl_run = []
            for p in args:
                ctrl_run.append(p)
            # simple: treat as polyline through flattened quad approximation
            flat_prev = current
            ctrls = list(args)
            last = ctrls[-1]
            inner = ctrls[:-1]
            if not inner:
                segments.append((current, last))
            else:
                # insert implied on-curve midpoints
                expanded = []
                for i in range(len(inner)):
                    expanded.append(inner[i])
                    if i < len(inner) - 1:
                        mx = (inner[i][0] + inner[i+1][0]) / 2
                        my = (inner[i][1] + inner[i+1][1]) / 2
                        expanded.append((mx, my))
                # now pairs of (ctrl, oncurve)
                oncurve = flat_prev
                idx = 0
                while idx < len(expanded):
                    c = expanded[idx]
                    if idx + 1 < len(expanded):
                        e = expanded[idx+1]
                    else:
                        e = last
                    for q in flatten_curve(oncurve, [c], e):
                        segments.append((oncurve, q))
                        oncurve = q
                    idx += 2
            current = last
        elif op == "curveTo":
            c1, c2, p1 = args
            prevp = current
            for q in flatten_curve(current, [c1, c2], p1):
                segments.append((prevp, q))
                prevp = q
            current = p1
        elif op == "closePath":
            if current and start and current != start:
                segments.append((current, start))
            current = start

    xs = []
    for (x1, y1), (x2, y2) in segments:
        if (y1 <= y < y2) or (y2 <= y < y1):
            if y2 != y1:
                t = (y - y1) / (y2 - y1)
                xs.append(x1 + t * (x2 - x1))
    xs.sort()
    return xs


def measure(path):
    font = TTFont(path)
    upm = font["head"].unitsPerEm
    hhea = font["hhea"]

    m = {}

    # x-height and cap-height from OS/2 or glyph bounds
    os2 = font.get("OS/2")
    xh = getattr(os2, "sxHeight", 0) or 0
    ch = getattr(os2, "sCapHeight", 0) or 0
    bx = glyph_bounds(font, "x")
    bH = glyph_bounds(font, "H")
    if bx and (not xh or xh <= 0):
        xh = bx[3]
    if bH and (not ch or ch <= 0):
        ch = bH[3]
    m["xheight_ratio"] = xh / ch if ch else 0

    # stroke contrast from 'o': horizontal scan at mid-height gives side wall
    # thickness (thick strokes); vertical extent top/bottom gives thin strokes
    bo = glyph_bounds(font, "o")
    if bo:
        mid_y = (bo[1] + bo[3]) / 2
        xs = scanline_stroke_widths(font, "o", mid_y)
        thick = None
        if len(xs) >= 4:
            thick = ((xs[1] - xs[0]) + (xs[3] - xs[2])) / 2
        # thin: scan near top of the 'o' bowl interior
        # sample multiple heights to find minimum wall at top/bottom
        thin = None
        h = bo[3] - bo[1]
        for frac in (0.08, 0.10, 0.12, 0.90, 0.88, 0.92):
            y = bo[1] + h * frac
            xs2 = scanline_stroke_widths(font, "o", y)
            if len(xs2) == 2:
                # single solid crossing = stroke cap region: width here is
                # horizontal chord, not stroke thickness; skip
                continue
        # better approach: vertical scanline through center measures top/bottom walls
        # rotate problem: use horizontal scans on 'o' but measure vertical walls via
        # bounding of interior. Approximate thin stroke = (outer height - inner height)/2
        xs_mid = scanline_stroke_widths(font, "o", mid_y)
        if len(xs_mid) >= 4:
            inner_left, inner_right = xs_mid[1], xs_mid[2]
            cx = (inner_left + inner_right) / 2
            # walk down from top to find outer and inner y at cx
            # sample scanlines and detect where cx is inside glyph
            inside_ys = []
            steps = 60
            for i in range(steps + 1):
                y = bo[1] + h * i / steps
                xs3 = scanline_stroke_widths(font, "o", y)
                # inside outline if odd number of crossings to the left
                cnt = sum(1 for x in xs3 if x < cx)
                if cnt % 2 == 1:
                    inside_ys.append(y)
            if inside_ys:
                spans = []
                s = inside_ys[0]
                prev = inside_ys[0]
                step = h / steps
                for y in inside_ys[1:]:
                    if y - prev > step * 1.5:
                        spans.append((s, prev))
                        s = y
                    prev = y
                spans.append((s, prev))
                if len(spans) == 2:
                    thin_top = spans[1][1] - spans[1][0] + step
                    thin_bottom = spans[0][1] - spans[0][0] + step
                    thin = (thin_top + thin_bottom) / 2
        if thick and thin and thin > 0:
            m["contrast"] = thick / thin
        else:
            m["contrast"] = None
    else:
        m["contrast"] = None

    # stem weight from 'n' left stem (vertical), scan at x-height/2
    bn = glyph_bounds(font, "n")
    if bn:
        y = xh * 0.4 if xh else (bn[1] + bn[3]) / 2
        xs = scanline_stroke_widths(font, "n", y)
        if len(xs) >= 2:
            m["stem"] = (xs[1] - xs[0]) / upm
        else:
            m["stem"] = None
    else:
        m["stem"] = None

    # average advance width of lowercase alphabet
    hmtx = font["hmtx"]
    cmap = font.getBestCmap()
    widths = []
    for c in "abcdefghijklmnopqrstuvwxyz":
        gname = cmap.get(ord(c))
        if gname:
            widths.append(hmtx[gname][0])
    m["width"] = (sum(widths) / len(widths) / upm) if widths else None

    # counter openness of 'o' (inner width / outer width at mid-height)
    if bo:
        xs = scanline_stroke_widths(font, "o", (bo[1] + bo[3]) / 2)
        if len(xs) >= 4:
            outer = xs[3] - xs[0]
            inner = xs[2] - xs[1]
            m["counter"] = inner / outer if outer else None
        else:
            m["counter"] = None
    else:
        m["counter"] = None

    # descender depth
    m["descender"] = abs(hhea.descender) / upm

    font.close()
    return m


# scoring: gaussian falloff from optimum
OPTIMA = {
    "xheight_ratio": (0.72, 0.06, 20),   # (optimum, sigma, weight)
    "contrast":      (2.5,  1.0,  20),
    "stem":          (0.085, 0.02, 15),
    "width":         (0.50, 0.05, 15),
    "counter":       (0.60, 0.08, 15),
    "descender":     (0.25, 0.05, 15),
}


def score(metrics):
    total = 0.0
    total_weight = 0
    detail = {}
    for key, (opt, sigma, weight) in OPTIMA.items():
        v = metrics.get(key)
        if v is None:
            detail[key] = None
            continue
        s = math.exp(-((v - opt) ** 2) / (2 * sigma ** 2))
        detail[key] = s * 100
        total += s * weight
        total_weight += weight
    return (total / total_weight * 100) if total_weight else 0, detail


if __name__ == "__main__":
    results = []
    for path in sorted(glob.glob("fonts/*.woff2")):
        name = path.split("/")[-1].replace(".woff2", "")
        try:
            metrics = measure(path)
            total, detail = score(metrics)
            results.append((name, total, metrics, detail))
        except Exception as e:
            print(f"{name}: ERROR {e}", file=sys.stderr)

    results.sort(key=lambda r: -r[1])

    hdr = f"{'Font':<20} {'SCORE':>6} | {'x-ht':>6} {'contr':>6} {'stem':>6} {'width':>6} {'countr':>6} {'desc':>6}"
    print(hdr)
    print("-" * len(hdr))
    for name, total, mx, detail in results:
        def fmt(v, prec=3):
            return f"{v:.{prec}f}" if v is not None else "  n/a"
        print(f"{name:<20} {total:>6.1f} | {fmt(mx['xheight_ratio'])} {fmt(mx['contrast'],2)} {fmt(mx['stem'])} {fmt(mx['width'])} {fmt(mx['counter'])} {fmt(mx['descender'])}")

    print()
    print("Per-metric scores (0-100):")
    hdr2 = f"{'Font':<20} | {'x-ht':>6} {'contr':>6} {'stem':>6} {'width':>6} {'countr':>6} {'desc':>6}"
    print(hdr2)
    print("-" * len(hdr2))
    for name, total, mx, detail in results:
        def fmts(k):
            v = detail.get(k)
            return f"{v:>6.0f}" if v is not None else "   n/a"
        print(f"{name:<20} | {fmts('xheight_ratio')} {fmts('contrast')} {fmts('stem')} {fmts('width')} {fmts('counter')} {fmts('descender')}")
