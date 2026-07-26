package fyi.n93.pickleball.engine

/**
 * The whole scorekeeper, minus the microphone.
 *
 * Feed it [Observation]s in the order the audio layer produces them; read [snapshot] to render or
 * broadcast. Everything is deterministic and side-effect free, which is the point: the hard part of
 * this app is the inference, and inference you cannot replay in a unit test is inference you cannot
 * trust on a windy court next to three other games.
 */
class ScoreEngine(initial: GameState, private val maxUndo: Int = 32) {

    val config: MatchConfig = initial.config

    private val tracker = HypothesisTracker(initial)
    private val undoStack = ArrayDeque<Saved>()

    private var phase: Phase = Phase.BETWEEN_RALLIES
    private var revision: Long = 0
    private var lastTimestamp: Long = 0
    private var lastServeMs: Long = -1

    /** A rejected call, remembered so a second identical one can trigger a resync. */
    private var pendingResync: ScoreCall? = null
    private var pendingResyncCount = 0

    /** Game/match wins already announced, so a speculative hypothesis cannot announce twice. */
    private var announcedGameWinner: Team? = null
    private var announcedMatchWinner: Team? = null

    private data class Saved(val beliefs: List<Hypothesis>, val phase: Phase, val lastServeMs: Long)

    fun observe(observation: Observation): List<EngineEvent> {
        lastTimestamp = observation.tMs
        val before = tracker.bestState()
        val wasAmbiguous = tracker.isAmbiguous()
        pushUndo()

        val events = mutableListOf<EngineEvent>()
        when (observation) {
            is Observation.RallyEnded -> handleRallyEnd(observation)
            is Observation.ServeDetected -> handleServe(observation, events)
            is Observation.SpokenCall -> handleSpokenCall(observation, events)
            is Observation.EndsSwitched -> {
                tracker.switchEnds()
                events += EngineEvent.EndsSwitchApplied
            }
            is Observation.ManualCorrection -> {
                tracker.reset(observation.state)
                phase = if (observation.state.isGameOver) Phase.GAME_OVER else Phase.BETWEEN_RALLIES
                pendingResync = null
                pendingResyncCount = 0
            }
        }

        events += diffEvents(before, tracker.bestState())
        events += winnerEvents()
        recomputePhase()
        if (!wasAmbiguous && tracker.isAmbiguous()) {
            events += EngineEvent.AmbiguityRaised(tracker.alternatives())
        }
        if (events.isNotEmpty()) revision++
        return events
    }

    private fun handleRallyEnd(observation: Observation.RallyEnded) {
        if (phase != Phase.IN_RALLY) return
        tracker.expandOnRallyEnd(observation.hits)
        phase = Phase.BETWEEN_RALLIES
    }

    private fun handleServe(observation: Observation.ServeDetected, events: MutableList<EngineEvent>) {
        if (phase == Phase.IN_RALLY) {
            // A serve while a rally is supposedly running means we missed the rally end. If enough
            // time has passed for that to be physically real, recover; otherwise it is a stray hit.
            if (lastServeMs >= 0 && observation.tMs - lastServeMs < STALE_RALLY_MS) return
            tracker.expandOnRallyEnd()
            phase = Phase.BETWEEN_RALLIES
        }

        if (phase == Phase.GAME_OVER) {
            // They are playing again, so the game really is over and someone racked up the next one.
            tracker.startNextGame()
            announcedGameWinner = null
            events += EngineEvent.NextGameStarted
        }

        tracker.observeServeSide(observation.side, observation.sideConfidence)
        phase = Phase.IN_RALLY
        lastServeMs = observation.tMs
    }

    private fun handleSpokenCall(observation: Observation.SpokenCall, events: MutableList<EngineEvent>) {
        val readings = CallGrammar.parse(observation.tokens, CallGrammar.expectedLength(config))
        if (readings.isEmpty()) return

        tracker.observeCall(readings, observation.side, observation.asrConfidence)

        if (!tracker.lastObservationRejected) {
            pendingResync = null
            pendingResyncCount = 0
            events += EngineEvent.CallAccepted(tracker.bestState().call(), tracker.confidence())
            return
        }

        // Nothing legal explains what we heard. Either it came from another court, or we have
        // drifted and the players are right. Require corroboration before believing it.
        val resyncTarget = readings
            .asSequence()
            .filter { it.weight >= MIN_RESYNC_READING_WEIGHT }
            .mapNotNull { stateFromReading(it, observation.side) }
            .firstOrNull()

        val trustworthy = observation.asrConfidence >= MIN_RESYNC_ASR_CONFIDENCE
        if (resyncTarget == null || !trustworthy) {
            events += EngineEvent.CallRejected(readings.take(3).map { it.toString() })
            return
        }

        val call = resyncTarget.call()
        val corroborated = pendingResync == call
        pendingResyncCount = if (corroborated) pendingResyncCount + 1 else 1
        pendingResync = call

        val lowConfidence = tracker.confidence() < RESYNC_WITHOUT_CORROBORATION_BELOW
        if (corroborated || lowConfidence) {
            tracker.injectResync(resyncTarget)
            pendingResync = null
            pendingResyncCount = 0
            events += EngineEvent.Resynced(call)
        } else {
            events += EngineEvent.CallRejected(readings.take(3).map { it.toString() })
        }
    }

    /**
     * Build a complete state from a heard call.
     *
     * The speaker's side is what makes this possible: the server calls the score, so the half of
     * the court the words came from tells us which team the first number belongs to.
     */
    private fun stateFromReading(reading: CallReading, speakerSide: CourtSide?): GameState? {
        val template = tracker.bestState()
        val expected = CallGrammar.expectedLength(config)

        val numerals = when {
            reading.numerals.size == expected -> reading.numerals
            reading.hasStart && reading.numerals.size == 2 && reading.numerals.all { it == 0 } ->
                listOf(0, 0, 2)
            else -> return null
        }
        if (numerals.size < 2) return null

        val servingScore = numerals[0]
        val receivingScore = numerals[1]
        val ceiling = (config.hardCap ?: (config.pointsToWin + SCORE_SLACK))
        if (servingScore !in 0..ceiling || receivingScore !in 0..ceiling) return null

        val serverNumber = when {
            !config.usesServerNumber -> ServerNumber.FIRST
            numerals.size < 3 -> return null
            numerals[2] == 1 -> ServerNumber.FIRST
            numerals[2] == 2 -> ServerNumber.SECOND
            else -> return null
        }

        // The server is the one who calls the score, so the half the words came from names the
        // serving team. With no direction, keep whoever we already believed was serving.
        val servingTeam = when (speakerSide) {
            null -> template.servingTeam
            CourtSide.NEAR -> template.teamOnNearSide
            CourtSide.FAR -> template.teamOnNearSide.other()
        }

        return template.copy(
            scoreA = if (servingTeam == Team.A) servingScore else receivingScore,
            scoreB = if (servingTeam == Team.B) servingScore else receivingScore,
            servingTeam = servingTeam,
            serverNumber = serverNumber,
            endsSwitchPending = false,
        )
    }

    private fun diffEvents(before: GameState, after: GameState): List<EngineEvent> {
        val events = mutableListOf<EngineEvent>()
        if (before == after) return events

        val scoredTeam = when {
            after.scoreA > before.scoreA -> Team.A
            after.scoreB > before.scoreB -> Team.B
            else -> null
        }
        if (scoredTeam != null) events += EngineEvent.PointScored(scoredTeam, after.call())

        if (after.servingTeam != before.servingTeam) {
            events += EngineEvent.SideOut(after.servingTeam)
        } else if (after.serverNumber != before.serverNumber && after.scoreA == before.scoreA &&
            after.scoreB == before.scoreB
        ) {
            events += EngineEvent.ServerHandoff(after.servingTeam)
        }

        if (after.teamOnNearSide != before.teamOnNearSide) events += EngineEvent.EndsSwitchApplied
        if (!before.endsSwitchPending && after.endsSwitchPending) events += EngineEvent.EndsSwitchDue

        return events
    }

    /**
     * Announce a game or match only once we actually believe it.
     *
     * The leading hypothesis can reach game point speculatively — "serving team scored" outranks
     * "the serve passed to the partner" by a hair — and flashing GAME! on a coin flip is worse than
     * being a beat late. The score still displays, flagged ambiguous; only the announcement waits.
     */
    private fun winnerEvents(): List<EngineEvent> {
        val state = tracker.bestState()
        if (tracker.confidence() < WINNER_ANNOUNCE_CONFIDENCE) return emptyList()

        val events = mutableListOf<EngineEvent>()
        val winner = state.gameWinner
        if (winner != null && announcedGameWinner != winner) {
            announcedGameWinner = winner
            events += EngineEvent.GameWon(winner, state.gamesWonA, state.gamesWonB)
        }
        val matchWinner = state.matchWinner
        if (matchWinner != null && announcedMatchWinner != matchWinner) {
            announcedMatchWinner = matchWinner
            events += EngineEvent.MatchWon(matchWinner)
        }
        return events
    }

    /** Keep [phase] consistent with what we currently believe. */
    private fun recomputePhase() {
        if (tracker.bestState().isGameOver) {
            phase = Phase.GAME_OVER
        } else if (phase == Phase.GAME_OVER) {
            phase = Phase.BETWEEN_RALLIES
        }
    }

    /** Force the state. The user's finger always wins. */
    fun correct(state: GameState): List<EngineEvent> =
        observe(Observation.ManualCorrection(lastTimestamp, state))

    /** Step back one observation. Returns false if there is nothing to undo. */
    fun undo(): Boolean {
        val saved = undoStack.removeLastOrNull() ?: return false
        tracker.restore(saved.beliefs)
        phase = saved.phase
        lastServeMs = saved.lastServeMs
        revision++
        return true
    }

    fun snapshot(): ScoreSnapshot {
        val state = tracker.bestState()
        return ScoreSnapshot(
            scoreA = state.scoreA,
            scoreB = state.scoreB,
            servingTeam = state.servingTeam,
            serverNumber = if (config.usesServerNumber) state.serverNumber.spoken else null,
            callText = state.call().toString(),
            teamOnNearSide = state.teamOnNearSide,
            gamesWonA = state.gamesWonA,
            gamesWonB = state.gamesWonB,
            confidence = tracker.confidence(),
            ambiguous = tracker.isAmbiguous(),
            alternatives = tracker.alternatives(),
            phase = phase,
            endsSwitchDue = state.endsSwitchPending,
            gameWinner = state.gameWinner,
            matchWinner = state.matchWinner,
            revision = revision,
            tMs = lastTimestamp,
        )
    }

    /** Exposed for tests and for the "why does it think that?" debug screen. */
    fun hypotheses(): List<Hypothesis> = tracker.all()

    private fun pushUndo() {
        undoStack.addLast(Saved(tracker.save(), phase, lastServeMs))
        while (undoStack.size > maxUndo) undoStack.removeFirst()
    }

    private companion object {
        /** A "serve" this long after the previous one means we simply missed the rally end. */
        const val STALE_RALLY_MS = 4_000L

        const val MIN_RESYNC_READING_WEIGHT = 0.5
        const val MIN_RESYNC_ASR_CONFIDENCE = 0.6

        /** With belief this weak, a single confident call is enough to resync. */
        const val RESYNC_WITHOUT_CORROBORATION_BELOW = 0.45

        /** How far past `pointsToWin` a spoken score can go before it is obviously not ours. */
        const val SCORE_SLACK = 6

        /** Belief required before shouting GAME. */
        const val WINNER_ANNOUNCE_CONFIDENCE = 0.6
    }
}
