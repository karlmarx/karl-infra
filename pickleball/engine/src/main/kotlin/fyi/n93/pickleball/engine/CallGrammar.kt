package fyi.n93.pickleball.engine

/**
 * One candidate interpretation of an utterance, e.g. tokens
 * `["sevens", "on", "one"]` yielding `[7, 1]` (with "on" as filler) and `[7, 1, 1]` (with "on"
 * heard as a clipped "one").
 */
data class CallReading(
    val numerals: List<Int>,
    val hasStart: Boolean = false,
    val sideOutHint: Boolean = false,
    val weight: Double = 1.0,
) {
    override fun toString(): String =
        numerals.joinToString("-") + (if (hasStart) "+start" else "") + " @%.2f".format(weight)
}

/**
 * Turns a recognised token stream into weighted [CallReading]s, then scores those readings against
 * the score calls the rules say are actually possible.
 *
 * The parser is deliberately permissive — it would rather emit six plausible readings than miss the
 * right one. Precision comes from [scoreAgainst], which throws away everything the rules forbid.
 */
object CallGrammar {

    /** Beam width while expanding readings. Small; utterances are a handful of words. */
    private const val BEAM = 24

    /** Number of numerals in a well-formed call: 3 for doubles side-out, 2 otherwise. */
    fun expectedLength(config: MatchConfig): Int = if (config.usesServerNumber) 3 else 2

    fun parse(tokens: List<String>, expected: Int): List<CallReading> {
        var beam = listOf(CallReading(emptyList()))

        for (token in tokens) {
            val readings = Numerals.readings(token)
            val next = mutableListOf<CallReading>()
            for (partial in beam) {
                for (reading in readings) {
                    when (reading.kind) {
                        TokenKind.FILLER ->
                            next += partial.copy(weight = partial.weight * reading.weight)

                        TokenKind.START ->
                            next += partial.copy(
                                hasStart = true,
                                weight = partial.weight * reading.weight,
                            )

                        TokenKind.SIDE_OUT ->
                            next += partial.copy(
                                sideOutHint = true,
                                weight = partial.weight * reading.weight,
                            )

                        TokenKind.NUMERAL -> {
                            val value = reading.value!!
                            next += partial.copy(
                                numerals = partial.numerals + value,
                                weight = partial.weight * reading.weight,
                            )
                            // Spoken compounds: "twenty one" -> 21, "one one" -> 11, "one five" -> 15.
                            val previous = partial.numerals.lastOrNull()
                            val merged = mergeSpoken(previous, value)
                            if (merged != null) {
                                next += partial.copy(
                                    numerals = partial.numerals.dropLast(1) + merged.first,
                                    weight = partial.weight * reading.weight * merged.second,
                                )
                            }
                        }
                    }
                }
            }
            beam = next.dedupe().sortedByDescending { it.weight }.take(BEAM)
        }

        // An utterance can carry chatter around the call ("okay, seven five two, here we go").
        // Slide a window of the expected size over anything longer.
        val windowed = beam.flatMap { reading ->
            if (reading.numerals.size <= expected) listOf(reading)
            else (0..reading.numerals.size - expected).map { start ->
                reading.copy(
                    numerals = reading.numerals.subList(start, start + expected),
                    weight = reading.weight * WINDOW_PENALTY,
                )
            }
        }

        return windowed.dedupe()
            .filter { it.numerals.isNotEmpty() || it.hasStart || it.sideOutHint }
            .sortedByDescending { it.weight }
            .take(BEAM)
    }

    /** "twenty"+"one" is 21; "one"+"one" is often 11. Returns the merged value and its penalty. */
    private fun mergeSpoken(previous: Int?, current: Int): Pair<Int, Double>? = when {
        previous == 20 && current in 1..9 -> (20 + current) to 0.9
        previous == 1 && current in 0..9 -> (10 + current) to 0.30
        else -> null
    }

    private fun List<CallReading>.dedupe(): List<CallReading> =
        groupBy { Triple(it.numerals, it.hasStart, it.sideOutHint) }
            .map { (_, group) -> group.maxByOrNull { it.weight }!! }

    /**
     * How strongly [reading] supports [call], in 0..1.
     *
     * Exact match is the common case. Partial credit exists because a mic 20 feet from a player
     * facing away routinely drops one word out of three — but partial readings must still align
     * from the start of the call (the serving score is spoken first and is the loudest word) and
     * must appear in order.
     */
    fun scoreAgainst(reading: CallReading, call: ScoreCall, isStartOfGame: Boolean): Double {
        val expected = call.asList()

        // "zero zero start" is the spoken form of "zero zero two", and it is decisive: it can only
        // be the opening call of a game. A stray "start" elsewhere in an utterance is ignored and
        // the numerals are matched normally.
        if (reading.hasStart && reading.numerals.size <= 2 && reading.numerals.all { it == 0 }) {
            return if (isStartOfGame) 1.0 else 0.0
        }

        if (reading.numerals.isEmpty()) return 0.0
        if (reading.numerals == expected) return 1.0
        if (reading.numerals.size > expected.size) return 0.0

        // Prefix/subsequence, anchored at the first spoken numeral.
        if (reading.numerals.first() != expected.first()) return 0.0
        var index = 1
        for (value in reading.numerals.drop(1)) {
            while (index < expected.size && expected[index] != value) index++
            if (index >= expected.size) return 0.0
            index++
        }
        val coverage = reading.numerals.size.toDouble() / expected.size
        return if (reading.numerals.size >= 2) PARTIAL_CREDIT * coverage else WEAK_CREDIT * coverage
    }

    private const val WINDOW_PENALTY = 0.85
    private const val PARTIAL_CREDIT = 0.75
    private const val WEAK_CREDIT = 0.25
}
