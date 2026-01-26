package mapgen.worldfeatures

import kotlin.math.abs

/**
 * FeaturePlanner
 *
 * Builds a deterministic list of world features for a payload.
 *
 * Why: Deterministic planning makes debugging and tests stable.
 */
class FeaturePlanner(
    private val logger: StageLogger
) {
    fun planFeatures(payload: ParsedPayload): List<WorldFeature> {
        logger.info("feature_plan_start", "Planning world features")

        val features = mutableListOf<WorldFeature>()

        val rampCandidate = selectRampCandidate(payload.tiles)
        if (rampCandidate != null) {
            features.add(
                WorldFeature(
                    type = "ramp",
                    x = rampCandidate.x,
                    y = rampCandidate.y,
                    reason = "lowest_slope_near_ridge",
                    details = mapOf("why" to "Ramps should connect ridge rings to low-slope tiles")
                )
            )
            logger.info("feature_ramp", "Selected ramp at (${rampCandidate.x}, ${rampCandidate.y})")
        } else {
            logger.warn("feature_ramp_missing", "No ramp candidate found")
        }

        val cavernCandidate = selectCavernCandidate(payload.tiles)
        if (cavernCandidate != null) {
            features.add(
                WorldFeature(
                    type = "cavern",
                    x = cavernCandidate.x,
                    y = cavernCandidate.y,
                    reason = "rock_or_mountain_tile",
                    details = mapOf("why" to "Caverns should connect to rocky terrain")
                )
            )
            logger.info("feature_cavern", "Selected cavern at (${cavernCandidate.x}, ${cavernCandidate.y})")
        } else {
            logger.warn("feature_cavern_missing", "No cavern candidate found")
        }

        val lumberCandidate = selectLumberCandidate(payload.tiles)
        if (lumberCandidate != null) {
            features.add(
                WorldFeature(
                    type = "lumber",
                    x = lumberCandidate.x,
                    y = lumberCandidate.y,
                    reason = "low_slope_grass_tile",
                    details = mapOf("why" to "Lumber should be reachable on stable terrain")
                )
            )
            logger.info("feature_lumber", "Selected lumber at (${lumberCandidate.x}, ${lumberCandidate.y})")
        } else {
            logger.warn("feature_lumber_missing", "No lumber candidate found")
        }

        logger.info("feature_plan_complete", "Planned ${features.size} features")
        return features
    }

    private fun selectRampCandidate(tiles: List<TileInfo>): TileInfo? {
        // Why: We look for a steep tile (ridge) and a nearby low slope tile.
        val ridgeTile = tiles
            .filter { it.weather != null }
            .maxByOrNull { tile -> tile.weather?.slope ?: 0 }

        if (ridgeTile == null) {
            return null
        }

        val slopeTiles = tiles.filter { it.weather != null }
        if (slopeTiles.isEmpty()) {
            return null
        }

        return slopeTiles
            .sortedWith(compareBy({ it.weather?.slope ?: Int.MAX_VALUE }, { it.y }, { it.x }))
            .minByOrNull { candidate ->
                manhattanDistance(ridgeTile.x, ridgeTile.y, candidate.x, candidate.y)
            }
    }

    private fun selectCavernCandidate(tiles: List<TileInfo>): TileInfo? {
        // Why: Caverns should be placed in rocky or mountainous terrain.
        return tiles
            .filter { tile -> tile.terrain == "rock" || tile.terrain == "mountain" }
            .sortedWith(compareBy({ it.y }, { it.x }))
            .firstOrNull()
    }

    private fun selectLumberCandidate(tiles: List<TileInfo>): TileInfo? {
        // Why: Lumber should be accessible and on stable terrain.
        return tiles
            .filter { tile -> tile.terrain == "grass" }
            .sortedWith(compareBy({ it.weather?.slope ?: Int.MAX_VALUE }, { it.y }, { it.x }))
            .firstOrNull()
    }

    private fun manhattanDistance(x1: Int, y1: Int, x2: Int, y2: Int): Int {
        // Why: Manhattan distance aligns with tile grid navigation.
        return abs(x1 - x2) + abs(y1 - y2)
    }
}
