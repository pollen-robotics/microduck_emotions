#!/usr/bin/env python
"""WOW (Rémi, 2026-10-10, by voice): amazed. An exaggerated half circle of the head from the duck's LEFT, up over the
top, down to the RIGHT, the beak opening at the start, with ONE long sound going low -> intense -> low.

    /Users/remi/microduck/.venv-mjlab/bin/python /Users/remi/microduck/notes/emotion-wow/wow.py [--orbit] [--only SUBSTR]

Built on the episode 3 renderer (`emotions-workshop/motion/episode3/lib.py`: the duck driven only through what the
real robot accepts, BAM servos, shipped policies). Default = debug renders (640x480, overlay with commands and joints)
into debug/; `--orbit` = the showcase look (studio scene, slow orbit camera, no overlay, SHOWCASE_SIZE) into clips/.

The arc: head_yaw = A cos(theta), head_pitch = p0 - (p0 - top) sin(theta), theta 0 -> pi (yaw > 0 = the duck's own
left, head_pitch < 0 = beak up). Commands lead what you see by LAG s (robotd's head EMA + the policy), so the sound and
the beak are placed on the SEEN head: the sound peaks when the head is at the top.
"""
import argparse, json, math, os, sys
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicHermiteSpline

HERE = Path(__file__).resolve().parent
WS = Path("/Users/remi/microduck/notes/emotions-workshop")
ORBIT = "--orbit" in sys.argv
if ORBIT:
    os.environ.setdefault("SHOWCASE_SIZE", "720x1280")
sys.path[:0] = [str(WS), str(WS / "sounds"), str(WS / "motion/episode3"), str(WS / "showcase")]
import lib  # noqa: E402
lib.ROOT, lib.COMBINE = WS, str(WS / "combine.py")
from lib import Motion, ramp  # noqa: E402
from quack import ROBOT_SEED, SR, Personality, Rng, normalise, quack, t_axis, write_wav  # noqa: E402

p = Personality(ROBOT_SEED)
LAG = 0.19                      # command -> seen head: yaw crosses 0 and the beak is highest 0.17-0.19 s after the command (debug render, 2026-10-10)
ST = 2 ** (1 / 12)


# ---------------------------------------------------------------------------------------------------------------
# motions
# ---------------------------------------------------------------------------------------------------------------
class Arc:
    """One WOW timeline. Times are COMMAND times (s)."""

    def __init__(self, name, desc, *, yaw=0.85, p0=0.05, top=-0.85, p_end=None, roll=0.0, neck_low=0.0, go=0.45, a0=0.75,
                 a1=2.55, linger=0.0, hold=0.5, back=0.6, tail=0.35):
        self.name, self.desc = name, desc
        self.yaw, self.p0, self.top, self.roll, self.neck_low = yaw, p0, top, roll, neck_low
        self.p_end = p0 if p_end is None else p_end          # where the beak ends at the right (> 0 = down)
        self.go, self.a0, self.a1, self.hold, self.back = go, a0, a1, hold, back
        self.t_back = a1 + hold
        self.total = round(self.t_back + back + 0.35, 2)
        tm = (a0 + a1) / 2
        if linger > 0:            # slow through the top: theta covers 0.16 pi in `linger` s around the middle
            w = 0.16 * math.pi
            v = w / linger
            self.theta = CubicHermiteSpline([a0, tm - linger / 2, tm + linger / 2, a1],
                                            [0.0, math.pi / 2 - w / 2, math.pi / 2 + w / 2, math.pi], [0.0, v, v, 0.0])
        else:
            self.theta = CubicHermiteSpline([a0, a1], [0.0, math.pi], [0.0, 0.0])
        # the sound on the SEEN head: starts as it leaves the left, peaks at the top, dies after it lands right
        self.s0 = a0 + LAG - 0.12
        self.s_peak = tm + LAG
        self.s1 = a1 + LAG + tail

    def th(self, t):
        if t <= self.a0:
            return 0.0
        if t >= self.a1:
            return math.pi
        return float(self.theta(t))

    def fn(self, t):
        g = ramp(t, self.go) * (1.0 - ramp(t - self.t_back, self.back))     # into the left start pose ... back home
        th = self.th(t)
        c, s = math.cos(th), math.sin(th)
        yaw = self.yaw * c
        if t >= self.t_back:                                              # home from the right
            yaw = -self.yaw * (1.0 - ramp(t - self.t_back, self.back))
        lo = self.p0 if th <= math.pi / 2 else self.p_end          # first half from the start height, second half to the end one
        out = dict(head_yaw=yaw if t >= self.a0 else self.yaw * g,
                   head_pitch=(lo - (lo - self.top) * s) * (g if t < self.a0 else 1.0)
                   * (1.0 - ramp(t - self.t_back, self.back)),
                   head_roll=self.roll * (yaw / self.yaw))
        if self.neck_low:
            # the neck low at both ends and up at the top: the head travels a taller half circle, not just a rotation
            out["neck"] = self.neck_low * (1.0 - s) * (g if t < self.a0 else 1.0) * (1.0 - ramp(t - self.t_back, self.back))
        out["mouth"] = self.mouth(t)
        return out

    def loud(self, t):
        """0..1 loudness of the sound at time t (absolute), shared by the sound and the beak."""
        if t <= self.s0 or t >= self.s1:
            return 0.0
        if t < self.s_peak:
            x = (t - self.s0) / (self.s_peak - self.s0)
            return 0.30 + 0.70 * (0.5 - 0.5 * math.cos(math.pi * x))
        x = (t - self.s_peak) / (self.s1 - self.s_peak)
        return (0.5 + 0.5 * math.cos(math.pi * x)) * (1.0 - 0.15 * x)

    def mouth(self, t):
        """The beak opens just before the sound (at the left), widens with the loudness, shuts as the sound dies."""
        o = ramp(t - (self.s0 - 0.12), 0.15) * (1.0 - ramp(t - (self.s1 - 0.25), 0.25))
        return round(o * (0.55 + 0.45 * self.loud(t)), 3)

    def motion(self):
        beats = [(self.go + LAG, "left, beak opens"), (self.s0, "wow starts"), (self.s_peak, "top, loudest"),
                 (self.a1 + LAG, "right"), (self.s1, "sound ends"), (self.t_back + self.back + LAG, "home")]
        return Motion(self.name, self.desc, self.total, self.fn, beats=beats, quacks=[self.s_peak])


ARCS = {
    "wow_arc": Arc("wow_arc", "the brief, plain: head to the left (yaw +0.85), beak opens, half circle up over the top (beak up -0.85) "
                   "and down to the right (yaw -0.85) in 1.8 s, hold, home"),
    "wow_arc_roll": Arc("wow_arc_roll", "the same arc, the head rolling into the turn (roll +-0.25: tilted left at the left, right at "
                        "the right)", roll=0.25),
    "wow_big": Arc("wow_big", "bigger and slower: yaw +-1.0, beak up -1.0, roll +-0.25; the 2.4 s arc slows down through the top "
                   "(the long 'OOO')", yaw=1.0, top=-1.0, roll=0.25, a1=3.15, linger=0.7, tail=0.45),
    # round 2 (Rémi, 2026-10-10: "the head should start lower, more dramatic; down, up, down again, or down, up, half")
    "wow_low": Arc("wow_low", "starts low: beak pointing down at the left (+0.65), up over the top (-0.85), down again at the "
                   "right (+0.65)", p0=0.65),
    "wow_low_half": Arc("wow_low_half", "starts low (+0.65 at the left), up over the top (-0.85), then only half way down at the "
                        "right (+0.3)", p0=0.65, p_end=0.3),
    "wow_low_big": Arc("wow_low_big", "the big one starting low: beak down at the left (+0.65), yaw +-1.0, beak up -1.0, roll "
                       "+-0.25, slow through the top, half way down at the right (+0.3)",
                       yaw=1.0, p0=0.65, top=-1.0, p_end=0.3, roll=0.25, a1=3.15, linger=0.7, tail=0.45),
}
# rejected 2026-10-10 (debug renders): neck_low -0.6 at both ends: the joint went -0.41 at the ends and -0.52 at the top
# (the stand policy dips the neck whenever the beak goes up), so no taller circle, only head mass forward (the real duck steps).
# rejected 2026-10-10: body pose on the arc (bow +0.07 at the left, lean back -0.12 and z +0.008 at the top):
# the trunk moved 2 deg at most and the policy pulled the head down instead (beak up at the top -0.21 instead of -0.79).


# ---------------------------------------------------------------------------------------------------------------
# sounds: ONE continuous vocalisation per motion, low -> intense -> low, on the arc's own timeline
# ---------------------------------------------------------------------------------------------------------------
def contour(arc, t_abs, lo, hi, end):
    """Pitch (Hz) along the sound: a short 'w' scoop up, an eased rise to `hi` at the peak, an eased fall to `end`."""
    rise = (t_abs - arc.s0) / (arc.s_peak - arc.s0)
    fall = (t_abs - arc.s_peak) / (arc.s1 - arc.s_peak)
    up = 0.5 - 0.5 * np.cos(np.pi * np.clip(rise, 0, 1))
    dn = 0.5 - 0.5 * np.cos(np.pi * np.clip(fall, 0, 1))
    semis_up, semis_dn = 12 * math.log2(hi / lo), 12 * math.log2(end / hi)
    out = np.where(t_abs < arc.s_peak, lo * ST ** (semis_up * up), hi * ST ** (semis_dn * dn))
    scoop = 1.0 - 0.10 * np.exp(-np.maximum(t_abs - arc.s0, 0) / 0.05)   # the 'w': starts a little flat, slides in
    return out * scoop


def timbre_mix(arc, dur, freq, loud, dark, bright, am_scale=0.6):
    """Render the same tone twice (same jitter / vibrato stream) with a dark and a bright timbre, and crossfade them
    with the loudness: 'oo' at the ends, 'aa' at the top (the w-o-w of the mouth)."""
    env = np.asarray(loud)
    a = quack(p, dur, freq, env, mods=dark, rng=Rng(0x57A5), am_scale=am_scale)
    b = quack(p, dur, freq, env, mods=bright, rng=Rng(0x57A5), am_scale=am_scale)
    w = np.clip(env, 0, 1) ** 1.5
    return a * (1 - w) + b * w


DARK = dict(tilt=2.8, brightness=0.05, nasal=0.15, formant_gain=0.0, quackiness=p.quackiness * 0.5, breath=0.08)
BRIGHT = dict(tilt=1.5, brightness=0.55, nasal=0.75, quackiness=p.quackiness * 0.7, breath=0.04)


def sound(arc, kind):
    t0 = arc.s0
    dur = arc.s1 - arc.s0
    t = t_axis(dur)
    ta = t + t0
    loud = np.array([arc.loud(x) for x in ta])
    loud *= np.clip(t / 0.04, 0, 1)                                       # soft 40 ms onset
    f0 = p.pitch_center_hz
    if kind == "W1_swell":
        freq = contour(arc, ta, 0.74 * f0, 1.70 * f0, 0.60 * f0)
        sig = timbre_mix(arc, dur, freq, loud, DARK, BRIGHT)
    elif kind == "W2_wobble":
        freq = contour(arc, ta, 0.74 * f0, 1.70 * f0, 0.60 * f0)
        wob = np.sin(2 * np.pi * 5.2 * t) * (0.15 + 0.75 * loud ** 2)          # the awe wobble swells at the top
        freq = freq * ST ** (0.55 * wob)
        sig = timbre_mix(arc, dur, freq, loud, dict(DARK, vibrato_depth=0.0), dict(BRIGHT, vibrato_depth=0.0))
    elif kind == "W3_ride":
        # the duck's own wheee recipe (voices.rs wheee_segments) retimed on the arc: f0 * 0.85 -> f0 * top, a flick
        # up at the top, a long fall to f0 * 0.6; its excitement wobble; louder in the middle (the wheee is flat)
        r = Rng(0x3EEE)
        top = 1.6 + 0.5 * p.pitch_spread + 0.25 * r.random()
        freq = contour(arc, ta, 0.85 * f0, top * f0, 0.60 * f0)
        flick = 1.0 + 0.04 * np.exp(-((ta - arc.s_peak - 0.15) / 0.12) ** 2)
        wob = np.sin(2 * np.pi * (4.5 + 3.0 * r.random()) * t) * (0.15 + 0.85 * np.clip((ta - t0) / (arc.s_peak - t0), 0, 1))
        freq = freq * flick * ST ** (0.5 * wob)
        joy = dict(vibrato_depth=p.vibrato_depth * 0.5, quackiness=p.quackiness * 0.5)
        sig = quack(p, dur, freq, loud, mods=joy, rng=Rng(0x3EEF), am_scale=0.5, breath_scale=0.5)
    else:
        raise ValueError(kind)
    sig = normalise(sig, -3.0)
    buf = np.zeros(int((arc.total + 0.5) * SR))
    i = int(round(t0 * SR))
    buf[i:i + len(sig)] += sig[: len(buf) - i]
    return buf


SOUNDS = {
    "W1_swell": "one tone, 176 Hz rising to 405 Hz at the top and falling to 143 Hz, loudness swelling to the top; the timbre opens "
                "from a dark 'oo' to a bright 'aa' and closes again (w-o-w)",
    "W2_wobble": "W1 plus a 5 Hz awe wobble that swells at the top (wooOOoOOow)",
    "W3_ride": "the duck's own wheee (ride) recipe retimed on the arc: rises to its top note, a little flick up, a long fall; "
               "its excitement wobble",
}
# first round: every motion with W1, the plain arc with the other two sounds
RENDERS = [("wow_arc", "W1_swell"), ("wow_arc_roll", "W1_swell"), ("wow_big", "W1_swell"),
           ("wow_arc", "W2_wobble"), ("wow_arc", "W3_ride"),
           ("wow_low", "W1_swell"), ("wow_low_half", "W1_swell"), ("wow_low_big", "W1_swell")]


def wav_path(motion, snd):
    return HERE / "sounds" / f"{motion}__{snd}.wav"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orbit", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--sounds-only", action="store_true")
    a = ap.parse_args()
    for mname, snd in RENDERS:
        stem = f"{mname}__{snd}"
        if a.only and a.only not in stem:
            continue
        arc = ARCS[mname]
        wav = wav_path(mname, snd)
        write_wav(wav, sound(arc, snd), -3.0)
        if a.sounds_only:
            print("wrote", wav)
            continue
        m = arc.motion()
        if a.orbit:
            import orbit
            lib.beats_sheet = lambda *a_, **k: None
            orbit.CAMS[mname] = dict(z=0.15, dist=0.62, elev=-6, centre=180)
            orbit.install(mname, m.total)
            meas = lib.render(m, wav, HERE / "orbit_motion", HERE / "clips", sound=snd, sound_desc=SOUNDS[snd], mouth_mode="motion", quiet=True)
            print(stem, "orbit done", "FELL" if meas["fell"] else "no fall")
        else:
            lib.render(m, wav, HERE / "motion", HERE / "debug", sound=snd, sound_desc=SOUNDS[snd], mouth_mode="motion")


if __name__ == "__main__":
    main()
