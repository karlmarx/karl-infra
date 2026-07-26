package fyi.n93.pickleball.engine

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Drives a [ScoreEngine] the way the audio layer would, with a clock that advances sensibly. */
private class Sim(state: GameState) {
    val engine = ScoreEngine(state)
    var t = 0L
    var lastEvents: List<EngineEvent> = emptyList()
    val allEvents = mutableListOf<EngineEvent>()

    private fun record(events: List<EngineEvent>): List<EngineEvent> {
        lastEvents = events
        allEvents += events
        return events
    }

    fun serve(side: CourtSide, confidence: Double = 0.92): Sim = apply {
        t += 3_000
        record(engine.observe(Observation.ServeDetected(t, side, confidence)))
    }

    fun rallyEnd(hits: Int = 5): Sim = apply {
        t += 6_000
        record(engine.observe(Observation.RallyEnded(t, hits)))
    }

    fun call(vararg tokens: String, side: CourtSide? = null, confidence: Double = 0.9): Sim = apply {
        t += 1_500
        record(engine.observe(Observation.SpokenCall(t, tokens.toList(), side, confidence)))
    }

    /** A whole rally that nobody bothered to call the score for. */
    fun silentRally(serveSide: CourtSide): Sim = serve(serveSide).rallyEnd()

    fun snapshot(): ScoreSnapshot = engine.snapshot()

    fun callText(): String = snapshot().callText
}

private val WORDS = listOf(
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen",
)

private fun spoken(call: ScoreCall): Array<String> =
    call.asList().map { WORDS[it] }.toTypedArray()

class InferenceTest {

    private val doubles = MatchConfig()
    private val singles = MatchConfig(doubles = false)

    // ---------------------------------------------------------------- silent play

    @Test
    fun `singles is fully determined by serve side alone`() {
        val sim = Sim(GameState.newGame(singles, servingTeam = Team.A, teamOnNearSide = Team.A))

        // A serves and wins the rally: the serve stays on the near side.
        sim.silentRally(CourtSide.NEAR)
        sim.serve(CourtSide.NEAR)
        assertEquals("1-0", sim.callText())
        assertFalse(sim.snapshot().ambiguous)

        // A loses the next one: serve crosses over, no point.
        sim.rallyEnd().serve(CourtSide.FAR)
        val snap = sim.snapshot()
        assertEquals("0-1", snap.callText)
        assertEquals(Team.B, snap.servingTeam)
        assertTrue(snap.confidence > 0.9, "confidence was ${snap.confidence}")
    }

    @Test
    fun `doubles keeps both readings when a rally goes uncalled`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 3, scoreB = 2, serverNumber = ServerNumber.FIRST)
        val sim = Sim(start)

        sim.silentRally(CourtSide.NEAR)
        sim.serve(CourtSide.NEAR)

        val snap = sim.snapshot()
        assertTrue(snap.ambiguous, "same-side serve in doubles must stay ambiguous")
        assertEquals(setOf("4-2-1", "3-2-2"), snap.alternatives.toSet())
    }

    @Test
    fun `a spoken call collapses the ambiguity`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 3, scoreB = 2, serverNumber = ServerNumber.FIRST)
        val sim = Sim(start)

        sim.silentRally(CourtSide.NEAR).serve(CourtSide.NEAR)
        assertTrue(sim.snapshot().ambiguous)

        sim.call("four", "two", "one", side = CourtSide.NEAR)
        val snap = sim.snapshot()
        assertEquals("4-2-1", snap.callText)
        assertFalse(snap.ambiguous)
        assertTrue(snap.confidence > 0.9, "confidence was ${snap.confidence}")
    }

    @Test
    fun `a side out is unambiguous even with nobody calling it`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 3, scoreB = 2, serverNumber = ServerNumber.SECOND)
        val sim = Sim(start)

        sim.silentRally(CourtSide.NEAR).serve(CourtSide.FAR)

        val snap = sim.snapshot()
        assertEquals(Team.B, snap.servingTeam)
        assertEquals("2-3-1", snap.callText)
        assertFalse(snap.ambiguous)
    }

    // ---------------------------------------------------------------- sloppy speech

    @Test
    fun `sevens on one lands on the only legal reading`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 6, scoreB = 1, serverNumber = ServerNumber.FIRST)
        val sim = Sim(start)

        sim.silentRally(CourtSide.NEAR)
        sim.call("sevens", "on", "one", side = CourtSide.NEAR)
        sim.serve(CourtSide.NEAR)

        assertEquals("7-1-1", sim.callText())
        assertFalse(sim.snapshot().ambiguous)
    }

    @Test
    fun `the rules rescue a misheard numeral`() {
        // Real call is "eleven eight one"; the recogniser hears "seven eight one", which is not a
        // legal successor of 10-8-1. The low-weight 7/11 confusion reading is, so the call lands.
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 10, scoreB = 8, serverNumber = ServerNumber.FIRST)
        val sim = Sim(start)

        sim.silentRally(CourtSide.NEAR)
        sim.call("seven", "eight", "one", side = CourtSide.NEAR)

        assertEquals("11-8-1", sim.callText())
        assertEquals(Team.A, sim.snapshot().gameWinner)
    }

    @Test
    fun `zero zero start is understood as zero zero two`() {
        val sim = Sim(GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A))
        sim.call("zero", "zero", "start", side = CourtSide.NEAR)
        assertEquals("0-0-2", sim.callText())
        assertTrue(sim.lastEvents.any { it is EngineEvent.CallAccepted })
    }

    // ---------------------------------------------------------------- hostile audio

    @Test
    fun `a call that cannot be ours is rejected, not applied`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 7, scoreB = 5, serverNumber = ServerNumber.SECOND)
        val sim = Sim(start)

        sim.call("three", "two", "one", side = CourtSide.FAR)

        assertEquals("7-5-2", sim.callText())
        assertTrue(sim.lastEvents.any { it is EngineEvent.CallRejected })
    }

    @Test
    fun `players insisting on a score twice resyncs the engine`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 7, scoreB = 5, serverNumber = ServerNumber.SECOND)
        val sim = Sim(start)

        sim.call("nine", "four", "two", side = CourtSide.NEAR)
        assertEquals("7-5-2", sim.callText(), "one odd call must not move the score")

        sim.call("nine", "four", "two", side = CourtSide.NEAR)
        assertEquals("9-4-2", sim.callText())
        assertTrue(sim.lastEvents.any { it is EngineEvent.Resynced })
    }

    @Test
    fun `one bad direction estimate does not derail the score`() {
        val start = GameState.newGame(singles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 4, scoreB = 3)
        val sim = Sim(start)

        // TDOA glitches and reports the far side with low confidence.
        sim.silentRally(CourtSide.NEAR).serve(CourtSide.FAR, confidence = 0.35)
        // The players call the real score and the engine snaps back.
        sim.call("five", "three", side = CourtSide.NEAR)

        assertEquals("5-3", sim.callText())
        assertEquals(Team.A, sim.snapshot().servingTeam)
    }

    // ---------------------------------------------------------------- ends and games

    @Test
    fun `change of ends is inferred from where the next serve comes from`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 5, scoreB = 2, serverNumber = ServerNumber.FIRST)
        val sim = Sim(start)

        sim.silentRally(CourtSide.NEAR)
        sim.call("six", "two", "one", side = CourtSide.NEAR)
        assertTrue(sim.snapshot().endsSwitchDue, "reaching 6 should prompt the switch")

        // They walk around; A now serves from the far end.
        sim.serve(CourtSide.FAR)
        val snap = sim.snapshot()
        assertEquals("6-2-1", snap.callText)
        assertEquals(Team.B, snap.teamOnNearSide)
        assertFalse(snap.endsSwitchDue)
    }

    @Test
    fun `game point is detected and the next game starts when play resumes`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 10, scoreB = 4, serverNumber = ServerNumber.FIRST)
        val sim = Sim(start)

        sim.silentRally(CourtSide.NEAR)
        sim.call("eleven", "four", "one", side = CourtSide.NEAR)

        assertTrue(sim.allEvents.any { it is EngineEvent.GameWon })
        assertEquals(Team.A, sim.snapshot().gameWinner)
        assertEquals(Phase.GAME_OVER, sim.snapshot().phase)

        // Ends change between games, so game two's opening serve comes from the far side.
        sim.serve(CourtSide.FAR)
        val snap = sim.snapshot()
        assertEquals("0-0-2", snap.callText)
        assertEquals(1, snap.gamesWonA)
        assertEquals(Team.A, snap.servingTeam)
    }

    // ---------------------------------------------------------------- long haul

    @Test
    fun `a full called game tracks a known rally script exactly`() {
        var truth = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
        val sim = Sim(truth)

        // Deterministic pseudo-random script so the test is reproducible.
        val script = generateSequence(12345L) { (it * 6364136223846793005L + 1442695040888963407L) }
            .map { (it ushr 33) % 3 != 0L } // ~2/3 of rallies won by the serving team
            .iterator()

        var guard = 0
        while (truth.gameWinner == null && guard++ < 400) {
            sim.call(*spoken(truth.call()), side = truth.servingSide)
            assertEquals(truth.call().toString(), sim.callText(), "diverged before rally $guard")

            sim.serve(truth.servingSide).rallyEnd()

            val outcome = if (script.next()) RallyOutcome.SERVING_TEAM_WON else RallyOutcome.SERVING_TEAM_LOST
            truth = Rules.applyRally(truth, outcome)
            if (truth.endsSwitchPending) truth = truth.switchEnds()
        }

        assertEquals(truth.call().toString(), sim.engine.hypotheses().let { sim.callText() })
        assertEquals(truth.scoreA, sim.snapshot().scoreA)
        assertEquals(truth.scoreB, sim.snapshot().scoreB)
        assertTrue(truth.gameWinner != null, "the scripted game should have finished")
    }

    @Test
    fun `an entirely silent doubles game still bounds the score`() {
        // Nobody calls anything for ten rallies. The engine must not claim certainty, but it must
        // also not lose the plot: every surviving hypothesis stays legally reachable.
        val sim = Sim(GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A))
        repeat(10) { sim.silentRally(CourtSide.NEAR).serve(CourtSide.NEAR) }

        val snap = sim.snapshot()
        assertTrue(snap.ambiguous, "ten uncalled same-side rallies cannot be certain")
        assertTrue(snap.alternatives.size >= 2)
        // The serve never crossed the net, so team B cannot have scored and A must still be serving
        // in every score the UI is willing to show.
        assertEquals(Team.A, snap.servingTeam)
        assertEquals(0, snap.scoreB)
        snap.alternatives.forEach { alternative ->
            val parts = alternative.split("-").map { it.toInt() }
            assertEquals(0, parts[1], "team B scored in alternative $alternative")
            assertTrue(parts[0] <= 10, "impossible score $alternative")
        }
    }

    // ---------------------------------------------------------------- user overrides

    @Test
    fun `manual correction wins outright`() {
        val sim = Sim(GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A))
        sim.silentRally(CourtSide.NEAR).serve(CourtSide.NEAR)

        val corrected = GameState.newGame(doubles, servingTeam = Team.B, teamOnNearSide = Team.A)
            .copy(scoreA = 2, scoreB = 9, serverNumber = ServerNumber.FIRST)
        sim.engine.correct(corrected)

        val snap = sim.snapshot()
        assertEquals("9-2-1", snap.callText)
        assertFalse(snap.ambiguous)
        assertEquals(1.0, snap.confidence)
    }

    @Test
    fun `undo steps back one observation`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(scoreA = 3, scoreB = 2, serverNumber = ServerNumber.FIRST)
        val sim = Sim(start)

        sim.silentRally(CourtSide.NEAR)
        sim.call("four", "two", "one", side = CourtSide.NEAR)
        assertEquals("4-2-1", sim.callText())

        assertTrue(sim.engine.undo())
        assertTrue(sim.snapshot().ambiguous, "undo should restore the pre-call uncertainty")
    }

    @Test
    fun `snapshot json carries everything a watch or scoreboard needs`() {
        val sim = Sim(GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A))
        sim.call("zero", "zero", "start", side = CourtSide.NEAR)

        val json = sim.snapshot().toJson()
        listOf("\"a\":0", "\"b\":0", "\"srv\":\"A\"", "\"call\":\"0-0-2\"", "\"conf\":", "\"rev\":")
            .forEach { assertTrue(it in json, "missing $it in $json") }
    }
}
