#!/usr/bin/env bash
# Build the vintage 1970s-style commercial from the truck video.
# usage: film/build.sh SOURCE.mp4 TITLE_CARD.jpg MESSAGE_CARD.jpg POSTER.jpg OUT.mp4 WORKDIR
set -euo pipefail
SRC=$1; TITLE=$2; MSG=$3; POSTER=$4; OUT=$5; WK=$6
HERE=$(cd "$(dirname "$0")" && pwd)
FPS=18
mkdir -p "$WK"

# gate weave + flicker + faded Kodachrome grade + grain + vignette
LOOK="scale=1120:1992,crop=1080:1920:x='20+3*sin(n*0.9)+2*(random(1)-0.5)':y='36+3*cos(n*1.3)+2*(random(2)-0.5)',\
eq=contrast=1.07:saturation=0.80:brightness='0.012*sin(n*2.7)+0.025*(random(0)-0.5)':eval=frame,\
colorbalance=rs=.07:gs=.02:bs=-.09:rm=.05:bm=-.06:rh=.04:bh=-.08,\
curves=r='0/0.07 0.5/0.55 1/0.95':g='0/0.06 0.5/0.51 1/0.93':b='0/0.09 0.5/0.45 1/0.84',\
noise=alls=13:allf=t,vignette=PI/4.6,format=yuv420p"

clip() { # name start dur
  ffmpeg -v error -y -ss "$2" -t "$3" -i "$SRC" -an -vf "fps=$FPS,$LOOK" -c:v libx264 -crf 16 -preset fast "$WK/$1.mp4"
}
still() { # name image dur extra-filter
  ffmpeg -v error -y -loop 1 -t "$3" -framerate $FPS -i "$2" -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x262320,${4:-null},$LOOK" \
    -c:v libx264 -crf 16 -preset fast "$WK/$1.mp4"
}

still s1_title "$TITLE" 3.5
clip  s2_orbit 0.0 5.0
clip  s3_side 19.5 4.0
clip  s4_face 43.0 1.8
still s5_msg  "$MSG" 2.5
clip  s6_rear 11.0 5.0
clip  s7_shelf 45.5 2.5
# end card: the aged poster, slow push-in
ffmpeg -v error -y -loop 1 -framerate $FPS -t 5 -i "$POSTER" -vf "scale=2160:-2,pad=2160:3840:(ow-iw)/2:(oh-ih)/2:color=0x262320,\
zoompan=z='1+0.0016*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=$FPS,$LOOK" -c:v libx264 -crf 16 -preset fast "$WK/s8_poster.mp4"

ls "$WK"/s*.mp4 | sort | sed "s/^/file '/;s/$/'/" > "$WK/list.txt"
ffmpeg -v error -y -f concat -safe 0 -i "$WK/list.txt" -c copy "$WK/base.mp4"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WK/base.mp4")

# dust & scratches layer (luma overlay only)
python3 "$HERE/fx.py" dirt "$DUR" $FPS | ffmpeg -v error -y -f rawvideo -pix_fmt gray -s 540x960 -r $FPS -i - \
  -vf "scale=1080:1920,format=yuv420p" -c:v libx264 -crf 12 -preset fast "$WK/dirt.mp4"

# bells ring at the open, the tailgate reveal and the end card
REVEAL=$(python3 -c "print(3.5+5+4+1.8+2.5+0.3)")
END=$(python3 -c "print($DUR-5+0.2)")
python3 "$HERE/fx.py" audio "$DUR" "$WK/sound.wav" "$REVEAL" "$END"

ffmpeg -v error -y -i "$WK/base.mp4" -i "$WK/dirt.mp4" -i "$WK/sound.wav" \
  -filter_complex "[0:v][1:v]blend=c0_expr='A+(B-128)*0.9':c1_expr=A:c2_expr=A,format=yuv420p[v]" \
  -map "[v]" -map 2:a -c:v libx264 -crf 25 -preset medium -c:a aac -b:a 160k -movflags +faststart -shortest "$OUT"
echo "built $OUT ($DUR s)"
