#nullable enable

using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using MapGen.Logging;
using System.Numerics;

// Namespace produced by: module {:extern "MapGen.Logging"} MapGenLogging
using MapGen.Logging;

namespace Tiler.Logging
{
    /// <summary>
    /// Stage-scoped logger for the Tiler process.
    ///
    /// PURPOSE:
    /// - Resolve a deterministic, per-job log file path using MAPGEN_LOG_ROOT
    /// - Enforce the Dafny logging contract before emitting any log entry
    /// - Write structured, append-only JSONL log records
    ///
    /// DESIGN PHILOSOPHY:
    /// - This class is intentionally small and boring
    /// - It is NOT a general-purpose logging framework
    /// - It does not manage sinks, rotation, or aggregation
    /// - It exists solely to make pipeline behavior observable and debuggable
    /// </summary>
    public sealed class MapGenStageLogger
    {
        private readonly string _jobId;
        private readonly string _stageName;
        private readonly string _logFilePath;

        /// <summary>
        /// Constructs a stage logger bound to a specific job and stage.
        ///
        /// PURPOSE:
        /// - Bind all log output to a single job identifier
        /// - Ensure log file paths are derived consistently and early
        ///
        /// INPUTS:
        /// - jobId:
        ///     Stable job identifier used for log scoping
        /// - stageName:
        ///     Stable stage name (e.g. "tiler", "heightmap")
        ///
        /// FAILURE MODES:
        /// - Throws if jobId or stageName are empty
        ///   (logging without identity is forbidden)
        /// </summary>
        public MapGenStageLogger(string jobId, string stageName)
        {
            if (string.IsNullOrWhiteSpace(jobId))
            {
                throw new ArgumentException("jobId must be provided.", nameof(jobId));
            }

            if (string.IsNullOrWhiteSpace(stageName))
            {
                throw new ArgumentException("stageName must be provided.", nameof(stageName));
            }

            _jobId = jobId;
            _stageName = stageName;
            _logFilePath = ResolveLogFilePath(jobId, stageName);
        }

        /// <summary>
        /// Converts a human-facing StageLogLevel into the Dafny-generated LogLevel datatype.
        ///
        /// PURPOSE:
        /// - Decouple Tiler code from Dafny code generation details
        /// - Centralize all Dafny interop in one place
        ///
        /// IMPORTANT:
        /// - Never expose Dafny LogLevel to the rest of the codebase
        /// - If Dafny codegen changes, only this method should need updating
        /// </summary>
        private static MapGen.Logging._ILogLevel ToDafnyLevel(StageLogLevel level)
        {
            return level switch
            {
                StageLogLevel.Trace => MapGen.Logging.LogLevel.create_Trace(),
                StageLogLevel.Debug => MapGen.Logging.LogLevel.create_Debug(),
                StageLogLevel.Info  => MapGen.Logging.LogLevel.create_Info(),
                StageLogLevel.Warn  => MapGen.Logging.LogLevel.create_Warn(),
                StageLogLevel.Error => MapGen.Logging.LogLevel.create_Error(),
                _ => throw new ArgumentOutOfRangeException(nameof(level), level, null)
            };
        }


        /// <summary>
        /// Exposes the resolved log file path.
        ///
        /// PURPOSE:
        /// - Allow orchestration or diagnostics code to discover
        ///   where logs are being written without recomputing paths
        /// </summary>
        public string LogFilePath => _logFilePath;

        /// <summary>
        /// Emit an informational log entry.
        ///
        /// PURPOSE:
        /// - Record normal progress and milestones
        /// - Communicate what the stage is doing and why
        /// </summary>
        public void Info(string eventName, string message, IDictionary<string, string>? kv = null)
            => Write(StageLogLevel.Info, eventName, message, kv);

        /// <summary>
        /// Emit a warning log entry.
        ///
        /// PURPOSE:
        /// - Record unusual but non-fatal conditions
        /// - Surface degraded or unexpected behavior
        /// </summary>
        public void Warn(string eventName, string message, IDictionary<string, string>? kv = null)
            => Write(StageLogLevel.Warn, eventName, message, kv);

        /// <summary>
        /// Emit an error log entry.
        ///
        /// PURPOSE:
        /// - Record failures that cause or explain stage termination
        /// - Provide structured context for debugging
        /// </summary>
        public void Error(string eventName, string message, IDictionary<string, string>? kv = null)
            => Write(StageLogLevel.Error, eventName, message, kv);

        /// <summary>
        /// Core logging implementation.
        ///
        /// PURPOSE:
        /// - Validate log intent and inputs
        /// - Enforce the Dafny log contract
        /// - Serialize and append a JSONL record
        ///
        /// DESIGN NOTES:
        /// - All validation happens BEFORE any file I/O
        /// - Contract enforcement is mandatory, not optional
        /// - This method is intentionally private to keep usage disciplined
        /// </summary>
        private void Write(
            StageLogLevel level,
            string eventName,
            string message,
            IDictionary<string, string>? kv
        )
        {
            if (string.IsNullOrWhiteSpace(eventName))
            {
                throw new ArgumentException("eventName must be provided.", nameof(eventName));
            }

            if (string.IsNullOrWhiteSpace(message))
            {
                throw new ArgumentException("message must be provided.", nameof(message));
            }

            long tsMillis = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

            var safeKv = kv is null
                ? new Dictionary<string, string>()
                : new Dictionary<string, string>(kv);

            // Convert key-value map into Dafny runtime map
            Dafny.IMap<string, string> dafnyKv = Dafny.Map<string, string>.Empty;
            foreach (var pair in safeKv)
            {
                dafnyKv = Dafny.Map<string, string>.Update(
                    dafnyKv,
                    pair.Key,
                    pair.Value
                );
            }
            
            var dafnyEvent = LogEvent.create_LogEvent(
                new BigInteger(tsMillis),
                DafnyInterop.String(_stageName),
                DafnyInterop.String(_jobId),
                ToDafnyLevel(level),
                DafnyInterop.String(eventName),
                DafnyInterop.String(message),
                DafnyInterop.StringMap(safeKv)
            );

            // Enforce invariants defined in Dafny
            LogContract.RequireValid(dafnyEvent);

            // Emit JSONL record (language-agnostic)
            var lineObject = new
            {
                ts = tsMillis,
                stage = _stageName,
                job_id = _jobId,
                level = level.ToString(),
                @event = eventName,
                msg = message,
                kv = safeKv
            };

            AppendJsonLine(_logFilePath, lineObject);
        }

        /// <summary>
        /// Resolve the log file path for a given job and stage.
        ///
        /// PURPOSE:
        /// - Centralize filesystem layout logic
        /// - Ensure all stages agree on log placement
        ///
        /// ENVIRONMENT:
        /// - MAPGEN_LOG_ROOT controls the root directory
        /// - Defaults to ./logs for local development
        /// </summary>
        private static string ResolveLogFilePath(string jobId, string stageName)
        {
            string logRoot =
                Environment.GetEnvironmentVariable("MAPGEN_LOG_ROOT") ?? "./logs";

            string jobDir = Path.Combine(logRoot, "jobs", jobId);
            Directory.CreateDirectory(jobDir);

            return Path.Combine(jobDir, $"{stageName}.log.jsonl");
        }

        /// <summary>
        /// Append a single JSON object as a line to the log file.
        ///
        /// PURPOSE:
        /// - Preserve crash safety via append-only writes
        /// - Maintain compatibility with tail, grep, jq, etc.
        /// </summary>
        private static void AppendJsonLine(string filePath, object lineObject)
        {
            var json = JsonSerializer.Serialize(lineObject);
            File.AppendAllText(filePath, json + Environment.NewLine);
        }
    }
}
