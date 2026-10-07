# Microduck emotions, ready to reuse

Fourteen emotions for the Microduck robot, made for the Microduck and Reachy Mini theater videos.
Each one is a motion and a sound designed together, beat by beat, with the beak opening on the sound.
This folder holds everything you need to replay them. It does not depend on anything else in the repo.

## What is here

- `emotions.json`: the index. One entry per emotion: name, gamepad button, duration, a one-line
  description, the keyframes file and the sound files.
- `keyframes/<name>.json`: the motion, as a timeline sampled every 0.1 s.
- `sounds/<name>.wav`: the sound the robot plays. 48 kHz, mono, 16 bit, peak at -3 dBFS.
  `_a`, `_b`, `_c` are alternative voicings of the same emotion: the robot picks one at random.
- Preview videos (simulation, with sound) are in the repo, not here: `../combined/showcase/clips/<name>.mp4`.

| emotion | button | length | what it does |
|---|---|---|---|
| sad | A, short | 7.5 s | The head droops while a low coo glides down, two slow silent shakes, back up. |
| devastated | A, long | 8.5 s | Sits at once with an alarmed call, the head droops and shakes on three sobs. Stays seated. |
| curious | Y, long | 3.0 s | "What? what?": the head tilts one way, then the other, on two rising chirps. |
| mmh | Y, short | 2.0 s | "What do you mean?": a small head tilt with a muffled rising "mmh?". |
| yes | LB, short | 1.5 s | One nod with one falling quack. |
| yes_fast | LB, long | 1.5 s | The same nod with a curt "wak". |
| no | RB, short | 1.8 s | One head shake with a two-note "no-ah". Three voicings. |
| defiant | RB, long | 2.2 s | "Says who?": beak up to one side with a quack, then to the other side. |
| angry | X, short | 2.6 s | Beak-up glare, four head snaps with a hard bark on each. Two voicings. |
| mock | X, long | 2.6 s | "Gnagnagnagna": beak up, the head rolling side to side. |
| excited | B, short | 3.4 s | Six faster and faster head swings, quacks climbing in pitch. |
| impatient | B, long | 2.6 s | "Come on!": four quick shakes, then the beak flicks up on a huff. |
| laugh | L3, short | 3.0 s | Beak up, the head wagging, one long "haaa" then short ha's dying out. |
| play_dead | L3, long | 7.5 s | Sits, goes limp, rolls onto its back, legs up, a dying quack. Needs a mat. |

The buttons are those of the robot build described below (emotion mode, short or long press).

## What an emotion is

An emotion is a timeline plus a wav.
The timeline gives, every 0.1 s from the trigger: head deltas, a body pose, the beak opening and an optional skill.
The wav starts at the trigger (t = 0; devastated is the one exception, see `sound_at_s`).

The timeline does not drive the leg motors.
It sits on top of the robot's own balance policy: the policy keeps the duck standing (or sitting),
and the timeline only offsets the head, tilts the body a little, opens the beak, or starts a trained skill (`sit`).
Play dead is the exception: after the sit it sends two scripted joint poses (see below).

## The keyframe format

`keyframes/<name>.json` = `{"keyframes": [...], "measured": {...}, "fps": 30}`.
`keyframes` is a list with one entry every 0.1 s:

| field | unit | meaning |
|---|---|---|
| `t` | s | Time since the trigger. |
| `neck` | rad | Neck pitch delta. Negative = the neck bends forward and down. The policies only follow the negative direction, about half of what is asked. On a standing real duck, keep it at or above -0.75 (devastated asks -1.5, but it is seated). |
| `head_pitch` | rad | Head pitch delta. Positive = beak down, negative = beak up. |
| `head_yaw` | rad | Head yaw delta. Positive = the beak turns to the duck's own left. About +-1 is usable. |
| `head_roll` | rad | Head roll delta. Positive = the head tilts to the duck's own left (from the front it looks like a tilt to the right). The joint stops at +-0.44. |
| `body_pitch` | rad | Body pose pitch. Positive = bow forward. Trained range +-0.26. |
| `body_z` | m | Body height offset. Negative = crouch. Trained range -0.025 to +0.010. Zero in all 14. |
| `twist` | m/s, m/s, rad/s | Walking command `[forward, left, turn left]`. Zero in all 14: nobody walks. |
| `skill` | text or null | A trained skill the duck is in. Only `"sit"` is used here (devastated, play_dead). Start it once, on the first frame where it appears. |
| `soften` | true / false | Gentle release (servo gain down to zero over 1 s, then torque off). False in all 14. |
| `relax` | true / false | Torque off at once. False in all 14. |
| `mouth` | 0 to 1 | Beak opening, 0 = closed. Already computed from the wav and already timed: use it as is. |

Rules that apply to every file:

- A missing field means 0, null or false. The three oldest files (sad, devastated, curious) have no `body_z`, `twist`, `soften` or `relax`.
- The head values are deltas from the robot's home pose, in radians, not absolute joint angles.
- Some files run past the emotion's end with neutral values (the simulation kept filming).
  Stop at `sound_at_s + duration_s`, both taken from `emotions.json`.
- `fps` is the frame rate of the simulation video (30), not the keyframe rate (every 0.1 s).
- `measured` is what the simulation saw for that render: drift, falls, joint extremes, and the beat times in `beats`.
  It is a record, not an input. Its `wav` path points into the author's workspace; the sound to play is the one in `emotions.json`.

Fields of `emotions.json` that are not obvious:

- `press`: `short` = released before 0.6 s, `long` = held 0.6 s (it fires at the threshold).
- `sound_at_s`: when the wav starts on the timeline. 0 for all emotions but devastated (0.3 s: that file starts 0.3 s before the press).
- `robot_note`: where the real robot differs from the file, and why. Read it before playing on a real duck.
- `pose_joints` (play_dead only): the dead pose. Two stages, at 1.8 s (legs straight: the seated duck rolls onto its back)
  and at 4.0 s (legs up). The targets are absolute joint angles in radians. Joints in `torque_off` hang free.
  The listed joints ramp from where they are over `ramp_s`, at servo gain `gain`, and hold. The balance policy is off from the first stage on.

## How to play one

### On a Microduck, with the film build

The robot side is `../runtime-pad-expressions.patch`: 29 commits for
[pollen-robotics/microduck](https://github.com/pollen-robotics/microduck), on top of its commit `2c61dcc`.

```bash
git clone https://github.com/pollen-robotics/microduck && cd microduck
git checkout -b pad-expressions 2c61dcc
git am /path/to/microduck_emotions/runtime-pad-expressions.patch
```

Build it and push it to the duck as the runtime's `docs/robot/dev-push.md` describes.
Then copy each wav into `/var/lib/robot/sounds/<name>/` on the duck (`no_a.wav`, `no_b.wav` and `no_c.wav` all go in `no/`).
`../install-on-duck.sh` is the author's script for both steps. It assumes his network and build paths, so read it before you use it.
Then, with a gamepad connected, tap D-pad Up to enter emotion mode and press the buttons from the table.
A script can also trigger them through the pad daemon's cue port (TCP 7777; a gamepad must still be connected):

```python
import json, socket
s = socket.create_connection(("<duck-ip>", 7777))
s.sendall(json.dumps({"express": "yes"}).encode() + b"\n")
print(s.recv(4096))  # {"ok": true, "duration": 1.5}
```

### On a Microduck with the stock runtime, or on any robot or simulator

The recipe is the same everywhere:

1. At `sound_at_s`, start the wav on any speaker.
2. Every control tick (Microduck runs at 50 Hz), interpolate the keyframes linearly at the current time and send:
   - the head: `neck`, `head_pitch`, `head_yaw`, `head_roll` (Microduck runtime: `robot.head`, fields `neck_pitch`, `head_pitch`, `head_yaw`, `head_roll`);
   - the body: `body_pitch`, `body_z` (`robot.pose`, fields `pitch`, `z`);
   - the beak: `mouth` (`robot.mouth`);
   - the skill: on the first frame where `skill` is `"sit"`, trigger the sit (`robot.do` with `sit_toggle`).
3. At the end, send zeros for the head and release the pose.

In a simulator without the Microduck balance policy, add the head deltas to the head joints' home angles and use them as position targets.
Same for the beak. If nothing in your sim takes a body-pose command, you can skip `body_pitch` and `body_z`: they are small bows and bobs.

One timing tip. The timeline was tuned on the real policy, which follows head commands about 0.25 to 0.4 s late,
and the sounds land on the head's real extremes. If your joints track their targets instantly,
start the motion about 0.3 s after the wav, or smooth the targets, to keep motion and sound in sync.

## Load one emotion in Python

Run from the repo root. Only the standard library is needed.

```python
import json
from pathlib import Path

root = Path("export")
index = json.loads((root / "emotions.json").read_text())
emo = next(e for e in index["emotions"] if e["name"] == "yes")
print(emo["name"], emo["button"], emo["press"], emo["duration_s"], "s:", emo["description"])
print("sounds:", emo["sounds"], "start at", emo["sound_at_s"], "s")

keys = json.loads((root / emo["keyframes"]).read_text())["keyframes"]
print("   t   neck  pitch    yaw   roll  body  mouth  skill")
for k in keys:
    print(f"{k['t']:4.1f} {k['neck']:+6.2f} {k['head_pitch']:+6.2f} {k['head_yaw']:+6.2f} "
          f"{k['head_roll']:+6.2f} {k['body_pitch']:+5.2f} {k['mouth']:5.2f}  {k.get('skill') or ''}")


def at(keys, t, field):
    """One field at time t (seconds), linearly interpolated. Missing fields count as 0."""
    if t <= keys[0]["t"]:
        return keys[0].get(field, 0.0)
    for a, b in zip(keys, keys[1:]):
        if t <= b["t"]:
            u = (t - a["t"]) / (b["t"] - a["t"])
            return a.get(field, 0.0) + u * (b.get(field, 0.0) - a.get(field, 0.0))
    return keys[-1].get(field, 0.0)


print("head_pitch at 0.25 s:", round(at(keys, 0.25, "head_pitch"), 3))
```

## Make new sounds in the robot's voice

`../quack.py` is a Python port of the robot's voice synthesizer. `Personality(4145077059)` is the voice of these sounds.
It needs numpy and scipy (tested with Python 3.9, numpy 2.0, scipy 1.13). Copy it next to your script, then:

```python
from quack import Personality, quack, write_wav
p = Personality(4145077059)
sig = quack(p, dur=1.0, contour=[(0.0, 300), (0.3, 250), (1.0, 120)], env=("expdecay", 0.02, 0.6))
write_wav("my_quack.wav", sig)  # 48 kHz mono, normalised to -3 dBFS
```

`contour` is a list of (time in s, pitch in Hz) points. `python quack.py` prints the voice's traits.
The module docstring lists the other options (envelopes, per-sound tweaks, sequences).

To make the beak follow a new sound, this is the recipe used for every `mouth` channel here.
It reproduces the shipped files to three decimals (devastated, the oldest, has no lag):

```python
import wave
import numpy as np

def mouth_from_wav(path, lag_s=0.16, step=0.02):
    """Beak opening 0..1 every `step` seconds: loudness in 20 ms windows, lightly smoothed, a bit late like the servo."""
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768.0
        win = int(w.getframerate() * step)
    n = len(x) // win
    rms = np.sqrt((x[: n * win].reshape(n, win) ** 2).mean(axis=1))
    rms = np.convolve(rms, np.ones(3) / 3, mode="same")
    env = np.clip(rms / (0.6 * rms.max()), 0.0, 1.0)
    return np.concatenate([np.zeros(round(lag_s / step)), env])
```

For laugh and mock, the syllables are 0.2 s apart, so the 0.1 s keyframes blur some of them.
The robot build uses a 0.05 s beak table for those two; this function at its default step gives you the crisp version.

## Licence

This repository has no licence file yet. Choosing one is the author's decision.
Until there is one, normal copyright applies: if you want to reuse these files in a project, open an issue and ask.
(The Microduck runtime and microduck_rl repositories are Apache-2.0. That does not cover this repository.)

## Contributing

Contributions are very welcome. For example: a new emotion in the same format (a keyframes file, a wav, an entry in `emotions.json`),
a player for another simulator or robot, or a video of these emotions on a real Microduck.

Designed by Rémi Fabre (Pollen Robotics) with Claude Code agents, September 2026.
