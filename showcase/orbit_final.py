#!/usr/bin/env python
"""The emotion clips for the final social cut: mujoco-scenes-df's orbit_bg.py (each emotion re-filmed by its own
renderer on a scenekit preset) with the quality fixes Rémi asked for on 2026-10-07:

- no film grain (it is redrawn every frame and shimmers, worst at night), bloom 0.25 at night;
- 1.5x supersampling everywhere (edges, stars and fireflies stop crawling as the camera turns);
- the shadow box: restored to the preset's extent BEFORE the render context is created (see FinalRenderer); it was
  hundreds of metres wide, hence the blocky, blinking shadows on the desk and the detached one on the beach;
  optional soft shadows per preset with SHOWCASE_SOFT=desk=4,night=2;
- the silent clip is written at CRF 10 instead of 20 (the dark scenes blocked up in the old encode chain).

    SHOWCASE_PRESET=desk SHOWCASE_CAM='{...}' /Users/remi/microduck/.venv-mjlab/bin/python orbit_final.py impatient OUT_DIR
"""
import math, os, sys
from pathlib import Path

import numpy as np

BG = Path("/Users/remi/mujoco_scenes/projects/emotions_bg")
sys.path.insert(0, str(BG))
import orbit_bg as OB  # noqa: E402  (patches orbit.py: preset scenes, kit renderer)
import imageio  # noqa: E402
import mujoco  # noqa: E402

PRESET = OB.PRESET
SOFT = {k: int(v) for k, v in (x.split("=") for x in os.environ.get("SHOWCASE_SOFT", "").split(",") if x)}
GRADE = {"grain": 0.0, **({"bloom": 0.25} if PRESET == "night" else {})}

_mimwrite = imageio.mimwrite


def mimwrite(path, frames, **kw):
    ps = list(kw.get("output_params", []))
    if "-crf" in ps:
        ps[ps.index("-crf") + 1] = "10"
    kw["output_params"] = ps
    return _mimwrite(path, frames, **kw)


imageio.mimwrite = mimwrite

_build = OB.preset_build_scene


def build(*a, **k):
    m, d = _build(*a, **k)
    if PRESET == "forest":
        m.vis.map.shadowclip = 5.0          # set before the render context exists (it bakes extent x shadowclip)
    if PRESET == "beach" and os.environ.get("SHOWCASE_BEACH_SUN_UP"):     # optional: a higher sun, shorter shadow
        i = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_LIGHT, "sun")
        dx, dy = m.light_dir[i][0], m.light_dir[i][1]
        h = math.hypot(dx, dy)
        el = math.radians(22.0)
        dn = np.array([dx / h * math.cos(el), dy / h * math.cos(el), -math.sin(el)])
        m.light_dir[i] = dn
        m.light_pos[i] = np.array([0.0, 0.0, 0.1]) - 1.5 * dn
    return m, d


OB.preset_build_scene = build


class NoSelfShadowKR(OB.KR.Renderer):
    """The kit renderer, but the robot never shows its own shadow (Rémi, 2026-10-07: a pixelated shadow edge crossing
    the duck's face reads as a colour change). Each frame is drawn twice, with and without shadows, plus a segmentation
    pass: the duck's pixels come from the shadowless render, everything else (its shadow on the ground included) from
    the shadowed one. Grade and depth effects then apply to the composite as before."""

    def __init__(self, *a, robot_prefix="duck_", **k):
        super().__init__(*a, **k)
        m = self.sc.model
        self.robot_geom = np.array([(m.body(m.geom_bodyid[g]).name or "").startswith(robot_prefix) for g in range(m.ngeom)])

    def raw(self, cam, depth=False):
        rgb, dep = super().raw(cam, depth=depth)                 # shadows on (soft if configured)
        scn = self.r.scene
        self._update(cam)
        scn.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = 0
        flat = self.r.render().copy()
        scn.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = 1
        self.r.enable_segmentation_rendering()
        seg = self.r.render().copy()
        self.r.disable_segmentation_rendering()
        ids, types = seg[..., 0], seg[..., 1]
        mask = (types == int(mujoco.mjtObj.mjOBJ_GEOM)) & (ids >= 0)
        mask[mask] = self.robot_geom[ids[mask]]
        return np.where(mask[..., None], flat, rgb), dep


class FinalRenderer(OB.KitOrbitRenderer):
    def __init__(self, m, height=None, width=None):
        super().__init__(m, height, width)
        self.kr.close()
        # THE shadow bug: MuJoCo bakes extent * shadowclip into the render context when it is created, and the emotion
        # code has just recomputed the extent from the whole terrain (141 m on the beach): the shadow box then spans
        # hundreds of metres (10 cm per shadow texel). Restoring the preset's extent per frame comes too late; restore
        # it before the context exists.
        if id(m) in OB.STAT:
            m.stat.center[:], m.stat.extent = OB.STAT[id(m)]
        KRC = NoSelfShadowKR if os.environ.get("SHOWCASE_SELF_SHADOW", "0") != "1" else OB.KR.Renderer
        self.kr = KRC(self.sc, size=OB.O.SIZE, fovy=OB.FOVY, ssaa=1.5, grade=GRADE,
                                 soft=SOFT.get(PRESET, 0), soft_deg=0.8)


OB.KitOrbitRenderer = FinalRenderer

if __name__ == "__main__":
    OB.O.render(sys.argv[1], sys.argv[2])
