package fyi.n93.pickleball.engine

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class RulesTest {

    private val doubles = MatchConfig()
    private val singles = MatchConfig(doubles = false)
    private val rally = MatchConfig(rallyScoring = true)

    @Test
    fun `doubles game opens at zero zero two`() {
        val state = GameState.newGame(doubles)
        assertEquals(ScoreCall(0, 0, 2), state.call())
        assertTrue(state.isStartOfGame)
        assertEquals(ServeBox.RIGHT_EVEN, state.serveBox)
    }

    @Test
    fun `singles call has no server number`() {
        val state = GameState.newGame(singles)
        assertEquals(ScoreCall(0, 0, null), state.call())
        assertEquals("0-0", state.call().toString())
    }

    @Test
    fun `only the serving team scores under side-out scoring`() {
        val start = GameState.newGame(doubles)
        val afterLoss = Rules.applyRally(start, RallyOutcome.SERVING_TEAM_LOST)
        assertEquals(0, afterLoss.scoreA)
        assertEquals(0, afterLoss.scoreB)
    }

    @Test
    fun `opening server is second server so losing hands the serve straight over`() {
        val start = GameState.newGame(doubles, servingTeam = Team.A)
        val afterLoss = Rules.applyRally(start, RallyOutcome.SERVING_TEAM_LOST)
        assertEquals(Team.B, afterLoss.servingTeam)
        assertEquals(ServerNumber.FIRST, afterLoss.serverNumber)
        assertEquals(ScoreCall(0, 0, 1), afterLoss.call())
    }

    @Test
    fun `first server losing passes to the partner, not the other team`() {
        val state = GameState.newGame(doubles).copy(serverNumber = ServerNumber.FIRST)
        val next = Rules.applyRally(state, RallyOutcome.SERVING_TEAM_LOST)
        assertEquals(Team.A, next.servingTeam)
        assertEquals(ServerNumber.SECOND, next.serverNumber)
    }

    @Test
    fun `second server losing is a side out`() {
        val state = GameState.newGame(doubles).copy(serverNumber = ServerNumber.SECOND)
        val next = Rules.applyRally(state, RallyOutcome.SERVING_TEAM_LOST)
        assertEquals(Team.B, next.servingTeam)
        assertEquals(ServerNumber.FIRST, next.serverNumber)
    }

    @Test
    fun `serve box follows the serving team's score parity`() {
        var state = GameState.newGame(doubles)
        assertEquals(ServeBox.RIGHT_EVEN, state.serveBox)
        state = Rules.applyRally(state, RallyOutcome.SERVING_TEAM_WON)
        assertEquals(ServeBox.LEFT_ODD, state.serveBox)
        state = Rules.applyRally(state, RallyOutcome.SERVING_TEAM_WON)
        assertEquals(ServeBox.RIGHT_EVEN, state.serveBox)
    }

    @Test
    fun `serving side follows the ends mapping`() {
        val state = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
        assertEquals(CourtSide.NEAR, state.servingSide)
        assertEquals(CourtSide.FAR, state.switchEnds().servingSide)
    }

    @Test
    fun `game requires win by two`() {
        val state = GameState.newGame(doubles).copy(scoreA = 11, scoreB = 10)
        assertNull(state.gameWinner)
        assertEquals(Team.A, state.copy(scoreA = 12, scoreB = 10).gameWinner)
    }

    @Test
    fun `hard cap ends the game without the margin`() {
        val capped = MatchConfig(pointsToWin = 11, hardCap = 15)
        val state = GameState.newGame(capped).copy(scoreA = 15, scoreB = 14)
        assertEquals(Team.A, state.gameWinner)
    }

    @Test
    fun `switch ends arms exactly once, for the first team to reach the trigger`() {
        var state = GameState.newGame(doubles, servingTeam = Team.A).copy(scoreA = 5)
        state = Rules.applyRally(state, RallyOutcome.SERVING_TEAM_WON)
        assertTrue(state.endsSwitchPending, "reaching 6 should arm the switch")

        val switched = state.switchEnds()
        assertFalse(switched.endsSwitchPending)

        // B later reaching 6 must not arm it again.
        var later = switched.copy(scoreB = 5, servingTeam = Team.B)
        later = Rules.applyRally(later, RallyOutcome.SERVING_TEAM_WON)
        assertFalse(later.endsSwitchPending)
    }

    @Test
    fun `rally scoring gives the receiving team a point on a side out`() {
        val state = GameState.newGame(rally, servingTeam = Team.A)
        val next = Rules.applyRally(state, RallyOutcome.SERVING_TEAM_LOST)
        assertEquals(1, next.scoreB)
        assertEquals(Team.B, next.servingTeam)
        assertNull(next.call().serverNumber)
    }

    @Test
    fun `candidates keep the serve on the same side for a point and a handoff`() {
        val state = GameState.newGame(doubles, servingTeam = Team.A, teamOnNearSide = Team.A)
            .copy(serverNumber = ServerNumber.FIRST)
        val candidates = Rules.candidates(state)

        val point = candidates.single { it.transition == Transition.POINT }
        val handoff = candidates.single { it.transition == Transition.SERVER_HANDOFF }
        assertEquals(CourtSide.NEAR, point.state.servingSide)
        assertEquals(CourtSide.NEAR, handoff.state.servingSide)
        assertTrue(candidates.none { it.transition == Transition.SIDE_OUT })
    }

    @Test
    fun `candidates in singles are unambiguous by side`() {
        val state = GameState.newGame(singles, servingTeam = Team.A, teamOnNearSide = Team.A)
        val candidates = Rules.candidates(state)
        val point = candidates.single { it.transition == Transition.POINT }
        val sideOut = candidates.single { it.transition == Transition.SIDE_OUT }
        assertEquals(CourtSide.NEAR, point.state.servingSide)
        assertEquals(CourtSide.FAR, sideOut.state.servingSide)
    }

    @Test
    fun `next game credits the win, switches ends and resets the score`() {
        val finished = GameState.newGame(doubles, servingTeam = Team.B, teamOnNearSide = Team.A)
            .copy(scoreA = 11, scoreB = 4)
        val next = Rules.startNextGame(finished)
        assertEquals(1, next.gamesWonA)
        assertEquals(0, next.scoreA)
        assertEquals(Team.A, next.servingTeam)
        assertEquals(Team.B, next.teamOnNearSide)
        assertTrue(next.isStartOfGame)
    }

    @Test
    fun `match is won at two games in a best of three`() {
        val state = GameState.newGame(doubles).copy(gamesWonA = 2)
        assertEquals(Team.A, state.matchWinner)
    }
}
