"""The episode 4 pull, staged for the emotion renders: Reachy Mini asleep 40 cm in front of the duck, the episode 3 leash
tied round its base, its knotted free end clamped in the duck's closed beak (Fable story session, 2026-10-24: rope about
30 cm, 8 mm thick, from the floor at Reachy's base up to the beak at a shallow angle).

    import rope_scene
    rope_scene.install()          # after orbit.install(): wraps duckfilm.add_duck / build_scene

The rope is a chain of capsule links on ball joints. Link 0 is fixed in the head (the knot between the lips, so it moves
with the head and pulls on it); the last link's end is held on Reachy's base by an equality connect. The rope touches the
floor only (its own contact bit), never the duck or Reachy, so it cannot jam the beak or the policy's feet.
"""
import math
import sys

import mujoco
import numpy as np

sys.path.insert(0, "/Users/remi/microduck/notes/reachy-encounter")
import duckfilm as F  # noqa: E402

REACHY_X = 0.40                     # Reachy's centre, this far from the duck (the duck faces +x)
STAGE_DEG = 0.0                     # where Reachy stands, from the duck's heading (+ = the duck's left): 0 = straight ahead
ROPE_LEN = 0.34                     # m, knot to tie (the story sim: about 30 cm; 31 cm was taut once the stand policy settles)
ROPE_R = 0.004                      # 8 mm rope
LINK = 0.02
ROPE_RGBA = [0.78, 0.64, 0.44, 1.0]  # cotton rope
KNOT_RGBA = [0.70, 0.56, 0.37, 1.0]
ROPE_BIT = 4                        # contact bit shared by the rope (conaffinity) and the floor (contype) only
# the knot, in the head frame (x = up, -z = forward): between the lips (soft_mouth_top x -0.009..-0.006 over jaw_soft
# x -0.016..-0.007, z -0.076..-0.044), 1.4 cm behind the front of the beak. (duckfilm's beak_tip site is 3.7 cm lower.)
CLAMP = np.array([-0.0095, 0.0, -0.062])
OUT_DIR = np.array([-0.45, 0.0, -1.0])        # the rope leaves the beak forward and a little down (head frame)
TIE_H = 0.022                                 # height of the tie round the base

_orig_add_duck = F.add_duck
_orig_build = None


def head_frame_at_spawn():
    """World pose of the head body with the duck spawned at the origin in HOME (what lib.fresh does)."""
    spec = mujoco.MjSpec()
    spec.compiler.degree = False
    spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.05])
    _orig_add_duck(spec, "duck_")
    m = spec.compile()
    d = mujoco.MjData(m)
    du = F.Duck(m, d, "duck_")
    du.spawn(0.0, 0.0, 0.0)
    mujoco.mj_forward(m, d)
    h = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "duck_jaw_soft")
    return d.xpos[h].copy(), d.xmat[h].reshape(3, 3).copy()


def bezier_path(p0, d0, p3, length, n=400):
    """A cubic from p0 (leaving along d0) to p3 (arriving flat along the floor), its handles grown until the curve is
    `length` long: the rope's resting shape, a sag between the beak and the tie."""
    d0 = d0 / np.linalg.norm(d0)
    flat = np.array([p3[0] - p0[0], p3[1] - p0[1], 0.0])
    flat /= np.linalg.norm(flat)

    def curve(k):
        p1, p2 = p0 + k * d0, p3 - k * flat
        s = np.linspace(0, 1, n)[:, None]
        return (1 - s) ** 3 * p0 + 3 * (1 - s) ** 2 * s * p1 + 3 * (1 - s) * s ** 2 * p2 + s ** 3 * p3

    lo, hi = 0.0, 0.5
    for _ in range(60):
        k = (lo + hi) / 2
        c = curve(k)
        if np.linalg.norm(np.diff(c, axis=0), axis=1).sum() < length:
            lo = k
        else:
            hi = k
    return curve((lo + hi) / 2)


def resample(c, n_seg):
    """n_seg + 1 points equally spaced along the polyline c."""
    seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    u = np.linspace(0, s[-1], n_seg + 1)
    return np.stack([np.interp(u, s, c[:, i]) for i in range(3)], axis=1), s[-1] / n_seg


def frame_z(direction):
    """A rotation matrix whose z axis is `direction` (capsules run along their body's z)."""
    z = direction / np.linalg.norm(direction)
    a = np.array([0.0, 1.0, 0.0]) if abs(z[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = np.cross(a, z)
    x /= np.linalg.norm(x)
    return np.stack([x, np.cross(z, x), z], axis=1)


def quat(R):
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, R.flatten())
    return q


def add_rope(spec, prefix="duck_"):
    hp, hR = head_frame_at_spawn()
    knot = hp + hR @ CLAMP
    out = hR @ (OUT_DIR / np.linalg.norm(OUT_DIR))
    tie = tie_world()
    first = 0.022                                                   # link 0: the knot and the rope's exit from the beak
    p1 = knot + first * out
    pts, seg = resample(bezier_path(p1, out, tie, ROPE_LEN - first), int(round((ROPE_LEN - first) / LINK)))
    head = spec.body(prefix + "jaw_soft")
    mass = 0.030 * seg                                              # 30 g/m
    rope_geom = dict(contype=0, conaffinity=ROPE_BIT, condim=3, friction=[0.8, 0.005, 0.0001], rgba=ROPE_RGBA, group=1)
    # link 0, fixed in the head: a knot between the lips and the first 2 cm of rope
    R0 = frame_z(out)
    b = head.add_body(name="rope_0", pos=hR.T @ (knot - hp), quat=quat(hR.T @ R0))
    b.add_geom(type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=[0, 0, 0, 0, 0, first], size=[ROPE_R, 0, 0], mass=0.0006,
               **dict(rope_geom, contype=0, conaffinity=0))
    b.add_geom(type=mujoco.mjtGeom.mjGEOM_ELLIPSOID, size=[0.0055, 0.0072, 0.0060], pos=[0, 0, 0.001], rgba=KNOT_RGBA,
               contype=0, conaffinity=0, mass=0.0005, group=1)
    parent, Rp, pp, Lp = b, R0, knot, first
    for i in range(len(pts) - 1):
        Ri = frame_z(pts[i + 1] - pts[i])
        bi = parent.add_body(name=f"rope_{i + 1}", pos=Rp.T @ (pts[i] - pp), quat=quat(Rp.T @ Ri))
        bi.add_joint(name=f"rope_j{i + 1}", type=mujoco.mjtJoint.mjJNT_BALL, damping=2e-4, armature=2e-6, stiffness=2e-4)
        bi.add_geom(type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=[0, 0, 0, 0, 0, seg], size=[ROPE_R, 0, 0], mass=mass,
                    **rope_geom)
        parent, Rp, pp, Lp = bi, Ri, pts[i], seg
    # the free end is tied round Reachy's base: hold it there
    eq = spec.add_equality(name="rope_tie", type=mujoco.mjtEq.mjEQ_CONNECT, objtype=mujoco.mjtObj.mjOBJ_BODY,
                           name1=parent.name, name2="rm_body")
    eq.data[0:3] = [0, 0, Lp]
    eq.solref = [0.01, 1.0]
    return tie


def reachy_xy():
    a = math.radians(STAGE_DEG)
    return np.array([REACHY_X * math.cos(a), REACHY_X * math.sin(a)])


def tie_world():
    """The tie on Reachy's base, on the side facing the duck."""
    c = reachy_xy()
    u = c / np.linalg.norm(c)
    xy = c - (F.RM_BODY_R + 0.004 + ROPE_R) * u
    return np.array([xy[0], xy[1], TIE_H])


def add_tie_ring(spec):
    """Two turns of rope round Reachy's base (visual only)."""
    rm = spec.body("rm_body")
    r = F.RM_BODY_R + 0.004 + ROPE_R
    n = 20
    for z in (TIE_H - 0.005, TIE_H + 0.004):
        for k in range(n):
            a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            rm.add_geom(type=mujoco.mjtGeom.mjGEOM_CAPSULE, size=[ROPE_R, 0, 0], rgba=ROPE_RGBA, contype=0, conaffinity=0,
                        fromto=[r * math.cos(a0), r * math.sin(a0), z, r * math.cos(a1), r * math.sin(a1), z], mass=0.0001)


def add_duck_with_rope(spec, prefix="duck_", variant=F.CREAM):
    _orig_add_duck(spec, prefix, variant)
    floor = spec.geom("floor")
    if floor is not None:
        floor.contype = floor.contype | ROPE_BIT
    rx, ry = reachy_xy()
    F.add_reachy(spec, rx, ry, math.radians(STAGE_DEG) + math.pi, mobile=False)   # facing the duck, cannot move (story: too heavy)
    add_tie_ring(spec)
    add_rope(spec, prefix)


def build_with_rope(size=(1280, 720), reachy_at=None, reachy_mobile=True):
    m, d = _orig_build(size, reachy_at=None)
    # the tie point on Reachy's base, in its body frame (set explicitly: the compiler would take it at qpos0, where
    # the duck stands at its XML pose rather than spawned in HOME)
    e = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_EQUALITY, "rope_tie")
    rb = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "rm_body")
    mujoco.mj_forward(m, d)
    tie_w = tie_world()
    R = d.xmat[rb].reshape(3, 3)
    m.eq_data[e, 3:6] = R.T @ (tie_w - d.xpos[rb])
    F.Reachy(m, d)                                                    # asleep: head low, antennas down
    return m, d


def install():
    """Wrap whichever scene builder is current (duckfilm's or the showcase studio one)."""
    global _orig_build
    if F.build_scene is build_with_rope:
        return
    F.add_duck = add_duck_with_rope
    _orig_build = F.build_scene
    F.build_scene = build_with_rope
