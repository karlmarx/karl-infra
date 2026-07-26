# Pickleball Voice Scorekeeper — Design

**Date:** 2026-07-26 · **Status:** Design locked, scoring engine built · **Owner:** Karl

An Android app that sits midcourt and keeps score by listening: it hears the players call the
score, works out which end each call came from, and — when nobody bothers to call it — infers what
happened from the ball sounds and which side the next serve came from.

**Read [LOGIC.md](LOGIC.md) first** if you want the diagrams. This document covers everything
around them: hardware assumptions, the audio pipeline, the recogniser choice, sync, UI, and what is
built versus what is next.

---

## Goals and non-goals

**Goals**

1. Keep an accurate doubles or singles score with **zero taps** during normal play.
2. Work **fully offline** with **no per-use cost** — no LLM API, no speech cloud, no account.
3. Degrade honestly. When the audio genuinely cannot determine the score, say so on screen rather
   than drift silently.
4. Mirror the score to a **Wear OS watch** and a **second Android phone**, with a wire format that a
   BLE LED scoreboard can consume later without redesign.
5. Survive a real court: wind, three games running next to yours, players who mumble, players who
   say "sevens on one", players who never call the score at all.

**Non-goals**

- iOS. This is Android-native Kotlin + Compose end to end — no cross-platform layer, because the
  audio path (raw multi-mic capture with the pre-processing chain disabled) is exactly the thing
  those layers abstract away badly.
- Line calls, let detection, or anything requiring a camera.
- Refereeing. If the players disagree with the app, the app is wrong by definition, and one tap
  fixes it.

---

## Why this can work without an LLM

The vocabulary of pickleball scorekeeping is about **60 words**: the numerals 0–21, the word
*start*, "side out", and a handful of connectives. Everything a player says that matters is a
2-or-3 number sequence.

Two mechanisms replace the language model entirely:

1. **A closed recognition grammar.** The on-device recogniser is restricted to that word list, which
   collapses the error space from "any English sentence" to "which numeral was that". Small offline
   models get dramatically more accurate under a constrained grammar.
2. **A legality filter.** From any given score, the rules of pickleball permit only three or four
   possible next calls. Any reading that is not one of them is discarded no matter how confident the
   recogniser was. This is what turns a mediocre recogniser into a reliable scorekeeper — and it is
   why "sevens on one" and a misheard "seven" for "eleven" both resolve correctly.

Running cost: **zero**. Model download: ~40 MB, once.

---

## Hardware and placement assumptions

| Assumption | Detail |
|---|---|
| Phone position | Sideline at the **net line**, midcourt — net post, fence clip, or a cone. Long axis pointing down the court. |
| Microphones | Two usable mics on the long axis (bottom + top). Effectively every Android phone since ~2016. A third mic improves rejection but is not required. |
| Capture | `AudioRecord`, **stereo, 48 kHz**, `MediaRecorder.AudioSource.UNPROCESSED` where available, `CAMCORDER` as fallback. |
| Power | Screen can be off. Foreground service with an ongoing notification. |

**Why `UNPROCESSED` matters:** the default `VOICE_RECOGNITION` source runs AEC, noise suppression
and AGC, all of which mangle inter-channel timing — which is precisely the signal direction
detection depends on. Check `AudioManager.getProperty(PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED)` at
startup and warn if the device lies about it.

**Mic spacing** is ~14 cm on a typical phone, so the maximum inter-channel delay is
`0.14 m ÷ 343 m/s ≈ 0.41 ms` — about 20 samples at 48 kHz. That is plenty for a **binary** near/far
decision with GCC-PHAT plus parabolic peak interpolation, which is all the engine ever asks for. It
would not be enough to estimate a precise bearing, and the design never asks it to.

---

## Audio pipeline

### Impact (ball) detection

Paddle-on-ball is a near-ideal detection target: a broadband click with a sub-3 ms attack and most
of its energy between 1.5 and 8 kHz — well clear of voice fundamentals and of wind, which is
low-frequency.

- 1024-sample frames, 50% overlap, Hann window.
- Band-limited **spectral flux**; adaptive threshold at `median + k · MAD` over a rolling 3 s
  window, so the detector self-calibrates to the venue.
- Refractory period of 80 ms so one strike is not counted twice off a fence echo.

A rally is a run of impacts with gaps under `RALLY_GAP_MS` (2 s). The rally ends when that gap is
exceeded; the next impact is a serve. **This is the "ball sound stopping and then starting again"
requirement** — see [LOGIC.md §2](LOGIC.md#2-rally-detection-state-machine-audio-layer).

### Direction

For every detected event — impact or utterance — compute GCC-PHAT cross-correlation between the two
channels over a ±0.6 ms lag window. The **sign** of the peak gives NEAR vs FAR; the **magnitude**
gives the court gate.

Because the array points down the court, our players are at endfire (large lag) and neighbouring
courts are off to the side, near broadside (lag ≈ 0). A minimum-lag gate therefore rejects the
court next door on geometry alone, before any scoring logic runs. A secondary level gate, learned
during calibration, catches whatever geometry misses.

Confidence for each event = normalised correlation peak height × how far the lag sits from
broadside. That number is what the engine receives as `sideConfidence`, and it is why a
low-confidence direction estimate can be overruled by the next spoken call instead of corrupting
the score.

### Speech

- Voice activity detection on the downmixed 16 kHz mono stream (energy + zero-crossing + a spectral
  flatness check to distinguish speech from impacts).
- **The recogniser only runs in the window after a rally ends**, roughly 0.5–6 s. That is when the
  score gets called, and gating on it cuts recogniser duty cycle by ~5×, which is most of the
  battery story.
- Recogniser: **Vosk** (Apache-2.0, Kaldi-based) with `vosk-model-small-en-us`, ~40 MB, constructed
  with a **runtime JSON grammar** built from `Numerals.recognitionVocabulary()`. Alternatives
  considered: Android's `SpeechRecognizer` with `EXTRA_PREFER_OFFLINE` (no grammar control, no
  continuous mode guarantees, OEM-dependent) and a custom TFLite keyword-spotting model (best
  accuracy ceiling, needs a labelled dataset first — see roadmap M5).
- The utterance's direction comes from GCC-PHAT over its voiced frames, averaged.

### Estimated battery

Continuous stereo capture plus light DSP is ~3–5%/hour on a modern phone; the duty-cycled
recogniser adds ~2–4%. Budget **6–10%/hour**, which comfortably covers open play. Measure on real
hardware at M2 and revisit if it lands high.

---

## The engine

Pure Kotlin, no Android or IO dependencies, in [`engine/`](engine/). It is a deterministic function
of the observation stream, which means every hard scenario is a unit test rather than a trip to the
courts.

### Why a weighted hypothesis set rather than a single score

Doubles has a structural blind spot. When the serving team loses a rally with server #1, the serve
passes to their partner — **same team, same end of the court**. From the phone's point of view that
is indistinguishable from the serving team winning the point: both leave the next serve on the same
half. No microphone anywhere solves this.

So the engine carries a small weighted set of legally reachable states, rather than picking one and
hoping. Uncalled rallies widen the set by exactly one bit; spoken calls, side outs, and the rules
themselves collapse it again. In practice the set is 1–3 states, and it is almost always 1, because
somebody calls the score within a rally or two.

Singles has no such ambiguity: same side means a point, other side means a side out, always. The
engine collapses to a single hypothesis every rally.

### What the rules do for accuracy

`Rules.candidates()` enumerates only the states that can legally follow the current one. Everything
downstream filters against it:

- A misheard numeral that produces an unreachable score is dropped.
- A call from the court next door almost never happens to be a legal successor of *our* score, so it
  is rejected without any acoustic cleverness.
- A garbled call missing one of its three numbers still lands, because a two-number partial that
  aligns with exactly one legal successor is unambiguous.

### When the players are right and the app is wrong

If a confident, complete, self-consistent call matches nothing the engine believes possible, and
either (a) the players repeat it, or (b) the engine's own confidence is already below 0.45, the
engine **resyncs** to what they said and emits a `Resynced` event. The players are the source of
truth; the app is a convenience.

### Public surface

```kotlin
val engine = ScoreEngine(GameState.newGame(MatchConfig()))

engine.observe(Observation.ServeDetected(t, CourtSide.NEAR, sideConfidence = 0.94))
engine.observe(Observation.RallyEnded(t, hits = 7))
engine.observe(Observation.SpokenCall(t, listOf("four", "two", "one"), CourtSide.NEAR))

engine.snapshot()   // ScoreSnapshot — score, call text, confidence, alternatives, phase
engine.undo()       // step back one observation
engine.correct(state)  // user's finger always wins
```

`MatchConfig` covers doubles/singles, points to win (11/15/21), win-by, hard cap, rally scoring,
the change-of-ends trigger, and best-of.

---

## Sync

One `ScoreSnapshot` feeds every surface, with a monotonic `revision` so receivers can drop stale
packets. Each transport is a thin adapter.

| Target | Transport | Notes |
|---|---|---|
| **Wear OS watch** | Data Layer: `DataClient` for state, `MessageClient` for events | State survives reconnects. Ships with a Tile and an Ongoing Activity so the score is on the watch face. Watch taps (undo, correct, confirm ends switch) come back as `ManualCorrection`. |
| **Second Android phone** | **Nearby Connections**, `P2P_STAR` | Fully offline, no pairing dance, works on public courts with no wifi. Phone with the mic is the host; others are read-only by default, with an "allow corrections" toggle. |
| **BLE LED scoreboard** *(later)* | GATT notify on a custom characteristic | Packed 8-byte frame: `scoreA·u8, scoreB·u8, flags·u8 (serving team, server number, ambiguous), games·u8 (two nibbles), revision·u16, crc·u8`. An ESP32 with a 7-segment or matrix panel is the target. |
| **Cloud** *(optional, off by default)* | Supabase | Match history only, opt-in. The offline path never depends on it. |

Audio never leaves the device. Nothing is written to disk except optional labelled debug clips,
behind an explicit per-session opt-in used for tuning (see M5).

---

## App shape

**Screens**

1. **Match setup** — doubles/singles, points to win, win-by, rally scoring on/off, which team starts
   on the near end, who serves first.
2. **Calibration** (30 seconds, once per venue) — "one player from each end, say your name". Learns
   per-side gain, the broadside gate, and the ambient noise floor. Skippable, with defaults.
3. **Scoreboard** — the whole point:
   - Enormous score, readable from the baseline.
   - Server indicator: which team, server 1 or 2, and which service box they should be in.
   - **Confidence ring** around the score, and an **ambiguity chip** (`or 3-2-2?`) that is tappable
     to pick the other reading.
   - Live direction meter so a mis-placed phone is visible at a glance.
   - Undo, manual score edit, "switch ends" prompt when it is due.
4. **Match history** — local Room database; games, durations, point sequences.

**Behaviour**

- Speaks the score back (TTS) after a side out, optionally — some players want this, some hate it.
- Vibration on the watch at game point and on a side out.
- Keeps running with the screen off; taps on the notification bring it back.

---

## Risks, honestly

| Risk | Severity | Response |
|---|---|---|
| Adjacent-court rejection is worse in practice than in theory | **High** | Geometry gate + level gate + legality filter are three independent layers. If it still leaks, the fallback is a stricter minimum-lag gate, which costs a little sensitivity at the net and nothing at the baseline. |
| Uncalled doubles rallies pile up in silent games | Medium | Ambiguity is displayed, never hidden; one tap resolves. Speaker identification (M5) would remove it entirely. |
| Impact detector fires on other courts' balls | Medium | Same direction gate; impacts also have to fit the rally timing model to matter. |
| OEM microphone processing that cannot be disabled | Medium | Detect at startup, warn, and fall back to level-difference-only direction (worse, still workable at the baseline). |
| Battery worse than budgeted | Low | Duty-cycled recogniser is already the big lever; next lever is dropping capture to 32 kHz between rallies. |
| Players who never call the score *and* play doubles | Low | This is the honest limit of the approach. The app shows a bounded set of possible scores instead of a wrong one. |

---

## Status and roadmap

| Milestone | Contents | State |
|---|---|---|
| **M0** | Logic design + diagrams | ✅ [LOGIC.md](LOGIC.md) |
| **M1** | Scoring engine: rules, grammar, hypothesis tracker, snapshots, 46 unit tests | ✅ [`engine/`](engine/) |
| **M2** | Android app skeleton: foreground service, stereo capture, impact detector, GCC-PHAT direction, on-screen debug meters | ⬜ next |
| **M3** | Vosk integration with the closed grammar; end-to-end scoring on a real court | ⬜ |
| **M4** | Compose scoreboard + Wear OS Data Layer sync + Nearby Connections to a second phone | ⬜ |
| **M5** | Recorded-audio replay harness, threshold tuning from real matches, optional TFLite keyword model, speaker-side identification to kill the doubles ambiguity | ⬜ |
| **M6** | BLE scoreboard packet + reference ESP32 firmware | ⬜ |

### Running the engine tests

```bash
cd pickleball/engine
gradle test        # 46 tests, no network beyond the first dependency fetch
```

The tests are the specification: `RulesTest` pins the pickleball rules, `CallGrammarTest` pins the
speech handling including "sevens on one", and `InferenceTest` drives whole simulated matches
through the engine the way the audio layer will — silent rallies, adjacent-court interference,
misheard numerals, change of ends, game and match end, undo.
