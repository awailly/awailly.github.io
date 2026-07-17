"""
Role-aware font scoring. Same outline-based measurement as measure.py
(scanline intersection of flattened glyph contours) but with optima
tuned per role:

SANS (body text at 14-16px):
  x-height ratio  optimum 0.73  (screen legibility)      w25
  stroke contrast optimum 1.2   (near-monolinear, warm)  w15
  counter open    optimum 0.62                           w20
  width economy   optimum 0.50                           w15
  stem weight     optimum 0.082                          w10
  descender depth optimum 0.22                           w15

MONO (metadata/labels at 11-13px):
  x-height ratio  optimum 0.75  (higher: tiny sizes)     w30
  stroke contrast optimum 1.1   (monolinear by design)   w10
  counter open    optimum 0.62                           w20
  width economy   optimum 0.60  (mono runs wider)        w10
  stem weight     optimum 0.09  (slightly sturdier)      w15
  descender depth optimum 0.22                           w15
"""
import glob
import math
import sys


from measure_outline import measure  # reuse outline-based measurement

ROLES = {
    "sans": {
        "xheight_ratio": (0.73, 0.05, 25),
        "contrast":      (1.2,  0.5,  15),
        "counter":       (0.62, 0.08, 20),
        "width":         (0.50, 0.05, 15),
        "stem":          (0.082, 0.02, 10),
        "descender":     (0.22, 0.05, 15),
    },
    "mono": {
        "xheight_ratio": (0.75, 0.05, 30),
        "contrast":      (1.1,  0.5,  10),
        "counter":       (0.62, 0.08, 20),
        "width":         (0.60, 0.06, 10),
        "stem":          (0.09, 0.02, 15),
        "descender":     (0.22, 0.05, 15),
    },
}


def score(metrics, optima):
    total = 0.0
    tw = 0
    detail = {}
    for key, (opt, sigma, weight) in optima.items():
        v = metrics.get(key)
        if v is None:
            detail[key] = None
            continue
        s = math.exp(-((v - opt) ** 2) / (2 * sigma ** 2))
        detail[key] = s * 100
        total += s * weight
        tw += weight
    return (total / tw * 100) if tw else 0, detail


def run(role):
    optima = ROLES[role]
    results = []
    for path in sorted(glob.glob(f"fonts/{role}/*.woff2")):
        name = path.split("/")[-1].replace(".woff2", "")
        try:
            metrics = measure(path)
            total, detail = score(metrics, optima)
            results.append((name, total, metrics, detail))
        except Exception as e:
            print(f"{name}: ERROR {e}", file=sys.stderr)

    results.sort(key=lambda r: -r[1])

    print(f"\n=== {role.upper()} ===")
    hdr = f"{'Font':<18} {'SCORE':>6} | {'x-ht':>6} {'contr':>6} {'stem':>6} {'width':>6} {'countr':>6} {'desc':>6}"
    print(hdr)
    print("-" * len(hdr))
    for name, total, mx, detail in results:
        def fmt(v, prec=3):
            return f"{v:.{prec}f}" if v is not None else "  n/a"
        print(f"{name:<18} {total:>6.1f} | {fmt(mx['xheight_ratio'])} {fmt(mx['contrast'],2)} {fmt(mx['stem'])} {fmt(mx['width'])} {fmt(mx['counter'])} {fmt(mx['descender'])}")


if __name__ == "__main__":
    run("mono")
    run("sans")
