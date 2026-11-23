"""Cut the 3D-printed truck out of a table photo (saturation seed + GrabCut)."""
import sys, cv2, numpy as np
from scipy import ndimage as ndi

src, out, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
img = cv2.imread(src)
crop = img[y0:y1, x0:x1].copy()
hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
s, v = hsv[..., 1].astype(int), hsv[..., 2].astype(int)
sure = (s > 110) & (v > 50)
sure = ndi.binary_opening(sure, iterations=2)
lab, n = ndi.label(sure)
sizes = ndi.sum(sure, lab, range(1, n + 1))
keep = np.isin(lab, 1 + np.where(sizes > 0.02 * sizes.max())[0])
filled = ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=6))

mask = np.full(s.shape, cv2.GC_BGD, np.uint8)
mask[ndi.binary_dilation(filled, iterations=25)] = cv2.GC_PR_BGD
mask[ndi.binary_dilation(filled, iterations=4)] = cv2.GC_PR_FGD
mask[ndi.binary_erosion(filled, iterations=6)] = cv2.GC_FGD
bg, fg = np.zeros((1, 65)), np.zeros((1, 65))
cv2.grabCut(crop, mask, None, bg, fg, 6, cv2.GC_INIT_WITH_MASK)
m = np.isin(mask, [cv2.GC_FGD, cv2.GC_PR_FGD])
m = ndi.binary_fill_holes(ndi.binary_closing(m, iterations=3))
lab, n = ndi.label(m)
m = lab == (1 + np.argmax(ndi.sum(m, lab, range(1, n + 1))))
# drop table showing through openings (truck has no white/grey parts)
hole = (s < 40) & (v > 140)
hole = ndi.binary_opening(hole, iterations=2)
m &= ~hole
alpha = cv2.GaussianBlur((m * 255).astype(np.uint8), (0, 0), 1.2)
rgba = cv2.cvtColor(crop, cv2.COLOR_BGR2BGRA); rgba[..., 3] = alpha
cv2.imwrite(out, rgba)
