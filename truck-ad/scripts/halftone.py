"""Turn an RGBA cutout into a vintage offset-print CMYK halftone (RGBA out)."""
import sys, numpy as np
from PIL import Image, ImageEnhance, ImageFilter

src, out, width = sys.argv[1], sys.argv[2], int(sys.argv[3])
cell = float(sys.argv[4]) if len(sys.argv) > 4 else 7.0
SS = 3  # supersampling for anti-aliased dots

im = Image.open(src).convert("RGBA")
im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
rgb, a = im.convert("RGB"), im.getchannel("A")
rgb = ImageEnhance.Color(rgb).enhance(0.88)
rgb = ImageEnhance.Contrast(rgb).enhance(1.18)
rgb = ImageEnhance.Brightness(rgb).enhance(1.04)
f = np.asarray(rgb, np.float32) / 255
f = f * np.array([1.03, 1.0, 0.92])            # warm, aged pigment
f = np.clip(f, 0, 1)

k = 1 - f.max(-1)
c, m, y = [(1 - f[..., i] - k) / np.maximum(1 - k, 1e-4) for i in range(3)]
k = k * 0.75                                     # partial GCR, like old presses
chans = {"c": (c, 15), "m": (m, 75), "y": (y, 0), "k": (k, 45)}
inks = {"c": np.array([0.05, 0.55, 0.80]), "m": np.array([0.88, 0.16, 0.38]),
        "y": np.array([0.98, 0.86, 0.10]), "k": np.array([0.12, 0.10, 0.10])}
reg = {"c": (-1.5, 1.0), "m": (1.5, 0.5), "y": (0.0, -1.0), "k": (0, 0)}  # misregistration

H, W = k.shape
yy, xx = np.mgrid[0:H * SS, 0:W * SS].astype(np.float32) / SS
paper = np.ones((H * SS, W * SS, 3), np.float32)
for name, (ch, ang) in chans.items():
    dx, dy = reg[name]
    t = np.deg2rad(ang); ct, st = np.cos(t), np.sin(t)
    X, Y = xx - dx, yy - dy
    u, v = (X * ct + Y * st) / cell, (-X * st + Y * ct) / cell
    cu, cv = np.floor(u) + 0.5, np.floor(v) + 0.5
    # cell centre back in image space -> sample tone there
    sx = (cu * ct - cv * st) * cell + dx; sy = (cu * st + cv * ct) * cell + dy
    sxi = np.clip(sx.astype(int), 0, W - 1); syi = np.clip(sy.astype(int), 0, H - 1)
    tone = np.clip(ch[syi, sxi], 0, 1)
    r = np.sqrt(tone / np.pi) * 1.18             # dot radius in cell units
    d = np.hypot(u - cu, v - cv)
    dot = (d < r).astype(np.float32)
    ink = inks[name]
    paper *= 1 - dot[..., None] * (1 - ink) * 0.93
img = (paper.reshape(H, SS, W, SS, 3).mean((1, 3)) * 255).astype(np.uint8)
out_im = Image.fromarray(img).convert("RGBA")
out_im.putalpha(a.filter(ImageFilter.GaussianBlur(0.8)))
out_im.save(out)
