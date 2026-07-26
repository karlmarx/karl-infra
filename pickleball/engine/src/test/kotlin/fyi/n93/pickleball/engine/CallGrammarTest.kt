package fyi.n93.pickleball.engine

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class CallGrammarTest {

    private fun readingsOf(vararg tokens: String, expected: Int = 3) =
        CallGrammar.parse(tokens.toList(), expected)

    private fun numeralSets(vararg tokens: String, expected: Int = 3) =
        readingsOf(*tokens, expected = expected).map { it.numerals }.toSet()

    @Test
    fun `clean doubles call parses exactly`() {
        val best = readingsOf("seven", "five", "two").first()
        assertEquals(listOf(7, 5, 2), best.numerals)
    }

    @Test
    fun `sloppy plurals are normalised`() {
        assertEquals("seven", Numerals.normalise("Sevens"))
        assertEquals("seven", Numerals.normalise("seven,"))
        assertTrue(numeralSets("sevens", "five", "two").contains(listOf(7, 5, 2)))
    }

    @Test
    fun `homophones read as numerals`() {
        assertTrue(numeralSets("for", "too", "won").contains(listOf(4, 2, 1)))
        assertTrue(numeralSets("ate", "oh", "one").contains(listOf(8, 0, 1)))
        assertTrue(numeralSets("nothing", "nothing", "two").contains(listOf(0, 0, 2)))
    }

    @Test
    fun `sevens on one yields both the filler and the clipped-numeral reading`() {
        val sets = numeralSets("sevens", "on", "one")
        assertTrue(listOf(7, 1) in sets, "\"on\" as filler: $sets")
        assertTrue(listOf(7, 1, 1) in sets, "\"on\" as a clipped one: $sets")
    }

    @Test
    fun `start token is captured`() {
        val reading = readingsOf("zero", "zero", "start").first()
        assertTrue(reading.hasStart)
        assertEquals(listOf(0, 0), reading.numerals)
    }

    @Test
    fun `chatter around the call is windowed away`() {
        val sets = numeralSets("okay", "score", "is", "three", "four", "one", "lets", "go")
        assertTrue(listOf(3, 4, 1) in sets, sets.toString())
    }

    @Test
    fun `spoken compounds are offered`() {
        assertTrue(numeralSets("twenty", "one", "nineteen", "two").contains(listOf(21, 19, 2)))
        assertTrue(numeralSets("one", "one", "five", "one").contains(listOf(11, 5, 1)))
    }

    @Test
    fun `unknown words do not destroy a call`() {
        val sets = numeralSets("grbl", "six", "three", "one")
        assertTrue(listOf(6, 3, 1) in sets, sets.toString())
    }

    @Test
    fun `exact match scores one and a wrong call scores zero`() {
        val reading = CallReading(listOf(7, 5, 2))
        assertEquals(1.0, CallGrammar.scoreAgainst(reading, ScoreCall(7, 5, 2), false))
        assertEquals(0.0, CallGrammar.scoreAgainst(reading, ScoreCall(7, 5, 1), false))
    }

    @Test
    fun `partial call gets partial credit but must align from the serving score`() {
        val dropped = CallReading(listOf(7, 2))
        val credit = CallGrammar.scoreAgainst(dropped, ScoreCall(7, 5, 2), false)
        assertTrue(credit > 0.0 && credit < 1.0, "expected partial credit, got $credit")
        assertEquals(0.0, CallGrammar.scoreAgainst(CallReading(listOf(5, 2)), ScoreCall(7, 5, 2), false))
    }

    @Test
    fun `start only matches the opening call of a game`() {
        val reading = CallReading(listOf(0, 0), hasStart = true)
        assertEquals(1.0, CallGrammar.scoreAgainst(reading, ScoreCall(0, 0, 2), isStartOfGame = true))
        assertEquals(0.0, CallGrammar.scoreAgainst(reading, ScoreCall(0, 0, 1), isStartOfGame = false))
    }

    @Test
    fun `confusable numerals appear as low-weight readings`() {
        val eleven = Numerals.readings("seven").filter { it.value == 11 }
        assertTrue(eleven.isNotEmpty(), "seven should offer 11 as a low-weight alternative")
        assertTrue(eleven.first().weight < 0.3)
    }

    @Test
    fun `recognition vocabulary is small enough for a closed grammar`() {
        val vocab = Numerals.recognitionVocabulary()
        assertTrue(vocab.size in 30..80, "vocabulary was ${vocab.size} words")
        assertTrue("start" in vocab && "seven" in vocab && "oh" in vocab)
    }
}
