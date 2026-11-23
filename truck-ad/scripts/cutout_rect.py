"""Cut an object out of a busy background with rectangle-seeded GrabCut. usage: IMG OUT x0 y0 x1 y1 [wood]
  wood: also strip table wood seen low between the wheels (rear views; red cabs can be mistaken for wood)."""
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
pale = (hsv[..., 1] < 85) & (hsv[..., 2] > 120) & (hsv[..., 0] < 38)   # beige wall, not green highlights
pale = ndi.binary_opening(pale, iterations=1)
ys_, xs_ = np.where(m)
top, bot = ys_.min(), ys_.max()
band = np.zeros_like(m); band[: top + int(0.35 * (bot - top))] = True   # arch gaps live near the top
m &= ~(pale & band)
# table wood showing between the wheels: orange-brown, low in the frame
h_, s_, v_ = hsv[..., 0], hsv[..., 1], hsv[..., 2]
wood = (h_ >= 9) & (h_ <= 22) & (s_ > 70) & (s_ < 215) & (v_ > 60) & (v_ < 225)
low = np.zeros_like(m); low[top + int(0.75 * (bot - top)):] = True
if len(sys.argv) > 7 and sys.argv[7] == "wood":
    m &= ~ndi.binary_opening(wood & low, iterations=2)
    m &= ~((v_ < 50) & (s_ < 120) & low)   # deep shadow under the body
m = ndi.binary_opening(m, iterations=2)
lab, n = ndi.label(m)
m = lab == (1 + np.argmax(ndi.sum(m, lab, range(1, n + 1))))
# smooth ragged edges (GrabCut leaves a comb where the object meets a similar background)
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
mm = cv2.morphologyEx((m * 255).astype(np.uint8), cv2.MORPH_OPEN, k)
mm = cv2.morphologyEx(mm, cv2.MORPH_CLOSE, k)
mm = cv2.medianBlur(mm, 9)
m = mm > 127
a = cv2.GaussianBlur((m * 255).astype(np.uint8), (0, 0), 1.3)
rgba = cv2.cvtColor(up, cv2.COLOR_BGR2BGRA); rgba[..., 3] = a
ys, xs = np.where(a > 10)
cv2.imwrite(out, rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
# where the crop sits in the source image (source pixels), so callouts can point at features
print(f"bbox {(x0*2*0 + xs.min())/2:.1f} {ys.min()/2:.1f} {(xs.max()+1)/2:.1f} {(ys.max()+1)/2:.1f}")
