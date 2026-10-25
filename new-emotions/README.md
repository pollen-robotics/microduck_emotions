# New emotions after the 2026-10-07 workshop

Work in progress, on this branch only (not main). Each folder holds the brief (Rémi's words), the running notes, the
renderer and its sounds; the videos are on the options pages, not here.

- `wow/`: WOW (amazed): a half circle of the head from the left over the top to the right, one low-intense-low sound.
  The motion is final (low big); `robot/` holds the robotd files on the duck for episode 5: `wow` (W5 short, on pad Y),
  its smoother sound candidates, and `wild_cartoon` (W8, now also in `robot-set`'s list).
- `rope-tug/robot/set/` is the shipped `rope_tug` (shake big, E1 grunts, staging A).
- `rope-tug/`: ROPE TUG (episode 4): the duck holds a leash in its shut beak and tugs it to the side; `robot/` holds the
  candidate robotd files (50 Hz keyframes, the microduck_emotions format).

The renderers run against this tree's workshop (`motion/episode3/lib.py`, `quack.py`, `showcase/orbit.py`) and
`/Users/remi/microduck/notes/reachy-encounter/duckfilm.py`, by absolute paths on Rémi's Mac.
