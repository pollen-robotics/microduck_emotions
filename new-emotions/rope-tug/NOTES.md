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

## Round 2 (2026-10-24 ~12:00): his pick, bigger

Rémi (voice via secretary): picks "two pulls then a shake" with the E1 grunts; wants bigger pulls ("I don't see the rope
tighten"); asks about the sim bug; wants branches pushed (never main); robot 3 gets the old voice; kicks back.

- `shake_big`: pulls 0.80 / 0.95 (were 0.55 / 0.72), shake around -0.62 +-0.34 at 3.3 Hz; yaw command clipped at +-1.0
  (the trained head range; the shiver had pushed it to -1.07). Same json for both stagings.
- Rope physics, measured with a slack rope: facing Reachy the knot gets only 0.5 cm (round 1) / 1.1 cm (round 2)
  further from the tie (the beak swings ACROSS the rope); a bigger lean (0.20) adds nothing (the policy dips the neck to
  -0.80 to keep the head). Side-on staging (`stage=60`: Reachy 60 deg to the duck's left) gives 2.6 cm per pull.
  Rope lengths: facing 33 cm (rest straightness 0.98 -> 0.994), side-on 35.7 cm (0.962 -> 0.990).
- Overrun check on shake_big (stand policy, kp 160): no joint target past its limit; peak speeds head yaw 2.6 rad/s,
  knees 1.6, neck 1.5.
- Robot files: `robot/set/rope_tug.json` (= shake_big.json, 276 keys at 50 Hz, mouth 0) + `rope_tug.wav` (E1, 5.5 s,
  48 kHz mono int16 like the shipped set). Guided test: `duck-rope-tug` (DUCK_HOST=..., installs, one restart with
  motors off, knot in by hand while resting, Enter per try, notes to rope-tug-test.log). Not run.

## The sim bug, measured on the six shipped emotions with a body pose (2026-10-24)

Replaying robot/emotions/<name>.json in duckfilm, old layout vs robotd layout: sad (bp 0.05) old sim bobs 0.8 cm / robot
bows 2.6 deg; impatient (0.068) 0.6 cm / 2.5 deg; mock (0.099) 1.7 cm / 4.5 deg; laugh (0.10) 1.8 cm / 5.0 deg; excited
(0.12) 2.3 cm / 5.2 deg; angry (0.14) 2.6 cm / 5.5 deg. Old sim: almost no bow (trunk pitch within ~2 deg). The robot
does what the files say (a small bow, no height change), which is what Rémi saw. duck-sim (robotd in the loop) was right.

## Branches pushed (2026-10-24, his go: own branches, never main, no PR)

microduck `ground-pick-mouth` (ec406c9), microduck_emotions `robot-set` (da7adaa) and `new-emotions` (c2c5e1e: WOW +
rope tug folders, without media and without wow/voice-seed, whose script holds the factory sudo password),
microduck_rl `ground-grasp` (31fcfe0). Already there: microduck `play-emotions` (PR #384). Not pushed (older or secret,
ask): microduck `pad-expressions` (23 commits, Sep 6), microduck_rl `emotions-stomp`, `flamingo-allcol`,
`wip/tricks-infer-policy`, `hostile-terrain` (ahead 1), microduck-challenges `arena-campaign` + 18 `v-*` (Arena = secret).

## Kicks + shoot duck setup (2026-10-24 ~12:40)

- Kicks were only unbound (4b47953c emptied LB/RB defaults); kick_left/right ONNX unchanged in v8 (sha256 d6928284…,
  147a32c3…). Branch microduck `kicks-on-main` (pushed): origin/main 942e58e3 + 57f294a7 (bumpers kick by default) +
  e603c93f (play-emotions cherry-pick, one conflict in robotctl/src/configure.rs). 1735 tests pass. CI build
  daemon-dev-kicks-on-main = **0.17.8-dev.1433.e603c93**, downloaded to ~/duck-sideload-kicks. The 9bcdc89 release is
  gone from GitHub (rollback only via a robot's kept previous release).
- Main on alpha (zero3, hw_rev 1): supported; needs `[bus] fast_sync_read = false`; v8 velstand drives faster, turns
  slower; **idle glances and yawns open the beak** (glance_mouth 0.4, yawn_every_s 90) -> would drop the rope: set 0.0.
  updater auto_apply default "mandatory" keeps a sideloaded build (check it is not "all").
- `notes/shoot-setup/duck-shoot-setup <host>`: read-only report, install on Enter with motors off (settings backed up
  *.bak-2026-10-24), tomlset.py for fast_sync_read/idle, 13 emotions + rope_tug, old voice seed (backup
  sounds.bak-before-seed-<hostname>, `--revert-voice`), one robotd restart, checks. Not run yet: robot 3 unknown.

## Robot 3 = cream-converse, set up (2026-10-24 ~14:50)

BLE name cream-converse, serial <serial>, wlan MAC <mac>, <lan-ip> (`ssh cream-converse`), alpha
(zero3), allow_dev_keys true. Rémi typed the Wi-Fi password in `notes/home-wifi/duck-wifi cream-converse`. Now on the kicks
build, idle beak shut, 14 emotions, first duck's voice, pad y (top, X label) = rope_tug, x (left, Y label) = sad. Details in
`notes/shoot-setup/setup.log`. Camera daemon fails on this duck since provisioning (no sensor probed), not ours.
