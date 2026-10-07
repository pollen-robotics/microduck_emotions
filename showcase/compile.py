#!/usr/bin/env python
"""The showcase compilation: every shipped emotion one after another, vertical 1080x1920, for social media.

    /Users/remi/microduck/.venv-mjlab/bin/python compile.py OUT_DIR [--no-render]

1. renders each emotion again with orbit.py, the camera continuing across the cuts (each clip starts at the azimuth the
   previous one ended on and the sweep swings back and forth across the duck's front), 3 renders at a time;
2. trims each clip (ORDER), lays the caption on it (counter + name), cuts them together, freezes the last frame of
   play dead under an end card, normalises the loudness to -14 LUFS (true peak -1 dB);
3. writes OUT_DIR/microduck_emotions_compilation.mp4 (1080x1920, H.264 High, AAC 48 kHz, faststart) and a 720x1280
   copy for the web page.
"""
import json, math, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
PY = "/Users/remi/microduck/.venv-mjlab/bin/python"
W, H, FPS = 1080, 1920, 30
FONT = "/System/Library/Fonts/Avenir Next.ttc"          # index 8 Heavy, 2 Demi Bold, 5 Medium
INFO = json.load(open(HERE / "emotions.json"))

# (emotion, trim start s, trim end s, camera). The order is the story: the hook, a comic snap, a quick-fire run of
# answers, the irritation that builds to anger, the release into teasing, laughter and joy, then the come-down and the
# punchline. See README.md.
ORDER = [
    ("devastated", 0.10, 7.00, dict(start=110, end=180)),      # side (the collapse reads) to the front; cut before the rise
    ("curious", 0.0, 3.00, None),
    ("mmh", 0.0, 2.00, None),
    ("yes", 0.0, 1.25, None),
    ("no", 0.0, 1.60, None),
    ("yes_fast", 0.0, 1.25, None),
    ("defiant", 0.0, 2.20, None),
    ("impatient", 0.0, 2.60, None),
    ("angry", 0.0, 2.60, None),
    ("mock", 0.0, 2.60, None),
    ("laugh", 0.0, 3.00, None),
    ("excited", 0.0, 3.40, None),
    ("sad", 0.0, 5.40, dict(start=110, end=165)),               # a new angle for the mood change; cut before the rise
    ("play_dead", 0.0, 7.50, dict(start=165, end=95)),          # swings back to the side: legs up in profile
]
SWING = (150.0, 210.0, 10.0)        # the pendulum between the explicit shots: bounds (deg) and speed (deg/s)
END_HOLD = 2.6                      # the end card on the frozen last frame (s)
END_TEXT = True                     # False: the last frame is simply held (no title, no dim)
SEG_CRF = "14"                      # intermediate segments and master (near-lossless with "8")
FINAL_X264 = ["-crf", "17", "-preset", "slow"]   # e.g. aq-mode 3 and a maxrate for dark scenes and size caps


def camera_paths():
    paths, az, sign = {}, 180.0, 1.0
    lo, hi, speed = SWING
    for name, a, b, cam in ORDER:
        if cam is not None:
            paths[name] = dict(cam, orbit_s=b, push=0)
            az = cam["end"]
            continue
        arc = min(30.0, max(14.0, speed * (b - a)))
        if not lo <= az + sign * arc <= hi:
            sign = -sign
        paths[name] = dict(start=az, end=az + sign * arc, orbit_s=b, push=0)
        az += sign * arc
    return paths


def render_clips(raw):
    raw.mkdir(parents=True, exist_ok=True)
    paths = camera_paths()

    def one(name):
        env = dict(os.environ, SHOWCASE_CAM=json.dumps(paths[name]))
        with open(raw / f"{name}.log", "w") as log:
            subprocess.run([PY, str(HERE / "orbit.py"), name, str(raw)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        return name

    with ThreadPoolExecutor(3) as ex:          # 3 at a time: each MuJoCo process takes 2-2.6 GB
        for n in ex.map(one, [o[0] for o in ORDER]):
            print("rendered", n, paths[n], flush=True)


# ---------------------------------------------------------------------------------------------------------------
def shadowed(img, xy, text, font, fill, anchor="ms", blur=10, alpha=150):
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0], xy[1] + 4), text, font=font, fill=(0, 0, 0, alpha), anchor=anchor)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(img).text(xy, text, font=font, fill=fill, anchor=anchor)


def caption(path, k, n, title):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadowed(img, (W // 2, 228), f"{k} / {n}", ImageFont.truetype(FONT, 40, index=2), (255, 255, 255, 200), blur=6)
    shadowed(img, (W // 2, 330), title, ImageFont.truetype(FONT, 104, index=8), (255, 255, 255, 255))
    img.save(path)


def end_frames(last_png, out_mp4, seconds=END_HOLD):
    base = Image.open(last_png).convert("RGBA")
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadowed(card, (W // 2, 560), "Microduck", ImageFont.truetype(FONT, 132, index=8), (255, 255, 255, 255))
    shadowed(card, (W // 2, 670), f"{len(ORDER)} emotions", ImageFont.truetype(FONT, 62, index=2), (255, 255, 255, 235), blur=6)
    # labels only: any sentence on screen in a public post must be Rémi's own words (the socials repo's rule)
    frames = []
    if not END_TEXT:
        for i in range(int(round(seconds * FPS))):
            frames.append(np.asarray(base.convert("RGB")))
        import imageio
        imageio.mimwrite(str(out_mp4), frames, fps=FPS, codec="libx264", pixelformat="yuv420p", macro_block_size=8,
                         output_params=["-crf", SEG_CRF])
        return
    for i in range(int(round(seconds * FPS))):
        u = min(1.0, i / (0.5 * FPS))
        e = 0.5 - 0.5 * math.cos(math.pi * u)
        f = base.copy()
        f.alpha_composite(Image.new("RGBA", (W, H), (8, 12, 20, int(110 * e))))
        c = card.copy()
        c.putalpha(c.getchannel("A").point(lambda v: int(v * e)))
        f.alpha_composite(c)
        frames.append(np.asarray(f.convert("RGB")))
    import imageio
    imageio.mimwrite(str(out_mp4), frames, fps=FPS, codec="libx264", pixelformat="yuv420p", macro_block_size=8,
                     output_params=["-crf", "14"])


def ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *map(str, args)], check=True)


def assemble(raw, out):
    seg = out / "segments"
    seg.mkdir(parents=True, exist_ok=True)
    n = len(ORDER)
    parts = []
    for k, (name, a, b, _) in enumerate(ORDER, 1):
        cap = seg / f"{k:02d}_{name}_caption.png"
        caption(cap, k, n, INFO[name]["title"])
        dst = seg / f"{k:02d}_{name}.mkv"
        ln = b - a
        ff("-ss", f"{a:.3f}", "-t", f"{ln:.3f}", "-i", raw / f"{name}.mp4", "-loop", "1", "-t", f"{ln:.3f}", "-i", cap,
           "-filter_complex", "[1:v]format=rgba,fade=in:st=0:d=0.15:alpha=1[c];[0:v][c]overlay=0:0:shortest=1,format=yuv420p[v];"
           f"[0:a]aresample=48000,aformat=channel_layouts=stereo,afade=in:d=0.008,afade=out:st={ln - 0.012:.3f}:d=0.012[a]",
           "-map", "[v]", "-map", "[a]", "-r", FPS, "-c:v", "libx264", "-crf", SEG_CRF, "-preset", "medium", "-c:a", "pcm_s16le", dst)
        parts.append(dst)
    # the end card: the last frame of the last clip (without its caption), frozen, with the title fading in; silent
    last = seg / "last.png"
    name, a, b, _ = ORDER[-1]
    last.unlink(missing_ok=True)
    ff("-ss", f"{b - 0.2:.3f}", "-i", raw / f"{name}.mp4", "-t", "0.2", "-update", "1", last)   # keeps the last one
    assert last.exists()
    endv = seg / "end_silent.mp4"
    end_frames(last, endv)
    end = seg / f"{n + 1:02d}_end.mkv"
    ff("-i", endv, "-f", "lavfi", "-t", END_HOLD, "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a",
       "-c:v", "libx264", "-crf", SEG_CRF, "-c:a", "pcm_s16le", "-shortest", end)
    parts.append(end)
    master = out / "master.mkv"
    ins = sum([["-i", p] for p in parts], [])
    fc = "".join(f"[{i}:v][{i}:a]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1:a=1[v][a]"
    ff(*ins, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", SEG_CRF, "-c:a", "pcm_s16le", master)
    # loudness: two-pass loudnorm to -14 LUFS integrated, -1 dBTP
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(master), "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr).group(0))
    ln_af = (f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
             f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    final = out / "microduck_emotions_compilation.mp4"
    ff("-i", master, "-af", ln_af, "-c:v", "libx264", "-profile:v", "high", *FINAL_X264, "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", final)
    web = out / "microduck_emotions_compilation_720.mp4"
    ff("-i", final, "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264", "-profile:v", "high", "-crf", "24", "-maxrate", "2.4M",
       "-bufsize", "4.8M", "-preset", "slow", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", web)
    print("loudness in:", m["input_i"], "LUFS, true peak", m["input_tp"], "dB")
    return final, web


if __name__ == "__main__":
    out = Path(sys.argv[1])
    raw = out / "raw"
    if "--no-render" not in sys.argv:
        render_clips(raw)
    final, web = assemble(raw, out)
    for f in (final, web):
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "csv=p=0", str(f)],
                           capture_output=True, text=True).stdout.strip()
        print(f, d)
