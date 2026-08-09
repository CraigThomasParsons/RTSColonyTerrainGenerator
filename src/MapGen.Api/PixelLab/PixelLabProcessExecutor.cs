using System.Diagnostics;

namespace MapGen.Api.PixelLab;

public sealed record PixelLabProcessRequest(string Command, IReadOnlyList<string> Arguments);
public sealed record PixelLabProcessResult(int ExitCode, string StandardOutput, string StandardError);

public interface IPixelLabProcessExecutor
{
    Task<PixelLabProcessResult> ExecuteAsync(PixelLabProcessRequest request, CancellationToken cancellationToken);
}

/// <summary>Runs the repository-owned Python adapter without a shell or user-controlled paths.</summary>
public sealed class PixelLabProcessExecutor(PixelLabOptions options) : IPixelLabProcessExecutor
{
    public async Task<PixelLabProcessResult> ExecuteAsync(
        PixelLabProcessRequest request,
        CancellationToken cancellationToken)
    {
        var start = new ProcessStartInfo
        {
            FileName = options.PythonExecutable,
            WorkingDirectory = options.RepositoryRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        if (request.Command == "balance")
        {
            start.ArgumentList.Add(options.ClientPath);
            start.ArgumentList.Add("--mode");
            start.ArgumentList.Add("balance");
        }
        else
        {
            start.ArgumentList.Add(options.OrchestratorPath);
            start.ArgumentList.Add(request.Command);
        }
        foreach (string argument in request.Arguments)
        {
            start.ArgumentList.Add(argument);
        }

        using var process = new Process { StartInfo = start };
        if (!process.Start())
        {
            throw new InvalidOperationException("The PixelLab worker process could not be started.");
        }

        Task<string> stdout = process.StandardOutput.ReadToEndAsync(cancellationToken);
        Task<string> stderr = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken);
        return new PixelLabProcessResult(process.ExitCode, await stdout, await stderr);
    }
}
