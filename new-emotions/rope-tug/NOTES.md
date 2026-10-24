# Rope tug emotion (episode 4): running notes

Brief: `/Users/remi/microduck/notes/emotion-rope-tug/BRIEF.md` (Rémi by voice, 2026-10-24). Session microduck-8b.
Options page: https://claude.ai/artifact/XNYTdv54tneHotnYu2fckv (republish `page/index.html`, root = this folder, then ONE
Artifact open call after an update he waits for).

## The scene (Fable story session agentic-robot-theater-b1, 2026-10-24)

Episode 4 beat "pull" (`/Users/remi/reachy_mini_apps/agentic_robot_theater/scenes/season_story_fable/ep4_final.html`,
`episode4/scene.json`): Reachy Mini sits on the floor, silent, head low, antennas down; the episode 3 leash is tied round
his base; the duck holds the knotted free end in its beak about 40 cm in front of him and tugs 2-3 times; then Rémi drives
it backward with the pad until the rope slides out; then Reachy's "We must accept our limitations" line while the duck
goes SAD. Film camera: floor level, profile, Reachy frame right, duck frame left, ~1.1 m. The story session wants the
keyframes json path once Rémi picks, to play it in its own sim take.

## Files

- `rope_tug.py`: motions (class `Tug`: keyed PCHIP channels + shiver + seeded slow wobble), muffled effort sounds,
  renders (`--debug` for the overlay), `robot/<motion>.json` = robotd emotion file at 50 Hz (robotd interpolates keys
  linearly; the 0.1 s keys of lib's json would flatten the 0.2 s yanks).
- `rope_scene.py`: Reachy (fixed, asleep) at x 0.40, rope = chain of capsule links on ball joints (8 mm, 34 cm, 30 g/m),
  link 0 fixed in the head between the lips, last link held on Reachy's base by an equality connect (anchor 2 set after
  compile: the compiler would take it at qpos0). Rope contacts the floor only (bit 4).
- `clips/` (page videos, 1280x720), `orbit_motion/` (silent + keyframes + log), `sounds/` (+ spectrograms.png).

## Findings (2026-10-24)

- **duckfilm feeds the body pose into the wrong policy slots.** `Duck._policy_tick` puts body (z, roll, pitch) at
  command[7:10], but the policies read (x, y, z, roll, pitch, yaw) at command[7:13] (robotd `duck-control/src/obs.rs`,
  microduck_rl `tasks/symmetry.py`). So in every lib/duckfilm render "body_pitch" acted as z and "body_z" went to the
  unbound x. robotd is right, so the robot was never affected; the old sim videos with a body pose do not show what the
  robot does. Patched only inside `rope_tug.py` (`_policy_tick_robotd_layout`); duckfilm itself untouched (other
  sessions use it). This also explains the WOW note "body pose on the arc makes the policy pull the head down".
- With the right layout, the shipped stand policy in sim (kp 160) barely tracks body z: -0.02 / -0.05 do nothing,
  -0.12 gives 1 cm; +0.01 rises 2 mm. It tracks pitch: -0.10 -> trunk +5.6 deg back, -0.18 -> +9.9 deg, ~0.5-1 s to
  settle, neck dips -0.4 to keep the head. So the "legs up and down" = a lean back into each pull (knees and ankles bend).
  The small z dip (-0.02) stays in the files in case the real policy follows it.
- Seen head yaw is about 0.8 of the command on the fast yanks (EMA + policy); the beak goes down ~+0.2 on the pulls.
- The 8 mm rope at 31 cm was taut once the stand policy settled (beak drops from 0.193 to 0.171 m): 34 cm used.
- duckfilm's `beak_tip` site is 3.7 cm below the real lips (head frame x -0.045 vs lips at x -0.008).
- Camera: any swing toward the front puts Reachy between the camera and the duck; kept to the film's profile (az 93 ->
  105, 0.74 -> 0.68 m, look-at between them).

## Round 1 (2026-10-24 ~11:15)

Motions (all with E1): `tug3` (3 pulls right, 0.50/0.64/0.76, last held), `tug3_alt` (right/left/right),
`tug2_shake` (2 pulls then a worrying shake at 3.3 Hz). Sounds on tug3: S0 silent, E1 grunts (one muffled rising
"nnngh" per pull, 90 ms raised-cosine attack, low-passed ~1 kHz, seed 4145077059), E2 = E1 + sniffs + end puff, E3 growl
(one continuous AM 24 Hz "rrrr" swelling per pull). All: no fall, drift <= 0.9 cm, trunk pitch -1..+8 deg, neck down to
-0.59, roll at its 0.27 limit on the big pulls, mouth 0 throughout.

Next: Rémi picks; iterate; then robot set (`<name>.json` + `<name>.wav`, name probably `tug`) and the guided test on
graphite (`notes/home-wifi/duck-emotions` pattern). Nothing on the robot without his go; nothing published.
