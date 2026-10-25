# WOW emotion + the old duck's voice on graphite: running notes

Brief: `/Users/remi/microduck/notes/emotion-wow/BRIEF.md` (Rémi by voice, 2026-10-10). Session microduck-fd.
Options page: https://claude.ai/artifact/NP8Jdi7yG9TN2LXFsXx3Mz (republish from `page/index.html`, root = this folder).
**2026-10-25: republished on Rémi's current Claude account as https://claude.ai/artifact/6zJiYtirjn1eoRHYJZsanu** (the old link
belongs to his other account's organization). Republish the same `page/index.html` with root = this folder.

## The voice seed

- **The previous duck (remi_duck, ssh microduck@<lan-ip>) had seed 4145077059.** It is the hash of its chip serial
  (`sounds::seed_from_id`, sha256 of `/proc/device-tree/serial-number`, first 8 hex digits). Evidence:
  `reachy-encounter/NOTES.md` 2026-09-02 ("this robot's seed is 4145077059"), the theater repo `microduck/README.md`
  ("The seed comes from the chip serial (this robot: 4145077059)"), and `emotions-workshop/quack.py`, whose port was checked
  sample-exact against that duck's real bank (alarm a-c, peck a-c). Ten other seeds were rendered on 2026-09-02 for
  auditioning (`reachy-encounter/voices/`); nothing in the notes or the transcripts shows Rémi picked one, so the old duck
  kept its own. All 14 emotion wavs (and the WOW sounds) are made with 4145077059.
- graphite (serial <serial>, if that is its device-tree serial) derives 72045712 by itself.
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

## Episode 5 (2026-10-25): WOW on the duck (session microduck-8b)

No pick was ever recorded, so the latest option, **low · big** (`wow_low_big__W1_swell`), is the default `wow`. Robot files
in `robot/`: `wow.json` + `wow.wav` (low · big, 4.5 s), plus `wow_low` and `wow_low_half` (3.9 s) to try by command. The
keyframes are the motion files with only the robotd fields kept, and the wavs are the W1 renders unchanged (sound
from 0.83 s, aligned to the keyframes' t = 0). They're installed on cream-converse by `notes/shoot-setup/duck-ep5`, with
pad Y (robot `x`) = wow.

## Round 3 (2026-10-25): the sound, on the final motion (session microduck-8b)

Rémi (voice via secretary-37): **the motion is final: low · big** ("super exaggerated, the best"). For the sound, W2 wobble is
the best so far but "sounds too much like the duck is trying to be a ghost". He wants it to start lower, rise more and be more
exaggerated, keeping the big O / small O shape. His idea: copy a real human "wow" in the klaxon voice, and make several options.

- References, analysis only, never published. Seven Owen Wilson "wow" film clips (owen-wilson-wow-api) and the myinstants
  cartoon "anime wow", which several sites host as one and the same clip. All noisy (music, crowds). The exaggerated ones
  start low, rise 9-14 st, peak a little before halfway and fall 7-9 st; the drawled ones only fall. They were kept in the
  session scratchpad, not in the repo.
- The ghost diagnosis: W2's pure, breathy dark "oo" at both ends of a slow symmetric glide. The new timbres HORN_OO,
  HORN_AA and KLAXON keep the buzz (quackiness, AM, nasal 2nd and 3rd harmonics) and drop the breath.
- `wow.py --round3`: W2_wobble, W4_lower, W5_human, W6_klaxon, W7_big_o, W8_cartoon, each muxed onto the existing orbit
  film `clips/wow_low_big__W1_swell.mp4`. No new simulation was needed: the beak follows `Arc.loud`, not the wav, and that
  clip's audio is the wav from t = 0 (checked by cross-correlation: offset 0.0 s, correlation 1.0). Energy above 800 Hz is
  54-71% for all of them, so they carry on the small speaker (rope_tug's was 5%). The pitch tracker confirms each designed
  contour.
- Robot files in `robot/`: `wow` = low · big + W2 (the Y placeholder until he picks), plus wow_lower, wow_human, wow_klaxon,
  wow_big_o and wow_cartoon on the same keyframes. `duck-ep5` installs all of them. wow_low and wow_low_half were dropped
  now that the motion is decided.
- Page version 2 (same URL), new top section. Waiting for his pick; then replace `robot/wow.wav` and put it on the duck.

## Round 4 (2026-10-25): W5 human, shorter

Rémi: "the best one is the W5 human one, but the middle sound is too long, so we don't understand that's a wow. Make it shorter,
a few variations. W8 cartoon is a great thing to keep, for comedic effects." The recipe is unchanged, only shorter (`wow.py --orbit
--round4`, retimed sound start, peak and end). The beak follows the sound, so these were simulated again (1.7 GB peak RSS, no fall,
0.2 cm drift, head keyframes identical to `wow`):
W5a_short 1.6 s and W5b_shorter 1.2 s and W5c_quick 0.85 s all peak on the seen top (2.14 s); W5d_at_left is 1.2 s from the
left start (0.82 s). Robot names: wow_short / wow_shorter / wow_quick / wow_at_left. `wow` (Y) = W5 human as it is, on the
unchanged keyframes, until he picks. wow_cartoon = W8, kept, on no button. Removed from robot/: wow_lower, wow_klaxon,
wow_big_o, wow_human. duck-ep5 now deletes wow_* files on the duck that are no longer in robot/. Page version 3.
