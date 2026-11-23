"""Cut an object out of a busy background with rectangle-seeded GrabCut. usage: IMG OUT x0 y0 x1 y1"""
import sys, cv2, numpy as np
from scipy import ndimage as ndi
src, out, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
img = cv2.imread(src)
up = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)   # work at 2x for cleaner edges
mask = np.zeros(up.shape[:2], np.uint8)
bg, fg = np.zeros((1, 65)), np.zeros((1, 65))
cv2.grabCut(up, mask, (2 * x0, 2 * y0, 2 * (x1 - x0), 2 * (y1 - y0)), bg, fg, 8, cv2.GC_INIT_WITH_RECT)
m = np.isin(mask, [cv2.GC_FGD, cv2.GC_PR_FGD])
m = ndi.binary_opening(m, iterations=2)
lab, n = ndi.label(m)
m = lab == (1 + np.argmax(ndi.sum(m, lab, range(1, n + 1))))
m = ndi.binary_fill_holes(m)
# clear background seen through openings (e.g. between the cargo-box arches): pale, low-saturation pixels
hsv = cv2.cvtColor(up, cv2.COLOR_BGR2HSV)
pale = (hsv[..., 1] < 85) & (hsv[..., 2] > 120)
pale = ndi.binary_opening(pale, iterations=1)
m &= ~pale
a = cv2.GaussianBlur((m * 255).astype(np.uint8), (0, 0), 1.3)
rgba = cv2.cvtColor(up, cv2.COLOR_BGR2BGRA); rgba[..., 3] = a
ys, xs = np.where(a > 10)
cv2.imwrite(out, rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
