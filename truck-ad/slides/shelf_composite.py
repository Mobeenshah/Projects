"""Place a truck cutout on the shelf frame: scale, light-match, contact shadow, soften, crop to 4:5.

usage: python3 shelf_composite.py SHELF.png CUTOUT.png OUT.png
"""
import sys
import cv2
import numpy as np

shelf_p, cut_p, out = sys.argv[1:4]
bg = cv2.imread(shelf_p).astype(np.float32)
cut = cv2.imread(cut_p, cv2.IMREAD_UNCHANGED)
W_T, X0, BASE = 410, 650, 905          # truck width, left edge, wheel line on the shelf (1080x1920 frame)
s = W_T / cut.shape[1]
cut = cv2.resize(cut, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
h, w = cut.shape[:2]
y0 = BASE - h
rgb, a = cut[..., :3].astype(np.float32), cut[..., 3:].astype(np.float32) / 255

# light match: the shelf is warm and dim, lit from the right
ref = bg[y0:BASE, X0:X0 + w].reshape(-1, 3).mean(0)
rgb = rgb * np.array([0.70, 0.80, 0.92]) * (0.85 + 0.15 * ref.mean() / 128)
grad = np.linspace(0.88, 1.06, w)[None, :, None]             # brighter on the lit (right) side
rgb = rgb * grad

# contact + cast shadow (light from the right, shadow falls left)
sh = np.zeros(bg.shape[:2], np.float32)
cv2.ellipse(sh, (X0 + w // 2 - 20, BASE - 8), (w // 2 + 10, 20), 0, 0, 360, 1, -1)
sh = cv2.GaussianBlur(sh, (0, 0), 14)
bg *= (1 - 0.55 * sh)[..., None]

region = bg[y0:BASE, X0:X0 + w]
comp = region * (1 - a) + rgb * a
bg[y0:BASE, X0:X0 + w] = comp
# match the video's softness and grain, then crop a 4:5 frame around the scene
bg = cv2.GaussianBlur(bg, (0, 0), 0.6)
bg += np.random.default_rng(3).normal(0, 3.0, bg.shape)
crop = bg[250:1225, 300:1080]
cv2.imwrite(out, np.clip(cv2.resize(crop, (1080, 1350), interpolation=cv2.INTER_CUBIC), 0, 255).astype(np.uint8))
