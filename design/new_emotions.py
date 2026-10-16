"""Three more emotions: surprised, hello and sleepy. One recipe per emotion, motion and sound written together.

    python design/new_emotions.py            # writes keyframes/<name>.json and sounds/<name>.wav

Each emotion is a list of head and body waypoints (eased from one to the next, so the policy gets smooth
targets) plus the quacks that land on its beats, made with `quack.py` in this robot's own voice
(seed 4145077059, pitch centre 238 Hz). The beak (`mouth`) is computed from the wav with the recipe
the 14 first emotions used: loudness in 20 ms windows, lightly smoothed, 0.16 s late like the servo.

Timing: the policy follows head commands 0.25 to 0.4 s late, so a pose is commanded about 0.25 s
before the quack that goes with it.

Robot limits kept: head_roll within +-0.27, body_pitch within +-0.26, body_z within -0.025..+0.010,
neck only down (<= 0), and the standing emotions keep the head's forward travel small (neck >= -0.5),
because a heavy head far forward makes the real duck step to stay up (see sad's robot_note).
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from quack import ROBOT_SEED, SR, Personality, mix, normalise, pink_noise, quack, t_axis, write_wav  # noqa: E402

STEP = 0.1
F0 = 238.0  # the duck's pitch centre
P = Personality(ROBOT_SEED)
FIELDS = ("neck", "head_pitch", "head_yaw", "head_roll", "body_pitch", "body_z")


# ----------------------------------------------------------------------------- motion helpers
def ease(points, t):
    """Value at times t from [(t, v), ...] waypoints, cosine-eased between neighbours, held outside."""
    ts = np.array([p[0] for p in points], float)
    vs = np.array([p[1] for p in points], float)
    out = np.empty_like(t)
    for i, x in enumerate(t):
        if x <= ts[0]:
            out[i] = vs[0]
        elif x >= ts[-1]:
            out[i] = vs[-1]
        else:
            k = int(np.searchsorted(ts, x, "right")) - 1
            a = (x - ts[k]) / (ts[k + 1] - ts[k])
            out[i] = vs[k] + (vs[k + 1] - vs[k]) * (0.5 - 0.5 * np.cos(np.pi * a))
    return out


# ----------------------------------------------------------------------------- sound helpers
def q(dur, contour, level=-3.0, env=("expdecay", None, None), **mods):
    return normalise(quack(P, dur, [(a, F0 * b) for a, b in contour], env, mods=mods or None), level)


def mouth_from_wav(sig, lag_s=0.16, step=0.02):
    """The 14 emotions' recipe (see the format notes), on a float signal instead of a file."""
    pcm = np.clip(normalise(sig, -3.0) * 32767, -32768, 32767).astype(np.int16) / 32768.0
    win = int(SR * step)
    n = len(pcm) // win
    rms = np.sqrt((pcm[: n * win].reshape(n, win) ** 2).mean(axis=1))
    rms = np.convolve(rms, np.ones(3) / 3, mode="same")
    env = np.clip(rms / (0.6 * rms.max()), 0.0, 1.0)
    return np.concatenate([np.zeros(round(lag_s / step)), env])


# ----------------------------------------------------------------------------- the four emotions
def surprised():
    """'Whoa!': the head snaps back and up with a quack that jumps an octave, a frozen beat,
    then a cautious lean forward with a tilt and a soft 'ooh?'."""
    total = 2.6
    t = np.arange(0, total + 1e-9, STEP)
    m = dict(
        neck=ease([(0, 0), (0.8, 0), (1.3, -0.45), (1.9, -0.45), (2.4, 0)], t),
        head_pitch=ease([(0, 0), (0.05, 0), (0.25, -0.65), (0.8, -0.6), (1.3, -0.1), (1.9, -0.1), (2.4, 0)], t),
        head_yaw=np.zeros_like(t),
        head_roll=ease([(0, 0), (0.9, 0), (1.3, 0.22), (1.9, 0.22), (2.4, 0)], t),
        body_pitch=ease([(0, 0), (0.05, 0), (0.25, -0.16), (0.8, -0.14), (1.3, 0.08), (1.9, 0.08), (2.4, 0)], t),
        body_z=ease([(0, 0), (0.25, 0.01), (0.8, 0.01), (1.3, 0), (2.4, 0)], t),
    )
    sound = mix([
        (0.12, q(0.30, [(0, 1.15), (0.12, 2.3), (0.30, 2.2)], -3.0, ("expdecay", 0.006, 0.2),
                 quackiness=0.8, attack_sharpness=0.9)),
        (1.3, q(0.42, [(0, 1.05), (0.15, 0.92), (0.42, 1.35)], -9.0, ("bell", 0.07, 0.15),
                quackiness=0.35, breath=0.08, vibrato_depth=0.2)),
    ], total)
    return dict(
        total=total, motion=m, sound=sound,
        description="'Whoa!': the head snaps back and up on a quack that jumps an octave, a frozen beat, "
                    "then a cautious lean forward with a head tilt and a soft 'ooh?'.",
    )


def hello():
    """A warm greeting: head tilted, a little bow on 'hel-', up on a rising '-lo~', then a happy
    sway on three climbing chirps."""
    total = 3.4
    t = np.arange(0, total + 1e-9, STEP)
    m = dict(
        neck=np.zeros_like(t),
        head_pitch=ease([(0, 0), (0.35, -0.12), (0.7, 0.3), (1.05, -0.2), (1.5, -0.25), (2.6, -0.2), (3.1, 0)], t),
        head_yaw=ease([(0, 0), (0.35, 0.2), (1.05, -0.15), (1.5, 0.25), (1.8, -0.25), (2.1, 0.25),
                       (2.4, -0.2), (2.7, 0), (3.1, 0)], t),
        head_roll=ease([(0, 0), (0.35, 0.25), (0.7, 0.25), (1.05, -0.25), (1.5, 0.2), (1.8, -0.2), (2.1, 0.2),
                        (2.4, -0.2), (2.7, 0), (3.1, 0)], t),
        body_pitch=ease([(0, 0), (0.35, 0), (0.7, 0.12), (1.05, 0), (1.5, 0.04), (1.8, 0), (2.1, 0.04),
                         (2.4, 0), (3.1, 0)], t),
        body_z=np.zeros_like(t),
    )
    warm = dict(quackiness=0.45, attack_sharpness=0.25, breath=0.04)
    sound = mix([
        (0.6, q(0.22, [(0, 1.0), (0.22, 0.95)], -4.0, ("bell", 0.03, 0.08), **warm)),
        (0.95, q(0.48, [(0, 1.2), (0.08, 1.26), (0.48, 1.5)], -3.0, ("bell", 0.04, 0.2),
                 vibrato_rate_hz=6.0, vibrato_depth=0.35, **warm)),
        (1.75, q(0.12, [(0, 1.5), (0.12, 1.65)], -7.0, ("expdecay", 0.008, 0.08), quackiness=0.5)),
        (2.05, q(0.12, [(0, 1.68), (0.12, 1.85)], -6.0, ("expdecay", 0.008, 0.08), quackiness=0.5)),
        (2.35, q(0.16, [(0, 2.0), (0.16, 2.25)], -5.0, ("expdecay", 0.008, 0.1), quackiness=0.5)),
    ], total)
    return dict(
        total=total, motion=m, sound=sound,
        description="A warm hello: head tilted, a little bow on a soft 'hel-', up on a rising '-lo~' "
                    "(a major third), then a happy sway on three climbing chirps.",
    )


def snore(dur_in=0.7, dur_out=0.6):
    """Breath in through a low rattle, then a soft purring quack out."""
    t = t_axis(dur_in)
    rng = P.variant_rng("snore", 0).numpy()
    rattle = pink_noise(len(t), rng) * (0.6 + 0.4 * np.sin(2 * np.pi * 28 * t)) * np.sin(np.pi * t / dur_in) ** 2
    out = q(dur_out, [(0, 0.62), (dur_out, 0.5)], -3.0, ("bell", 0.12, 0.3),
            quackiness=1.0, am_rate_hz=26.0, am_depth=0.8, breath=0.2, vibrato_depth=0.0)
    return np.concatenate([normalise(rattle, -9.0), np.zeros(int(0.1 * SR)), out])


def sleepy():
    """A long yawn, beak up; the duck sits, the head droops, nods off, jerks awake on a 'wek?',
    droops again and sleeps on two snores. It stays seated, head down."""
    total = 9.0
    t = np.arange(0, total + 1e-9, STEP)
    m = dict(
        neck=ease([(0, 0), (2.9, 0), (4.3, -0.9), (4.5, -0.9), (4.7, -0.1), (5.5, -0.1), (7.2, -1.2), (9.0, -1.2)], t),
        head_pitch=ease([(0, 0), (1.0, -0.55), (1.6, -0.5), (2.2, 0), (2.9, 0), (4.3, 0.6), (4.5, 0.6),
                         (4.7, -0.15), (5.5, -0.1), (7.2, 0.85), (9.0, 0.85)], t),
        head_yaw=ease([(0, 0), (4.7, 0), (5.0, 0.2), (5.4, 0), (9.0, 0)], t),
        head_roll=ease([(0, 0), (6.2, 0), (7.2, 0.15), (9.0, 0.15)], t),
        body_pitch=np.zeros_like(t),
        body_z=np.zeros_like(t),
    )
    sit_from = 2.2
    yawn = q(1.7, [(0, 1.3), (0.35, 1.5), (0.9, 1.2), (1.7, 0.7)], -3.0, ("bell", 0.18, 0.7),
             quackiness=0.25, breath=0.28, vibrato_depth=0.15, attack_sharpness=0.0)
    sound = mix([
        (0.3, yawn),
        (3.4, q(0.5, [(0, 0.8), (0.5, 0.65)], -13.0, ("bell", 0.1, 0.3), quackiness=0.2, breath=0.3)),
        (4.75, q(0.15, [(0, 1.2), (0.15, 1.55)], -6.0, ("expdecay", 0.006, 0.1), quackiness=0.7)),
        (6.4, snore()),
        (7.9, snore(0.6, 0.5)),
    ], total)
    return dict(
        total=total, motion=m, sound=sound, sit_from=sit_from,
        description="A long yawn with the beak up, then it sits; the head droops, nods off, jerks awake on a "
                    "small 'wek?', droops again and falls asleep on two soft snores. It stays seated, head down.",
        robot_note="Stays seated with the head down, asleep: stand it up again with the sit toggle (D-pad Down). "
                   "Not bound on the pad yet (all twelve slots are taken).",
    )


EMOTIONS = {"surprised": surprised, "hello": hello, "sleepy": sleepy}


def build(name: str) -> dict:
    e = EMOTIONS[name]()
    total, m, sound = e["total"], e["motion"], e["sound"]
    t = np.arange(0, total + 1e-9, STEP)
    mouth = mouth_from_wav(sound)
    mouth_t = np.arange(len(mouth)) * 0.02
    keyframes = []
    for i, ti in enumerate(t):
        # The beak value at a keyframe is the loudest 20 ms window around it, so a short quack is not missed.
        near = mouth[(mouth_t > ti - STEP / 2) & (mouth_t <= ti + STEP / 2)]
        kf = {"t": round(float(ti), 3)}
        for f in FIELDS:
            kf[f] = round(float(m[f][i]), 3) + 0.0
        kf.update(twist=[0.0, 0.0, 0.0], skill="sit" if ti >= e.get("sit_from", 1e9) - 1e-9 else None,
                  soften=False, relax=False, mouth=round(float(near.max()) if len(near) else 0.0, 3))
        keyframes.append(kf)
    keyframes[-1]["mouth"] = 0.0
    (ROOT / "keyframes" / f"{name}.json").write_text(
        json.dumps({"step_s": STEP, "keyframes": keyframes}, indent=1) + "\n", encoding="utf-8")
    write_wav(ROOT / "sounds" / f"{name}.wav", sound, -3.0)
    return e


def check(name: str) -> None:
    k = json.loads((ROOT / "keyframes" / f"{name}.json").read_text())["keyframes"]
    col = {f: np.array([x[f] for x in k]) for f in FIELDS}
    assert np.abs(col["head_roll"]).max() <= 0.27 + 1e-9, name
    assert np.abs(col["body_pitch"]).max() <= 0.26 + 1e-9, name
    assert col["body_z"].min() >= -0.025 - 1e-9 and col["body_z"].max() <= 0.01 + 1e-9, name
    assert col["neck"].max() <= 1e-9, name
    sitting = any(x["skill"] == "sit" for x in k)
    assert sitting or col["neck"].min() >= -0.5 - 1e-9, name
    with wave.open(str(ROOT / "sounds" / f"{name}.wav")) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1


if __name__ == "__main__":
    for name in sys.argv[1:] or EMOTIONS:
        e = build(name)
        check(name)
        print(f"{name}: {e['total']} s  keyframes/{name}.json  sounds/{name}.wav")
