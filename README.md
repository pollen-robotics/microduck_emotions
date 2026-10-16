# microduck_emotions

An early prototype of emotional design for Microduck: 17 emotions, each a motion and a sound designed together.
Watch them in `previews/`.

The first 14 are bound to the gamepad in the robot build. Three later ones, `surprised`, `hello` and `sleepy`, were made
in simulation only and are not bound to a button yet (`"button": null`): every pad slot is taken.

## Files

- `emotions.json`: the list (name, duration, description, files, notes for the real robot).
- `keyframes/<name>.json`: the motion, one sample every 0.1 s.
- `sounds/<name>.wav`: the sound, played from `sound_at_s` (0 except devastated, 0.3 s).
- `robot/pad-expressions.patch`: the Microduck runtime code that plays them from the gamepad
  (applies on [pollen-robotics/microduck](https://github.com/pollen-robotics/microduck) commit `2c61dcc`).
- `quack.py`: the robot's voice synth in Python (numpy, scipy), to make new sounds.
- `design/new_emotions.py`: the recipe for `surprised`, `hello` and `sleepy` (head waypoints and quacks written together;
  `python design/new_emotions.py` rewrites their keyframes and wavs).
- `to_arena.py`: turns emotions into a performance for the
  [Microduck Arena](https://github.com/pollen-robotics/microduck-arena)'s "Got a Talent" stage.
- `preview.py`: renders a preview video in simulation (the Arena plays it, MuJoCo films it, the wav goes on top).

## Replay one

Interpolate the keyframes, send the head and body targets to your robot or simulation at that rate, and start the wav
at `sound_at_s`. Values are deltas from the home pose, in radians (body height in metres); a missing field means 0.

| field | meaning |
|---|---|
| `neck`, `head_pitch`, `head_yaw`, `head_roll` | head deltas; `head_pitch` > 0 = beak down, `head_yaw` > 0 = turn to the duck's left |
| `body_pitch`, `body_z` | body pose: > 0 = bow; < 0 = crouch |
| `skill` | `"sit"` when the duck sits (devastated, play dead, sleepy) |
| `mouth` | beak opening, 0 to 1, already synced to the sound |

```python
import json
e = json.load(open("emotions.json"))["emotions"][0]
for k in json.load(open(e["keyframes"]))["keyframes"]:
    print(k["t"], k["head_pitch"], k["head_yaw"], k["mouth"])
```

## Play them in the Microduck Arena

```bash
python to_arena.py sleepy                      # -> arena/sleepy.json
python to_arena.py yes no hello -o show.json   # a medley, one after the other (20 s at most)
arena score talent.onnx --event got-a-talent --timeline arena/sleepy.json
```

Any "Got a Talent" policy plays them: the head deltas go to the command's `head`, `skill: "sit"` to the sit flag, the
beak to the pad's RT (it opens the beak and quacks in the Arena's voice). The body pose and the wav are not played there.
`python preview.py sleepy --policy talent.onnx` makes the video, with the Arena installed in the same Python and ffmpeg.

Licence: Apache-2.0. Contributions are very welcome. The full design history (renderers, candidate sounds, notes) is
in the git tag `workshop-2026-10-07`.
