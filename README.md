# microduck_emotions

An early prototype of emotional design for Microduck: 15 emotions, each a motion and a sound designed together.
Watch them in `previews/`.

## Files

- `emotions.json`: the list (name, duration, description, files, notes for the real robot).
- `keyframes/<name>.json`: the motion, one sample every 0.1 s.
- `sounds/<name>.wav`: the sound, played from `sound_at_s` (0 except devastated, 0.3 s).
- `robot/emotions/`: the same emotions ready for a Microduck, one `<name>.json` and `<name>.wav` each (made by
  `robot/make_robot_set.py`; play dead is not in it, its dead pose needs a joint-level call the runtime lacks).
- `robot/pad-expressions.patch`: the older runtime code that played them from the gamepad
  (applies on [pollen-robotics/microduck](https://github.com/pollen-robotics/microduck) commit `2c61dcc`).
- `quack.py`: the robot's voice synth in Python (numpy, scipy), to make new sounds.

## Play one on a Microduck, or in its simulator

With a runtime that plays emotions ([pollen-robotics/microduck#384](https://github.com/pollen-robotics/microduck/pull/384),
in review), copy `robot/emotions/` to `/var/lib/robot/emotions/` on the robot and restart `robotd`; each emotion is
then a skill:

```
robotctl robot do sad
sudo robotctl pad bind y sad      # Y plays it
```

In the simulator (`scripts/duck-sim` in the runtime repo), copy them to `~/.cache/duck-sim/emotions/` before
starting it, then `scripts/duck-sim ctl robot do sad`.

## Replay one anywhere else

Interpolate the keyframes, send the head and body targets to your robot or simulation at that rate, and start the wav
at `sound_at_s`. Values are deltas from the home pose, in radians (body height in metres); a missing field means 0.

| field | meaning |
|---|---|
| `neck`, `head_pitch`, `head_yaw`, `head_roll` | head deltas; `head_pitch` > 0 = beak down, `head_yaw` > 0 = turn to the duck's left |
| `body_pitch`, `body_z` | body pose: > 0 = bow; < 0 = crouch |
| `skill` | `"sit"` when the duck sits (devastated, play dead) |
| `mouth` | beak opening, 0 to 1, already synced to the sound |

```python
import json
e = json.load(open("emotions.json"))["emotions"][0]
for k in json.load(open(e["keyframes"]))["keyframes"]:
    print(k["t"], k["head_pitch"], k["head_yaw"], k["mouth"])
```

Licence: Apache-2.0. Contributions are very welcome. The full design history (renderers, candidate sounds, notes) is
in the git tag `workshop-2026-10-07`.
