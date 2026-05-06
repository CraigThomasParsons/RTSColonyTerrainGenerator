package mapgen.pathfinder

import kotlinx.serialization.json.Json
import java.io.File
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

fun main(arguments: Array<String>) {
    val configuration = PathFinderConfig.fromArgs(arguments)

    val logger = StageLogger(
        jobId = "unknown",
        logDirectory = configuration.logDirectory
    )

    logger.info("pathfinder_start", "PathFinder starting")

    val inputPayloadFile = InputPayloadLocator.locatePayload(
        inputPath = configuration.inputPath,
        logger = logger
    )

    if (inputPayloadFile == null) {
        logger.warn("payload_missing", "No worldpayload file found to process")
        return
    }

    val payloadText = inputPayloadFile.readText()
    val payloadParser = Json { ignoreUnknownKeys = true }
    
    val payload: WorldFeaturesPayload
    try {
        payload = payloadParser.decodeFromString<WorldFeaturesPayload>(payloadText)
        logger.updateJobId(payload.jobId)
        logger.info("payload_loaded", "Loaded payload for job: ${payload.jobId}")
        logger.info("payload_stats", "Tiles: ${payload.tiles.size}, Features: ${payload.features.size}")
        
    } catch (e: Exception) {
        logger.error("payload_parse_failed", "Failed to parse payload: ${e.message}")
        return
    }

    // TYS Phase 2: Graph & Pathfinding Core
    
    // 1. Index tiles for O(1) lookup
    logger.info("indexing_tiles", "Indexing ${payload.tiles.size} tiles...")
    val tileMap = payload.tiles.associateBy { "${it.x},${it.y}" }

    // 2. Initialize Engine
    // Why: payload.map dimensions seem to mismatch the actual tile count (header says 248, data implies 496).
    // We calculate limits from the data to be safe.
    val actualWidth = (payload.tiles.maxOfOrNull { it.x } ?: 0) + 1
    val actualHeight = (payload.tiles.maxOfOrNull { it.y } ?: 0) + 1
    
    logger.info("map_dimensions", "Header: ${payload.map.widthInCells}x${payload.map.heightInCells}, Actual: ${actualWidth}x${actualHeight}")

    val engine = PathFindingEngine(
        tiles = tileMap,
        width = actualWidth,
        height = actualHeight,
        logger = logger
    )

    // 3. Phase 3: Infrastructure Analysis & Output
    val routes = mutableListOf<Route>()
    val requests = mutableListOf<InfrastructureRequest>()
    val features = payload.features
    
    logger.info("analysis_start", "Analyzing connectivity for ${features.size} features")
    
    for (i in 0 until features.size) {
        for (j in i + 1 until features.size) {
            val from = features[i]
            val to = features[j]
            
            logger.info("path_search", "Route: ${from.type}(${from.x},${from.y}) -> ${to.type}(${to.x},${to.y})")
            val result = engine.findPath(from.x, from.y, to.x, to.y)
            
            val route = Route(
                from = "${from.type}(${from.x},${from.y})",
                to = "${to.type}(${to.x},${to.y})",
                success = result.success,
                cost = result.cost,
                pathLength = result.path.size,
                path = if (result.success) result.path.map { "${it.x},${it.y}" } else emptyList()
            )
            routes.add(route)
            
            if (!result.success) {
                 requests.add(InfrastructureRequest(
                     type = "investigation",
                     x = from.x,
                     y = from.y,
                     reason = "Route to ${to.type} failed: ${result.failureReason}"
                 ))
            }
        }
    }
    
    val report = ConnectivityReport(
        jobId = payload.jobId,
        map = payload.map,
        tiles = payload.tiles,
        features = payload.features,
        routes = routes,
        requests = requests
    )
    
    val json = Json { prettyPrint = true }
    val reportJson = json.encodeToString(ConnectivityReport.serializer(), report)
    
    val outputDir = File(configuration.outputDirectory)
    outputDir.mkdirs()
    val outputFile = File(outputDir, "${payload.jobId}.json")
    outputFile.writeText(reportJson)
    
    logger.info("report_written", "Wrote connectivity report: ${outputFile.absolutePath}")
    
    logger.info("pathfinder_complete", "PathFinder phase 2 complete (core logic)")
}

data class PathFinderConfig(
    val inputPath: String,
    val outputDirectory: String,
    val logDirectory: String
) {
    companion object {
        fun fromArgs(arguments: Array<String>): PathFinderConfig {
            var inputPath = "MapGenerator/WorldFeatures/outbox"
            var outputDirectory = "MapGenerator/PathFinder/outbox"
            var logDirectory = "logs/jobs"

            val iterator = arguments.iterator()
            while (iterator.hasNext()) {
                when (val argument = iterator.next()) {
                    "--input" -> inputPath = iterator.next()
                    "--output" -> outputDirectory = iterator.next()
                    "--log-dir" -> logDirectory = iterator.next()
                }
            }

            return PathFinderConfig(
                inputPath = inputPath,
                outputDirectory = outputDirectory,
                logDirectory = logDirectory
            )
        }
    }
}

class StageLogger(
    jobId: String,
    private val logDirectory: String
) {
    private var currentJobId: String = jobId

    fun updateJobId(jobId: String) {
        currentJobId = jobId
    }

    fun info(event: String, message: String) = write("INFO", event, message)
    fun warn(event: String, message: String) = write("WARN", event, message)
    fun error(event: String, message: String) = write("ERROR", event, message)

    private fun write(level: String, event: String, message: String) {
        val timestamp = DateTimeFormatter.ISO_INSTANT
            .withZone(ZoneOffset.UTC)
            .format(Instant.now())

        val line = "$timestamp [job=$currentJobId] [stage=pathfinder] $level $message"

        val jobLogDirectory = File(logDirectory, currentJobId)
        jobLogDirectory.mkdirs()
        val logFile = File(jobLogDirectory, "pathfinder.log")
        logFile.appendText(line + "\n")
        println(line)
    }
}

object InputPayloadLocator {
    fun locatePayload(inputPath: String, logger: StageLogger): File? {
        val inputFile = File(inputPath)

        if (inputFile.isFile && inputFile.extension == "worldpayload") {
            logger.info("payload_found", "Using explicit payload file: ${inputFile.absolutePath}")
            return inputFile
        }

        if (!inputFile.exists() || !inputFile.isDirectory) {
            logger.warn("payload_missing", "Input path is not a directory: ${inputFile.absolutePath}")
            return null
        }

        val payloadFile = inputFile
            .listFiles { file -> file.extension == "worldpayload" }
            ?.maxByOrNull { file -> file.lastModified() }

        if (payloadFile == null) {
            logger.warn("payload_missing", "No worldpayload files found in: ${inputFile.absolutePath}")
            return null
        }

        logger.info("payload_found", "Selected payload file: ${payloadFile.absolutePath}")
        return payloadFile
    }
}
