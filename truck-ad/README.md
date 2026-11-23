# Vintage Pakistani Truck Ad — "The Grand Trunk King" (1972-style)

A 1970s Pakistani print ad and film commercial built around a 3D-printed truck-art model.
"Shaheen Goods Transport Co." is a made-up company created for the ad.

| Output | What it is |
|---|---|
| `output/shaheen_truck_ad_1972.jpg` | 1880×2480 print ad, aged like a scanned original |
| `output/shaheen_truck_commercial_1972.mp4` | 29 s vertical (9:16) film-style commercial with soundtrack |

## How it's made
1. `scripts/cutout.py` – cuts the truck out of the table photo (colour seed + GrabCut).
2. `scripts/halftone.py` – reprints it as a CMYK offset halftone with press misregistration.
3. `poster/ad.html` – layout (truck-art border, Nastaliq Urdu, period type), rendered by `scripts/render.js` (Playwright).
4. `scripts/age.py` – paper stock, ink wear, fold creases, foxing, water stain, chipped edges.
5. `film/build.sh` + `film/fx.py` – grades the phone video as faded 18 fps film (gate weave, flicker,
   grain, dust, scratches, hairs), adds title cards, and synthesises a harmonium + dholak + truck-bell
   soundtrack with projector clatter.

Fonts: Noto Nastaliq Urdu, Abril Fatface, Alfa Slab One, Oswald, Playfair Display, Lobster (all SIL OFL, via Fontsource).
