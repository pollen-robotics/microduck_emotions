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
# round 3 (Rémi 2026-10-25: W2 is the best, but it "sounds like a ghost"; start lower, rise more, exaggerate, keep the big
# and small O's, the klaxon tonality). The ghost is the near-sine dark "oo" with breath on a slow symmetric glide: the
# klaxon timbres keep their buzz (quackiness, AM, nasal 2nd/3rd harmonics) at both ends and lose the breath.
HORN_OO = dict(tilt=2.1, brightness=0.15, nasal=0.55, quackiness=p.quackiness * 0.9, breath=0.0, vibrato_depth=0.0)
HORN_AA = dict(tilt=1.4, brightness=0.60, nasal=0.95, quackiness=p.quackiness * 1.1, breath=0.0, vibrato_depth=0.0)
KLAXON = dict(tilt=1.25, brightness=0.70, nasal=1.0, quackiness=min(p.quackiness * 1.4, 1.0), breath=0.0, vibrato_depth=0.0)


def contour_human(arc, t_abs, lo, hi, end, onset=0.85):
    """The shape of the real wows measured on 2026-10-25 (internet clips, kept local): a low start, a rise that is fast
    at first and settles into the top (ease-out), the peak a little before halfway, then a fall that starts slowly and
    drops into the closing 'w' (ease-in). The 'w' slides in from `onset` x lo."""
    rise = np.clip((t_abs - arc.s0) / (arc.s_peak - arc.s0), 0, 1)
    fall = np.clip((t_abs - arc.s_peak) / (arc.s1 - arc.s_peak), 0, 1)
    up, dn = 1 - (1 - rise) ** 2.2, fall ** 1.8
    semis_up, semis_dn = 12 * math.log2(hi / lo), 12 * math.log2(end / hi)
    out = np.where(t_abs < arc.s_peak, lo * ST ** (semis_up * up), hi * ST ** (semis_dn * dn))
    return out * (onset + (1 - onset) * (1 - np.exp(-np.maximum(t_abs - arc.s0, 0) / 0.06)))


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
    elif kind == "W4_lower":
        # W2 exactly, only the range: from two octaves under the top instead of one and a bit
        freq = contour(arc, ta, 0.50 * f0, 2.00 * f0, 0.55 * f0)
        wob = np.sin(2 * np.pi * 5.2 * t) * (0.15 + 0.75 * loud ** 2)
        freq = freq * ST ** (0.55 * wob)
        sig = timbre_mix(arc, dur, freq, loud, dict(DARK, vibrato_depth=0.0), dict(BRIGHT, vibrato_depth=0.0))
    elif kind == "W5_human":
        freq = contour_human(arc, ta, 0.55 * f0, 1.90 * f0, 0.62 * f0)
        wob = np.sin(2 * np.pi * 5.0 * t) * (0.10 + 0.90 * loud ** 2)
        freq = freq * ST ** (0.8 * wob)
        sig = timbre_mix(arc, dur, freq, loud, HORN_OO, HORN_AA, am_scale=0.85)
    elif kind in ("W5_light", "W5_smooth", "W5_clean", "W5_swell"):
        # round 5 (Rémi: W5 short is the one, but "still a bit of a ghost, too oscillating"): W5 with less or no wobble
        freq = contour_human(arc, ta, 0.55 * f0, 1.90 * f0, 0.62 * f0)
        oo, aa, am = HORN_OO, HORN_AA, 0.85
        if kind == "W5_light":                     # a third of the wobble, and only right at the top
            freq = freq * ST ** (0.25 * np.sin(2 * np.pi * 5.0 * t) * loud ** 3)
        elif kind == "W5_clean":                   # no wobble, no jitter, half the buzz's tremolo: the plainest tone
            oo, aa, am = dict(HORN_OO, jitter_depth=0.0), dict(HORN_AA, jitter_depth=0.0), 0.45
        elif kind == "W5_swell":                   # no wobble; one overshoot past the top that settles: a single "O"
            ov = np.exp(-((ta - arc.s_peak + 0.05) / 0.16) ** 2)
            freq = freq * ST ** (1.5 * ov)
        sig = timbre_mix(arc, dur, freq, loud, oo, aa, am_scale=am)
    elif kind == "W6_klaxon":
        freq = contour_human(arc, ta, 0.55 * f0, 1.90 * f0, 0.62 * f0)
        wob = np.sin(2 * np.pi * 5.0 * t) * (0.10 + 0.90 * loud ** 2)
        freq = freq * ST ** (0.8 * wob)
        sig = quack(p, dur, freq, loud, mods=KLAXON, rng=Rng(0x57A5), am_scale=1.0)
    elif kind == "W7_big_o":
        # the big O and the small O, slow enough to hear each: 3.2 Hz swells of pitch AND loudness, deepest at the top
        freq = contour_human(arc, ta, 0.50 * f0, 2.00 * f0, 0.55 * f0)
        depth = 0.2 + 0.8 * loud ** 2
        swell = np.sin(2 * np.pi * 3.2 * (t - 0.15))
        freq = freq * ST ** (1.6 * depth * swell)
        loud = loud * (1.0 + 0.30 * depth * swell) / 1.3
        sig = timbre_mix(arc, dur, freq, loud, HORN_OO, HORN_AA, am_scale=0.85)
    elif kind == "W8_cartoon":
        # a short low 'w' that leaps up an octave and a half in 0.3 s, a fast wobble on the held top, then a long slide
        # down past where it started
        a0, a1 = arc.s0 + 0.10, arc.s0 + 0.40
        k_up = np.clip((ta - a0) / (a1 - a0), 0, 1)
        k_up = k_up * k_up * (3 - 2 * k_up)
        f_lo, f_hi, f_end = 0.45 * f0, 2.10 * f0, 0.42 * f0
        fall = np.clip((ta - (arc.s_peak + 0.30)) / (arc.s1 - arc.s_peak - 0.30), 0, 1)
        fall = fall * fall * (3 - 2 * fall)
        freq = f_lo * ST ** (12 * math.log2(f_hi / f_lo) * k_up) * ST ** (12 * math.log2(f_end / f_hi) * fall)
        wob = np.sin(2 * np.pi * 6.5 * t) * np.clip((ta - a1) / 0.3, 0, 1) * (1 - fall)
        freq = freq * ST ** (0.9 * wob)
        sig = timbre_mix(arc, dur, freq, loud, HORN_OO, KLAXON, am_scale=0.9)
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
    "W4_lower": "W2 with a bigger range: 119 Hz up to 476 Hz (two octaves) and down to 131 Hz; same timbre and wobble",
    "W5_human": "the real wow's shape: low start, fast rise settling into a held top, slow then sudden fall; 131 -> 452 -> 148 Hz; "
                "a wider wobble; the klaxon's buzz kept from the oo to the aa, no breath",
    "W6_klaxon": "W5's pitch in the full klaxon voice: bright, nasal, buzzing all the way through",
    "W7_big_o": "big O, small O: 3.2 Hz swells of pitch and loudness you can count, 119 -> 476 -> 131 Hz, klaxon oo/aa",
    "W8_cartoon": "a low 'w' that leaps up an octave and a half in 0.3 s, a fast wobble on the held top, a long slide down below "
                  "the start; klaxon at the top",
}
# first round: every motion with W1, the plain arc with the other two sounds
RENDERS = [("wow_arc", "W1_swell"), ("wow_arc_roll", "W1_swell"), ("wow_big", "W1_swell"),
           ("wow_arc", "W2_wobble"), ("wow_arc", "W3_ride"),
           ("wow_low", "W1_swell"), ("wow_low_half", "W1_swell"), ("wow_low_big", "W1_swell")]


# round 3: the motion is final (low big); only the sound changes, so each one is muxed onto the same film
ROUND3 = ["W2_wobble", "W4_lower", "W5_human", "W6_klaxon", "W7_big_o", "W8_cartoon"]
FILM = HERE / "clips" / "wow_low_big__W1_swell.mp4"     # the orbit film of the final motion; its audio is the wav from t = 0


def round3():
    import subprocess
    arc = ARCS["wow_low_big"]
    for snd in ROUND3:
        wav = wav_path("wow_low_big", snd)
        write_wav(wav, sound(arc, snd), -3.0)
        out = HERE / "clips" / f"wow_low_big__{snd}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(FILM), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
        print("wrote", out.name)


# round 4 (Rémi 2026-10-25: "W5 human is the best, but the middle is too long, so we don't understand it's a wow"):
# W5's recipe, unchanged, on a shorter sound. The motion stays; only where the sound sits on it changes, and the beak
# follows the sound (it opens just before it and shuts as it dies), so these are simulated again, not muxed.
SEEN_TOP = ARCS["wow_low_big"].s_peak         # 2.14 s: the head at its highest, as seen
ROUND4 = {   # label: (sound start, peak, end), absolute seconds
    "W5a_short": (SEEN_TOP - 0.60, SEEN_TOP, SEEN_TOP + 1.00),      # 1.6 s, peak on the top
    "W5b_shorter": (SEEN_TOP - 0.45, SEEN_TOP, SEEN_TOP + 0.75),    # 1.2 s, peak on the top
    "W5c_quick": (SEEN_TOP - 0.30, SEEN_TOP, SEEN_TOP + 0.55),      # 0.85 s, a spoken "wow!" on the top
    "W5d_at_left": (ARCS["wow_low_big"].s0, ARCS["wow_low_big"].s0 + 0.45, ARCS["wow_low_big"].s0 + 1.20),  # 1.2 s, as the head leaves the left
}


# round 5: W5 short's timing (so the same film and beak), smoother sounds; muxed like round 3
ROUND5 = {"W5a_light": "W5_light", "W5a_smooth": "W5_smooth", "W5a_clean": "W5_clean", "W5a_swell": "W5_swell"}


def round5():
    import subprocess
    arc = retimed(ARCS["wow_low_big"], *ROUND4["W5a_short"])
    film = HERE / "clips" / "wow_low_big__W5a_short.mp4"
    for label, kind in ROUND5.items():
        wav = wav_path("wow_low_big", label)
        write_wav(wav, sound(arc, kind), -3.0)
        out = HERE / "clips" / f"wow_low_big__{label}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(film), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
        print("wrote", out.name)


def retimed(arc, s0, s_peak, s1):
    import copy
    a = copy.copy(arc)
    a.s0, a.s_peak, a.s1 = s0, s_peak, s1
    return a


def round4():
    import orbit
    lib.beats_sheet = lambda *a_, **k: None
    orbit.CAMS["wow_low_big"] = dict(z=0.15, dist=0.62, elev=-6, centre=180)
    for label, (s0, sp, s1) in ROUND4.items():
        arc = retimed(ARCS["wow_low_big"], s0, sp, s1)
        wav = wav_path("wow_low_big", label)
        write_wav(wav, sound(arc, "W5_human"), -3.0)
        m = arc.motion()
        orbit.install("wow_low_big", m.total)
        meas = lib.render(m, wav, HERE / "orbit_motion", HERE / "clips", sound=label, sound_desc=SOUNDS["W5_human"],
                          mouth_mode="motion", quiet=True)
        print(label, f"{s1 - s0:.2f} s", "FELL" if meas["fell"] else "no fall", "drift", meas.get("drift_cm"))


def wav_path(motion, snd):
    return HERE / "sounds" / f"{motion}__{snd}.wav"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orbit", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--sounds-only", action="store_true")
    ap.add_argument("--round3", action="store_true")
    ap.add_argument("--round4", action="store_true")
    ap.add_argument("--round5", action="store_true")
    a = ap.parse_args()
    if a.round5:
        return round5()
    if a.round3:
        return round3()
    if a.round4:
        return round4()
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
