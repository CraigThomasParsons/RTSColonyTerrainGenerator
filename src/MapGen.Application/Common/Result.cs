namespace MapGen.Application.Common;

/// <summary>
/// Minimal explicit success/failure type for handler boundaries (ADR upstream/0017's
/// Result idiom, kept dependency-free until a shared kernel earns its place).
/// Failures carry a human-readable reason, never an exception.
/// </summary>
public sealed record Result<T>
{
    public bool IsSuccess { get; }
    public T? Value { get; }
    public string? Error { get; }

    private Result(bool isSuccess, T? value, string? error)
    {
        IsSuccess = isSuccess;
        Value = value;
        Error = error;
    }

    public static Result<T> Ok(T value) => new(true, value, null);
    public static Result<T> Fail(string error) => new(false, default, error);
}
