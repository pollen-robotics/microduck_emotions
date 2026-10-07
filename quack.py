"""Python port of the robot's voice synth (`sounds/` in pollen-robotics/microduck), for designing
emotion sounds on the Mac with the SAME duck identity as the robot.

The personality traits (pitch centre, timbre, quackiness...) are derived with an exact port of the
Rust RNG (splitmix64 + xoshiro256++), so `Personality(4145077059)` is this robot's voice. Per-sample
noise (jitter, breath) uses numpy's RNG seeded from that stream: same character, not bit-identical.

Main entry point for candidate design:

    from quack import Personality, quack, write_wav, note, seq
    p = Personality(4145077059)
    sig = quack(p, dur=1.0, contour=[(0.0, 300), (0.3, 250), (1.0, 120)], env=("expdecay", 0.02, 0.6))
    write_wav("/tmp/x.wav", sig)

`contour` is a list of (time_s, hz) points (piecewise linear, like the Rust recipes), or a full
per-sample frequency array. `env` is ("expdecay", attack_s, decay_s), ("bell", attack_s, release_s),
or an array. `mods` overrides personality fields for this one sound (e.g. {"quackiness": 1.0,
"am_rate_hz": 25.0} for a growl). `seq([...], gaps)` concatenates sounds with silences.
"""
from __future__ import annotations

import math
import wave
import zlib
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

SR = 48_000
TUNED_SR = 22_050.0
TAU = 2 * math.pi
MASK = (1 << 64) - 1
ROBOT_SEED = 4145077059


# ----------------------------------------------------------------------------- RNG (exact port)
class Rng:
    """xoshiro256++ seeded by splitmix64, as in `sounds/src/rng.rs`."""

    def __init__(self, seed: int):
        x = seed & 0xFFFFFFFF

        def nxt():
            nonlocal x
            x = (x + 0x9E3779B97F4A7C15) & MASK
            z = x
            z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
            z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
            return z ^ (z >> 31)

        self.s = [nxt() for _ in range(4)]
        self.spare = None

    @staticmethod
    def _rotl(v, k):
        return ((v << k) | (v >> (64 - k))) & MASK

    def next_u64(self):
        s = self.s
        result = (self._rotl((s[0] + s[3]) & MASK, 23) + s[0]) & MASK
        t = (s[1] << 17) & MASK
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = self._rotl(s[3], 45)
        return result

    def random(self):
        return (self.next_u64() >> 11) * (1.0 / (1 << 53))

    def uniform(self, lo, hi):
        return lo + (hi - lo) * self.random()

    def integers(self, lo, hi):
        return lo + int(math.floor(self.random() * (hi - lo)))

    def choice(self, choices):
        return choices[self.integers(0, len(choices))]

    def standard_normal(self):
        if self.spare is not None:
            z, self.spare = self.spare, None
            return z
        r = 1.0 - self.random()
        theta = TAU * self.random()
        rad = math.sqrt(-2.0 * math.log(r))
        self.spare = rad * math.sin(theta)
        return rad * math.cos(theta)

    def numpy(self):
        """A numpy generator seeded from this stream, for bulk per-sample noise."""
        return np.random.default_rng(self.next_u64())


# ----------------------------------------------------------------------------- personality (exact port)
@dataclass
class Personality:
    seed: int
    pitch_center_hz: float = 0.0
    register: float = 0.0
    pitch_spread: float = 0.0
    glide_bias: float = 0.0
    brightness: float = 0.0
    tilt: float = 0.0
    nasal: float = 0.0
    harmonic_skew: float = 0.0
    formant_n: int = 1
    formant_gain: float = 0.0
    vibrato_rate_hz: float = 0.0
    vibrato_depth: float = 0.0
    jitter_depth: float = 0.0
    breath: float = 0.0
    quackiness: float = 0.0
    am_rate_hz: float = 0.0
    am_depth: float = 0.0
    warble_hz: float = 0.0
    warble_depth: float = 0.0
    attack_sharpness: float = 0.0
    speed: float = 1.0

    def __post_init__(self):
        if self.pitch_center_hz:
            return  # already filled (a `replace` copy)
        rng = Rng(self.seed)
        register = rng.choice([-1.0, 0.0, 0.0, 1.0]) + rng.uniform(-0.4, 0.4)
        base = rng.uniform(160.0, 380.0)
        self.pitch_center_hz = min(max(base * 2.0 ** (register * 0.45), 110.0), 620.0)
        self.register = register
        self.pitch_spread = rng.uniform(0.4, 1.2)
        self.glide_bias = rng.uniform(-1.0, 1.0)
        self.brightness = rng.uniform(0.05, 0.55)
        self.tilt = rng.uniform(1.4, 2.8)
        self.nasal = rng.uniform(0.1, 1.0)
        self.harmonic_skew = rng.uniform(-1.0, 1.0)
        self.formant_n = rng.integers(1, 6)
        self.formant_gain = rng.uniform(0.0, 1.4)
        self.vibrato_rate_hz = rng.uniform(3.5, 9.5)
        self.vibrato_depth = rng.uniform(0.0, 0.7)
        self.jitter_depth = rng.uniform(0.03, 0.35)
        self.breath = rng.uniform(0.0, 0.30)
        self.quackiness = rng.uniform(0.2, 1.0)
        self.am_rate_hz = rng.uniform(18.0, 55.0)
        self.am_depth = rng.uniform(0.15, 0.70)
        self.warble_hz = rng.uniform(7.0, 18.0)
        self.warble_depth = rng.uniform(0.0, 1.4)
        self.attack_sharpness = rng.uniform(0.0, 1.0)
        self.speed = rng.uniform(0.82, 1.22)

    def variant_rng(self, tag: str, variant: int) -> Rng:
        h = ((self.seed * 1_000_003) & MASK) ^ zlib.crc32(tag.encode()) ^ ((variant * 2_654_435_761) & MASK)
        return Rng(h & 0xFFFFFFFF)

    def harmonics(self) -> np.ndarray:
        n_harm = 7
        w = []
        for n in range(1, n_harm + 1):
            base = 1.0 / n ** self.tilt
            high_lift = self.brightness * (n / n_harm) ** 1.5
            nasal = self.nasal * (0.6 if n in (2, 3) else 0.0)
            if self.harmonic_skew >= 0.0:
                skew = self.harmonic_skew * (0.4 if n % 2 == 0 else -0.2)
            else:
                skew = -self.harmonic_skew * (-0.3 if n % 2 == 0 else 0.4)
            formant = self.formant_gain if n == self.formant_n else 0.0
            w.append(max(base + high_lift + nasal + skew + formant * base * 1.5, 0.0))
        w[0] = max(w[0], 0.7)
        return np.array(w)

    def with_(self, **mods) -> "Personality":
        return replace(self, **mods)


# ----------------------------------------------------------------------------- DSP primitives
def t_axis(duration_s: float) -> np.ndarray:
    n = max(1, int(round(duration_s * SR)))
    return np.arange(n, dtype=np.float64) / SR


def lerp(t: np.ndarray, points) -> np.ndarray:
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return np.interp(t, xs, ys)


def expdecay(t, attack_s, decay_s):
    a = np.clip(t / max(attack_s, 1e-4), 0, 1)
    d = np.exp(-np.maximum(t - attack_s, 0) / max(decay_s, 1e-4))
    return a * d


def bell(t, attack_s, release_s):
    total = t[-1] if len(t) else 0.0
    rel_start = max(total - release_s, 0.0)
    v = np.ones_like(t)
    v = np.where(t < attack_s, t / max(attack_s, 1e-4), v)
    v = np.where(t > rel_start, np.maximum(1.0 - (t - rel_start) / max(release_s, 1e-4), 0.0), v)
    return np.clip(v, 0, 1)


def phase_from_freq(freq):
    return TAU * np.cumsum(freq) / SR


def harmonic_osc(phase, weights):
    out = np.zeros_like(phase)
    for i, w in enumerate(weights):
        if w:
            out += w * np.sin((i + 1) * phase)
    return out


def vibrato(t, rate_hz, depth_semitones, phase):
    if rate_hz <= 0 or depth_semitones <= 0:
        return np.ones_like(t)
    return 2.0 ** (depth_semitones * np.sin(TAU * rate_hz * t + phase) / 12.0)


def jitter(t, depth_semitones, nrng):
    if depth_semitones <= 0:
        return np.ones_like(t)
    raw = nrng.standard_normal(len(t))
    k = max(1, int(round(64.0 * SR / TUNED_SR)))
    sm = np.convolve(raw, np.ones(k) / k, mode="same")
    return 2.0 ** (depth_semitones * sm / 12.0)


def pink_noise(n, nrng):
    a = 0.985 ** (TUNED_SR / SR)
    white = nrng.standard_normal(n)
    # leaky integrator: y[i] = a*y[i-1] + x[i]
    from scipy.signal import lfilter

    pink = lfilter([1.0], [1.0, -a], white)
    return pink / (np.abs(pink).max() + 1e-9)


def click(n, nrng, length):
    out = np.zeros(n)
    l = min(length, n)
    fade = 1.0 - np.arange(l) / l
    out[:l] = nrng.uniform(-1, 1, l) * fade * fade
    return out


def normalise(x, peak_dbfs=-3.0):
    peak = np.abs(x).max() + 1e-9
    return x * (10 ** (peak_dbfs / 20) / peak)


# ----------------------------------------------------------------------------- the voice
def voice(p: Personality, t, freq, rng: Rng, am_scale=1.0, breath_scale=1.0):
    """Shared core: harmonic osc + vibrato + jitter + AM buzz (quackiness) + breath."""
    vib = vibrato(t, p.vibrato_rate_hz, p.vibrato_depth, rng.uniform(0.0, TAU))
    nrng = rng.numpy()
    jit = jitter(t, p.jitter_depth, nrng)
    f = np.asarray(freq, dtype=np.float64) * vib * jit
    body = harmonic_osc(phase_from_freq(f), p.harmonics())
    am_d = p.am_depth * am_scale * p.quackiness
    if am_d > 0.01:
        body *= 1.0 - am_d * (0.5 + 0.5 * np.sin(TAU * p.am_rate_hz * t))
    breath = p.breath * breath_scale
    if breath > 0:
        body += breath * pink_noise(len(t), nrng)
    return body


def attack_time(p: Personality, dur, snappy):
    soft = 0.04 * dur
    sharp = 0.003 * dur
    return max(soft + (sharp - soft) * p.attack_sharpness * snappy, 0.001)


def quack(p: Personality, dur: float, contour, env=("expdecay", None, None), *, mods=None,
          am_scale=1.0, breath_scale=1.0, rng: Rng | None = None, click_gain=0.0,
          crackle=0.0, peak_dbfs=None) -> np.ndarray:
    """One vocalisation. See the module docstring. Returns float64 mono at SR, not normalised
    unless `peak_dbfs` is given."""
    pp = p.with_(**mods) if mods else p
    rng = rng or pp.variant_rng("emotion", 0)
    t = t_axis(dur)
    if callable(contour):
        freq = contour(t)
    elif isinstance(contour, np.ndarray) and contour.shape == t.shape:
        freq = contour
    else:
        freq = lerp(t, contour)
    if isinstance(env, np.ndarray):
        e = env
    elif env[0] == "expdecay":
        a = env[1] if env[1] is not None else attack_time(pp, dur, 1.0)
        d = env[2] if env[2] is not None else dur * 0.5
        e = expdecay(t, a, d)
    elif env[0] == "bell":
        e = bell(t, env[1], env[2])
    else:
        raise ValueError(env)
    sig = voice(pp, t, freq, rng, am_scale, breath_scale) * e
    if click_gain > 0:
        nrng = rng.numpy()
        sig += click_gain * click(len(t), nrng, int((0.003 + 0.006 * pp.attack_sharpness) * SR))
    if crackle > 0:
        nrng = rng.numpy()
        sig += crackle * nrng.standard_normal(len(t)) * e
    if peak_dbfs is not None:
        sig = normalise(sig, peak_dbfs)
    return sig


# ----------------------------------------------------------------------------- music helpers
def note(name: str) -> float:
    """'A4' -> 440.0; supports sharps '#' and flats 'b'."""
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    n = names[name[0].upper()]
    rest = name[1:]
    if rest.startswith("#"):
        n += 1
        rest = rest[1:]
    elif rest.startswith("b"):
        n += 1 - 2
        rest = rest[1:]
    octave = int(rest)
    midi = 12 * (octave + 1) + n
    return 440.0 * 2 ** ((midi - 69) / 12)


def semitones(hz: float, n: float) -> float:
    return hz * 2 ** (n / 12)


def silence(dur: float) -> np.ndarray:
    return np.zeros(max(0, int(round(dur * SR))))


def seq(parts, gap: float = 0.0) -> np.ndarray:
    """Concatenate sounds, with `gap` seconds of silence between them (or a list of gaps)."""
    out = []
    gaps = gap if isinstance(gap, (list, tuple)) else [gap] * (len(parts) - 1)
    for i, part in enumerate(parts):
        out.append(np.asarray(part, dtype=np.float64))
        if i < len(parts) - 1:
            out.append(silence(gaps[i]))
    return np.concatenate(out) if out else silence(0)


def mix(parts_at, total=None) -> np.ndarray:
    """Overlay [(start_s, signal), ...]."""
    end = max(s + len(x) / SR for s, x in parts_at)
    out = np.zeros(int(round((total or end) * SR)) + 1)
    for s, x in parts_at:
        i = int(round(s * SR))
        n = min(len(x), len(out) - i)
        out[i:i + n] += x[:n]
    return out


def write_wav(path, sig, peak_dbfs=-3.0):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    x = normalise(np.asarray(sig, dtype=np.float64), peak_dbfs) if peak_dbfs is not None else sig
    pcm = np.clip(x * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


def read_wav(path):
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768.0
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
    return sr, x


# ----------------------------------------------------------------------------- ports of two bank recipes
# (used to verify the RNG port against the robot's real bank; also handy raw material)
def alarm(p: Personality, variant: int) -> np.ndarray:
    rng = p.variant_rng("alarm", variant)
    dur = (0.20 + 0.12 * rng.random()) / p.speed
    t = t_axis(dur)
    f0 = p.pitch_center_hz * (1.25 + 0.35 * p.pitch_spread) * (0.94 + 0.12 * rng.random())
    peak_mul = 1.15 + 0.25 * p.pitch_spread + 0.10 * rng.random()
    fall_mul = 0.75 + 0.20 * (1.0 - p.pitch_spread)
    freq = lerp(t, [(0.0, f0), (0.05 * dur, f0 * peak_mul), (dur, f0 * fall_mul)])
    env = expdecay(t, attack_time(p, dur, 1.0), dur * (0.40 + 0.20 * rng.random()))
    sig = voice(p, t, freq, rng, 0.5, 1.0) * env
    crackle = 0.04 + 0.10 * p.brightness
    sig += crackle * rng.numpy().standard_normal(len(t)) * env
    return normalise(sig, -3.0)


def peck(p: Personality, variant: int) -> np.ndarray:
    rng = p.variant_rng("peck", variant)
    dur = (0.16 + 0.12 * rng.random()) / p.speed
    t = t_axis(dur)
    f0 = p.pitch_center_hz * (0.45 + 0.20 * rng.random())
    freq = lerp(t, [(0.0, f0 * 1.5), (0.04 * dur, f0), (dur, f0 * 0.80)])
    env = expdecay(t, attack_time(p, dur, 1.0), dur * 0.35)
    body = voice(p, t, freq, rng, 0.3, 0.5) * env
    click_len = int((0.003 + 0.006 * p.attack_sharpness) * SR)
    body += (0.4 + 0.4 * p.attack_sharpness) * click(len(t), rng.numpy(), click_len)
    return normalise(body, -3.0)


if __name__ == "__main__":
    import sys

    p = Personality(int(sys.argv[1]) if len(sys.argv) > 1 else ROBOT_SEED)
    for k, v in p.__dict__.items():
        print(f"{k:18s} {v}")
