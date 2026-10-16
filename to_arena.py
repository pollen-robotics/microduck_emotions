"""Turn emotions into a Microduck Arena performance: a `timeline.json` for the "Got a Talent" event.

    python to_arena.py sad                        # one emotion -> arena/sad.json
    python to_arena.py yes no curious -o show.json  # a medley, played one after the other
    python to_arena.py --all                      # every emotion, one timeline each, in arena/

Play one in the Arena (https://github.com/pollen-robotics/microduck-arena) with any talent policy:

    arena score talent.onnx --event got-a-talent --timeline arena/sad.json

What carries over: the four head deltas (neck, head_pitch, head_yaw, head_roll) go to the command's
`head` group, `skill: "sit"` to the sit flag `twist[0]`, and the beak (`mouth`) to the pad's RT, which
opens the beak and quacks with the Arena's voice. The body pose (`body_pitch`, `body_z`) has no slot
the talent policy reads, so it is dropped; the robot-only fields (`relax`, `soften`) too. The wav
files are not played by the Arena: lay them over the video at `sound_at_s` (see `preview.py`).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
HEAD = ("neck", "head_pitch", "head_yaw", "head_roll")
MAX_S = 20.0  # the event's time limit
MAX_KEYFRAMES = 1000


def load(name: str) -> tuple[dict, list[dict]]:
    index = json.loads((HERE / "emotions.json").read_text(encoding="utf-8"))
    for e in index["emotions"]:
        if e["name"] == name:
            return e, json.loads((HERE / e["keyframes"]).read_text(encoding="utf-8"))["keyframes"]
    raise SystemExit(f"no emotion named {name!r}; known: {', '.join(e['name'] for e in index['emotions'])}")


def sample(frames: list[dict], step: float) -> list[tuple[float, list[float], bool, float]]:
    """(t, head, sitting, mouth) every `step` seconds, the head and beak interpolated linearly."""
    t = np.array([f["t"] for f in frames])
    grid = np.arange(0.0, t[-1] + 1e-9, step)
    cols = {k: np.interp(grid, t, [f.get(k) or 0.0 for f in frames]) for k in (*HEAD, "mouth")}
    sit = [frames[int(np.searchsorted(t, g + 1e-9, "right")) - 1].get("skill") == "sit" for g in grid]
    return [(float(g), [float(cols[k][i]) for k in HEAD], sit[i], float(cols["mouth"][i]))
            for i, g in enumerate(grid)]


def build(names: list[str], lead_s: float, gap_s: float, step: float, stay_seated: bool) -> dict:
    keyframes, clock, sitting = [], lead_s, False
    keyframes.append({"t": 0.0})
    for n, name in enumerate(names):
        _, frames = load(name)
        for t, head, sit, mouth in sample(frames, step):
            kf = {"t": round(clock + t, 3), "head": [round(v, 4) for v in head]}
            if sit:
                kf["twist"] = [1, 0, 0]
            if mouth > 0.0:
                kf["triggers"] = [round(min(mouth, 1.0), 3), 0]
            keyframes.append(kf)
            sitting = sit
        clock += frames[-1]["t"] + step
        last = n == len(names) - 1
        if sitting and not (last and stay_seated):
            # Stand up again before the next one: the sit-stand takes about 2 s.
            keyframes.append({"t": round(clock, 3)})
            clock += 2.0
        if not last:
            keyframes.append({"t": round(clock, 3)})
            clock += gap_s
    duration = round(clock + 1.0, 3)
    if duration > MAX_S:
        raise SystemExit(f"{' + '.join(names)} lasts {duration:g} s; the Arena plays at most {MAX_S:g} s")
    if len(keyframes) > MAX_KEYFRAMES:
        raise SystemExit(f"{len(keyframes)} keyframes; use a coarser --step")
    # The Arena holds each keyframe until the next one, so identical neighbours add nothing.
    slim = [keyframes[0]]
    for kf in keyframes[1:]:
        if {k: v for k, v in kf.items() if k != "t"} != {k: v for k, v in slim[-1].items() if k != "t"}:
            slim.append(kf)
    return {"timeline_version": 1, "duration_s": duration, "keyframes": slim}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("names", nargs="*", help="emotions to play, in order")
    ap.add_argument("--all", action="store_true", help="one timeline per emotion, into arena/")
    ap.add_argument("-o", "--out", type=Path, help="output file (default arena/<names>.json)")
    ap.add_argument("--lead", type=float, default=1.5, help="seconds standing still before the first one")
    ap.add_argument("--gap", type=float, default=1.0, help="seconds between two emotions")
    ap.add_argument("--step", type=float, default=0.05, help="keyframe spacing in seconds")
    ap.add_argument("--stay-seated", action="store_true", help="do not stand up after a final seated emotion")
    args = ap.parse_args()

    if args.all:
        index = json.loads((HERE / "emotions.json").read_text(encoding="utf-8"))
        jobs = [([e["name"]], HERE / "arena" / f"{e['name']}.json") for e in index["emotions"]]
    elif args.names:
        jobs = [(args.names, args.out or HERE / "arena" / f"{'+'.join(args.names)}.json")]
    else:
        ap.error("name at least one emotion, or --all")
    for names, out in jobs:
        timeline = build(names, args.lead, args.gap, args.step, args.stay_seated)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(timeline, indent=1) + "\n", encoding="utf-8")
        print(f"{out.relative_to(HERE) if out.is_relative_to(HERE) else out}: "
              f"{timeline['duration_s']:g} s, {len(timeline['keyframes'])} keyframes")


if __name__ == "__main__":
    main()
