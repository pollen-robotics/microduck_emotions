# microduck_emotions

## Reuse the emotions

The 14 shipped emotions are in [`export/`](export/): for each one, the motion as a keyframes timeline (JSON, a
sample every 0.1 s) and the sound the robot plays (wav), indexed in `export/emotions.json`.
[`export/README.md`](export/README.md) explains the format and how to play an emotion on a Microduck or in any
simulator, and needs nothing else from this repo. Preview videos: `combined/showcase/clips/`. `quack.py` (numpy and
scipy) makes new sounds in the robot's voice, and `runtime-pad-expressions.patch` is the robot side, for
[pollen-robotics/microduck](https://github.com/pollen-robotics/microduck).
The simulation renderers (`motion/`, `showcase/`, the `sounds/make_*.py` generators) still need the author's
Microduck workspace: they import `duckfilm.py` (not in this repo), the robot model from `microduck_rl` and the
policies from `microduck` through absolute paths.

Licence: Apache-2.0 ([`LICENSE`](LICENSE)). Contributions are very welcome.

The rest of this README is the working log of the design.

Body language and quack sounds for Microduck, designed so that Reachy Mini and Microduck can act emotional scenes
together. Working copy: `/Users/remi/microduck/notes/emotions/` (this repo). Started 2026-09-04.

The rule that guides everything: **sound is paramount**. An emotion is a motion plus a quack designed together,
synchronized beat by beat, and the beak opens with the sound.

## Decided so far

| emotion | motion | sound | status |
|---|---|---|---|
| **devastated** | `motion/sadness/v2/devastated_3x1.0__D3v2_sobs_gentler.mp4`: sit (surprise), head droops, three slow head shakes starting while the head is still going down, hold, rise. Beats in `motion/sadness/v2_spec.json` | `sounds/synced_v2/devastated_3x1.0__D3v2_sobs_gentler.wav`: inquire shock at the sit, silence, three soft sobs (gentler voice) on the head extremes, the third dying into the ending | **decided, tested on the robot: "perfect"** (2026-09-04) |
| **sad** | `motion/sadness/v6/sad_droop2.5__S6_coo_voice_200_140.mp4`: standing, body pitch 0.05, head droops over 2.5 s, two silent slow shakes, hold, rise. Beats in `motion/sadness/v6_spec.json` | `sounds/synced_v6/sad_droop2.5__S6_coo_voice_200_140.wav`: the robot's coo recipe synthesized, gliding 200 -> 140 Hz with the head, silent shakes; robot file `sounds/robot/sad_a.wav` | **decided** (2026-09-04) |
| **curious** (Y, "what? what?") | `motion/curious/curious_two_tilts_r35_leftboost__Q3_up2.mp4`: standing, head forward (neck -0.8, head_pitch -0.35), tilt right +0.35 on the first quack, tilt left -0.44 on the second, hold, back; 3.0 s. Spec `motion/curious/spec_v3.json` | `sounds/curious/curious_two_tilts_r35_leftboost__Q3_up2.wav`: two of the bank's rising chirp blips at 0.6 / 1.2 s, the second 2 semitones higher; robot file `sounds/robot/curious_a.wav` | **decided** (2026-09-04) |
| **angry** (X) | `motion/angry/` pick `bow_snaps`: standing, beak-up glare, four snaps (yaw +0.7/-0.7/+0.7/centre, a short head jab, a small fast bow pulse on the pose slot), beak forced wide 0.3-0.7 s so a held leash drops; 2.6 s. `REPORT.md` there | `sounds/robot/angry_a.wav` four hard barks on the snaps (`angry_b.wav` = a growl into the same barks) | **sim pick (2026-09-06), shipped in the build, not yet tested on the robot** |
| **yes** (LB) | `motion/yes/` pick `yes_single`: one nod, head_pitch +0.7 for 0.25 s, back over 0.35 s; 1.5 s | `sounds/robot/yes_a.wav` one quack falling 3 semitones at 0.45 s | sim pick, shipped, to test |
| **no** (RB) | `motion/no/` pick `no_one`: one yaw shake +0.55 / -0.55 at 0.35 / 0.85 s; 1.8 s | `no_a.wav` "no-ah" (second note a fourth lower), `no_b` nasal, `no_c` drawn-out; the robot picks one | sim pick, shipped, to test |
| **excited** (RT) | `motion/excited/` pick `excited_wag_pump`: six accelerating yaw swings +-0.6 with a body bob (bow pulse +0.12) on each, beak climbing to -0.7, a flourish; 3.4 s | `excited_a.wav` X1 synth climb: each quack higher, shorter, rising more (Rémi's pick) | shipped, to test |
| **play dead** (LT) | `motion/playdead/` pick `pd_v3_dead` (Rémi's second feedback): sit + alarm on the press while the head turns hard to the side (yaw 1.0) and goes back; at 1.4 s `robot.poseJoints`: the three head servos hang free and every leg joint goes to zero over 1.5 s, the seated duck rolls flat onto its back; at 3.6 s the legs come up (hips +-1.0, knees +-1.5); death quack 5.0-6.8 s; 7.5 s; the robot holds the dead pose until Start (no relax, no re-init) | `play_dead_a.wav` bank alarm, silence, a falling synth glide with a dying wobble | v3 shipped, to test on a mat |
| **mmh** (Y), "what do you mean?" | `motion/mmh/`: roll tilt +0.22 from 0.45 s, held, back by 1.6 s; 2.0 s. Rémi's pick from the closed-beak page (the grumbles are dropped) | `mmh_a.wav` a muffled rising "mmh?" | Rémi's pick, shipped |
| **yes, fast** (L3) | the yes nod | `yes_fast_a.wav` a curt "wak" (Y3) | Rémi's pick, shipped |
| **laugh** (R3) | `motion/laugh/` pick `laugh_wag_v2`: beak aimed up (-0.7), yaw swings +-0.45, a body dip on every ha; 3.0 s | `laugh_a.wav` one longer "haaa" then seven short ha's dying out (Rémi's "dying of laughter") | v2 shipped |
| **mock** (cue only) | `laugh_roll`: beak up, the head rolling +-0.35 on every other ha, body dips; 2.6 s | `mock_a.wav` the staccato run "gnagnagnagna" | Rémi's find, shipped as a cue |
| **defiant** (cue only) | `motion/defiant/`: beak up (-0.6) and to the left (yaw +0.6) with a quack, then to the right with a second; 2.2 s | `defiant_a.wav` two curt "wak"s | Rémi's one-shot request, shipped as a cue |
| **impatient** (cue only) | `motion/impatient/`: four quick yaw shakes +-0.4 with a body bob each, then the beak flicks up on a huff; 2.6 s | `impatient_a.wav` four grumbles and a huff | our take (Laureen's is not in her source), shipped as a cue |
| **pick** (cue only) | the ground pick with the beak opening on the way down and shutting at the floor (sim: floor at 0.7 s); 3.0 s | none | shipped |
| angry stomp (RL) | three small stomps (`Mjlab-Stomp*-Flat-MicroDuck`, branch `emotions-stomp` of `microduck_rl`, patch in `rl/`), r3 small-stomp redesign was in progress | barks on the foot contacts | parked (`motion/anger-rl/REPORT.md`) |

Later: excited, scared (see `HANDOFF.md`). Real-robot lessons: anything that moves the head's mass forward makes the walking policy step forward (sad went to half depth, curious lost its head-forward); the simulation does not show it. The Reachy Mini side (scenes, voice, captions) is https://github.com/RemiFabre/agentic_robot_theater (`microduck/EMOTIONS.md` there is the bridge back here).

## What an emotion is

An emotion = a motion + a sound designed together, on one pad button in emotion mode. The motion is one of three kinds:
1. a **program**: head deltas, body pose and mouth as a pure function of time on top of the shipped standing / walking policy (sad, curious);
2. a **policy**: a trained network started as a skill (sit, ground pick, kicks, roulade, the RL stomp when it works);
3. a **combination**: a skill plus a program on top while the skill's policy holds the pose (devastated = sit, then a head program; the head slots track while seated).

Episode 3 (2026-09-06, brief `EPISODE3-HANDOFF.md`): the six emotions above, the pad's emotion mode extended (A sad, B devastated,
X angry, Y mmh, LB yes, RB no, L3 fast yes, R3 laugh, RT excited, LT play dead; Start / Select / sticks / D-pad
untouched; the full map in `BINDINGS.md`), a
**cue port** on the pad daemon (TCP 7777, `{"express":"yes"}` etc., see `NOTES.md`) so one script plays both robots, and the
scene `scenes/episode3` in the theater repo with a simulated preview. Summary page with the six picks and the scene preview:
`combined/episode3/index.html`. Simulator Space fork: https://huggingface.co/spaces/RemiFabre/microduck-reachy-simulator (bundle only).

## Layout

- `HANDOFF.md` the original brief; `NOTES.md` the running log (what was tried, what failed, why; Rémi's decisions).
- `showcase/` (2026-10-01) clean re-renders of the 14 shipped emotions with a slow orbit camera (`orbit.py`) and the
  social-media compilation (`compile.py`); outputs and the shareable page in `combined/showcase/`. See `showcase/README.md`.
- `quack.py` Python port of the robot's Rust voice synth (`microduck/sounds`). `Personality(4145077059)` = this robot;
  the random generator is ported exactly (verified sample-exact against the robot's bank). `quack()` renders one
  vocalisation from a pitch contour + envelope + per-sound personality mods.
- `combine.py` muxes one or more wavs into a motion mp4 at given times.
- `reference/` the four Reachy Mini reference sounds as wav (dataset `pollen-robotics/reachy-mini-emotions-library`).
- `sounds/` candidates and generators: `make_A_port.py` (port of the Reachy flute sounds), `make_B_notes.py` (music
  theory), `make_C_grains.py` (bank grains), `make_long_sad.py`, `make_synced*.py` (soundtracks
  designed on the motion beats), `make_index.py` (audition page `sounds/index.html`), `analysis/` plots.
- `motion/sadness/` the programmatic sad motions: `sadness.py` (simulation renderer built on
  `notes/reachy-encounter/duckfilm.py`: the duck is driven only through what the real robot accepts), per candidate
  mp4 + contact sheet + keyframe JSON (t, neck, head_pitch, head_yaw, head_roll, body_pitch, skill, mouth), `REPORT.md`
  §0 with the expression formulas, `v2/` the three-swing versions with the beak following the sound.
- `motion/anger-rl/` the RL stomp: report, curves, evaluation videos. `rl/` = patch of the `emotions-stomp` branch
  (env, mdp functions, tests, spec) so it can be re-applied on `microduck_rl`.
- `motion/anger-programmatic/` a rejected probe (kept as a record; its two-stomp claims for B4/B5/B8 are wrong).
- `combined/` sound + motion preview pages, one folder per round (`synced/`, `v2/` ... `v6/`); the decided pairs are named in the table above.
- `motion/episode3/lib.py` the shared episode 3 renderer (Motion = pure function of time incl. pose z/pitch, twist, skill, soften,
  relax, mouth; keyframes json, beats sheet, cards); `motion/{yes,no,closed,angry,excited,playdead}/` one renderer + `REPORT.md`
  (formulas, beat table, rejects, questions) + `PICK.json` each; `combined/episode3/` the summary page.

## How to make a new emotion (the recipe that worked)

1. **Motion first, in simulation**, as a pure function of time on the shipped policies (head deltas, body pitch, a
   skill trigger, mouth). Render candidates with `motion/sadness/sadness.py` as the pattern, contact sheets, a page.
   Rémi picks. Write the beats (droop start/end, extremes, hold, rise) in a spec JSON.
2. **Sound on the beats.** Smooth glides, soft attacks, no brutal transitions for sad emotions (hard hits are fine for
   anger). Shock from the existing bank at a surprise beat, silence where nothing happens, one slide per head movement,
   the last one dying away. Normalise the shock and the phrase to the same level. `make_synced_v2.py` is the pattern.
3. **Beak follows the sound**: RMS envelope at 50 Hz -> mouth open in [0, 1]. Render, mux (`combine.py`), page, open it.
4. **Ship**: expression in `padd/src/expressions.rs` (branch `pad-expressions` of the runtime), new `SoundTag` variants
   in `duck-ipc-proto` + `robotd/src/intents.rs`, wav folder under `/var/lib/robot/sounds/<tag>/`,
   `notes/reachy-encounter/ship-to-duck.sh`.

Environment: `/Users/remi/microduck/.venv-mjlab/bin/python` (numpy, scipy, mujoco, imageio); ffmpeg on PATH.
