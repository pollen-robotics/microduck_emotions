#!/usr/bin/env python
"""Rémi's cut for socials, from the choices saved on the emotions page (the cut builder, db document cut/choice).

    /Users/remi/microduck/.venv-mjlab/bin/python cut.py CHOICE.json OUT_DIR [--dry]

CHOICE.json (as the page saves it): order (14 emotion ids), scenes {emotion: night | mountain_summit | beach | forest |
desk | studio | sim_grid | original}, off [emotions left out], music (Fluffing_a_Duck | Carefree | Sneaky_Snitch |
Life_of_Riley | Wallpaper | none), note.

Clips come from mujoco-scenes-df's per-scene cache (~/Videos/agentic_socials/emotions_backgrounds_2026-10/cache,
rendered by ~/mujoco_scenes/projects/emotions_bg/orbit_bg.py with the compilation's original camera path per emotion);
a missing (scene, emotion) pair is rendered there, one MuJoCo process at a time (about 2.5 GB, a minute each).
"original" = the slate showcase clip (combined/showcase/clips). Caveat (mujoco-scenes-df): cached clips keep the camera
path of the ORIGINAL order, so under a new order the orbit's swing can jump at a cut (most visible between two long
clips); if Rémi notices, re-render those emotions with the new order's paths (a new cache key). Then compile.assemble (captions k / n, end card) and the
music bed of tryout.py (enters with the second emotion, ducked under the quacks, -14 LUFS). --dry lists what it would do.
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BG = Path("/Users/remi/mujoco_scenes/projects/emotions_bg")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BG))
import compile as C  # noqa: E402
import tryout as T  # noqa: E402   (shares this compile module)

CACHE = T.OUT / "cache"
SLATE = HERE.parent / "combined" / "showcase" / "clips"
KM = T.KM
TRACKS = {k: dict(file=f"{k}.mp3", title=k.replace("_", " "), credit=f'"{k.replace("_", " ")}" by {KM}',
                  url=f"https://incompetech.com/music/royalty-free/mp3-royaltyfree/{k.replace('_', '%20')}.mp3")
          for k in ("Fluffing_a_Duck", "Carefree", "Sneaky_Snitch", "Life_of_Riley", "Wallpaper")}
MUSIC_DB = -22.0


def preset_of(scene, emotion):
    if scene == "night" and emotion in ("sad", "play_dead"):
        return "night:lantern_far"              # play dead rolls onto the lantern at its default spot
    return scene


def main():
    choice = json.load(open(sys.argv[1]))
    out = Path(sys.argv[2])
    dry = "--dry" in sys.argv
    by_name = {o[0]: o for o in C.ORDER}
    paths_orig = C.camera_paths()               # the cached clips were rendered with these camera paths
    keep = [e for e in choice["order"] if e not in set(choice.get("off", []))]
    plan = []
    for e in keep:
        scene = choice["scenes"].get(e, "original")
        if scene == "original":
            plan.append((e, "original", SLATE / f"{e}.mp4", True))
            continue
        p = preset_of(scene, e)
        d = CACHE / p.replace(":", "_")
        clip, camf = d / f"{e}.mp4", d / f"{e}.cam.json"
        cam = json.dumps(dict(paths_orig[e], render_version=2), sort_keys=True)
        ok = clip.exists() and camf.exists() and camf.read_text() == cam
        plan.append((e, p, clip, ok))
    for e, p, clip, ok in plan:
        print(f"{e:11s} {p:18s} {'cached' if ok else 'TO RENDER'}")
    if dry:
        return
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for e, p, clip, ok in plan:
        if not ok:
            free = subprocess.run(["/usr/bin/memory_pressure", "-Q"], capture_output=True, text=True).stdout
            pct = int(free.rsplit(":", 1)[-1].strip().rstrip("%")) if "percentage" in free else 100
            if pct < 40:
                sys.exit(f"only {pct}% memory free: not rendering {e} on {p}")
            clip.parent.mkdir(parents=True, exist_ok=True)
            t = time.time()
            env = dict(os.environ, SHOWCASE_CAM=json.dumps(paths_orig[e]), SHOWCASE_PRESET=p)
            with open(clip.parent / f"{e}.log", "w") as log:
                subprocess.run([T.PY, str(BG / "orbit_bg.py"), e, str(clip.parent)], env=env, stdout=log,
                               stderr=subprocess.STDOUT, check=True)
            (clip.parent / f"{e}.cam.json").write_text(json.dumps(dict(paths_orig[e], render_version=2), sort_keys=True))
            print(f"rendered {e} on {p} in {time.time() - t:.0f} s", flush=True)
        shutil.copy(clip, raw / f"{e}.mp4")
    C.ORDER = [by_name[e] for e in keep]
    final, _ = C.assemble(raw, out)             # captions k / n, end card, quacks at -14 LUFS
    music = choice.get("music", "none")
    notes = dict(scenes=[(e, p) for e, p, *_ in plan], music=None, video=str(final), note=choice.get("note", ""))
    if music != "none":
        start = C.ORDER[0][2] - C.ORDER[0][1]   # the music enters with the second emotion (the snap after the hook)
        dst = out / "microduck_emotions_cut.mp4"
        dst, web, gain = T.add_music(final, TRACKS[music], MUSIC_DB, start, 0.0, dst)
        notes.update(video=str(dst), web=str(web), music=TRACKS[music]["credit"], music_url=TRACKS[music]["url"],
                     music_enters_s=round(start, 2))
    json.dump(notes, open(out / "NOTES.json", "w"), indent=1)
    print(json.dumps(notes, indent=1))


if __name__ == "__main__":
    main()
