package fyi.n93.pickleball.engine

/**
 * Everything the audio layer (or the user's finger) can tell the engine.
 *
 * The engine deliberately knows nothing about spectral flux, TDOA or recognisers — the DSP layer's
 * whole job is to reduce a noisy microphone stream to this handful of facts.
 */
sealed interface Observation {
    val tMs: Long

    /** The first ball strike after a gap: a serve, and which half of the court it came from. */
    data class ServeDetected(
        override val tMs: Long,
        val side: CourtSide,
        /** 0..1 confidence that the *side* is right, from the TDOA estimator. */
        val sideConfidence: Double = 0.9,
    ) : Observation

    /** Ball strikes stopped for longer than the rally-gap threshold: the rally is over. */
    data class RallyEnded(
        override val tMs: Long,
        /** How many strikes were in the rally. One or zero suggests a fault/let, not a real rally. */
        val hits: Int = 2,
    ) : Observation

    /** Words recognised from a single utterance, plus which side of the phone they came from. */
    data class SpokenCall(
        override val tMs: Long,
        val tokens: List<String>,
        val side: CourtSide? = null,
        /** 0..1 recogniser confidence for the utterance as a whole. */
        val asrConfidence: Double = 0.9,
    ) : Observation

    /** Players changed ends (user tapped confirm, or the engine's prompt was accepted). */
    data class EndsSwitched(override val tMs: Long) : Observation

    /** The user overrode the score. This is ground truth: it wipes every competing hypothesis. */
    data class ManualCorrection(override val tMs: Long, val state: GameState) : Observation
}

/** Things worth telling the UI, the watch, or the LED board about. */
sealed interface EngineEvent {
    data class PointScored(val team: Team, val call: ScoreCall) : EngineEvent
    data class ServerHandoff(val team: Team) : EngineEvent
    data class SideOut(val toTeam: Team) : EngineEvent

    /** A score call was heard and accepted. */
    data class CallAccepted(val call: ScoreCall, val confidence: Double) : EngineEvent

    /** A call was heard but no legal state matched it — almost always a neighbouring court. */
    data class CallRejected(val readings: List<String>) : EngineEvent

    /** The heard call matched nothing legal but was self-consistent, so we jumped to it. */
    data class Resynced(val call: ScoreCall) : EngineEvent

    /** More than one score is still consistent with what we heard. The UI must show this. */
    data class AmbiguityRaised(val alternatives: List<String>) : EngineEvent

    /** The score reached the switch-ends trigger. */
    data object EndsSwitchDue : EngineEvent
    data object EndsSwitchApplied : EngineEvent

    data class GameWon(val team: Team, val gamesWonA: Int, val gamesWonB: Int) : EngineEvent
    data class MatchWon(val team: Team) : EngineEvent
    data object NextGameStarted : EngineEvent
}

/** Whether a rally is currently in progress, as far as the ball-sound detector can tell. */
enum class Phase {
    BETWEEN_RALLIES,
    IN_RALLY,
    GAME_OVER,
}

/**
 * The full picture, ready to render or ship over the wire.
 *
 * One snapshot type serves every surface: the phone UI, the Wear OS tile, a second phone over
 * Nearby Connections, and (later) a BLE scoreboard. [revision] lets a receiver drop stale packets.
 */
data class ScoreSnapshot(
    val scoreA: Int,
    val scoreB: Int,
    val servingTeam: Team,
    val serverNumber: Int?,
    val callText: String,
    val teamOnNearSide: Team,
    val gamesWonA: Int,
    val gamesWonB: Int,
    val confidence: Double,
    val ambiguous: Boolean,
    val alternatives: List<String>,
    val phase: Phase,
    val endsSwitchDue: Boolean,
    val gameWinner: Team?,
    val matchWinner: Team?,
    val revision: Long,
    val tMs: Long,
) {
    /**
     * Minimal JSON, hand-rolled to keep the engine dependency-free (it has to run inside a Wear OS
     * data-layer callback and, eventually, be transcoded for a microcontroller).
     */
    fun toJson(): String = buildString {
        append("{")
        append("\"a\":").append(scoreA).append(',')
        append("\"b\":").append(scoreB).append(',')
        append("\"srv\":\"").append(servingTeam).append("\",")
        append("\"num\":").append(serverNumber ?: 0).append(',')
        append("\"call\":\"").append(callText).append("\",")
        append("\"near\":\"").append(teamOnNearSide).append("\",")
        append("\"ga\":").append(gamesWonA).append(',')
        append("\"gb\":").append(gamesWonB).append(',')
        append("\"conf\":").append(String.format(java.util.Locale.US, "%.3f", confidence)).append(',')
        append("\"amb\":").append(ambiguous).append(',')
        append("\"alts\":[")
        append(alternatives.joinToString(",") { "\"$it\"" })
        append("],")
        append("\"phase\":\"").append(phase).append("\",")
        append("\"switch\":").append(endsSwitchDue).append(',')
        append("\"gw\":").append(gameWinner?.let { "\"$it\"" } ?: "null").append(',')
        append("\"mw\":").append(matchWinner?.let { "\"$it\"" } ?: "null").append(',')
        append("\"rev\":").append(revision).append(',')
        append("\"t\":").append(tMs)
        append("}")
    }
}
