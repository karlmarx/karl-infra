# Pickleball Voice Scorekeeper

Android app that keeps the score of a pickleball game by listening from midcourt.

- It hears the players **call the score** and works out **which end** the call came from.
- When nobody calls it, it hears the **ball sounds stop and start again**, notes **which side the
  next serve came from**, and infers what must have happened from the rules.
- Offline, on-device, **no LLM and no per-use cost** — the vocabulary is ~60 words and the rules of
  pickleball throw away almost every misrecognition on their own.

| Document | What's in it |
|---|---|
| **[LOGIC.md](LOGIC.md)** | The logic diagrams: signal chain, rally detection, the scoring state machine, how an uncalled rally is resolved, how a spoken call is parsed and filtered, change of ends, failure modes. |
| **[DESIGN.md](DESIGN.md)** | Everything around them: placement and hardware assumptions, audio pipeline detail, recogniser choice, sync to watch/second phone/LED board, app shape, risks, roadmap. |
| **[engine/](engine/)** | The scoring engine — pure Kotlin, no Android dependencies, 46 unit tests. |

## Status

- ✅ **M0** logic design
- ✅ **M1** scoring engine (rules · speech grammar · hypothesis tracker · snapshots · tests)
- ⬜ **M2** Android audio layer — see the roadmap in [DESIGN.md](DESIGN.md#status-and-roadmap)

## Engine at a glance

```kotlin
val engine = ScoreEngine(GameState.newGame(MatchConfig(doubles = true, pointsToWin = 11)))

engine.observe(Observation.ServeDetected(t, CourtSide.NEAR, sideConfidence = 0.94))
engine.observe(Observation.RallyEnded(t, hits = 7))
engine.observe(Observation.SpokenCall(t, listOf("sevens", "on", "one"), CourtSide.NEAR))

engine.snapshot().callText   // "7-1-1"
engine.snapshot().ambiguous  // false — only one legal call fits what was said
```

```bash
cd engine && gradle test
```
