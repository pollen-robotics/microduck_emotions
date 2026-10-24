# WOW emotion + the old duck's voice on graphite: running notes

Brief: `/Users/remi/microduck/notes/emotion-wow/BRIEF.md` (Rémi by voice, 2026-10-10). Session microduck-fd.
Options page: https://claude.ai/artifact/NP8Jdi7yG9TN2LXFsXx3Mz (republish from `page/index.html`, root = this folder).

## The voice seed

- **The previous duck (remi_duck, ssh microduck@192.168.1.29) had seed 4145077059.** It is the hash of its chip serial
  (`sounds::seed_from_id`, sha256 of `/proc/device-tree/serial-number`, first 8 hex digits). Evidence:
  `reachy-encounter/NOTES.md` 2026-09-02 ("this robot's seed is 4145077059"), the theater repo `microduck/README.md`
  ("The seed comes from the chip serial (this robot: 4145077059)"), and `emotions-workshop/quack.py`, whose port was checked
  sample-exact against that duck's real bank (alarm a-c, peck a-c). Ten other seeds were rendered on 2026-09-02 for
  auditioning (`reachy-encounter/voices/`); nothing in the notes or the transcripts shows Rémi picked one, so the old duck
  kept its own. All 14 emotion wavs (and the WOW sounds) are made with 4145077059.
- graphite (serial cec2b3808a7238ff, if that is its device-tree serial) derives 72045712 by itself.
- How the robot gets its voice: `sounds ensure-bank` (run by every release's postinstall) renders
  `/var/lib/robot/sounds/<tag>/*.wav` + a `.seed` marker `seed:bank_version`. `--seed N` overrides the hardware seed.
  robotd reads the wavs at play time (quacks switch at once) and caches the personality for the theremin/chorale from the
  marker (switches at the next robotd start). **A release install re-runs ensure-bank from the serial and brings graphite's
  own seed back**: rerun the script after an update (no config option for the seed on main; a small PR could add one).
- `voice-seed/apply-old-seed.sh`: backs up the bank once to `/var/lib/robot/sounds.bak-before-seed-2026-10-10`, keeps any
  extra folders, renders seed 4145077059, verifies the marker and the tag folders. No sound, no motion. `--check`, `--revert`.
  Log: `voice-seed/apply.log`. A background watcher (this session) pings graphite every 3 min and runs it once it is up.

## WOW round 1 (2026-10-10, simulation)

`wow.py` (debug renders into `debug/` + `motion/`; `--orbit` = showcase look 720x1280 into `clips/`). Built on
`emotions-workshop/motion/episode3/lib.py` (its ROOT patched to the workshop) and `showcase/orbit.py` (studio scene + orbit).

- The arc: yaw = A cos(theta), head_pitch = p0 - (p0 - top) sin(theta), theta 0 -> pi (cubic Hermite, zero end speed).
  Into the left pose 0-0.45 s, arc 0.75-2.55 s (big: 0.75-3.15 with a slow stretch through the top), hold 0.5 s, home 0.6 s.
- Lag command -> seen head: **0.19 s** (yaw crosses 0 and the beak is highest 0.17-0.19 s after the command). The sound and
  the beak are placed on the seen head: sound from a0 + 0.07, peak at the seen top, ends 0.35 s after the seen right arrival.
- Beak: scripted (`mouth_mode="motion"`): opens just before the sound, 0.55 + 0.45 x loudness, shuts as it dies.
- Measured (debug): no fall, drift <= 0.1 cm, trunk pitch within 1 deg. Joints: yaw reaches the command, beak up -0.79 for
  -0.85 (big: -0.96 for -1.0). **The stand policy dips the neck by itself when the beak goes up** (-0.19 at rest -> -0.43).
- Rejected: body pose (bow at the left, lean back + z up at the top): trunk moved 2 deg at most and the head pitch at the top
  dropped to -0.21. Neck -0.6 at both ends: joint -0.41 at the ends, -0.52 at the top anyway: no taller circle, only head mass
  forward (the real duck steps forward when the head's mass goes forward).
- Sounds (seed 4145077059, pitch centre 238 Hz): W1 swell 176 -> 405 -> 143 Hz, loudness 0.3 -> 1 -> 0, dark/bright timbre
  crossfade (two renders on the same jitter stream) = w-o-w; W2 = W1 + 5 Hz wobble growing to the top; W3 = the wheee recipe
  (voices.rs wheee_segments) retimed: 202 -> 522 Hz, flick, long fall, its excitement wobble. `sounds/spectrograms.png`.
- Page: motion row (arc, arc+roll, big; all W1) and sound row (W1, W2, W3 on the arc).

Next: Rémi picks; iterate; then robot set (`emotions/robot/make_robot_set.py` format: `<name>.json` keyframes + `<name>.wav`,
`robotctl robot do wow` on graphite's play-emotions build) and a guided test script. Nothing on the robot without his go.

## WOW round 2 (2026-10-10): starting low

Rémi (voice via secretary): "the head should start lower because it would be more dramatic; keep these three but iterate;
starts pointing down and up and down again, or down and up then half distance". New `p_end` (the beak height at the right;
the first half of the arc runs from p0, the second half to p_end). Added, all with W1: `wow_low` (+0.65 / -0.85 / +0.65),
`wow_low_half` (+0.65 / -0.85 / +0.3), `wow_low_big` (big timing, yaw 1.0, top -1.0, roll, +0.65 -> +0.3).
Measured: no fall, drift <= 0.3 cm, beak down reaches +0.68..+0.72, top still 0.19 s after the command (big: yaw crosses 0
0.08 s later, inside the slow stretch). With the beak down the stand policy LIFTS the neck (-0.19 -> -0.01..-0.11), so a
low start does not push the head mass forward. Page: new section "Starting low" above the round 1 motions (version 2).

## Seed applied on graphite (2026-10-10 20:06 CEST)

graphite came up at 20:05; the watcher ran `apply-old-seed.sh`: marker 72045712:5 -> **4145077059:5**, 82 wavs, all 7 tag
folders, no extra folders. Backup of graphite's own voice: `/var/lib/robot/sounds.bak-before-seed-2026-10-10` (5.2 MB,
marker 72045712:5); `apply-old-seed.sh --revert` puts it back. `sounds` printed the old duck's personality (237.9 Hz,
quackiness 0.63). Nothing played, nothing moved. robotd was started at boot before the change, so quacks already use the old
voice but the theremin/chorale personality follows at its next start (reboot or robotd restart; not done, it is Rémi's).
