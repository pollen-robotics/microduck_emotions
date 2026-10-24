#!/usr/bin/env python
"""ROPE TUG (Rémi, 2026-10-24, by voice, for episode 4): the duck holds the leash in its closed beak and tugs it to the
side two or three times, mainly with head yaw, the legs dipping a little with each pull so it looks alive, not robotic.
Then Rémi takes the pad and backs the duck up until the rope slides out (not part of the emotion). No sound, or a small
effort sound through the shut beak.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotion-rope-tug/rope_tug.py [--only SUBSTR] [--debug]

Built like the WOW (`emotion-wow/wow.py`): the episode 3 renderer (`emotions-workshop/motion/episode3/lib.py`: the duck
driven only through what the real robot accepts, BAM servos, shipped stand policy) and the showcase studio look, plus
`rope_scene.py` (Reachy Mini asleep 40 cm away, the rope tied round its base, its knot in the beak). Default = the
studio clips (1280x720, slow camera from the film's profile toward 3/4 front) into clips/; `--debug` = 640x480 with
the overlay into debug/. Every render also writes robot/<stem>.json, the robotd emotion file at 50 Hz (`robot.do`).

What makes it less robotic than a sine: each pull has an anticipation (a small wind-up the other way), a fast yank,
a strain hold that creeps a little further with a shiver, and a slower give-back as if the rope pulled the head home;
the pulls grow and their rhythm is uneven; the legs dip into each pull and push back up after it, the body leans back;
a slow, small, seeded wobble rides on every channel. The beak stays shut throughout (mouth 0) so the rope stays in.

The legs: with the robotd command layout (see the patch below), the shipped stand policy in sim barely tracks body z
(-0.05 does nothing, -0.12 gives 1 cm) but tracks a lean (body_pitch -0.10 -> trunk 5-6 deg back in ~0.5 s, the knees
and ankles bend, the neck dips -0.4 to keep the head). So each pull leans the duck back into the rope; the small z dip
stays in (harmless, in the trained range) in case the real stand policy follows it.
"""
import argparse, json, math, os, sys
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.signal import butter, lfilter

HERE = Path(__file__).resolve().parent
WS = Path("/Users/remi/microduck/notes/emotions-workshop")
DEBUG = "--debug" in sys.argv
if not DEBUG:
    os.environ.setdefault("SHOWCASE_SIZE", "1280x720")
sys.path[:0] = [str(HERE), str(WS), str(WS / "sounds"), str(WS / "motion/episode3"), str(WS / "showcase")]
import lib  # noqa: E402
lib.ROOT, lib.COMBINE = WS, str(WS / "combine.py")
from lib import Motion, ramp  # noqa: E402
from quack import ROBOT_SEED, SR, Personality, Rng, normalise, quack, t_axis, write_wav  # noqa: E402

import duckfilm as F  # noqa: E402

p = Personality(ROBOT_SEED)


# duckfilm puts its body pose (z, roll, pitch) in command slots 7..9, but the policies read (x, y, z, roll, pitch, yaw)
# there (robotd duck-control/src/obs.rs, microduck_rl symmetry.py): in duckfilm "body_pitch" lands on z and "body_z" on
# the unbound x. Found 2026-10-24 (a -0.14 "lean" crouched the trunk 1.3 cm; a -0.02 "z" did nothing). Fixed here only,
# for these renders, by feeding the policy the robotd layout.
_duckfilm_policy_tick = F.Duck._policy_tick


def _policy_tick_robotd_layout(self):
    body = self.body_s.copy()
    self.body_s[:] = 0.0
    self.body_s[2:5] = body[0:3]
    try:
        _duckfilm_policy_tick(self)
    finally:
        self.body_s[:] = body


F.Duck._policy_tick = _policy_tick_robotd_layout
LAG = 0.19                      # command -> seen head on the stand policy (WOW debug renders, 2026-10-10)
ST = 2 ** (1 / 12)
ROLL_MAX = 0.27                 # head_roll joint range
RIGHT, LEFT = -1, 1             # head_yaw sign: > 0 = the duck's own left. The film camera is on the duck's right.


def smooth_noise(seed, t, amp, freqs=(0.55, 0.9, 1.45, 2.1)):
    """A slow, seeded, sum-of-sines wobble (amplitude ~amp): the life on top of the keyed motion."""
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 2 * math.pi, len(freqs))
    w = r.uniform(0.6, 1.0, len(freqs))
    return amp * sum(wi * math.sin(2 * math.pi * f * t + pi) for f, pi, wi in zip(freqs, ph, w)) / sum(w) * 1.6


class Tug:
    """One rope-tug timeline. `pulls` = [(t0, side, amp, yank, hold, back, keep), ...] in COMMAND time (s):
    the yank starts at t0, reaches side * amp after `yank` s, creeps 7 % further through the `hold` (with a shiver),
    then gives back over `back` s to side * amp * keep (the rope pulling the head home). `shake` = (t0, dur, centre,
    amp, hz): a dog-like worrying shake around `centre`."""

    def __init__(self, name, desc, pulls, *, shake=None, settle=0.45, end=0.7, dip=0.020, lean=0.12, beak_down=0.10,
                 roll_k=0.36, shiver=0.06, life=1.0, seed=7, rope_len=0.34, stage=0.0):
        self.name, self.desc, self.pulls, self.shake = name, desc, pulls, shake
        self.rope_len, self.stage = rope_len, stage
        self.dip, self.lean, self.beak_down, self.roll_k, self.shiver, self.life, self.seed = \
            dip, lean, beak_down, roll_k, shiver, life, seed
        last = max([t0 + y + h + b for t0, _, _, y, h, b, _ in pulls] + ([shake[0] + shake[1] + 0.35] if shake else []))
        self.t_release = last + 0.15            # head and body go home from here
        self.total = round(self.t_release + end + 0.25, 2)
        self.settle = settle
        # --- keyed channels (PCHIP: no overshoot between keys) -----------------------------------------------
        yk, zk, bk, pk = [(0.0, 0.0)], [(0.0, 0.0)], [(0.0, 0.0)], [(0.0, 0.0)]
        zk.append((settle, -0.30 * dip))        # sets its feet: a small crouch, lean back, beak a touch down
        bk.append((settle, -0.35 * lean))
        pk.append((settle, 0.35 * beak_down))
        rest = 0.0
        self.holds = []
        for t0, side, amp, yank, hold, back, keep in pulls:
            a = side * amp
            yk += [(t0 - 0.2, rest), (t0, rest - 0.15 * a), (t0 + yank, a), (t0 + yank + hold, 1.07 * a),
                   (t0 + yank + hold + back, keep * a)]
            g = amp / 0.8                       # bigger pulls dig in deeper
            zk += [(t0 - 0.2, -0.30 * dip), (t0 + 0.04, -0.20 * dip), (t0 + 0.8 * yank, -dip * min(1.0, 0.75 + 0.3 * g)),
                   (t0 + yank + hold, -0.9 * dip), (t0 + yank + hold + 0.6 * back, +0.05 * dip), (t0 + yank + hold + back, -0.30 * dip)]
            bk += [(t0 - 0.2, -0.35 * lean), (t0 + yank, -lean * min(1.0, 0.7 + 0.35 * g)), (t0 + yank + hold, -lean),
                   (t0 + yank + hold + back, -0.35 * lean)]
            pk += [(t0 - 0.2, 0.35 * beak_down), (t0 + yank, beak_down), (t0 + yank + hold, beak_down),
                   (t0 + yank + hold + back, 0.35 * beak_down)]
            self.holds.append((t0 + yank, t0 + yank + hold))
            rest = keep * a
        if shake:
            s0, sd, centre, samp, hz = shake
            yk += [(s0 - 0.2, rest), (s0 + 0.15, centre), (s0 + sd, centre), (s0 + sd + 0.3, 0.5 * centre)]
            zk += [(s0 - 0.1, -0.5 * dip), (s0 + 0.15, -dip), (s0 + sd, -dip), (s0 + sd + 0.3, -0.3 * dip)]
            bk += [(s0 + 0.15, -lean), (s0 + sd, -lean), (s0 + sd + 0.3, -0.35 * lean)]
            pk += [(s0 + 0.15, beak_down), (s0 + sd, beak_down), (s0 + sd + 0.3, 0.35 * beak_down)]
        for k in (yk, zk, bk, pk):              # let go: everything home, the beak still shut on the rope
            k += [(self.t_release, k[-1][1]), (self.t_release + end, 0.0), (self.total, 0.0)]
        mk = lambda keys: PchipInterpolator(*map(np.array, zip(*self._sorted(keys))))
        self.yaw_k, self.z_k, self.bp_k, self.hp_k = mk(yk), mk(zk), mk(bk), mk(pk)

    @staticmethod
    def _sorted(keys):
        out = []
        for t, v in sorted(keys, key=lambda kv: kv[0]):
            if out and t - out[-1][0] < 1e-3:
                out[-1] = (t, v)
            else:
                out.append((t, v))
        return out

    def strain(self, t):
        """0..1: inside a strain hold (eased in and out), where the shiver lives."""
        w = 0.0
        for h0, h1 in self.holds:
            w = max(w, ramp(t - h0, 0.08) * (1.0 - ramp(t - (h1 - 0.06), 0.1)))
        return w

    def shake_at(self, t):
        if not self.shake:
            return 0.0
        s0, sd, centre, samp, hz = self.shake
        env = ramp(t - (s0 + 0.1), 0.12) * (1.0 - ramp(t - (s0 + sd - 0.15), 0.15))
        return samp * env * math.sin(2 * math.pi * hz * (t - s0 - 0.1))

    def fn(self, t):
        life = self.life * ramp(t, 0.4) * (1.0 - ramp(t - self.t_release, 0.6))
        st = self.strain(t)
        sh = self.shake_at(t)
        yaw = float(self.yaw_k(t)) + sh + st * self.shiver * math.sin(2 * math.pi * 6.3 * t) \
            + life * smooth_noise(self.seed, t, 0.022)
        roll = self.roll_k * (float(self.yaw_k(t)) + 0.6 * sh) + st * 0.8 * self.shiver * math.sin(2 * math.pi * 6.3 * t + 1.3) \
            + life * smooth_noise(self.seed + 1, t, 0.02)
        pitch = float(self.hp_k(t)) + life * smooth_noise(self.seed + 2, t, 0.02)
        z = float(self.z_k(t)) + life * smooth_noise(self.seed + 3, t, 0.0015, (0.8, 1.3, 1.9))
        bp = float(self.bp_k(t)) + life * smooth_noise(self.seed + 4, t, 0.012)
        return dict(head_yaw=yaw, head_roll=max(-ROLL_MAX, min(ROLL_MAX, roll)), head_pitch=pitch,
                    body_z=max(-0.025, min(0.010, z)), body_pitch=bp, mouth=0.0)

    def efforts(self):
        """(seen start, seen end of strain, seen release end, strength 0..1) per pull, for the sounds."""
        out = []
        top = max(a for _, _, a, *_ in self.pulls)
        for t0, side, amp, yank, hold, back, keep in self.pulls:
            out.append((t0 + LAG - 0.03, t0 + yank + hold + LAG, t0 + yank + hold + 0.55 * back + LAG, amp / top))
        if self.shake:
            s0, sd, *_ = self.shake
            out.append((s0 + 0.1 + LAG, s0 + sd + LAG, s0 + sd + 0.3 + LAG, 1.0))
        return out

    def motion(self):
        beats = [(self.settle, "sets its feet")]
        for i, (t0, side, amp, yank, hold, back, keep) in enumerate(self.pulls):
            beats += [(t0 + yank + LAG, f"pull {i + 1}")]
        if self.shake:
            beats += [(self.shake[0] + 0.5, "shake")]
        beats += [(self.t_release + 0.7 + LAG, "home, rope still held")]
        return Motion(self.name, self.desc, self.total, self.fn, beats=beats, quacks=[])


# (t0, side, amp, yank, hold, back, keep)
MOTIONS = {
    "tug3": Tug("tug3", "three pulls to the duck's right (toward the film camera), growing: yaw 0.50, 0.64, 0.76; "
                "uneven rhythm, the last one held longest; legs dip into each pull and push back up after it",
                [(0.70, RIGHT, 0.50, 0.20, 0.30, 0.45, 0.25),
                 (1.80, RIGHT, 0.64, 0.19, 0.36, 0.45, 0.30),
                 (3.05, RIGHT, 0.76, 0.18, 0.60, 0.50, 0.20)]),
    "tug3_alt": Tug("tug3_alt", "dog tug-of-war: pulls right, left, right (yaw 0.60, 0.60, 0.80), the same leg dips",
                    [(0.70, RIGHT, 0.60, 0.20, 0.30, 0.42, 0.15),
                     (1.80, LEFT, 0.60, 0.20, 0.32, 0.42, 0.15),
                     (3.00, RIGHT, 0.80, 0.18, 0.55, 0.50, 0.15)], seed=11),
    "tug2_shake": Tug("tug2_shake", "two pulls to the right (yaw 0.55, 0.72), then a dog's worrying shake: crouched low, quick "
                      "small side to side head shakes around the pull side",
                      [(0.70, RIGHT, 0.55, 0.20, 0.30, 0.45, 0.30),
                       (1.80, RIGHT, 0.72, 0.18, 0.40, 0.40, 0.55)],
                      shake=(2.95, 1.05, -0.45, 0.30, 3.3), seed=5),
}
# round 2 (Rémi, 2026-10-24 voice: "two pulls then a shake, with the sound under that video; the pulls bigger, I don't
# see the rope tighten"). Pulls 0.80 / 0.95 (was 0.55 / 0.72), shake around -0.62 (was -0.45).
# Measured with a slack rope (2026-10-24): facing Reachy, a sideways head pull swings the beak ACROSS the rope, so the knot
# gets only 0.5 cm (round 1) / 1.1 cm (these) further from the tie; leaning back adds nothing (the policy dips the neck to
# keep the head where it was). So: facing Reachy with a rope that sags only ~1 cm at rest (it goes straight on the pulls),
# or side-on staging (Reachy 60 deg to the duck's left, the pulls to its right go ALONG the rope).
BIG = [(0.70, RIGHT, 0.80, 0.20, 0.32, 0.45, 0.35), (1.85, RIGHT, 0.95, 0.19, 0.42, 0.40, 0.60)]
BIG_SHAKE = (3.0, 1.05, -0.62, 0.34, 3.3)
MOTIONS.update({
    "shake_big": Tug("shake_big", "round 1's two pulls then a shake, bigger: pulls to yaw 0.80 and 0.95, the shake further "
                     "to the side; facing Reachy, the rope 33 cm (a slight sag at rest)", BIG, shake=BIG_SHAKE, seed=5,
                     rope_len=0.330),
    "shake_big_side": Tug("shake_big_side", "the same move, the duck standing side-on: Reachy 60 deg to its left, so each "
                          "pull to its right goes along the rope", BIG, shake=BIG_SHAKE, seed=5, rope_len=0.357, stage=60.0),
})
# tried 2026-10-24 and dropped: lean 0.20 (neck to -0.80, no extra rope take-up), beak up on the pulls (less dog-like).


# ---------------------------------------------------------------------------------------------------------------
# sounds: effort through a SHUT beak (it holds the rope), so muffled; smooth glides only (Rémi's taste)
# ---------------------------------------------------------------------------------------------------------------
MUFFLED = dict(brightness=0.05, nasal=1.0, quackiness=0.6, breath=0.03, vibrato_depth=0.15, attack_sharpness=0.0, tilt=2.6,
               am_depth=0.35)
STRAIN = dict(MUFFLED, quackiness=0.9, am_depth=0.6, am_rate_hz=31.0, vibrato_depth=0.1, jitter_depth=0.25)
GROWL = dict(MUFFLED, quackiness=1.0, am_depth=0.8, am_rate_hz=24.0, vibrato_depth=0.05, jitter_depth=0.3, tilt=2.8)


def lowpass(x, fc):
    b, a = butter(2, fc / (SR / 2))
    return lfilter(b, a, x)


def bandpass(x, lo, hi):
    b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return lfilter(b, a, x)


def db(x, g):
    return x * 10 ** (g / 20)


def grunt(dur, f_lo, f_hi, f_end, strain_end, strength, seed):
    """One 'nnngh': a soft-attacked muffled tone rising (eased) from f_lo to f_hi until the end of the strain, then
    gliding down to f_end as the effort lets go. The buzz (roughness) grows with the effort."""
    t = t_axis(dur)
    u = np.clip(t / strain_end, 0, 1)
    up = 0.5 - 0.5 * np.cos(np.pi * u)
    v = np.clip((t - strain_end) / max(1e-3, dur - strain_end), 0, 1)
    dn = 0.5 - 0.5 * np.cos(np.pi * v)
    freq = np.where(t < strain_end, f_lo * (f_hi / f_lo) ** up, f_hi * (f_end / f_hi) ** dn)
    env = (0.5 - 0.5 * np.cos(np.pi * np.clip(t / 0.09, 0, 1))) * (0.55 + 0.45 * up) * (1.0 - dn) ** 1.3
    mods = dict(STRAIN, am_depth=0.35 + 0.35 * strength)
    sig = quack(p, dur, freq, env, mods=mods, rng=Rng(seed))
    return lowpass(sig, 950.0 + 250.0 * strength)


def breath(dur, f0, f1, seed, out=True):
    """A nose breath: band-passed noise with a gliding centre and a soft bell envelope (in = shorter, brighter)."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    x = r.standard_normal(n)
    t = np.arange(n) / SR
    halves = []
    for k in range(4):                                   # a gliding band: crossfade 4 fixed bands
        c = f0 * (f1 / f0) ** (k / 3)
        halves.append(bandpass(x, c * 0.6, c * 1.5))
    pos = np.clip(t / dur, 0, 1) * 3
    sig = sum(h * np.clip(1 - np.abs(pos - k), 0, 1) for k, h in enumerate(halves))
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** (1.5 if out else 1.0)
    return sig * env


def sound(tug, kind):
    total = tug.total + 0.5
    buf = np.zeros(int(total * SR))

    def put(t, sig):
        i = int(round(t * SR))
        n = min(len(sig), len(buf) - i)
        buf[i:i + n] += sig[:n]

    f0 = p.pitch_center_hz
    eff = tug.efforts()
    if kind == "S0_silent":
        return buf
    if kind in ("E1_grunts", "E2_grunts_breaths"):
        for i, (s, e, r_, k) in enumerate(eff):
            dur = r_ - s + 0.12
            lo = f0 * (0.74 + 0.05 * i)
            g = grunt(dur, lo, lo * ST ** (3.5 + 1.5 * k), lo * ST ** -2.0, e - s, k, 0x7A6 + i)
            put(s, db(normalise(g, -3.0), -7.5 + 5.0 * k))
        if kind == "E2_grunts_breaths":
            for i in range(len(eff) - 1):              # a quick sniff in before the next pull
                t_in = eff[i + 1][0] - 0.28
                put(t_in, db(normalise(breath(0.22, 2600, 3400, 31 + i, out=False), -3.0), -19.0))
            last_end = eff[-1][2]                      # and one tired puff out through the nose when it lets go
            put(last_end + 0.05, db(normalise(breath(0.55, 2200, 900, 77), -3.0), -15.0))
    elif kind == "E3_growl":
        s_all, r_all = eff[0][0] - 0.05, eff[-1][2] + 0.15
        dur = r_all - s_all
        t = t_axis(dur) + s_all
        level = np.full_like(t, 0.28)
        bend = np.zeros_like(t)
        for s, e, r_, k in eff:                        # each pull swells the growl and bends it up a little
            up = np.clip((t - s) / 0.18, 0, 1)
            down = np.clip((t - e) / max(0.05, r_ - e), 0, 1)
            w = (0.5 - 0.5 * np.cos(np.pi * up)) * (0.5 + 0.5 * np.cos(np.pi * down))
            level = np.maximum(level, 0.28 + 0.72 * k * w)
            bend = np.maximum(bend, (1.5 + 1.5 * k) * w)
        level *= np.clip((t - s_all) / 0.15, 0, 1) * np.clip((r_all - t) / 0.3, 0, 1)
        freq = 0.62 * f0 * ST ** bend
        sig = quack(p, dur, freq, level, mods=GROWL, rng=Rng(0x6A0))
        put(s_all, normalise(lowpass(sig, 800.0), -4.0))
    else:
        raise ValueError(kind)
    return buf


SOUNDS = {
    "S0_silent": "no sound",
    "E1_grunts": "one small muffled 'nnngh' per pull, through the shut beak: rises 4 to 5 semitones while it strains, glides down "
                 "as it gives back; each pull a little louder and higher",
    "E2_grunts_breaths": "E1 plus a quick sniff before each new pull and one tired puff out of the nose at the end",
    "E3_growl": "a dog's tug-of-war growl: one low muffled 'rrrr' through the whole tug, swelling and bending up at each pull",
}
RENDERS = [("tug3", "E1_grunts"), ("tug3_alt", "E1_grunts"), ("tug2_shake", "E1_grunts"),
           ("tug3", "S0_silent"), ("tug3", "E2_grunts_breaths"), ("tug3", "E3_growl"),
           ("shake_big", "E1_grunts"), ("shake_big_side", "E1_grunts")]


# ---------------------------------------------------------------------------------------------------------------
# camera: the film's side (profile, Reachy on the right), a slow 12 deg drift toward the duck's face. Any wider swing
# toward the front puts Reachy between the camera and the duck.
# ---------------------------------------------------------------------------------------------------------------
def install_camera(total, stage=0.0):
    import mujoco
    import orbit
    import rope_scene

    class RopeCam(orbit.OrbitRenderer):
        def update_scene(self, d, camera=None, scene_option=None):
            n = max(1, int(round(total * orbit.FPS)) - 1)
            u = min(1.0, self.i / n)
            e = 0.5 - 0.5 * math.cos(math.pi * u)
            p_ = np.array(d.xpos[self.trunk], float)
            a = math.radians(stage)
            tgt = np.array([p_[0] + 0.15 * math.cos(a), p_[1] + 0.15 * math.sin(a), 0.150])
            self.look = tgt if self.look is None else self.look + (tgt - self.look) * (1 - math.exp(-(1.0 / orbit.FPS) / 0.6))
            cam = mujoco.MjvCamera()
            cam.type = mujoco.mjtCamera.mjCAMERA_FREE
            cam.lookat[:] = self.look
            cam.azimuth = 93 + stage + 12 * e
            cam.elevation = -5 - 2 * e
            cam.distance = 0.74 - 0.06 * e
            self.i += 1
            self.r.update_scene(d, camera=cam)

    orbit.install("rope_tug", total)
    mujoco.Renderer = RopeCam
    rope_scene.install()


def robot_file(tug, path):
    """The robotd emotion file (microduck_emotions keyframe format), one keyframe per control tick (robotd interpolates
    linearly; the 0.1 s keys of the renderer's json would flatten the yanks)."""
    keys = []
    n = int(round(tug.total / 0.02))
    for k in range(n + 1):
        t = round(k * 0.02, 3)
        h = tug.fn(min(t, tug.total))
        keys.append(dict(t=t, neck=0.0, head_pitch=round(h["head_pitch"], 4), head_yaw=round(h["head_yaw"], 4),
                         head_roll=round(h["head_roll"], 4), body_pitch=round(h["body_pitch"], 4), body_z=round(h["body_z"], 5),
                         mouth=0.0, skill=None))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"keyframes": keys}) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--sounds-only", action="store_true")
    a = ap.parse_args()
    for mname, snd in RENDERS:
        stem = f"{mname}__{snd}"
        if a.only and a.only not in stem:
            continue
        tug = MOTIONS[mname]
        wav = HERE / "sounds" / f"{stem}.wav"
        wav.parent.mkdir(exist_ok=True)
        write_wav(wav, sound(tug, snd), -3.0)
        robot_file(tug, HERE / "robot" / f"{mname}.json")
        if a.sounds_only:
            print("wrote", wav)
            continue
        m = tug.motion()
        if a.debug:
            import rope_scene
            rope_scene.install()
            lib.render(m, wav, HERE / "motion", HERE / "debug", sound=snd, sound_desc=SOUNDS[snd], mouth_mode="motion")
        else:
            import rope_scene
            rope_scene.ROPE_LEN, rope_scene.STAGE_DEG = tug.rope_len, tug.stage
            install_camera(m.total, tug.stage)
            lib.beats_sheet = lambda *a_, **k: None
            taut = []

            def straightness(dr, t, h, du):
                """End-to-end distance knot -> tie over the rope length: 1.0 = a straight, taut rope."""
                import mujoco
                mm, dd = du.m, du.d
                k0 = dd.xpos[mujoco.mj_name2id(mm, mujoco.mjtObj.mjOBJ_BODY, "rope_0")]
                e = mujoco.mj_name2id(mm, mujoco.mjtObj.mjOBJ_EQUALITY, "rope_tie")
                rb = mujoco.mj_name2id(mm, mujoco.mjtObj.mjOBJ_BODY, "rm_body")
                tie = dd.xpos[rb] + dd.xmat[rb].reshape(3, 3) @ mm.eq_data[e, 3:6]
                taut.append((round(t, 2), float(np.linalg.norm(tie - k0)) / tug.rope_len))

            meas = lib.render(m, wav, HERE / "orbit_motion", HERE / "clips", sound=snd, sound_desc=SOUNDS[snd],
                              mouth_mode="motion", quiet=True, extra_frames=straightness)
            tv = np.array([v for _, v in taut])
            print(f"   rope straightness: rest {tv[:10].mean():.3f}, max {tv.max():.3f} at {taut[int(tv.argmax())][0]} s, "
                  f"time above 0.98: {(tv > 0.98).sum() / 30:.2f} s", flush=True)
            print(f"{stem}: {m.total} s  {'FELL@%.2f' % meas['fell_at'] if meas['fell'] else 'no fall'}  drift {meas['drift_cm']} cm  "
                  f"yaw {meas['head_yaw_absmax']:.2f} roll {meas['head_roll_absmax']:.2f} pitch [{meas['head_pitch_min']:+.2f},"
                  f"{meas['head_pitch_max']:+.2f}] neck {meas['neck_min']:+.2f} trunk pitch [{meas['trunk_pitch_min']:+.0f},"
                  f"{meas['trunk_pitch_max']:+.0f}]deg z [{meas['trunk_z_min']:.3f}]", flush=True)


if __name__ == "__main__":
    main()
