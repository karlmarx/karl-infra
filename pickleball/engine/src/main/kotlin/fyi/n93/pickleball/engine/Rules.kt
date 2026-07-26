package fyi.n93.pickleball.engine

/** Who won the rally that just ended, expressed relative to the team that was serving. */
enum class RallyOutcome {
    SERVING_TEAM_WON,
    SERVING_TEAM_LOST,
}

/** What structurally happened between one serve and the next. Drives the UI's explanation text. */
enum class Transition {
    /** Serving team won the rally and scored. */
    POINT,

    /** Doubles side-out scoring: first server lost, partner serves. Same team, no point. */
    SERVER_HANDOFF,

    /** Serve passed to the other team. */
    SIDE_OUT,

    /** Nothing happened: a let, a re-serve, or the score simply being re-announced. */
    REPEAT,
}

/** A legal next state together with how we got there and how likely that route is a priori. */
data class Candidate(
    val state: GameState,
    val transition: Transition,
    val prior: Double,
)

object Rules {

    /**
     * Advance one rally.
     *
     * Side-out scoring: only the serving team can score. Losing the rally costs the serve —
     * to the partner first (doubles), then to the other team.
     *
     * Rally scoring: every rally awards a point; the serving team losing awards the point to the
     * receiving team *and* hands them the serve.
     */
    fun applyRally(state: GameState, outcome: RallyOutcome): GameState {
        val cfg = state.config
        return when (outcome) {
            RallyOutcome.SERVING_TEAM_WON -> state.addPoint(state.servingTeam)

            RallyOutcome.SERVING_TEAM_LOST -> when {
                cfg.rallyScoring ->
                    state.addPoint(state.receivingTeam).sideOut()

                cfg.usesServerNumber && state.serverNumber == ServerNumber.FIRST ->
                    state.copy(serverNumber = ServerNumber.SECOND)

                else -> state.sideOut()
            }
        }
    }

    /** Serve moves to the other team, whose first server takes it. */
    private fun GameState.sideOut(): GameState = copy(
        servingTeam = servingTeam.other(),
        serverNumber = ServerNumber.FIRST,
    )

    /** Award a point and arm the switch-ends flag the first time the trigger score is reached. */
    private fun GameState.addPoint(team: Team): GameState {
        val next = if (team == Team.A) copy(scoreA = scoreA + 1) else copy(scoreB = scoreB + 1)
        val trigger = config.switchEndsAt ?: return next
        val justReached = next.scoreOf(team) == trigger && this.scoreOf(team) == trigger - 1
        // Only the first team to reach the trigger arms the switch, and only once per game.
        val alreadyPast = this.scoreOf(team.other()) >= trigger
        return if (justReached && !alreadyPast) next.copy(endsSwitchPending = true) else next
    }

    /**
     * Every state that could legally follow [state] at the moment of the next serve, with priors.
     *
     * This is the backbone of inference: the audio layer never observes "who won the rally", it
     * observes which physical half of the court the next serve came from. That observation is
     * matched against [Candidate.state]'s [GameState.servingSide].
     *
     * Note the structural ambiguity in doubles: POINT and SERVER_HANDOFF both keep the serve on the
     * same physical side, so a serve-side observation alone cannot separate them. Only a spoken
     * call (or a manual correction) can. Singles has no such ambiguity — same side means a point,
     * other side means a side out, always.
     */
    fun candidates(state: GameState): List<Candidate> {
        if (state.isGameOver) return listOf(Candidate(state, Transition.REPEAT, 1.0))

        val out = mutableListOf<Candidate>()
        val won = applyRally(state, RallyOutcome.SERVING_TEAM_WON)
        out += Candidate(won, Transition.POINT, PRIOR_POINT)

        val lost = applyRally(state, RallyOutcome.SERVING_TEAM_LOST)
        val lostTransition = when {
            lost.servingTeam != state.servingTeam -> Transition.SIDE_OUT
            else -> Transition.SERVER_HANDOFF
        }
        out += Candidate(lost, lostTransition, if (lostTransition == Transition.SIDE_OUT) PRIOR_SIDE_OUT else PRIOR_HANDOFF)

        // A let, a re-serve, or someone simply repeating the score leaves the state untouched.
        out += Candidate(state, Transition.REPEAT, PRIOR_REPEAT)
        return out
    }

    /**
     * Start the next game of the match: credit the win, switch ends, reset the score.
     *
     * Convention used here (configurable by passing [servingTeam]): the team that won the previous
     * game serves first in the next one.
     */
    fun startNextGame(finished: GameState, servingTeam: Team? = null): GameState {
        val winner = requireNotNull(finished.gameWinner) { "game is not over: $finished" }
        return GameState.newGame(
            config = finished.config,
            servingTeam = servingTeam ?: winner,
            teamOnNearSide = finished.teamOnNearSide.other(),
            gamesWonA = finished.gamesWonA + if (winner == Team.A) 1 else 0,
            gamesWonB = finished.gamesWonB + if (winner == Team.B) 1 else 0,
        )
    }

    // Priors, tuned to be deliberately mild. They only break ties when no call is heard; a spoken
    // call outweighs them by orders of magnitude.
    private const val PRIOR_POINT = 0.5
    private const val PRIOR_SIDE_OUT = 0.42
    private const val PRIOR_HANDOFF = 0.42
    private const val PRIOR_REPEAT = 0.02
}
