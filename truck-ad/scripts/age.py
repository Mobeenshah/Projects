"""Age a flat ad render so it reads as a scanned 1970s printed original.

usage: python3 age.py flat.png out.jpg [seed]
"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

src, out = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 1972)

flat = Image.open(src).convert("RGB")
W, H = flat.size
ink = np.asarray(flat.filter(ImageFilter.GaussianBlur(0.7)), np.float32) / 255


def noise(scale, octaves=4):
    """Smooth fractal noise in [0,1]."""
    acc, amp, tot = np.zeros((H, W), np.float32), 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(min(H, W) / (scale * 2 ** o)))
        n = rng.random((H // s + 2, W // s + 2)).astype(np.float32)
        n = ndi.zoom(n, s, order=3)[:H, :W]
        acc += amp * n; tot += amp; amp *= 0.5
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
ex = np.minimum(xx, W - 1 - xx) / W; ey = np.minimum(yy, H - 1 - yy) / H
edge = np.clip(np.minimum(ex, ey) / 0.07, 0, 1)            # 0 at edge -> 1 inside

# --- paper: cream stock, yellowed toward the edges, blotchy, fibrous
cream = np.array([0.93, 0.87, 0.74], np.float32)
yellow = np.array([0.80, 0.66, 0.45], np.float32)
blotch = noise(6)
age = (1 - edge) ** 1.6 * 0.85 + blotch * 0.25
paper = cream * (1 - age[..., None] * 0.55) + yellow * (age[..., None] * 0.55)
fib = ndi.gaussian_filter(rng.standard_normal((H, W)).astype(np.float32), (0.6, 2.2))
paper *= (1 + fib[..., None] * 0.035)
paper *= (0.97 + 0.03 * noise(40, 2))[..., None]

# --- ink: uneven density, worn speckle drop-outs, slight press bleed
density = 0.80 + 0.20 * noise(10)
wear = ndi.gaussian_filter(rng.random((H, W)).astype(np.float32), 1.0)
density *= np.where(wear > 0.66, 0.55, 1.0)
img = paper * (1 - density[..., None] * (1 - ink))

# --- fold creases (one vertical, one horizontal, like a folded magazine page)
def crease(dist, width):
    d = np.abs(dist)
    hi = np.exp(-(d / width) ** 2)                      # bright ridge
    sh = np.exp(-((dist - width * 2.5) / (width * 3)) ** 2)  # shadow on one side
    return hi, sh

wob = (noise(3, 2) - 0.5) * 6
for dist in (xx - W * 0.502 + wob, yy - H * 0.497 + wob.T[:H, :W] if W == H else yy - H * 0.497 + wob):
    hi, sh = crease(dist, 2.2)
    loss = hi * (rng.random((H, W)) > 0.35)
    img = img * (1 - sh[..., None] * 0.10) + (paper * 1.05 - img) * (loss[..., None] * 0.85)
    img += hi[..., None] * 0.035

# --- foxing and a faint water stain
fox = np.zeros((H, W), np.float32)
for _ in range(140):
    cx, cy = rng.integers(0, W), rng.integers(0, H)
    r = rng.uniform(1.5, 9) if rng.random() < 0.9 else rng.uniform(14, 40)
    fox[max(0, cy - 1):cy + 1, max(0, cx - 1):cx + 1] += 0
    yy0, yy1 = max(0, int(cy - 3 * r)), min(H, int(cy + 3 * r))
    xx0, xx1 = max(0, int(cx - 3 * r)), min(W, int(cx + 3 * r))
    d2 = ((yy[yy0:yy1, xx0:xx1] - cy) ** 2 + (xx[yy0:yy1, xx0:xx1] - cx) ** 2) / r ** 2
    fox[yy0:yy1, xx0:xx1] += np.exp(-d2) * rng.uniform(0.15, 0.6)
fox *= 0.6 + 0.8 * noise(30, 2)
stain_c = np.array([0.55, 0.38, 0.20], np.float32)
ring_d = np.hypot(xx - W * 0.86, yy - H * 0.86) / (W * 0.13) + (noise(8, 3) - 0.5) * 0.25
ring = np.exp(-((ring_d - 1) / 0.035) ** 2) * 0.35 + (ring_d < 1) * 0.06
stain = np.clip(fox + ring, 0, 1)[..., None]
img = img * (1 - stain * 0.35) + img * stain_c * stain * 0.35

# --- grain, slight overall fade
img = img * 0.97 + 0.02
img += rng.normal(0, 0.012, (H, W, 1)).astype(np.float32)
img = np.clip(img, 0, 1)

import os
if os.environ.get("FULLBLEED"):
    Image.fromarray((img * 255).astype(np.uint8)).save(out, quality=93, subsampling=0)
    sys.exit()

# --- worn, chipped edges: mask on a dark scanner bed
chip = noise(25, 3)
inside = (np.minimum(ex * W, ey * H) > 3 + chip * 16)
inside = ndi.binary_opening(inside, iterations=2)
for _ in range(7):                                       # a few small tears
    side = rng.integers(4); r = rng.uniform(8, 26)
    cx = {0: rng.uniform(0, W), 1: rng.uniform(0, W), 2: 0, 3: W}[side]
    cy = {0: 0, 1: H, 2: rng.uniform(0, H), 3: rng.uniform(0, H)}[side]
    inside &= np.hypot(xx - cx, yy - cy) > r
mask = ndi.gaussian_filter(inside.astype(np.float32), 0.8)[..., None]
bed = np.array([0.15, 0.14, 0.13], np.float32)
img = img * mask + bed * (1 - mask)

pad = 40
canvas = np.empty((H + 2 * pad, W + 2 * pad, 3), np.float32); canvas[:] = bed
canvas[pad:pad + H, pad:pad + W] = img
res = Image.fromarray((canvas * 255).astype(np.uint8)).rotate(-0.45, Image.BICUBIC, fillcolor=tuple((bed * 255).astype(int)))
res.save(out, quality=93, subsampling=0)
