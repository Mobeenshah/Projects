"""Paint a city plate on the front bumper / a name plate on the rear bumper of the desk stills.

usage: python3 customize.py front|rear STILL.png PLATE.png OUT.png
"""
import sys
import cv2
import numpy as np

kind, still, plate_p, out = sys.argv[1:5]
img = cv2.imread(still)
plate = cv2.imread(plate_p, cv2.IMREAD_UNCHANGED)
ys, xs = np.where(plate[..., 3] > 8)
plate = plate[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

# bumper faces measured on the 1200x896 stills (TL, TR, BR, BL), following each face's perspective
QUAD = {"front": [(406, 521), (463, 536), (463, 557), (406, 543)],   # lower face of the red cab
        "rear":  [(413, 489), (522, 511), (522, 532), (413, 510)]}[kind]  # strip under the tailgate

h, w = plate.shape[:2]
SS = 4  # warp at 4x, then downsample, for clean anti-aliased edges
q = np.float32(QUAD) * SS
M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), q)
big = cv2.resize(img, None, fx=SS, fy=SS, interpolation=cv2.INTER_CUBIC)
lay = cv2.warpPerspective(plate, M, (big.shape[1], big.shape[0]), flags=cv2.INTER_AREA)
lay = cv2.resize(lay, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_AREA)
a = lay[..., 3:].astype(np.float32) / 255
# match the scene's light: shade by the local brightness of what the plate covers, plus a touch of blur
g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), 4).astype(np.float32)
ref = np.percentile(g[a[..., 0] > 0.5], 70)
shade = np.clip(g / ref, 0.7, 1.08)[..., None] * 0.95
col = cv2.GaussianBlur(lay[..., :3].astype(np.float32), (0, 0), 0.45) * shade
res = img.astype(np.float32) * (1 - a) + col * a
cv2.imwrite(out, np.clip(res, 0, 255).astype(np.uint8))
