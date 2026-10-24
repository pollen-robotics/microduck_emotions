# Microduck new emotion "ROPE TUG" for episode 4: brief (Remi by voice, 2026-10-24 morning, relayed by the secretary)

## Remi's words (from a long episode 4 review dictation; transcription fixes in brackets)

"Also, I think we need a side movement for the rope thing. So the video, once the camera is on the robots,
we need to see the duck trying with its beak, with a lateral movement. So mainly a yaw movement on the head.
I think it would be good if the legs also move up and down a little bit. Not too much, but something that
makes the movement feel like it's alive. So the problem with the movements that are code-based is that they
feel very robotic and not like an animal. And the movements done through RL, reinforcement learning,
typically look more like an animal moving, and it's more natural. I think you can do the rope [tugging] by
starting through a pre-programmed movement where it does the [tug?] thing on the side two or three times,
and then afterwards I'll just use the controller, and I make it try to go back until the rope slides and
falls on the ground. Okay? But I think that's one task. Maybe start an agent on that. As always, the same
procedure we always do, where I've got candidate moves on the page and I choose between several ones and we
iterate until we get the correct move. By the way, this is like an emotion, like the emotions we did and
pushed. So it should be the same format. But let's make it so that this one has no sound. Or maybe? Maybe it
could be a small sound of effort. Yeah, let's try it. That's interesting."

## What that means (secretary's reading, check it against the episode 4 script)

- A new emotion in the same format as the pushed emotions (pollen-robotics/microduck_emotions, the
  play-emotion skill): the duck grips a rope with its beak and tugs it sideways two or three times, mainly
  head yaw, with small, lively leg up/down motion so it does not look robotic. After the emotion ends,
  Remi takes over with the gamepad and backs the duck up until the rope slides and falls.
- Candidate moves as videos on a page; he picks and you iterate. Offer variants without sound and with a
  small effort sound (strain/grunt in the duck's voice), since he wants to try that.
- Shooting of episodes 4 to 6 is planned for today (2026-10-24): a first set of candidates soon matters
  more than polish.

## Secretary notes (house rules and pointers, not new orders)

- How emotions were made before: `/Users/remi/microduck/notes/emotions-workshop/`,
  `/Users/remi/microduck/notes/emotions/` (emotions.json, keyframes, sounds, robot/, PLAY-EMOTION-PR-*.md),
  and the most recent one, the WOW emotion: `/Users/remi/microduck/notes/emotion-wow/` (BRIEF, NOTES,
  wow.py, motion/, sounds/, page/). Follow the WOW process; it worked well. The `mujoco-scenes` skill covers
  renders.
- Episode 4 script and sim takes belong to the session `agentic-robot-theater-b1` (Reachy Mini and
  Microduck story, page claude.ai/artifact/SdrgGy25azC1NFQtAC7qPb). Coordinate with it by SendMessage for
  the rope scene (when the camera is on the robots, rope length/size) and tell it when a move is chosen so
  its sim take can use it. The grasp RL work is in `/Users/remi/microduck/notes/ground-grasp/` (its first
  grasp video had the duck holding something sideways; reuse what helps).
- Nothing moves and no sound plays on a physical duck without Remi's go. A real-robot test gets a guided
  script (one command that prints each step and reports back). Respect joint limits on the real robot.
- Options page: a Claude artifact with the video options (sound on, the camera framing used before),
  concise first. The first publish opens by itself: never run `open` after publishing. Each in-place update
  he waits for (new candidates) ends with exactly one Artifact `open` call on the same URL.
- Mac memory (36 GB, it froze before): one heavy render at a time across all agents, a heavy job only with
  at least 40 percent free (`memory_pressure -Q`), at most 3 parallel MuJoCo renders. The theater session
  also renders: coordinate.
- Nothing published (public emotions repo, HF dataset, socials, PRs) without his go.
- Reporting: the options page is the notification. End your final messages with a `Spoken:` paragraph; add
  a `Notify:` line only when he must decide something no page shows, or a real-robot test is ready.
