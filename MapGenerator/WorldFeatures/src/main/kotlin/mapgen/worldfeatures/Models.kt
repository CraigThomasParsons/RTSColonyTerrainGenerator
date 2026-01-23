package mapgen.worldfeatures

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject

/**
 * ParsedPayload
 *
 * Minimal model of the world payload for WorldFeatures.
 *
 * Why: We keep only the fields needed for feature planning and preserve the tiles array.
 */
@Serializable
data class ParsedPayload(
    val version: Int,
    @SerialName("job_id") val jobId: String,
    val map: MapInfo,
    val tiles: List<TileInfo>,
    val features: List<WorldFeature> = emptyList()
) {
    companion object {
        fun fromJson(payloadElement: JsonElement, logger: StageLogger): ParsedPayload {
            val payloadObject = payloadElement.jsonObject

            val version = payloadObject["version"]?.jsonPrimitive?.int ?: 1
            val jobId = payloadObject["job_id"]?.jsonPrimitive?.content ?: "unknown"

            val mapObject = payloadObject["map"]?.jsonObject ?: JsonObject(emptyMap())
            val mapInfo = MapInfo.fromJson(mapObject)

            val tileElements = payloadObject["tiles"]?.jsonArray ?: emptyList()
            val tiles = tileElements.mapNotNull { tileElement ->
                TileInfo.fromJson(tileElement, logger)
            }

            return ParsedPayload(
                version = version,
                jobId = jobId,
                map = mapInfo,
                tiles = tiles,
                features = emptyList()
            )
        }
    }

    fun withFeatures(featureList: List<WorldFeature>): ParsedPayload {
        // Why: WorldFeatures must emit a new payload with added features.
        return copy(features = featureList)
    }
}

@Serializable
data class MapInfo(
    @SerialName("width_in_cells") val widthInCells: Int,
    @SerialName("height_in_cells") val heightInCells: Int
) {
    companion object {
        fun fromJson(mapObject: JsonObject): MapInfo {
            val width = mapObject["width_in_cells"]?.jsonPrimitive?.int ?: 0
            val height = mapObject["height_in_cells"]?.jsonPrimitive?.int ?: 0

            return MapInfo(widthInCells = width, heightInCells = height)
        }
    }
}

@Serializable
data class TileInfo(
    val x: Int,
    val y: Int,
    val terrain: String,
    val weather: WeatherInfo? = null,
    val decorations: List<JsonElement> = emptyList()
) {
    companion object {
        fun fromJson(tileElement: JsonElement, logger: StageLogger): TileInfo? {
            val tileObject = tileElement.jsonObject

            val x = tileObject["x"]?.jsonPrimitive?.int
            val y = tileObject["y"]?.jsonPrimitive?.int
            val terrain = tileObject["terrain"]?.jsonPrimitive?.content

            if (x == null || y == null || terrain == null) {
                logger.warn("tile_skip", "Skipping tile missing x/y/terrain")
                return null
            }

            val weatherObject = tileObject["weather"]?.jsonObject
            val weatherInfo = weatherObject?.let { WeatherInfo.fromJson(it) }

            val decorations = tileObject["decorations"]?.jsonArray ?: emptyList()

            return TileInfo(
                x = x,
                y = y,
                terrain = terrain,
                weather = weatherInfo,
                decorations = decorations
            )
        }
    }
}

@Serializable
data class WeatherInfo(
    val x: Int,
    val y: Int,
    val slope: Int,
    val flow: Int,
    val basin: Int
) {
    companion object {
        fun fromJson(weatherObject: JsonObject): WeatherInfo? {
            val x = weatherObject["x"]?.jsonPrimitive?.int ?: return null
            val y = weatherObject["y"]?.jsonPrimitive?.int ?: return null
            val slope = weatherObject["slope"]?.jsonPrimitive?.int ?: 0
            val flow = weatherObject["flow"]?.jsonPrimitive?.int ?: 0
            val basin = weatherObject["basin"]?.jsonPrimitive?.int ?: 0

            return WeatherInfo(x = x, y = y, slope = slope, flow = flow, basin = basin)
        }
    }
}

@Serializable
data class WorldFeature(
    val type: String,
    val x: Int,
    val y: Int,
    val reason: String,
    val details: Map<String, String> = emptyMap()
)
