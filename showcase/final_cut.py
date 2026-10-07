#!/usr/bin/env python
"""The candidate FINAL social cut (Rémi, 2026-10-07): 13 emotions (laugh out, mock kept), sad first, play dead last,
every neighbour different in emotion and in background, "Carefree" under the quacks, the k / 13 counter, no end text.

    /Users/remi/microduck/.venv-mjlab/bin/python final_cut.py OUT_DIR [--dry] [--only EMOTION]

Every clip is rendered fresh by orbit_final.py (the shadow-box fix, no grain, 1.5x SSAA, CRF 10) with the camera paths of
THIS order, so the orbit flows from one shot into the next; one MuJoCo process at a time, about 3 GB, cached in
~/Videos/agentic_socials/emotions_final_2026-10/cache/<preset>/ (keyed on the camera path). Then compile.assemble with
near-lossless intermediates and a final encode tuned for dark scenes and Bluesky's 50 MB cap, and tryout.add_music.
"""
import json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BG = Path("/Users/remi/mujoco_scenes/projects/emotions_bg")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BG))
import compile as C  # noqa: E402
import tryout as T  # noqa: E402

PY = "/Users/remi/microduck/.venv-mjlab/bin/python"
CACHE = Path("/Users/remi/Videos/agentic_socials/emotions_final_2026-10/cache")
CUT = [  # (emotion, preset): Rémi's frame (sad, curious, yes, no, defiant, impatient, angry, excited, play dead) + mock, mmh, yes!, devastated
    ("sad", "forest"),               # his opener, on his pick
    ("curious", "night"),            # his pick: perks up, by the lantern
    ("no", "sim_grid"),              # v2: no, then yes (Rémi)
    ("yes", "studio"),
    ("defiant", "mountain_summit"),
    ("impatient", "desk"),
    ("angry", "sim_grid"),
    ("mock", "studio"),              # the teasing after the anger (kept instead of laugh)
    ("mmh", "forest"),               # "the interrogation thing", later in the video as he asked
    ("yes_fast", "mountain_summit"), # a quick "yes!" that tips into joy
    ("excited", "beach"),
    ("devastated", "night"),         # the crash before the end
    ("play_dead", "sim_grid"),       # last, for sure: game over, back on the simulator grid
]
# v2: clips Rémi called good in v1 are kept as rendered (renderer orbit_final-1, self-shadows and all); the others are
# re-rendered without self-shadow on the robot (orbit_final-2)
KEEP_V1 = {"defiant", "impatient", "yes_fast", "devastated"}
# v4: play dead's camera mirrored (Rémi): it swung to the duck's right and showed the back of the head as the beak opened
# wide at 0.3 s; now 195 -> 265 deg, from front-left (the open beak three-quarters on) to the left side (legs up, face on)
CAM_OVERRIDE = {"play_dead": dict(start=195, end=265)}
RENDERER = "orbit_final-2"      # v3 = v2's clips, only the music mix changes
TRACK = dict(file="Carefree.mp3", title="Carefree", credit=f'"Carefree" by {T.KM}',
             url="https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3")
MUSIC_DB = -21.0                 # v3: a touch louder
SOFT = os.environ.get("SHOWCASE_SOFT", "")


DUCK = dict(threshold=0.1, ratio=2, attack=20, release=300)     # v3: light, about 3 dB under a quack (tryout.py: 0.015 / 8 / 8 / 280)


def add_music(src, track, music_db, start, offset, out, duck=DUCK, bed_only=None):
    """tryout.add_music with a gentler sidechain: the music dips a few dB under each quack instead of vanishing (v2's
    deep ducking hid the music under sad's opening coo for 3 s, which sounded like a late start). bed_only: also write
    the ducked music alone, for checking."""
    import re
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                               capture_output=True, text=True).stdout)
    length = dur - start
    m = T.loudness(T.MUSIC / track["file"], af=f"atrim=start={offset}:duration={length}")
    gain = music_db - float(m["input_i"])
    ms = int(round(start * 1000))
    sc = f"sidechaincompress=threshold={duck['threshold']}:ratio={duck['ratio']}:attack={duck['attack']}:release={duck['release']}:makeup=1"
    fc = (f"[1:a]atrim=start={offset}:duration={length:.3f},asetpts=PTS-STARTPTS,aresample=48000,"
          f"aformat=channel_layouts=stereo,volume={gain:.2f}dB,afade=t=in:st=0:d=0.15,"
          f"afade=t=out:st={max(0.0, length - 2.4):.3f}:d=2.4,adelay={ms}|{ms},apad=whole_dur={dur:.3f}[m];"
          f"[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[q][qs];"
          f"[m][qs]{sc}[md];[md]asplit=2[md1][md2];"
          f"[q][md1]amix=inputs=2:normalize=0:duration=first[a]")
    mix = out.with_suffix(".mix.mkv")
    args = ["-i", src, "-i", T.MUSIC / track["file"], "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "pcm_s16le", mix]
    if bed_only:
        args += ["-map", "[md2]", "-c:a", "pcm_s16le", str(bed_only)]
    else:
        args[args.index("-filter_complex") + 1] = fc.replace(";[md]asplit=2[md1][md2]", "").replace("[md1]", "[md]")
    T.ff(*args)
    L = T.loudness(mix)
    af = (f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={L['input_i']}:measured_TP={L['input_tp']}:measured_LRA={L['input_lra']}"
          f":measured_thresh={L['input_thresh']}:offset={L['target_offset']}:linear=true,aresample=48000")
    T.ff("-i", mix, "-af", af, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out)
    mix.unlink()
    return out, None, gain


def main():
    out = Path(sys.argv[1])
    dry = "--dry" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    by_name = {o[0]: o for o in C.ORDER}
    for e, cam in CAM_OVERRIDE.items():
        n, a, b, _ = by_name[e]
        by_name[e] = (n, a, b, cam)
    C.ORDER = [by_name[e] for e, _ in CUT]
    paths = C.camera_paths()                     # continuous across THIS order's cuts
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for e, preset in CUT:
        d = CACHE / preset
        clip, camf = d / f"{e}.mp4", d / f"{e}.cam.json"
        key = json.dumps(dict(paths[e], preset=preset, renderer=RENDERER, soft=SOFT), sort_keys=True)
        ok = clip.exists() and camf.exists() and (camf.read_text() == key or (e in KEEP_V1 and "orbit_final-1" in camf.read_text()))
        print(f"{e:11s} {preset:16s} {'cached' if ok else 'render'}  cam {paths[e]}", flush=True)
        if dry or ok or (only and e != only):
            continue
        free = subprocess.run(["/usr/bin/memory_pressure", "-Q"], capture_output=True, text=True).stdout
        pct = int(free.rsplit(":", 1)[-1].strip().rstrip("%")) if "percentage" in free else 100
        if pct < 40:
            sys.exit(f"only {pct}% memory free: stopping before {e}")
        d.mkdir(parents=True, exist_ok=True)
        t = time.time()
        env = dict(os.environ, SHOWCASE_CAM=json.dumps(paths[e]), SHOWCASE_PRESET=preset)
        with open(d / f"{e}.log", "w") as log:
            subprocess.run([PY, str(HERE / "orbit_final.py"), e, str(d)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        camf.write_text(key)
        print(f"   rendered in {time.time() - t:.0f} s", flush=True)
    if dry or only:
        return
    for e, preset in CUT:
        subprocess.run(["cp", str(CACHE / preset / f"{e}.mp4"), str(raw / f"{e}.mp4")], check=True)
    C.END_TEXT, C.END_HOLD = False, 1.4          # no end text: the dead duck is held a moment, then the loop
    C.SEG_CRF = "8"
    C.FINAL_X264 = ["-crf", "16", "-preset", "slow", "-tune", "film", "-x264-params", "aq-mode=3",
                    "-maxrate", "8M", "-bufsize", "16M"]
    final, _ = C.assemble(raw, out)
    start = 0.0                                   # v2: the music starts on the first frame (Rémi)
    dst = out / "microduck_emotions_final.mp4"
    dst, web, gain = add_music(final, TRACK, MUSIC_DB, start, 0.0, dst, bed_only=out / "music_bed_ducked.wav")
    web2 = out / "microduck_emotions_final_page.mp4"     # the page copy, kinder to dark scenes than tryout's CRF 24
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(dst), "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264",
                    "-profile:v", "high", "-crf", "19", "-preset", "slow", "-tune", "film", "-x264-params", "aq-mode=3",
                    "-maxrate", "5M", "-bufsize", "10M", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(web2)], check=True)
    notes = dict(video=str(dst), page_copy=str(web2), music=TRACK["credit"], music_url=TRACK["url"],
                 music_enters_s=round(start, 2), scenes=CUT)
    json.dump(notes, open(out / "NOTES.json", "w"), indent=1)
    print(json.dumps(notes, indent=1))


if __name__ == "__main__":
    main()
