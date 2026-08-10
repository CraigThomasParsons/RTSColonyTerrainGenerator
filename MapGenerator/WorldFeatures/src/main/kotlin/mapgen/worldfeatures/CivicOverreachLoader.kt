package mapgen.worldfeatures

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File

object CivicOverreachLoader {
    private val json = Json {
        ignoreUnknownKeys = true
    }

    fun load(jobId: String, outputDirectory: String, logger: StageLogger): CivicOverreachData? {
        val payloadFile = File(outputDirectory, "$jobId.civic_overreach.worldpayload")
        if (!payloadFile.exists()) {
            logger.info("civic_missing", "No CivicOverreach payload found for job $jobId")
            return null
        }

        val payloadText = payloadFile.readText()
        return try {
            val payloadElement = json.parseToJsonElement(payloadText)
            parse(payloadElement, logger)
        } catch (exception: Exception) {
            logger.warn("civic_parse_failed", "Failed to parse CivicOverreach payload: ${payloadFile.absolutePath}")
            null
        }
    }

    private fun parse(element: JsonElement, logger: StageLogger): CivicOverreachData {
        val root = element.jsonObject
        val concrete = root["concrete"]?.jsonObject ?: JsonObject(emptyMap())

        val bridges = parseBridges(concrete["bridges"])
        val roads = parseRoads(concrete["roads"])
        val buildings = parseBuildings(concrete["buildings"])

        logger.info(
            "civic_loaded",
            "Loaded CivicOverreach bridges=${bridges.size} roads=${roads.size} buildings=${buildings.size}"
        )

        return CivicOverreachData(
            bridges = bridges,
            roads = roads,
            buildings = buildings
        )
    }

    private fun parseBridges(element: JsonElement?): List<CivicBridge> {
        val array = element?.jsonArray ?: JsonArray(emptyList())
        return array.mapNotNull { bridgeElement ->
            val bridge = bridgeElement.jsonObject
            val x = bridge["x"]?.jsonPrimitive?.intOrNull ?: return@mapNotNull null
            val y = bridge["y"]?.jsonPrimitive?.intOrNull ?: return@mapNotNull null
            CivicBridge(
                id = bridge["id"]?.jsonPrimitive?.content,
                x = x,
                y = y,
                length = bridge["length"]?.jsonPrimitive?.intOrNull,
                orientation = bridge["orientation"]?.jsonPrimitive?.content,
                status = bridge["status"]?.jsonPrimitive?.content,
                cause = bridge["cause"]?.jsonPrimitive?.content
            )
        }
    }

    private fun parseRoads(element: JsonElement?): List<CivicRoad> {
        val array = element?.jsonArray ?: JsonArray(emptyList())
        return array.mapNotNull { roadElement ->
            val road = roadElement.jsonObject
            val path = parsePath(road["path"])
            if (path.isEmpty()) return@mapNotNull null

            CivicRoad(
                path = path,
                status = road["status"]?.jsonPrimitive?.content
            )
        }
    }

    private fun parseBuildings(element: JsonElement?): List<CivicBuilding> {
        val array = element?.jsonArray ?: JsonArray(emptyList())
        return array.mapNotNull { buildingElement ->
            val building = buildingElement.jsonObject
            val x = building["x"]?.jsonPrimitive?.intOrNull ?: return@mapNotNull null
            val y = building["y"]?.jsonPrimitive?.intOrNull ?: return@mapNotNull null
            CivicBuilding(
                x = x,
                y = y,
                type = building["type"]?.jsonPrimitive?.content,
                status = building["status"]?.jsonPrimitive?.content
            )
        }
    }

    private fun parsePath(element: JsonElement?): List<CivicCoord> {
        val array = element?.jsonArray ?: JsonArray(emptyList())
        return array.mapNotNull { pairElement ->
            val pair = pairElement.jsonArray
            val x = pair.getOrNull(0)?.jsonPrimitive?.intOrNull
            val y = pair.getOrNull(1)?.jsonPrimitive?.intOrNull
            if (x == null || y == null) {
                null
            } else {
                CivicCoord(x, y)
            }
        }
    }
}
