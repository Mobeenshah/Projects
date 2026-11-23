"""Diaspora-nostalgia cut: real Pakistani trucks (memory) -> the 3D-printed truck far from home.

usage: python3 build.py --own OWN.mp4 --trucks A.mp4 B.mp4 C.mp4 --text DIR --work DIR --out OUT.mp4 [--music TRACK]
  A = orange truck by the highway (2a3e...), B = truck approaching through trees (0316...),
  C = truck loaded with sacks (6f1c...). DIR holds caption PNGs t1..t6 from text.html.
"""
import argparse
import subprocess
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--own"); ap.add_argument("--trucks", nargs=3); ap.add_argument("--text")
ap.add_argument("--work"); ap.add_argument("--out"); ap.add_argument("--music")
ap.add_argument("--desk-front"); ap.add_argument("--desk-rear")
a = ap.parse_args()
W = Path(a.work); W.mkdir(parents=True, exist_ok=True)
TA, TB, TC = a.trucks
FPS, XF = 24, 0.6  # frame rate, crossfade length

# memory = warm, soft, blooming super-8; today = cool, quiet; home = the toy glowing in home's colours
GRADE = {
    "memory": "eq=saturation=0.92:contrast=0.94:gamma=1.06,"
              "colorbalance=rs=.10:gs=.03:bs=-.12:rm=.07:bm=-.08:rh=.06:bh=-.07,"
              "curves=all='0/0.07 0.5/0.52 1/0.96',"
              "split[a][b];[b]gblur=sigma=14[g];[a][g]blend=all_mode=screen:all_opacity=0.28,"
              "noise=alls=16:allf=t,vignette=PI/3.8",
    "today":  "eq=saturation=0.55:contrast=1.02:gamma=0.97,"
              "colorbalance=rs=-.04:bs=.07:rm=-.02:bm=.05,"
              "noise=alls=8:allf=t,vignette=PI/4.5",
    "night":  "eq=saturation=0.92:contrast=1.03,"
              "colorbalance=rs=.04:bs=-.03,"
              "split[a][b];[b]gblur=sigma=14[g];[a][g]blend=all_mode=screen:all_opacity=0.16,"
              "noise=alls=10:allf=t,vignette=PI/4",
    "card":   "noise=alls=5:allf=t",
    "home":   "eq=saturation=1.05:contrast=1.02,"
              "colorbalance=rs=.05:bs=-.05:rm=.04:bm=-.04,"
              "split[a][b];[b]gblur=sigma=12[g];[a][g]blend=all_mode=screen:all_opacity=0.18,"
              "noise=alls=9:allf=t,vignette=PI/4.2",
}

# (source, start, dur, grade, caption, push-in per second[, crop (x0, y0, size) as fractions])
# truck clips are cropped (and trimmed before the watermark jumps corners) to leave out the TikTok
# watermark; the creator is credited on screen instead.
SHOTS = [
    (None, 0, 3.6, "memory", "t1", 0),
    (TB, 0.0, 4.5, "memory", "t2", 0.02, (0.36, 0.18, 0.64)),
    (TA, 8.0, 4.0, "memory", None, 0.015, (0.02, 0.03, 0.64)),
    (TC, 1.5, 3.5, "memory", "t3", 0.015, (0.21, 0.06, 0.74)),
    (TB, 12.0, 3.0, "memory", None, 0.02, (0.17, 0.02, 0.66)),
    (TA, 14.0, 3.0, "memory", None, 0.02, (0.30, 0.02, 0.66)),
    # today: a student's desk far from home (stills brought to life), with the best moment of the real truck
    (("still", a.desk_front, "252,448,896", "606,448,896", "188,330"), 0, 6.0, "night", "t4", 0),
    (a.own, 0.0, 2.8, "home", None, 0.0),
    (("still", a.desk_rear, "790,448,896", "592,448,860", "190,345"), 0, 6.5, "night", "t5", 0),
    (("still", a.desk_front, "600,448,896", "600,448,860", "188,330", "9"), 0, 5.0, "night", "t6", 0),
    # the pitch: Zedem Bazaar card, the tailgate city cycling Lahore -> Karachi -> Peshawar
    (("cards", "cta_lahore", "cta_karachi", "cta_peshawar"), 0, 7.5, "card", None, 0),
]


def run(cmd):
    subprocess.run(cmd, check=True)


segs = []
credit_span = []
starts = []
t_acc = 0.0
for i, (src, ss, dur, grade, cap, push, *crop) in enumerate(SHOTS):
    starts.append(t_acc - (XF if i else 0))
    if src in (TA, TB, TC):
        credit_span.append((t_acc - (XF if i else 0), t_acc - (XF if i else 0) + dur))
    t_acc += dur - (XF if i else 0)
    out = W / f"s{i:02d}.mp4"
    if isinstance(src, tuple) and src[0] == "cards":  # cross-dissolving card variants
        k = len(src) - 1; each = (dur + 0.5 * (k - 1)) / k
        ins = sum([["-loop", "1", "-t", f"{each:.3f}", "-framerate", str(FPS), "-i", f"{a.text}/{c}.png"] for c in src[1:]], [])
        xf, prev = [], "[0:v]"
        for j in range(1, k):
            xf.append(f"{prev}[{j}:v]xfade=transition=fade:duration=0.5:offset={j * (each - 0.5):.3f}[c{j}]"); prev = f"[c{j}]"
        clip = W / f"cards{i:02d}.mp4"
        run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(xf) + f";{prev}format=yuv420p[o]",
             "-map", "[o]", "-r", str(FPS), "-c:v", "libx264", "-crf", "14", "-preset", "fast", str(clip)])
        inp = ["-i", str(clip)]
        base = "zoompan=z='1+0.0004*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=24"
    elif isinstance(src, tuple):  # an animated still
        _, img, p0, p1, candle, *bl = src
        clip = W / f"still{i:02d}.mp4"
        run(["python3", str(Path(__file__).with_name("animate_still.py")), img, str(clip), str(dur), p0, p1, candle,
             *(bl or [])])
        inp = ["-i", str(clip)]
        base = "null"
    elif src is None:
        inp = ["-f", "lavfi", "-t", str(dur), "-i", f"color=c=0x120f0c:s=1080x1920:r={FPS}"]
        base = "null"
    else:
        inp = ["-ss", str(ss), "-t", str(dur), "-i", src]
        z = f"1+{push / FPS:.5f}*on"
        cr = f"crop=iw*{crop[0][2]}:ih*{crop[0][2]}:iw*{crop[0][0]}:ih*{crop[0][1]}," if crop else ""
        base = (f"fps={FPS},{cr}scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={FPS}")
    fc = f"[0:v]{base},{GRADE[grade]},format=yuv420p[v0]"
    extra = []
    if cap:
        extra = ["-loop", "1", "-t", str(dur), "-i", f"{a.text}/{cap}.png"]
        fi, fo = 0.5, max(0.6, dur - 0.9)
        fc += (f";[1:v]format=rgba,fade=t=in:st={fi}:d=0.8:alpha=1,fade=t=out:st={fo}:d=0.6:alpha=1[t]"
               f";[v0][t]overlay=0:0:shortest=1,format=yuv420p[v1]")
        vout = "[v1]"
    else:
        vout = "[v0]"
    run(["ffmpeg", "-v", "error", "-y", *inp, *extra, "-filter_complex", fc, "-map", vout,
         "-t", str(dur), "-r", str(FPS), "-c:v", "libx264", "-crf", "15", "-preset", "fast", str(out)])
    segs.append((out, dur))

# crossfade chain
inputs, fc, prev, t = [], [], "[0:v]", segs[0][1]
for i, (p, d) in enumerate(segs):
    inputs += ["-i", str(p)]
for i in range(1, len(segs)):
    off = t - XF
    fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{i}]")
    prev, t = f"[x{i}]", off + segs[i][1]
total = t
c0, c1 = credit_span[0][0], credit_span[-1][1]
inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", f"{a.text}/credit.png"]
ci = len(segs)
b0, b1 = starts[6], starts[-2]          # logo badge: from the desk scenes until the end card
inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", f"{a.text}/bug.png"]
fc.append(f"[{ci}:v]format=rgba,fade=t=in:st={c0 + 0.6:.3f}:d=0.6:alpha=1,fade=t=out:st={c1 - 0.9:.3f}:d=0.6:alpha=1[cr]")
fc.append(f"[{ci + 1}:v]format=rgba,fade=t=in:st={b0 + 0.4:.3f}:d=0.8:alpha=1,fade=t=out:st={b1:.3f}:d=0.6:alpha=1[bg]")
fc.append(f"{prev}[cr]overlay=0:0:shortest=1[pc]")
prev = "[pc][bg]overlay=0:0:shortest=1"
fc.append(f"{prev},fade=t=in:st=0:d=1.0,fade=t=out:st={total - 1.2:.3f}:d=1.2,format=yuv420p[v]")
cmd = ["ffmpeg", "-v", "error", "-y", *inputs]
if a.music:
    cmd += ["-i", a.music]
    mi = len(segs) + 2
    fc.append(f"[{mi}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=1.5,"
              f"afade=t=out:st={total - 3:.3f}:d=3,loudnorm=I=-16:TP=-1.5[a]")
    maps = ["-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
else:
    maps = ["-map", "[v]"]
cmd += ["-filter_complex", ";".join(fc), *maps, "-c:v", "libx264", "-crf", "21", "-preset", "medium",
        "-movflags", "+faststart", a.out]
run(cmd)
print(f"built {a.out} ({total:.1f}s)")
