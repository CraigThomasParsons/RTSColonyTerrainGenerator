using System.Text.Json;
using System.Buffers.Binary;
using System.IO.Compression;

namespace MapGen.Api.PixelLab;

/// <summary>
/// Credit-free development transport for clicking through Map Studio. It is registered only
/// when Development configuration explicitly enables it; production never falls back to it.
/// </summary>
public sealed class FakePixelLabProcessExecutor : IPixelLabProcessExecutor
{
    public Task<PixelLabProcessResult> ExecuteAsync(PixelLabProcessRequest request,
        CancellationToken cancellationToken)
    {
        if (request.Command == "balance")
            return Task.FromResult(new PixelLabProcessResult(0,
                "{\"mode\":\"balance\",\"balance\":{\"amount\":999,\"currency\":\"fake credits\"}}", ""));

        string output = Value(request.Arguments, "--output");
        if (request.Command == "run")
        {
            int count = int.Parse(Value(request.Arguments, "--candidates"));
            Directory.CreateDirectory(output);
            WriteControls(output);
            File.WriteAllText(Path.Combine(output, "run-plan.json"), JsonSerializer.Serialize(new
            {
                candidates = Enumerable.Range(0, count).Select(index => new { candidateIndex = index, seed = index + 1 })
            }));
            for (int index = 0; index < count; index++) WriteCandidate(output, index);
            return Task.FromResult(new PixelLabProcessResult(0,
                $"{{\"submissions\":0,\"transport\":\"development-fake\",\"candidateCount\":{count}}}", ""));
        }

        int candidateIndex = int.Parse(Value(request.Arguments, "--candidate"));
        string directory = Path.Combine(output, "candidates", $"candidate-{candidateIndex:D3}");
        string state = request.Command == "approve" ? "human-approved" : "rejected";
        File.WriteAllText(Path.Combine(directory, "approval.json"), JsonSerializer.Serialize(new
        {
            currentState = state,
            decisions = new[] { new { actor = Value(request.Arguments, "--actor"), reason = Value(request.Arguments, "--reason") } }
        }));
        return Task.FromResult(new PixelLabProcessResult(0, $"{{\"currentState\":\"{state}\"}}", ""));
    }

    private static void WriteCandidate(string output, int index)
    {
        string directory = Path.Combine(output, "candidates", $"candidate-{index:D3}");
        Directory.CreateDirectory(directory);
        File.WriteAllBytes(Path.Combine(directory, "candidate.png"), BuildCandidatePng(index));
        File.WriteAllText(Path.Combine(directory, "validation.json"),
            """{"structurallyValid":true,"eligibleForApproval":true,"resultingState":"generated","failures":[]}""");
        File.WriteAllText(Path.Combine(directory, "generation-manifest.json"),
            JsonSerializer.Serialize(new
            {
                provider = "development-fake",
                remote = new { cacheHit = index > 0, usage = (object?)null },
            }));
    }

    private static void WriteControls(string output)
    {
        string controls = Path.Combine(output, "controls");
        Directory.CreateDirectory(controls);
        File.WriteAllText(Path.Combine(controls, "visual-brief.json"),
            "{\"contractVersion\":\"development-fake\"}");
        byte[] image = BuildCandidatePng(0);
        File.WriteAllBytes(Path.Combine(controls, "semantic-control.png"), image);
        File.WriteAllBytes(Path.Combine(controls, "protected-mask.png"), image);
    }

    private static byte[] BuildCandidatePng(int variant)
    {
        const int size = 128;
        using var raw = new MemoryStream();
        for (int y = 0; y < size; y++)
        {
            raw.WriteByte(0);
            for (int x = 0; x < size; x++)
            {
                double ridge = 56 + (14 * Math.Sin((y + variant * 9) / 13.0));
                bool water = x < ridge || (x > 92 && y > 92 - variant * 5);
                bool rock = !water && ((x + y + variant * 17) % 29 < 4);
                (byte R, byte G, byte B) color = water
                    ? ((byte)(35 + variant * 8), (byte)(105 + variant * 6), (byte)(140 + variant * 5))
                    : rock ? ((byte)132, (byte)126, (byte)114)
                    : ((byte)(48 + variant * 7), (byte)(104 - variant * 5), (byte)(43 + variant * 3));
                raw.WriteByte(color.R);
                raw.WriteByte(color.G);
                raw.WriteByte(color.B);
            }
        }

        using var compressed = new MemoryStream();
        using (var zlib = new ZLibStream(compressed, CompressionLevel.SmallestSize, true))
            zlib.Write(raw.ToArray());
        using var png = new MemoryStream();
        png.Write(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 });
        Span<byte> header = stackalloc byte[13];
        BinaryPrimitives.WriteInt32BigEndian(header[..4], size);
        BinaryPrimitives.WriteInt32BigEndian(header.Slice(4, 4), size);
        header[8] = 8;
        header[9] = 2;
        WriteChunk(png, "IHDR"u8, header);
        WriteChunk(png, "IDAT"u8, compressed.ToArray());
        WriteChunk(png, "IEND"u8, []);
        return png.ToArray();
    }

    private static void WriteChunk(Stream output, ReadOnlySpan<byte> type, ReadOnlySpan<byte> data)
    {
        Span<byte> integer = stackalloc byte[4];
        BinaryPrimitives.WriteInt32BigEndian(integer, data.Length);
        output.Write(integer);
        output.Write(type);
        output.Write(data);
        uint crc = 0xffffffff;
        foreach (byte value in type) crc = UpdateCrc(crc, value);
        foreach (byte value in data) crc = UpdateCrc(crc, value);
        BinaryPrimitives.WriteUInt32BigEndian(integer, ~crc);
        output.Write(integer);
    }

    private static uint UpdateCrc(uint crc, byte value)
    {
        crc ^= value;
        for (int bit = 0; bit < 8; bit++)
            crc = (crc & 1) == 1 ? 0xedb88320 ^ (crc >> 1) : crc >> 1;
        return crc;
    }

    private static string Value(IReadOnlyList<string> arguments, string name)
    {
        for (int index = 0; index < arguments.Count - 1; index++)
            if (arguments[index] == name) return arguments[index + 1];
        throw new InvalidOperationException($"Missing fake argument {name}.");
    }
}
