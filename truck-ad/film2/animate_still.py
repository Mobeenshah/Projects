"""Bring a still to life as a 9:16 clip: slow camera move, candle flicker and glow.

usage: python3 animate_still.py IMG OUT.mp4 DUR "cx0,cy0,h0" "cx1,cy1,h1" [candle_x,candle_y] [blur]
  The window is a 9:16 rectangle of height h centred on (cx, cy) in image pixels, eased from start to end.
"""
import subprocess
import sys
import cv2
import numpy as np

img_p, out, dur = sys.argv[1], sys.argv[2], float(sys.argv[3])
p0 = np.array(sys.argv[4].split(","), float); p1 = np.array(sys.argv[5].split(","), float)
candle = np.array(sys.argv[6].split(","), float) if len(sys.argv) > 6 and sys.argv[6] else None
blur = float(sys.argv[7]) if len(sys.argv) > 7 else 0
FPS, OW, OH = 24, 1080, 1920
img = cv2.imread(img_p).astype(np.float32)
H, W = img.shape[:2]
rng = np.random.default_rng(7)

if candle is not None:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d2 = (xx - candle[0]) ** 2 + (yy - candle[1]) ** 2
    glow = np.exp(-d2 / (2 * 260 ** 2))[..., None]            # light the candle throws on the scene
    flame = np.exp(-d2 / (2 * 22 ** 2))[..., None]            # the flame and its halo
    warm = np.array([0.80, 0.93, 1.0], np.float32)             # BGR warm tint

n = int(round(dur * FPS))
# smooth random flicker: sum of a few slow sines + filtered noise
tt = np.arange(n) / FPS
flick = (0.035 * np.sin(2 * np.pi * 1.3 * tt) + 0.025 * np.sin(2 * np.pi * 3.7 * tt + 1)
         + np.convolve(rng.normal(0, 0.05, n + 6), np.ones(7) / 7, "valid")[:n])

ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
                       "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
for i in range(n):
    s = i / max(1, n - 1)
    e = s * s * (3 - 2 * s)                                     # ease in/out
    cx, cy, h = p0 + (p1 - p0) * e
    w = h * 9 / 16
    fr = img
    if candle is not None:
        f = flick[i]
        fr = img * (1 + glow * f * 1.6 * warm) + flame * 255 * max(0, f) * 1.2 * warm
    scale = OH / h
    M = np.float32([[scale, 0, -(cx - w / 2) * scale], [0, scale, -(cy - h / 2) * scale]])
    o = cv2.warpAffine(np.clip(fr, 0, 255), M, (OW, OH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    if blur:
        o = cv2.GaussianBlur(o, (0, 0), blur) * 0.55
    else:  # gentle sharpening after the upscale
        o = cv2.addWeighted(o, 1.35, cv2.GaussianBlur(o, (0, 0), 2.2), -0.35, 0)
    ff.stdin.write(np.clip(o, 0, 255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait()
