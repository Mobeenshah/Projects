"""Film effects for the vintage commercial.

  python3 fx.py dirt  SECONDS FPS  > raw gray frames on stdout (540x960, 128 = neutral)
  python3 fx.py audio SECONDS OUT.wav [reveal_s ...]  synthesised optical-track soundtrack
"""
import sys
import wave
import numpy as np
from scipy import signal

rng = np.random.default_rng(14)


def dirt(seconds, fps):
    W, H = 540, 960
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    scratch_x, scratch_life = rng.uniform(0, W), 0
    hair = None
    out = sys.stdout.buffer
    for n in range(int(seconds * fps)):
        f = np.full((H, W), 128.0, np.float32)
        for _ in range(rng.poisson(5)):                      # dust specks
            cx, cy, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 2.8)
            shade = -110 if rng.random() < 0.75 else 90
            m = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r))
            f += shade * m
        if scratch_life <= 0 and rng.random() < 0.05:        # long vertical scratch
            scratch_x, scratch_life = rng.uniform(40, W - 40), rng.integers(6, 30)
        if scratch_life > 0:
            scratch_x += rng.normal(0, 0.8); scratch_life -= 1
            f += 70 * np.exp(-((xx - scratch_x) / 0.7) ** 2) * (rng.random((H, 1)) > 0.08)
        if hair is None and rng.random() < 0.012:            # a hair caught in the gate
            t = np.linspace(0, 1, 60)
            hx = rng.uniform(60, W - 60) + np.cumsum(rng.normal(0, 2.5, 60))
            hy = rng.uniform(60, H - 200) + t * rng.uniform(80, 200)
            hair = [hx, hy, rng.integers(6, 16)]
        if hair is not None:
            for px, py in zip(hair[0], hair[1]):
                f += -120 * np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / 1.4)
            hair[2] -= 1
            if hair[2] <= 0:
                hair = None
        out.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())


SR = 44100


def env(n, a, d, s, r, sr=SR):
    a, d, r = int(a * sr), int(d * sr), int(r * sr)
    sus = max(0, n - a - d - r)
    e = np.concatenate([np.linspace(0, 1, a, False), np.linspace(1, s, d, False),
                        np.full(sus, s), np.linspace(s, 0, r)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def harmonium(freq, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
    x = np.zeros(n)
    for det in (1.0, 1.004, 0.997):                         # reeds, slightly detuned
        ph = 2 * np.pi * np.cumsum(freq * det * vib) / SR
        x += signal.sawtooth(ph) * 0.33
    b, a = signal.butter(2, [200, 2600], btype="band", fs=SR)
    return signal.lfilter(b, a, x) * env(n, 0.04, 0.1, 0.8, 0.12)


def thump(dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 55 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def slap(dur=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    b, a = signal.butter(2, [600, 3500], btype="band", fs=SR)
    tone = np.sin(2 * np.pi * 420 * t) * 0.6
    return (signal.lfilter(b, a, rng.normal(0, 1, n)) * 0.7 + tone) * np.exp(-t * 35)


def bells(dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for _ in range(26):                                     # cluster of small truck bells
        start = int(rng.uniform(0, 0.7) * SR)
        f = rng.uniform(2400, 5200)
        tt = t[: n - start]
        x[start:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * rng.uniform(5, 12)) * rng.uniform(0.2, 0.6)
    return x / 6


def audio(seconds, out, reveals):
    n = int(seconds * SR)
    mix = np.zeros(n)
    bpm = 104; beat = 60 / bpm
    sa = 261.63
    # raag-flavoured melody (Kafi-ish): scale degrees in semitones
    deg = {"S": 0, "R": 2, "g": 3, "m": 5, "P": 7, "D": 9, "n": 10, "S'": 12, "R'": 14}
    phrase = [("S", 1), ("R", .5), ("g", .5), ("m", 1), ("P", 1), ("D", .5), ("n", .5), ("S'", 1.5), ("-", .5),
              ("n", .5), ("D", .5), ("P", 1), ("m", .5), ("g", .5), ("R", 1), ("S", 1.5), ("-", .5),
              ("P", .5), ("P", .5), ("D", .5), ("n", .5), ("S'", 1), ("R'", .5), ("S'", .5), ("n", 1), ("D", 1),
              ("P", .5), ("m", .5), ("g", .5), ("R", .5), ("S", 2)]
    t0 = 0.6
    while t0 < seconds - 1:
        for note, beats in phrase:
            d = beats * beat
            if note != "-" and t0 + d < seconds:
                f = sa * 2 ** (deg[note] / 12)
                s = harmonium(f, d * 0.98)
                i = int(t0 * SR); mix[i:i + len(s)] += s[: n - i] * 0.30
                drone = harmonium(sa / 2, d) * 0.09               # Sa drone underneath
                mix[i:i + len(drone)] += drone[: n - i]
            t0 += d
    # dholak: dha . ge na | ti na ka dhin
    pat = [(0, "t"), (1.5, "t"), (2, "s"), (2.75, "s"), (3, "s"), (3.5, "t")]
    t0 = 0.6
    th, sl = thump(), slap()
    while t0 < seconds - 1:
        for off, kind in pat:
            i = int((t0 + off * beat) * SR)
            s = th * 0.55 if kind == "t" else sl * 0.35
            if i < n:
                mix[i:i + len(s)] += s[: n - i]
        t0 += 4 * beat
    for r in [0.1] + reveals:
        b = bells(); i = int(r * SR)
        mix[i:i + len(b)] += b[: n - i]
    # fade music at the end
    fade = np.ones(n); k = int(1.8 * SR); fade[-k:] = np.linspace(1, 0, k)
    mix *= fade
    # optical-track character: band-limit, soft saturation, wow & flutter
    t = np.arange(n) / SR
    wow = (0.0018 * np.sin(2 * np.pi * 0.7 * t) + 0.0007 * np.sin(2 * np.pi * 6.3 * t)) * SR
    mix = np.interp(np.arange(n) + wow, np.arange(n), mix)
    b, a = signal.butter(2, [180, 4200], btype="band", fs=SR)
    mix = np.tanh(signal.lfilter(b, a, mix) * 1.6) * 0.6
    # projector: 18 fps shutter clatter + hiss + mains hum + crackle
    proj = np.zeros(n)
    click = np.exp(-np.arange(300) / 40) * rng.normal(0, 1, 300)
    for k in range(int(seconds * 18)):
        i = int(k / 18 * SR); proj[i:i + 300] += click[: n - i] * rng.uniform(0.5, 1)
    b, a = signal.butter(2, [800, 6000], btype="band", fs=SR)
    proj = signal.lfilter(b, a, proj) * 0.05
    hiss = signal.lfilter(*signal.butter(1, 3000, fs=SR), rng.normal(0, 1, n)) * 0.012
    hum = 0.006 * np.sin(2 * np.pi * 50 * t)
    crackle = (rng.random(n) > 0.9993) * rng.normal(0, 0.25, n)
    full = mix + proj + hiss + hum + crackle
    full = full / np.abs(full).max() * 0.89
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((full * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    if sys.argv[1] == "dirt":
        dirt(float(sys.argv[2]), int(sys.argv[3]))
    else:
        audio(float(sys.argv[2]), sys.argv[3], [float(x) for x in sys.argv[4:]])
