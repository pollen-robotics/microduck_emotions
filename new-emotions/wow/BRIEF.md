# Microduck new emotion "WOW" + voice seed: brief (Remi by voice, 2026-10-10, relayed by the secretary)

## Remi's words (verbatim; transcription fixes in brackets)

"okay another request for a different agent that will work on Microduck in the same way we've created the 13 or
14 emotions i want to create another one or a few other ones so please look up how it was done the other ways
the previous way the previous times and and do it in a similar fashion because it's been working really well
including the fact that I want options open up in my browser through videos, and we iterate on the movement and
we iterate on the sounds and stuff like that. By the way, my Microduck is now off, but on my previous Microduck,
which is not the physical same one, we had a specific voice, right? We have generated a specific seed for it.
And I want to make sure that the seed is the same on this one. So please find it and find that seed. And next
time I boot up my macro doc [Microduck], please switch it to this seed so that my character remains identical.
Do not... create a new one because if for some reason we're not able to retrieve the previous one honestly the
current version I have has a nice sounding voice very close to the previous one so I mean it wouldn't be the
end of the world if we were not able to update it Now the emotion I want to generate here is the WOW emotion,
like being amazed. And the movement I want is an exaggerated left to right half circle of the head where it
goes WOW. A long WOW. like starting to the left, opening the beak, and then going up, and then the aftercommon
[after coming] reaching to the right. And next, exaggerated WOW motion with a single... sound that that goes
from low to intense to low again so wow and yeah that will be the first emotion maybe I have other ideas
afterwards"

## Secretary notes (house rules and pointers, not new orders)

- How it was done before: `/Users/remi/microduck/notes/emotions-workshop/` (README, HANDOFF, NOTES,
  EPISODE3-HANDOFF*.md, motion/, sounds/, showcase/), `/Users/remi/microduck/notes/emotions/` (README,
  emotions.json, keyframes, sounds, robot/, PLAY-EMOTION-PR-*.md) and
  `/Users/remi/microduck/notes/SHOWCASE-BRIEF-2026-10-01.md`. The agent that made them is the session
  `microduck-a5` (its context is huge, so send it short questions by SendMessage only if the notes are not
  enough). `microduck-08` made the play-emotion PR. `microduck-75` trains a grasp move (RL) and renders too.
- The current duck is "graphite" (home Wi-Fi, SSH set up by the session that was microduck-bb, see
  `/Users/remi/microduck/notes/home-wifi/`). The PREVIOUS duck was a different unit: find its voice seed
  (notes, sounds folders, quack.py, robot config, git history). Never generate a new seed. If you cannot
  find it, say so and leave graphite's current voice as it is.
- Remi already gave the go to switch graphite to the old seed. graphite is off now: apply it the next time
  it is reachable (a light check every few minutes is fine, or when Remi says it is on). Back up the
  current value first, keep the change reversible, and verify it without playing sound or moving the robot.
- Nothing moves and no sound plays on a physical duck without Remi's go. A real-robot test gets a guided
  script (one command that prints each step and reports back).
- Options page: a Claude artifact with the video options (sound on, the circular camera like before),
  concise first. The first publish opens by itself: never run `open` after publishing. Each in-place update
  he waits for (new movement or sound options) ends with exactly one Artifact `open` call on the same URL.
- Mac memory (36 GB, it froze before): one heavy render at a time across all agents (microduck-75 renders
  too, so coordinate with it by SendMessage); a heavy job only with at least 40 percent free
  (`memory_pressure -Q`); at most 3 parallel MuJoCo renders.
- Nothing published (the public emotions repo pollen-robotics/microduck_emotions, the HF dataset,
  socials, PRs) without his go.
- Reporting: the options page is the notification. End your final messages with a `Spoken:` paragraph;
  add a `Notify:` line only when he must decide, or when the seed is applied or found missing (no page
  shows that).
