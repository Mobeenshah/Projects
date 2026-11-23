"""Replace the AI-gibberish lettering in the desk stills with real Urdu.

usage: python3 fix_stills.py STILL_FRONT STILL_REAR NOTE.png TAIL.png OUTDIR
"""
import sys
import cv2
import numpy as np

front, rear, note_png, tail_png, outdir = sys.argv[1:6]
note = cv2.imread(note_png, cv2.IMREAD_UNCHANGED)
tail = cv2.imread(tail_png, cv2.IMREAD_UNCHANGED)


def crop_alpha(rgba):
    ys, xs = np.where(rgba[..., 3] > 8)
    return rgba[max(0, ys.min() - 4):ys.max() + 5, max(0, xs.min() - 4):xs.max() + 5]


def warp_onto(img, rgba, quad, blur=0.6, strength=1.0, mode="ink"):
    """Perspective-warp an RGBA layer into quad (TL, TR, BR, BL) and composite."""
    rgba = crop_alpha(rgba)
    h, w = rgba.shape[:2]
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
    lay = cv2.warpPerspective(rgba, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_AREA)
    a = cv2.GaussianBlur(lay[..., 3].astype(np.float32) / 255, (0, 0), blur)[..., None] * strength
    col = lay[..., :3].astype(np.float32)
    base = img.astype(np.float32)
    if mode == "ink":   # ink soaks into paper: multiply, keeps paper texture and lighting
        out = base * (1 - a) + base * (col / 255) * a
    else:               # paint: tint by local light so it sits under the scene's lighting
        g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), 6).astype(np.float32)
        ref = np.median(g[lay[..., 3] > 128])
        lum = np.clip(g / ref, 0.85, 1.1)[..., None] * 0.97
        out = base * (1 - a) + np.clip(col * lum, 0, 255) * a
    return np.clip(out, 0, 255).astype(np.uint8)


def erase(img, poly, keep_out=None, kind="dark"):
    """Inpaint old lettering strokes found inside poly."""
    region = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(region, [np.int32(poly)], 255)
    if keep_out is not None:
        cv2.fillPoly(region, [np.int32(keep_out)], 0)
    if kind == "dark":
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.int16)
        bg = cv2.medianBlur(g.astype(np.uint8), 21).astype(np.int16)
        strokes = (bg - g) > 22
    else:  # yellow paint on green
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        strokes = (hsv[..., 0] > 15) & (hsv[..., 0] < 40) & (hsv[..., 1] > 80) & (hsv[..., 2] > 120)
    m = (strokes & (region > 0)).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=2)
    return cv2.inpaint(img, m, 5, cv2.INPAINT_TELEA)


# the notebook page sits in the same place in both stills
PAGE = [(578, 596), (888, 562), (902, 706), (594, 728)]
NOTE_QUAD = [(583, 586), (880, 556), (893, 690), (598, 718)]

im = cv2.imread(front)
im = erase(im, PAGE)
im = warp_onto(im, note, NOTE_QUAD, blur=0.55, strength=0.92)
cv2.imwrite(f"{outdir}/desk_front.png", im)

im = cv2.imread(rear)
PEN = [(666, 650), (1190, 726), (1190, 772), (666, 667)]
im = erase(im, PAGE, keep_out=PEN)
note_rgba = note.copy()
im2 = warp_onto(im, note_rgba, NOTE_QUAD, blur=0.55, strength=0.92)
pen_mask = np.zeros(im.shape[:2], np.uint8); cv2.fillPoly(pen_mask, [np.int32(PEN)], 255)
im = np.where(pen_mask[..., None] > 0, im, im2)          # the pen lies on top of the writing
TAILBOX = [(424, 425), (522, 415), (522, 485), (424, 497)]
im = erase(im, TAILBOX, kind="yellow")
im = warp_onto(im, tail, [(432, 428), (514, 420), (514, 482), (432, 492)], blur=0.5, mode="paint")
cv2.imwrite(f"{outdir}/desk_rear.png", im)
