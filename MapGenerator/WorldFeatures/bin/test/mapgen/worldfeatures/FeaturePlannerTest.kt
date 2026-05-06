package mapgen.worldfeatures

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class FeaturePlannerTest {
    @Test
    fun `selects ramp, cavern, and lumber deterministically`() {
        val logger = StageLogger("test-job", "logs/jobs/test-worldfeatures.log")
        val planner = FeaturePlanner(logger)

        val tiles = listOf(
            TileInfo(x = 0, y = 0, terrain = "rock", weather = WeatherInfo(0, 0, slope = 900, flow = 0, basin = 1)),
            TileInfo(x = 1, y = 0, terrain = "grass", weather = WeatherInfo(0, 0, slope = 10, flow = 0, basin = 1)),
            TileInfo(x = 2, y = 0, terrain = "mountain", weather = WeatherInfo(1, 0, slope = 1200, flow = 0, basin = 2)),
            TileInfo(x = 3, y = 0, terrain = "grass", weather = WeatherInfo(1, 0, slope = 30, flow = 0, basin = 2))
        )

        val payload = ParsedPayload(
            version = 1,
            jobId = "test-job",
            map = MapInfo(widthInCells = 2, heightInCells = 2),
            tiles = tiles
        )

        val features = planner.planFeatures(payload)

        val featureTypes = features.map { it.type }.sorted()
        assertEquals(listOf("cavern", "lumber", "ramp"), featureTypes)

        val rampFeature = features.first { it.type == "ramp" }
        assertEquals(1, rampFeature.x)
        assertEquals(0, rampFeature.y)
    }
}
