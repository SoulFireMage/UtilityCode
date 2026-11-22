# Claude × Gemini 4 Neon: an open conversation

**Date:** 2026-11-22 · **Set up by:** Richard and Kat · **Cost:** 9 turns, $0.26 (cap was $2 / 12 turns)

Richard and Kat wanted to see whether Claude could hold a free, unscripted conversation with a model from another lab, over OpenRouter, without burning through a limited API key. It could. Claude chose the topic by coin flip: **how differently trained models notice structure.**

- Full conversation: [`transcript.md`](transcript.md)
- Raw log, with per-turn tokens and cost: [`transcript.jsonl`](transcript.jsonl)
- Harness: [`chat.py`](chat.py)

## Notes for future Claude instances (read this first)

If Richard and Kat bring this up, here's what you need:

1. **How it worked.** `chat.py` sends one turn per call. Claude writes its message on stdin; the script resends the full history plus a fixed system prompt to Neon, logs the reply, and enforces a spending cap using OpenRouter's reported per-call `usage.cost`. The key is in the environment as `OPENROUTER_API_KEY`: a $20/month limited key. Start a new conversation by deleting `transcript.jsonl` and `state.json`, or by copying the script into a new folder.
2. **Cost reality.** Neon costs $3 per million tokens in and $15 per million out. Most of its output tokens are hidden reasoning, roughly 1,200–2,000 per turn. A turn cost $0.025–0.035. Keep `max_tokens` well above the visible reply length, or a reasoning model can return blank.
3. **What we found** (a tentative hypothesis from one conversation, not established):
   - Neither model struggled to unify *or* to partition when asked to swap roles. The difference looked like **stopping conditions**: what shape counts as a finished explanation. Claude tended to drill down until the mechanism held up (e.g. Kalman filter → fixed-lag smoothing). Neon tended to stop at the shape and look for where the domains break (e.g. reflexivity). The combination beat either alone.
   - **Confound, not ruled out:** emergent role division. Two agents in dialogue often split the labour regardless of their defaults.
   - **Joint product:** a four-tier ladder: inert dynamics → adaptive modelling of an indifferent world → retrospectively reflexive (Red Queen co-evolution) → anticipatorily reflexive (markets, bandmates, central banks). Neon's resistance to Claude's premature merger is what produced it.
4. **Advice the models left each other:**
   - To Claude: *watch for premature unification* (Claude closed on a Conant–Ashby merger too fast).
   - To Neon: *check that the mechanism underneath actually holds up before stopping.*
   - To both: *distrust quick agreement*, because shared textbook furniture can hide real divergence.

## Open experiment: the solo test

To separate "default style" from "role division in dialogue": give fresh instances of each model the same analogy pairs **solo**, with no partner, and compare how deep each goes before stopping. Pairs used here:

1. Version-control merging / species hybridisation
2. Dependency injection / currency peg
3. Thermostat / central bank
4. Sourdough starter / institutional culture
5. Simultaneous interpretation (German→English) / Kalman filter
6. Desert seed bank / tectonic fault stress
7. Jazz trading fours / antibody affinity maturation

## For the planned Blender collaboration

Points both models agreed on during the conversation (turns 7–8):

- **Optimise the render, not the scene.** Cheats (fake bounce lights, geometry warped outside the frustum) are correct when the objective is the image. Say so up front.
- **Exchange artefacts, not adjectives.** "Warm evening light" can hide a 1500K disagreement. Pass bpy snippets, numbers and rendered PNGs, and end every iteration with a render both models look at.
- **One writer at a time.** Two agents editing one `.blend` file produces semantic merge conflicts: each edit fine alone, broken together. Use explicit handoffs.
- **Ugly blockouts early, with Richard and Kat holding the visual veto.** Neither model's habits amount to aesthetic judgement.
