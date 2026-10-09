"""Write robot/emotions/: the files a Microduck plays with `robotctl robot do <name>`.

One `<name>.json` (keyframes) and one `<name>.wav` per emotion, to copy to /var/lib/robot/emotions/
on the robot. Made from keyframes/ and emotions.json, with what the real robot needs:

- each emotion starts at its sound and stops at its duration (devastated loses its 0.3 s lead-in);
- curious keeps only its two head tilts: the head-forward part made the real duck step forward;
- no and angry keep their first take (no_a, angry_a);
- play dead is left out: its dead pose needs a joint-level call the runtime does not have.

Run from the repo root: python3 robot/make_robot_set.py
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "robot" / "emotions"
FIELDS = ("neck", "head_pitch", "head_yaw", "head_roll", "body_pitch", "body_z", "mouth")
SKIP = {"play_dead"}
ROLL_ONLY = {"curious"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.iterdir():
        old.unlink()
    for e in json.loads((ROOT / "emotions.json").read_text())["emotions"]:
        if e["name"] in SKIP:
            continue
        start, end = e["sound_at_s"], e["sound_at_s"] + e["duration_s"]
        keys = []
        for k in json.loads((ROOT / e["keyframes"]).read_text())["keyframes"]:
            if not start - 1e-6 <= k["t"] <= end + 1e-6:
                continue
            out = {"t": round(k["t"] - start, 3)}
            out.update({f: k.get(f, 0.0) for f in FIELDS})
            if e["name"] in ROLL_ONLY:
                out["neck"] = out["head_pitch"] = 0.0
            out["skill"] = k.get("skill")
            keys.append(out)
        (OUT / f"{e['name']}.json").write_text(json.dumps({"keyframes": keys}, indent=1) + "\n")
        shutil.copyfile(ROOT / e["sounds"][0], OUT / f"{e['name']}.wav")
        print(f"{e['name']:<11} {keys[-1]['t']:4.1f} s  {len(keys)} keyframes")


if __name__ == "__main__":
    main()
