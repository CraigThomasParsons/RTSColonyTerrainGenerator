package mapgen.worldfeatures

import kotlinx.serialization.json.Json
import java.io.File
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * WorldFeaturesApp
 *
 * Entry point for WorldFeatures processing.
 *
 * Why: Keeping a single entry point makes the stage easy to run locally and in systemd.
 */
fun main(arguments: Array<String>) {
    val configuration = WorldFeaturesConfig.fromArgs(arguments)

    val logger = StageLogger(
        jobId = "unknown",
        logDirectory = configuration.logDirectory
    )

    logger.info("worldfeatures_start", "WorldFeatures starting")

    val inputPayloadFile = InputPayloadLocator.locatePayload(
        inputPath = configuration.inputPath,
        logger = logger
    )

    if (inputPayloadFile == null) {
        logger.warn("payload_missing", "No worldpayload file found to process")
        return
    }

    val payloadText = inputPayloadFile.readText()
    val payload = WorldPayloadParser.parse(payloadText, logger)

    if (payload == null) {
        logger.error("payload_parse_failed", "Failed to parse payload: ${inputPayloadFile.absolutePath}")
        return
    }

    val jobId = payload.jobId
    logger.updateJobId(jobId)
    logger.info("payload_loaded", "Loaded worldpayload for job: $jobId")

    val planner = FeaturePlanner(logger)
    val features = planner.planFeatures(payload)

    val civicData = CivicOverreachLoader.load(
        jobId = jobId,
        outputDirectory = configuration.civicOutputDirectory,
        logger = logger
    )

    val civicFeatures = civicData?.let { planner.planCivicFeatures(it, payload.map) } ?: emptyList()
    if (civicFeatures.isNotEmpty()) {
        logger.info("civic_features", "Merged ${civicFeatures.size} CivicOverreach features")
    }
    val outputPayload = payload.withFeatures(features + civicFeatures)
    val outputPath = OutputWriter.writePayload(
        outputPayload,
        configuration.outputDirectory,
        logger
    )

    logger.info("worldfeatures_complete", "WorldFeatures output written: $outputPath")
}

/**
 * WorldFeaturesConfig
 *
 * Lightweight configuration container for runtime parameters.
 *
 * Why: Simple config avoids external files while keeping args explicit.
 */
data class WorldFeaturesConfig(
    val inputPath: String,
    val outputDirectory: String,
    val logDirectory: String,
    val civicOutputDirectory: String
) {
    companion object {
        fun fromArgs(arguments: Array<String>): WorldFeaturesConfig {
            var inputPath = "MapGenerator/TreePlanter/outbox"
            var outputDirectory = "MapGenerator/WorldFeatures/outbox"
            var logDirectory = "logs/jobs"
            var civicOutputDirectory = "MapGenerator/CivicOverreach/outbox"

            val iterator = arguments.iterator()
            while (iterator.hasNext()) {
                when (val argument = iterator.next()) {
                    "--input" -> inputPath = iterator.next()
                    "--output" -> outputDirectory = iterator.next()
                    "--log-dir" -> logDirectory = iterator.next()
                    "--civic-outbox" -> civicOutputDirectory = iterator.next()
                    else -> {
                        // Why: Ignore unknown arguments to keep the tool tolerant.
                    }
                }
            }

            return WorldFeaturesConfig(
                inputPath = inputPath,
                outputDirectory = outputDirectory,
                logDirectory = logDirectory,
                civicOutputDirectory = civicOutputDirectory
            )
        }
    }
}

/**
 * StageLogger
 *
 * Writes MapGenerator-formatted log lines to a job log and stdout.
 *
 * Why: Consistent log formatting feeds the LogStreamer and the AI tester.
 */
class StageLogger(
    jobId: String,
    private val logDirectory: String
) {
    private var currentJobId: String = jobId

    fun updateJobId(jobId: String) {
        // Why: The logger is created before parsing the payload, so we update later.
        currentJobId = jobId
    }

    fun info(event: String, message: String) = write("INFO", event, message)
    fun warn(event: String, message: String) = write("WARN", event, message)
    fun error(event: String, message: String) = write("ERROR", event, message)

    private fun write(level: String, event: String, message: String) {
        val timestamp = DateTimeFormatter.ISO_INSTANT
            .withZone(ZoneOffset.UTC)
            .format(Instant.now())

        // Why: The log format must match mapgenctl for downstream parsing.
        val line = "$timestamp [job=$currentJobId] [stage=worldfeatures] $level $message"

        val jobLogDirectory = File(logDirectory, currentJobId)
        jobLogDirectory.mkdirs()

        val logFile = File(jobLogDirectory, "worldfeatures.log")
        logFile.appendText(line + "\n")
        println(line)
    }
}

object InputPayloadLocator {
    /**
     * Locate a worldpayload file based on a file path or directory.
     *
     * Why: Developers may point directly at a file or a directory.
     */
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

        // Why: We prefer the newest payload to avoid reprocessing old jobs.
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

/**
 * WorldPayloadParser
 *
 * Parses payload JSON into a lightweight, Kotlin-friendly model.
 *
 * Why: Parsing into a model lets us write deterministic feature logic.
 */
object WorldPayloadParser {
    private val json = Json {
        ignoreUnknownKeys = true
    }

    fun parse(payloadText: String, logger: StageLogger): ParsedPayload? {
        return try {
            val payloadElement = json.parseToJsonElement(payloadText)
            ParsedPayload.fromJson(payloadElement, logger)
        } catch (exception: Exception) {
            logger.error("payload_parse_exception", exception.message ?: "Unknown parse error")
            null
        }
    }
}

/**
 * OutputWriter
 *
 * Writes the updated payload JSON to the outbox.
 *
 * Why: WorldFeatures must emit a new payload rather than mutating the input file.
 */
object OutputWriter {
    private val json = Json {
        prettyPrint = true
        prettyPrintIndent = "    "
    }

    fun writePayload(payload: ParsedPayload, outputDirectory: String, logger: StageLogger): String {
        val outputDir = File(outputDirectory)
        outputDir.mkdirs()

        val outputFile = File(outputDir, "${payload.jobId}.worldpayload")
        outputFile.writeText(json.encodeToString(ParsedPayload.serializer(), payload))

        // Why: Logging the output path helps validate the stage output quickly.
        logger.info("payload_written", "Wrote worldpayload: ${outputFile.absolutePath}")
        return outputFile.absolutePath
    }
}
