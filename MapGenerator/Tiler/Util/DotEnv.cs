using System;
using System.Collections.Generic;
using System.IO;

namespace Tiler.Util
{
    /// <summary>
    /// Minimal .env file reader.
    ///
    /// This is intentionally simple:
    /// - KEY=VALUE pairs
    /// - Ignores comments (#)
    /// - Ignores malformed lines
    /// - Does NOT override existing environment variables
    ///
    /// Designed for debug flags only.
    /// </summary>
    public static class DotEnv
    {
        /// <summary>
        /// Loads environment variables from a .env file if it exists.
        /// </summary>
        /// <param name="path">Path to .env file.</param>
        public static void Load(string path)
        {
            if (!File.Exists(path))
                return;

            foreach (var line in File.ReadAllLines(path))
            {
                var trimmed = line.Trim();

                // Skip empty lines and comments
                if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith("#"))
                    continue;

                int idx = trimmed.IndexOf('=');
                if (idx <= 0)
                    continue;

                string key = trimmed.Substring(0, idx).Trim();
                string value = trimmed.Substring(idx + 1).Trim();

                // Do not override existing env vars
                if (Environment.GetEnvironmentVariable(key) == null)
                {
                    Environment.SetEnvironmentVariable(key, value);
                }
            }
        }

        /// <summary>
        /// Reads a boolean environment variable with permissive parsing.
        /// </summary>
        public static bool GetBool(string key)
        {
            string? value = Environment.GetEnvironmentVariable(key);
            if (value == null)
                return false;

            return value.Equals("1")
                || value.Equals("true", StringComparison.OrdinalIgnoreCase)
                || value.Equals("yes", StringComparison.OrdinalIgnoreCase);
        }
    }
}
