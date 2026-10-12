/**
	Benchmark harness: runs FaultLineHeightmap.generate with fixed parameters
	several times, reporting the fastest trial (minimises JIT/startup noise
	on cs) and a checksum. Same seed/size/passes on every target, so the
	checksum is the parity check and the timing is the only thing that's
	expected to differ. See haxe/README.md "Benchmark: cpp vs cs".
**/
class Main {
	static final Width = 512;
	static final Height = 512;
	static final Passes = 3000;
	static final Seed = 20261012;
	static final Trials = 3;

	public static function main():Void {
		var best = -1.0;
		var lastChecksum = 0;

		for (trial in 1...(Trials + 1)) {
			var start = Sys.time();
			var heights = FaultLineHeightmap.generate(Width, Height, Passes, Seed);
			var elapsedMs = (Sys.time() - start) * 1000;
			lastChecksum = FaultLineHeightmap.checksum(heights);

			Sys.println('trial $trial: ${elapsedMs}ms');
			if (best < 0 || elapsedMs < best) {
				best = elapsedMs;
			}
		}

		Sys.println('size=${Width}x$Height passes=$Passes seed=$Seed trials=$Trials');
		Sys.println('best=${best}ms checksum=$lastChecksum');
	}
}
