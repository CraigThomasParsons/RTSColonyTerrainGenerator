package mapgen.pathfinder

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class WorldFeaturesPayload(
    val version: Int,
    @SerialName("job_id") val jobId: String,
    val map: MapInfo,
    val tiles: List<TileInfo>,
    val features: List<WorldFeature> = emptyList()
)

@Serializable
data class MapInfo(
    @SerialName("width_in_cells") val widthInCells: Int,
    @SerialName("height_in_cells") val heightInCells: Int
)

@Serializable
data class TileInfo(
    val x: Int,
    val y: Int,
    val terrain: String,
    val weather: WeatherInfo? = null,
    val decorations: List<JsonElement> = emptyList()
)

@Serializable
data class WeatherInfo(
    val x: Int,
    val y: Int,
    val slope: Int,
    val flow: Int,
    val basin: Long
)

@Serializable
data class WorldFeature(
    val type: String,
    val x: Int,
    val y: Int,
    val reason: String,
    val details: Map<String, String> = emptyMap()
)

// --- Phase 3: Output Models ---

@Serializable
data class ConnectivityReport(
    val version: Int = 1,
    @SerialName("job_id") val jobId: String,
    val map: MapInfo,
    val tiles: List<TileInfo>,
    val features: List<WorldFeature> = emptyList(),
    val routes: List<Route>,
    val requests: List<InfrastructureRequest>
)

@Serializable
data class Route(
    val from: String,
    val to: String,
    val success: Boolean,
    val cost: Double,
    @SerialName("path_length") val pathLength: Int,
    val path: List<String> = emptyList() // "x,y"
)

@Serializable
data class InfrastructureRequest(
    val type: String,
    val x: Int,
    val y: Int,
    val reason: String
)
