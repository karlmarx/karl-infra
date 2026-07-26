package fyi.n93.pickleball.engine

import kotlin.math.max

/** One candidate belief about where the match currently stands. */
data class Hypothesis(
    val state: GameState,
    val weight: Double,
    val lastTransition: Transition? = null,
)

/**
 * A small weighted set of beliefs about the score.
 *
 * Why a set and not a single state: after a rally that nobody called, doubles is *structurally*
 * ambiguous — "serving team scored" and "serve passed to the partner" both leave the serve on the
 * same physical half of the court, and no microphone can tell them apart. Rather than guess and
 * silently drift, the tracker carries both, shows the ambiguity in the UI, and lets the next spoken
 * call collapse it. Singles has no such ambiguity and collapses to one hypothesis every rally.
 *
 * All the pruning power comes from the rules: [Rules.candidates] only ever proposes states that are
 * legally reachable, so a misheard "eleven" that cannot possibly be the score is simply gone.
 */
class HypothesisTracker(
    initial: GameState,
    private val maxHypotheses: Int = 8,
    private val minWeight: Double = 0.005,
) {
    private var beliefs: List<Hypothesis> = listOf(Hypothesis(initial, 1.0))

    /** Set to true when the last observation matched nothing legal. */
    var lastObservationRejected: Boolean = false
        private set

    fun all(): List<Hypothesis> = beliefs

    /** Opaque copy of the belief set, for the undo stack. */
    fun save(): List<Hypothesis> = beliefs

    fun restore(saved: List<Hypothesis>) {
        require(saved.isNotEmpty()) { "cannot restore an empty belief set" }
        beliefs = saved
        lastObservationRejected = false
    }

    /**
     * Belief grouped by the score that would be *displayed*, heaviest first.
     *
     * Two hypotheses that disagree only about which end each team is standing on show the same
     * score, so they must not read as uncertainty about the score. Everything user-facing —
     * confidence, ambiguity, the leading state — is computed over these groups, not raw beliefs.
     */
    private fun byCall(): List<Pair<ScoreCall, List<Hypothesis>>> = beliefs
        .groupBy { it.state.call() }
        .toList()
        .sortedByDescending { (_, group) -> group.sumOf { it.weight } }

    fun best(): Hypothesis = byCall().first().second.maxByOrNull { it.weight }!!

    fun bestState(): GameState = best().state

    /** Confidence in the displayed score: the total belief behind it. */
    fun confidence(): Double = byCall().first().second.sumOf { it.weight }

    /**
     * Distinct score calls still in play above [minDisplayWeight], best first. One entry means the
     * engine is certain; more than one is what the UI renders as "7-5-2 or 7-5-1?".
     */
    fun alternatives(minDisplayWeight: Double = 0.12): List<String> = byCall()
        .filter { (_, group) -> group.sumOf { it.weight } >= minDisplayWeight }
        .map { (call, _) -> call.toString() }

    fun isAmbiguous(): Boolean = alternatives().size > 1

    /** Replace all belief with a single known-good state. Used for manual correction. */
    fun reset(state: GameState) {
        beliefs = listOf(Hypothesis(state, 1.0))
        lastObservationRejected = false
    }

    /**
     * A rally ended. Fan every belief out over its legal successors.
     *
     * A rally of one hit or fewer is treated as a fault or a let: the REPEAT branch gets extra
     * weight, because a whiffed serve does not necessarily change anything.
     */
    fun expandOnRallyEnd(hits: Int = 2) {
        val expanded = beliefs.flatMap { hypothesis ->
            // A change of ends is offered exactly once, on the rally end that triggers it. If the
            // next serve says they did not walk, they are not going to — plenty of rec players skip
            // the changeover entirely — so the flag is dropped rather than left to breed
            // hypotheses forever.
            val alreadyOffered = hypothesis.state.endsSwitchPending
            Rules.candidates(hypothesis.state).flatMap { candidate ->
                val prior = if (hits <= 1 && candidate.transition == Transition.REPEAT) {
                    candidate.prior * SHORT_RALLY_REPEAT_BOOST
                } else {
                    candidate.prior
                }
                when {
                    !candidate.state.endsSwitchPending -> listOf(
                        Hypothesis(candidate.state, hypothesis.weight * prior, candidate.transition),
                    )

                    alreadyOffered -> listOf(
                        Hypothesis(
                            candidate.state.copy(endsSwitchPending = false),
                            hypothesis.weight * prior,
                            candidate.transition,
                        ),
                    )

                    // Freshly triggered: carry both "they walked" and "they haven't (yet)".
                    else -> listOf(
                        Hypothesis(candidate.state, hypothesis.weight * prior * NOT_YET_SWITCHED, candidate.transition),
                        Hypothesis(candidate.state.switchEnds(), hypothesis.weight * prior * SWITCHED, candidate.transition),
                    )
                }
            }
        }
        beliefs = expanded.merge().normaliseAndPrune()
        lastObservationRejected = false
    }

    /**
     * A serve was heard coming from [side]. Reweight — never advance; the fan-out already happened
     * at rally end.
     *
     * A hypothesis whose serving team is on the other half of the court is not deleted outright,
     * only heavily penalised: TDOA gets it wrong occasionally (wind, a shout from the next court,
     * the phone getting kicked), and an over-confident delete is unrecoverable.
     */
    fun observeServeSide(side: CourtSide, sideConfidence: Double) {
        val trust = sideConfidence.coerceIn(0.0, 1.0)
        beliefs = beliefs.map { hypothesis ->
            val matches = hypothesis.state.servingSide == side
            val likelihood = if (matches) {
                trust + (1 - trust) * 0.5
            } else {
                max(SIDE_MISMATCH_FLOOR, (1 - trust) * SIDE_MISMATCH_SCALE)
            }
            hypothesis.copy(weight = hypothesis.weight * likelihood)
        }.normaliseAndPrune()
    }

    /**
     * A score call was heard. Reweight every belief by how well it explains the utterance.
     *
     * [speakerSide] matters: in pickleball the *server* calls the score, so an utterance from the
     * receiving half is weak evidence. Weak, not zero — partners and bystanders repeat the score.
     *
     * Returns the total evidence mass found. A near-zero return means nothing on this court could
     * have produced that call, which is the caller's cue to consider a resync or to reject it.
     */
    fun observeCall(
        readings: List<CallReading>,
        speakerSide: CourtSide?,
        asrConfidence: Double,
    ): Double {
        var totalEvidence = 0.0
        val reweighted = beliefs.map { hypothesis ->
            val call = hypothesis.state.call()
            val best = readings.maxOfOrNull { reading ->
                CallGrammar.scoreAgainst(reading, call, hypothesis.state.isStartOfGame) * reading.weight
            } ?: 0.0

            val sideFactor = when {
                speakerSide == null -> 1.0
                speakerSide == hypothesis.state.servingSide -> 1.0
                else -> WRONG_SPEAKER_SIDE
            }

            val evidence = best * sideFactor * asrConfidence.coerceIn(0.0, 1.0)
            totalEvidence += hypothesis.weight * evidence
            // Keep a floor so a single garbled call cannot annihilate a belief the rules still allow.
            hypothesis.copy(weight = hypothesis.weight * (UNHEARD_FLOOR + evidence))
        }

        lastObservationRejected = totalEvidence < REJECT_THRESHOLD
        beliefs = reweighted.normaliseAndPrune()
        return totalEvidence
    }

    /**
     * Inject a state we did not derive from the current beliefs — used when a confident, complete,
     * self-consistent call matches nothing we believed (app opened mid-game, or we drifted).
     */
    fun injectResync(state: GameState, weight: Double = RESYNC_WEIGHT) {
        beliefs = (beliefs.map { it.copy(weight = it.weight * (1 - weight)) } +
            Hypothesis(state, weight, null)).merge().normaliseAndPrune()
    }

    /** Apply a change of ends to every belief. */
    fun switchEnds() {
        beliefs = beliefs.map { it.copy(state = it.state.switchEnds()) }.merge().normaliseAndPrune()
    }

    /** Move every finished game on to the next one. */
    fun startNextGame() {
        beliefs = beliefs.map {
            if (it.state.isGameOver) it.copy(state = Rules.startNextGame(it.state)) else it
        }.merge().normaliseAndPrune()
    }

    /** Identical states reached by different routes are the same belief; add their weights. */
    private fun List<Hypothesis>.merge(): List<Hypothesis> =
        groupBy { it.state }.map { (state, group) ->
            Hypothesis(
                state = state,
                weight = group.sumOf { it.weight },
                lastTransition = group.maxByOrNull { it.weight }?.lastTransition,
            )
        }

    private fun List<Hypothesis>.normaliseAndPrune(): List<Hypothesis> {
        val merged = merge()
        val total = merged.sumOf { it.weight }
        if (total <= 0.0) {
            // Everything was annihilated. Fall back to the previous leader rather than crash.
            return listOf(best().copy(weight = 1.0))
        }
        val scaled = merged.map { it.copy(weight = it.weight / total) }.sortedByDescending { it.weight }
        val normalised = scaled.filter { it.weight >= minWeight }.take(maxHypotheses)
            .ifEmpty { listOf(scaled.first()) }
        val renormalise = normalised.sumOf { it.weight }
        return normalised.map { it.copy(weight = it.weight / renormalise) }
    }

    private companion object {
        /** Belief a hypothesis keeps when a call says nothing about it. */
        const val UNHEARD_FLOOR = 0.05

        /**
         * Serve came from the "wrong" half: not impossible, just unlikely. A two-mic array with the
         * players 20+ feet apart on either side is a very strong discriminator, so a confident
         * mismatch is heavily penalised — but never to zero, because a kicked phone is unrecoverable
         * if we delete outright.
         */
        const val SIDE_MISMATCH_FLOOR = 0.015
        const val SIDE_MISMATCH_SCALE = 0.15

        /** The score was called by someone on the receiving half. */
        const val WRONG_SPEAKER_SIDE = 0.35

        /** Below this much total evidence, the utterance was not about this court. */
        const val REJECT_THRESHOLD = 0.06

        const val RESYNC_WEIGHT = 0.75
        const val SHORT_RALLY_REPEAT_BOOST = 20.0
        const val NOT_YET_SWITCHED = 0.45
        const val SWITCHED = 0.55
    }
}
