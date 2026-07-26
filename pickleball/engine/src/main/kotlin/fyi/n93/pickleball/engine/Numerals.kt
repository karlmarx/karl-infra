package fyi.n93.pickleball.engine

/** What a single recognised word can mean. */
enum class TokenKind {
    /** A number. [TokenReading.value] is set. */
    NUMERAL,

    /** The word "start" — doubles shorthand for the second half of a "zero zero two" call. */
    START,

    /** Someone announcing a side out verbally. A hint, not a command. */
    SIDE_OUT,

    /** Recognised but meaningless here ("score", "is", "and", "uh"). */
    FILLER,
}

/**
 * One possible interpretation of one recognised word, with how much we believe it.
 *
 * A word can have several readings. "on" is usually filler but is a common clipped "one"; "sevens"
 * is a sloppy "seven"; "to" and "too" are "two" almost every time on a pickleball court.
 */
data class TokenReading(
    val kind: TokenKind,
    val value: Int? = null,
    val weight: Double = 1.0,
)

/**
 * Word-level lexicon for the tiny vocabulary this app needs.
 *
 * This is deliberately not a language model. The recogniser is run with a closed grammar of ~40
 * words, so the only errors that survive are homophones and sloppy speech, and both are enumerable.
 * Anything this lexicon gets wrong is caught downstream by the legality filter in [CallGrammar] /
 * [HypothesisTracker]: a reading that cannot follow the current state is discarded no matter how
 * confident the recogniser was.
 */
object Numerals {

    private val FILLER_READING = TokenReading(TokenKind.FILLER, weight = 1.0)

    private fun num(value: Int, weight: Double = 1.0) =
        listOf(TokenReading(TokenKind.NUMERAL, value, weight))

    private val lexicon: Map<String, List<TokenReading>> = buildMap {
        // Canonical numerals 0..21 (games are played to 11, 15 or 21).
        val canonical = listOf(
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
            "eighteen", "nineteen", "twenty",
        )
        canonical.forEachIndexed { value, word -> put(word, num(value)) }
        put("twentyone", num(21))

        // Digits, in case the recogniser emits them directly.
        (0..21).forEach { put(it.toString(), num(it)) }

        // Zero, as actually spoken.
        put("oh", num(0))
        put("o", num(0))
        put("nothing", num(0))
        put("love", num(0))
        put("nil", num(0))
        put("zip", num(0))
        put("none", num(0))

        // Homophones and mush. Weights below 1.0 mean "probably this, but stay open".
        put("won", num(1))
        put("wan", num(1, 0.8))
        put("juan", num(1, 0.7))
        put("to", num(2))
        put("too", num(2))
        put("tu", num(2, 0.8))
        put("tree", num(3, 0.7))
        put("free", num(3, 0.6))
        put("for", num(4))
        put("fore", num(4))
        put("sex", num(6, 0.6))
        put("sicks", num(6, 0.8))
        put("ate", num(8))
        put("eat", num(8, 0.6))
        put("nein", num(9, 0.8))
        put("tin", num(10, 0.7))
        put("tan", num(10, 0.6))

        // "start" — and what recognisers hear instead of it.
        put("start", listOf(TokenReading(TokenKind.START)))
        put("starts", listOf(TokenReading(TokenKind.START)))
        put("stark", listOf(TokenReading(TokenKind.START, weight = 0.8)))
        put("star", listOf(TokenReading(TokenKind.START, weight = 0.8)))
        put("started", listOf(TokenReading(TokenKind.START, weight = 0.7)))

        // Verbal side-out announcements.
        put("sideout", listOf(TokenReading(TokenKind.SIDE_OUT)))
        put("side", listOf(TokenReading(TokenKind.SIDE_OUT, weight = 0.5), FILLER_READING))
        put("out", listOf(TokenReading(TokenKind.SIDE_OUT, weight = 0.4), FILLER_READING))

        // Common connective noise inside a call: "seven, five — two", "score is seven five two".
        listOf("score", "is", "and", "uh", "um", "the", "we", "they", "at", "dash", "serving")
            .forEach { put(it, listOf(FILLER_READING)) }

        // "on" is filler far more often than not, but "seven on one" is a real thing people say.
        put("on", listOf(FILLER_READING, TokenReading(TokenKind.NUMERAL, 1, 0.35)))
    }

    /**
     * Acoustically confusable numerals, added as low-weight extra readings.
     *
     * These exist purely so the legality filter has something to rescue. If the recogniser hears
     * "seven" but only 11 is a legal score, the 11 reading survives and the call still lands.
     */
    private val confusions: Map<Int, List<Pair<Int, Double>>> = mapOf(
        7 to listOf(11 to 0.10),
        11 to listOf(7 to 0.10),
        9 to listOf(5 to 0.08, 19 to 0.08),
        5 to listOf(9 to 0.08, 15 to 0.08),
        15 to listOf(5 to 0.08, 16 to 0.06),
        13 to listOf(3 to 0.08),
        3 to listOf(13 to 0.08),
        14 to listOf(4 to 0.08),
        4 to listOf(14 to 0.08),
        16 to listOf(6 to 0.08),
        6 to listOf(16 to 0.08),
        18 to listOf(8 to 0.08),
        8 to listOf(18 to 0.08),
        10 to listOf(2 to 0.06),
    )

    /** Lowercase, drop punctuation, and undo the plural people tack onto numerals ("sevens"). */
    fun normalise(raw: String): String {
        val cleaned = raw.lowercase().filter { it.isLetterOrDigit() }
        if (cleaned in lexicon) return cleaned
        if (cleaned.length > 2 && cleaned.endsWith("s")) {
            val singular = cleaned.dropLast(1)
            if (singular in lexicon) return singular
        }
        return cleaned
    }

    /**
     * All readings of one word, best first. Unknown words read as filler — an unrecognised word in
     * the middle of a call must not destroy the call.
     */
    fun readings(raw: String): List<TokenReading> {
        val word = normalise(raw)
        val base = lexicon[word] ?: return listOf(FILLER_READING)
        val expanded = base.flatMap { reading ->
            val extra = reading.value
                ?.let { confusions[it] }
                ?.map { (alt, w) -> TokenReading(TokenKind.NUMERAL, alt, reading.weight * w) }
                ?: emptyList()
            listOf(reading) + extra
        }
        return expanded.sortedByDescending { it.weight }
    }

    /** True if the word carries no score information at all. */
    fun isFillerOnly(raw: String): Boolean =
        readings(raw).all { it.kind == TokenKind.FILLER }

    /**
     * The closed grammar handed to the on-device recogniser. Restricting recognition to this list
     * is what makes an offline 40 MB model accurate enough to trust.
     */
    fun recognitionVocabulary(): List<String> = lexicon.keys
        .filter { it.any(Char::isLetter) }
        .sorted()
}
