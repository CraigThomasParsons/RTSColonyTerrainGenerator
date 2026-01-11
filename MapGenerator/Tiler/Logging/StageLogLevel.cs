namespace Tiler.Logging
{
    /// <summary>
    /// Human-facing log levels used by Tiler code.
    ///
    /// These intentionally mirror the Dafny LogLevel datatype,
    /// but are kept separate to avoid codegen coupling.
    /// </summary>
    public enum StageLogLevel
    {
        Trace,
        Debug,
        Info,
        Warn,
        Error
    }
}
