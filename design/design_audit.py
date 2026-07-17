"""
Design audit: parse the site's CSS, compute measurable design metrics,
score against research-backed optima (gaussian falloff, like the font audit).

Uses real font metrics (average advance width measured from the font files)
to compute true characters-per-line.
"""
import math
import re
import sys



# ---------- color math ----------

def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rel_luminance(rgb):
    def f(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(hex1, hex2):
    l1 = rel_luminance(hex_to_rgb(hex1))
    l2 = rel_luminance(hex_to_rgb(hex2))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def rgb_to_hue_chroma(rgb):
    """Approximate LCH hue/chroma via simple HSL-ish math (sufficient for
    hue-angle relationships)."""
    r, g, b = (c / 255 for c in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    c = mx - mn
    if c == 0:
        return None, 0
    if mx == r:
        h = ((g - b) / c) % 6
    elif mx == g:
        h = (b - r) / c + 2
    else:
        h = (r - g) / c + 4
    return h * 60, c


# ---------- gaussian scoring ----------

def gauss(v, opt, sigma):
    return math.exp(-((v - opt) ** 2) / (2 * sigma ** 2)) * 100


# ---------- audit ----------

def audit(html_path):
    with open(html_path) as f:
        src = f.read()

    results = []  # (metric, value_desc, score, weight)

    # palette
    def var(name):
        m = re.search(rf"--{name}:\s*(#[0-9a-fA-F]+)", src)
        return m.group(1) if m else None

    bg = var("bg") or "#ffffff"
    text = var("text")
    secondary = var("secondary")
    accent = var("accent")
    blue = var("blue")
    amber = var("amber")

    # 1. body contrast: optimum 13 (AAA but not harsh), sigma 3
    c = contrast(text, bg)
    results.append(("body contrast", f"{c:.1f}:1", gauss(c, 13, 3), 15))

    # 2. secondary contrast: optimum 7 (AAA), sigma 1.5, floor hard-fail < 4.5
    c = contrast(secondary, bg)
    s = gauss(c, 7, 1.5) if c >= 4.5 else 0
    results.append(("secondary contrast", f"{c:.1f}:1", s, 15))

    # 3. functional color contrast (blue used for text-ish labels): >= 4.5
    c = contrast(blue, bg)
    s = gauss(c, 5.5, 1.2) if c >= 4.5 else max(0, gauss(c, 5.5, 1.2) - 40)
    results.append(("blue label contrast", f"{c:.1f}:1", s, 10))

    # 4. decorative color contrast (amber, non-text glyph): WCAG non-text 3:1
    if amber:
        c = contrast(amber, bg)
        s = 100 if c >= 3 else c / 3 * 100
        results.append(("amber decorative contrast", f"{c:.1f}:1", s, 5))

    # 5. line length of main reading text (bio: Lora at 1.15rem in 600px)
    from fontTools.ttLib import TTFont
    lf = TTFont("fonts/LoraFull.ttf")
    upm = lf["head"].unitsPerEm
    cmap = lf.getBestCmap()
    hmtx = lf["hmtx"]
    # weighted by English letter frequency approximation: just lowercase + space
    advs = [hmtx[cmap[ord(ch)]][0] for ch in "abcdefghijklmnopqrstuvwxyz " if ord(ch) in cmap]
    avg_adv = sum(advs) / len(advs) / upm  # em units
    font_px = 1.15 * 16
    cpl = 600 / (font_px * avg_adv)
    results.append(("bio line length", f"{cpl:.0f} cpl", gauss(cpl, 66, 10), 15))

    # 6. body line-height (main body rule)
    m = re.search(r"body \{[^}]*line-height:\s*([\d.]+)", src)
    lh = float(m.group(1)) if m else None
    results.append(("body line-height", f"{lh}", gauss(lh, 1.5, 0.15), 10))

    # 7. bio line-height
    m = re.search(r"header p \{[^}]*line-height:\s*([\d.]+)", src, re.S)
    lh2 = float(m.group(1)) if m else None
    if lh2:
        results.append(("bio line-height", f"{lh2}", gauss(lh2, 1.5, 0.15), 10))

    # 8. type scale consistency: h1, h2, pub title, body
    sizes = {}
    m = re.search(r"header h1 \{[^}]*font-size:\s*([\d.]+)rem", src)
    sizes["h1"] = float(m.group(1)) if m else None
    m = re.search(r"section > h2 \{[^}]*font-size:\s*([\d.]+)rem", src)
    sizes["h2"] = float(m.group(1)) if m else None
    m = re.search(r"\.pub-entry \.details h3 \{[^}]*font-size:\s*([\d.]+)rem", src)
    sizes["h3"] = float(m.group(1)) if m else None
    sizes["body"] = 1.0
    if all(sizes.values()):
        r1 = sizes["h1"] / sizes["h2"]
        r2 = sizes["h2"] / sizes["h3"]
        r3 = sizes["h3"] / sizes["body"]
        # consistency: coefficient of variation of the ratios
        ratios = [r1, r2, r3]
        mean = sum(ratios) / 3
        cv = math.sqrt(sum((r - mean) ** 2 for r in ratios) / 3) / mean
        s = gauss(cv, 0, 0.12)  # 0 = perfectly geometric
        results.append(("type scale consistency", f"ratios {r1:.2f}/{r2:.2f}/{r3:.2f}", s, 10))

    # 9. color harmony: hue angle between blue and amber (complementary=180)
    hb, cb = rgb_to_hue_chroma(hex_to_rgb(blue)) if blue else (None, 0)
    ha, ca = rgb_to_hue_chroma(hex_to_rgb(amber)) if amber else (None, 0)
    if hb is not None and ha is not None:
        d = abs(hb - ha)
        d = min(d, 360 - d)
        results.append(("accent hue relationship", f"{d:.0f}deg apart", gauss(d, 180, 30), 5))

    # 10. spacing rhythm: all margin/padding rem values should sit on 0.25 grid
    vals = re.findall(r"(?:margin|padding)[^:]*:\s*([^;]+);", src)
    nums = []
    for v in vals:
        nums += re.findall(r"([\d.]+)rem", v)
    nums = [float(n) for n in nums]
    if nums:
        off_grid = sum(1 for n in nums if (n * 20) % 1 > 1e-6)  # 0.05rem grid
        frac = off_grid / len(nums)
        results.append(("spacing grid adherence", f"{100-frac*100:.0f}% on grid", (1 - frac) * 100, 5))

    return results


def report(results, title):
    print(f"\n=== {title} ===")
    hdr = f"{'Metric':<28} {'Value':>18} {'Score':>7} {'Wt':>4}"
    print(hdr)
    print("-" * len(hdr))
    total, tw = 0, 0
    for name, val, s, w in results:
        print(f"{name:<28} {val:>18} {s:>7.0f} {w:>4}")
        total += s * w
        tw += w
    print("-" * len(hdr))
    print(f"{'TOTAL':<28} {'':>18} {total/tw:>7.1f}")
    return total / tw


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../index.html"
    results = audit(path)
    report(results, path)
