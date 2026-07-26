package fyi.n93.pickleball.engine

/**
 * Core value types for the scoring engine.
 *
 * Nothing in this file (or anywhere in the engine) touches Android, audio, or IO. The engine is a
 * pure function of the observation stream so it can be exhaustively unit tested on the JVM.
 */

/** Logical team identity. Stable for the whole match, independent of which end they stand on. */
enum class Team {
    A,
    B;

    fun other(): Team = if (this == A) B else A
}

/**
 * Physical half of the court, as seen by the phone lying midcourt.
 *
 * NEAR is the half on the side of the phone's primary mic (the end where the phone's bottom edge
 * points); FAR is the other. The audio layer resolves a sound to one of these via TDOA; the engine
 * never cares which is "left" or "right", only that the two halves are distinguishable.
 */
enum class CourtSide {
    NEAR,
    FAR;

    fun other(): CourtSide = if (this == NEAR) FAR else NEAR
}

/** First or second server of the serving team (doubles, traditional side-out scoring). */
enum class ServerNumber(val spoken: Int) {
    FIRST(1),
    SECOND(2);

    fun other(): ServerNumber = if (this == FIRST) SECOND else FIRST
}

/** Which service box the server must serve from, derived from the serving team's score parity. */
enum class ServeBox {
    RIGHT_EVEN,
    LEFT_ODD,
}

/** Match-level configuration. Defaults are recreational doubles: 11, win by 2, side-out scoring. */
data class MatchConfig(
    val doubles: Boolean = true,
    val pointsToWin: Int = 11,
    val winBy: Int = 2,
    /** Hard cap: first to this score wins even without the win-by margin. Null = play it out. */
    val hardCap: Int? = null,
    /** Rally scoring: every rally is a point, and losing the serve also concedes a point. */
    val rallyScoring: Boolean = false,
    /** Teams switch ends when either team first reaches this score. Null = never. */
    val switchEndsAt: Int? = 6,
    val bestOf: Int = 3,
) {
    init {
        require(pointsToWin > 0) { "pointsToWin must be positive" }
        require(winBy >= 1) { "winBy must be at least 1" }
        require(bestOf >= 1) { "bestOf must be at least 1" }
    }

    val gamesToWinMatch: Int get() = bestOf / 2 + 1

    /** Rally scoring has no first/second server; doubles side-out scoring does. */
    val usesServerNumber: Boolean get() = doubles && !rallyScoring
}

/**
 * A spoken score call: what a server would say out loud before serving.
 *
 * Doubles side-out: (serving score, receiving score, server number) — "seven five two".
 * Singles / rally: (server score, receiver score, null) — "seven five".
 */
data class ScoreCall(
    val servingScore: Int,
    val receivingScore: Int,
    val serverNumber: Int?,
) {
    fun asList(): List<Int> = listOfNotNull(servingScore, receivingScore, serverNumber)

    override fun toString(): String = asList().joinToString("-")
}

/**
 * Complete, immutable state of the match between rallies.
 *
 * [teamOnNearSide] is the mapping between logical teams and physical court halves. It is the only
 * field that changes when players switch ends, and it is what turns a serve-side observation into a
 * statement about which *team* is serving.
 */
data class GameState(
    val config: MatchConfig,
    val scoreA: Int,
    val scoreB: Int,
    val servingTeam: Team,
    val serverNumber: ServerNumber,
    val teamOnNearSide: Team,
    val gamesWonA: Int = 0,
    val gamesWonB: Int = 0,
    /** Set when the score crosses the switch-ends trigger and cleared once the swap is applied. */
    val endsSwitchPending: Boolean = false,
) {
    val receivingTeam: Team get() = servingTeam.other()

    fun scoreOf(team: Team): Int = if (team == Team.A) scoreA else scoreB

    fun gamesWonBy(team: Team): Int = if (team == Team.A) gamesWonA else gamesWonB

    val servingScore: Int get() = scoreOf(servingTeam)
    val receivingScore: Int get() = scoreOf(receivingTeam)

    /** Which physical half of the court the serve will come from. */
    val servingSide: CourtSide
        get() = if (servingTeam == teamOnNearSide) CourtSide.NEAR else CourtSide.FAR

    /** Server's required service box: right/even court when the serving team's score is even. */
    val serveBox: ServeBox
        get() = if (servingScore % 2 == 0) ServeBox.RIGHT_EVEN else ServeBox.LEFT_ODD

    /** The score as it should be called aloud before this serve. */
    fun call(): ScoreCall = ScoreCall(
        servingScore = servingScore,
        receivingScore = receivingScore,
        serverNumber = if (config.usesServerNumber) serverNumber.spoken else null,
    )

    /**
     * True at the very first serve of a game in doubles side-out scoring, where the call is
     * "zero zero two" — spoken by most players as "zero zero start".
     */
    val isStartOfGame: Boolean
        get() = config.usesServerNumber && scoreA == 0 && scoreB == 0 &&
            serverNumber == ServerNumber.SECOND

    val gameWinner: Team?
        get() {
            val cap = config.hardCap
            if (cap != null) {
                if (scoreA >= cap) return Team.A
                if (scoreB >= cap) return Team.B
            }
            val margin = scoreA - scoreB
            if (scoreA >= config.pointsToWin && margin >= config.winBy) return Team.A
            if (scoreB >= config.pointsToWin && -margin >= config.winBy) return Team.B
            return null
        }

    val matchWinner: Team?
        get() = when {
            gamesWonA >= config.gamesToWinMatch -> Team.A
            gamesWonB >= config.gamesToWinMatch -> Team.B
            else -> null
        }

    val isGameOver: Boolean get() = gameWinner != null
    val isMatchOver: Boolean get() = matchWinner != null

    /** Apply the physical end change: the team on the near side becomes the other team. */
    fun switchEnds(): GameState =
        copy(teamOnNearSide = teamOnNearSide.other(), endsSwitchPending = false)

    override fun toString(): String {
        val srv = if (config.usesServerNumber) "-${serverNumber.spoken}" else ""
        return "A$scoreA/B$scoreB serve=$servingTeam$srv near=$teamOnNearSide" +
            (if (endsSwitchPending) " [switch-due]" else "")
    }

    companion object {
        /**
         * Fresh game. In doubles side-out scoring the first server of a game is designated the
         * *second* server, which is why the opening call is "zero zero two" / "zero zero start".
         */
        fun newGame(
            config: MatchConfig = MatchConfig(),
            servingTeam: Team = Team.A,
            teamOnNearSide: Team = Team.A,
            gamesWonA: Int = 0,
            gamesWonB: Int = 0,
        ): GameState = GameState(
            config = config,
            scoreA = 0,
            scoreB = 0,
            servingTeam = servingTeam,
            serverNumber = if (config.usesServerNumber) ServerNumber.SECOND else ServerNumber.FIRST,
            teamOnNearSide = teamOnNearSide,
            gamesWonA = gamesWonA,
            gamesWonB = gamesWonB,
        )
    }
}
