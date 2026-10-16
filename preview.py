"""Render an emotion's preview video: the Arena simulation plays it, MuJoCo films it up close, the wav goes on top.

    python preview.py sad                      # -> previews/sad.mp4
    python preview.py scared --policy talent.onnx --out /tmp/scared.mp4

Needs the Microduck Arena (https://github.com/pollen-robotics/microduck-arena) installed in the same
Python (it brings mujoco and the robot model), a talent policy (any "Got a Talent" .onnx: it sits,
stands and follows head commands), and ffmpeg on the PATH.

The Arena plays the emotion's timeline (`to_arena.py`) with the policy keeping the duck up; this
script replays the recorded trace in MuJoCo at 30 fps, 1080x1920, with a camera that follows the
duck, opens the beak from the keyframes' `mouth` (the Arena's model has no beak joint, so the two
jaw meshes are turned about the beak hinge), and lays the emotion's sound in at `sound_at_s`.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32" and not hasattr(os, "getloadavg"):
    os.getloadavg = lambda: (0.0, 0.0, 0.0)

import mujoco
import numpy as np

import arena
from arena.constants import CTRL_DT, JOINT_NAMES

import to_arena

HERE = Path(__file__).resolve().parent
ROBOT_XML = Path(arena.__file__).parent / "assets" / "robot" / "legs" / "robot_allcollisions.xml"
FPS = 30
W, H = 1080, 1920
LEAD_S = 1.5          # standing still before the emotion starts (to_arena's default)
PRE_S, POST_S = 0.4, 0.8  # what the video keeps before and after the emotion
# The beak: the jaw meshes turn about this hinge, in the head body's frame (found by eye).
JAW_GEOMS = ("jaw", "jaw_soft")
JAW_PIVOT = np.array([0.0, 0.0, -0.012])
JAW_AXIS = np.array([0.0, 1.0, 0.0])
JAW_OPEN_RAD = 0.45


def scene() -> mujoco.MjModel:
    spec = mujoco.MjSpec.from_file(str(ROBOT_XML))
    spec.visual.global_.offwidth, spec.visual.global_.offheight = W, H
    spec.visual.quality.shadowsize = 4096
    spec.visual.headlight.ambient = [0.35, 0.35, 0.38]
    spec.visual.headlight.diffuse = [0.45, 0.45, 0.45]
    spec.add_texture(name="sky", type=mujoco.mjtTexture.mjTEXTURE_SKYBOX,
                     builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT, rgb1=[0.27, 0.33, 0.45],
                     rgb2=[0.12, 0.15, 0.22], width=512, height=512)
    spec.add_texture(name="grid", type=mujoco.mjtTexture.mjTEXTURE_2D,
                     builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER, rgb1=[0.33, 0.42, 0.58],
                     rgb2=[0.27, 0.35, 0.5], mark=mujoco.mjtMark.mjMARK_EDGE,
                     markrgb=[0.55, 0.65, 0.8], width=512, height=512)
    mat = spec.add_material(name="floor", texrepeat=[8, 8], reflectance=0.15)
    mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = "grid"
    spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.05], material="floor")
    spec.worldbody.add_light(pos=[0.6, -0.8, 2.0], dir=[-0.3, 0.4, -1.0], castshadow=True,
                             diffuse=[0.7, 0.7, 0.7])
    return spec.compile()


def jaw_setter(m: mujoco.MjModel):
    ids = [i for i in range(m.ngeom)
           if m.geom_dataid[i] >= 0 and m.mesh(m.geom_dataid[i]).name in JAW_GEOMS
           and m.geom_group[i] == 2]
    pos0 = {i: m.geom_pos[i].copy() for i in ids}
    quat0 = {i: m.geom_quat[i].copy() for i in ids}

    def set_open(mouth: float):
        q = np.zeros(4)
        mujoco.mju_axisAngle2Quat(q, JAW_AXIS, JAW_OPEN_RAD * float(np.clip(mouth, 0, 1)))
        for i in ids:
            r = np.zeros(3)
            mujoco.mju_rotVecQuat(r, pos0[i] - JAW_PIVOT, q)
            m.geom_pos[i] = JAW_PIVOT + r
            out = np.zeros(4)
            mujoco.mju_mulQuat(out, q, quat0[i])
            m.geom_quat[i] = out
    return set_open


def play_in_arena(name: str, policy: Path, work: Path) -> np.ndarray:
    """Score the emotion's timeline on the talent stage; the recorded trace, (frames, 21)."""
    timeline = to_arena.build([name], LEAD_S, 1.0, 0.05, stay_seated=True)
    tl = work / f"{name}.json"
    tl.write_text(json.dumps(timeline), encoding="utf-8")
    store = work / "store"
    cmd = [sys.executable, "-c", "import os,sys\nif not hasattr(os,'getloadavg'): os.getloadavg=lambda:(0,0,0)\n"
           "from arena.cli import main; sys.exit(main())",
           "score", str(policy), "--event", "got-a-talent", "--timeline", str(tl), "--store", str(store),
           "--name", f"emotion-{name}"]
    env = {**os.environ, "PYTHONUTF8": "1"}
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    run = re.search(r"recorded (\w+)", out.stdout)
    if out.returncode or not run:
        raise SystemExit(f"arena score failed:\n{out.stdout}\n{out.stderr}")
    print(" ", " / ".join(line.strip() for line in out.stdout.splitlines()[:2]))
    with np.load(store / "traces" / f"{run.group(1)}.npz") as z:
        trace = z["trace"].astype(np.float32)
    return trace[0] if trace.ndim == 3 else trace


def mouth_curve(name: str) -> tuple[np.ndarray, np.ndarray]:
    _, frames = to_arena.load(name)
    return np.array([f["t"] for f in frames]), np.array([f.get("mouth") or 0.0 for f in frames])


def render(name: str, trace: np.ndarray, out_video: Path, azimuth: float = 130.0) -> float:
    m = scene()
    d = mujoco.MjData(m)
    adr = np.array([int(m.joint(n).qposadr[0]) for n in JOINT_NAMES])
    set_jaw = jaw_setter(m)
    mt, mv = mouth_curve(name)
    emotion_s = float(mt[-1])
    t0 = max(LEAD_S - PRE_S, 0.0)
    t1 = min(LEAD_S + emotion_s + POST_S, (len(trace) - 1) * CTRL_DT)
    times = np.arange(t0, t1, 1.0 / FPS)

    # The camera follows the trunk slowly, from the duck's left-front (`azimuth` degrees round from
    # behind it: 90 is side on, 180 face on), a little above the head.
    heading = []
    for f in trace:
        w, x, y, z = f[3:7]
        heading.append(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
    yaw0 = float(np.median(heading))
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.distance, cam.elevation = 0.55, -10.0
    cam.azimuth = np.degrees(yaw0) + azimuth
    look = None

    renderer = mujoco.Renderer(m, H, W)
    opt = mujoco.MjvOption()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "20",
                           "-preset", "medium", "-pix_fmt", "yuv420p", str(out_video)], stdin=subprocess.PIPE)
    for t in times:
        i = min(int(t / CTRL_DT), len(trace) - 2)
        a = t / CTRL_DT - i
        f = (1 - a) * trace[i] + a * trace[i + 1]
        d.qpos[0:3] = f[0:3]
        d.qpos[3:7] = f[3:7] / np.linalg.norm(f[3:7])
        d.qpos[adr] = f[7:]
        set_jaw(np.interp(t - LEAD_S, mt, mv, left=0.0, right=0.0))
        mujoco.mj_forward(m, d)
        target = d.qpos[0:3] + np.array([0.0, 0.0, 0.03])
        look = target if look is None else look + 0.08 * (target - look)
        cam.lookat[:] = look
        renderer.update_scene(d, cam, opt)
        ff.stdin.write(renderer.render().tobytes())
    ff.stdin.close()
    ff.wait()
    return LEAD_S - t0  # where the emotion starts in the video


def main() -> None:
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("names", nargs="+")
    ap.add_argument("--policy", type=Path, required=True, help="a Got a Talent policy (.onnx)")
    ap.add_argument("--out", type=Path, help="output file (one emotion only; default previews/<name>.mp4)")
    ap.add_argument("--azimuth", type=float, default=130.0, help="camera: 90 = side on, 180 = face on")
    ap.add_argument("--sound", type=int, default=None, help="which voicing when there are several (default random)")
    args = ap.parse_args()
    if not shutil.which("ffmpeg"):
        raise SystemExit("needs ffmpeg on the PATH")
    for name in args.names:
        entry, _ = to_arena.load(name)
        out = args.out if args.out and len(args.names) == 1 else HERE / "previews" / f"{name}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            print(f"{name}: playing in the Arena")
            trace = play_in_arena(name, args.policy, work)
            print(f"{name}: rendering")
            silent = work / "video.mp4"
            start = render(name, trace, silent, args.azimuth)
            sounds = entry["sounds"]
            wav = HERE / (sounds[args.sound] if args.sound is not None else random.choice(sounds))
            delay_ms = int(round((start + entry.get("sound_at_s", 0.0)) * 1000))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav),
                            "-filter_complex", f"[1:a]adelay={delay_ms}:all=1,apad[a]", "-map", "0:v",
                            "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                            "-movflags", "+faststart", str(out)], check=True)
        print(f"{name}: {out}")


if __name__ == "__main__":
    main()
