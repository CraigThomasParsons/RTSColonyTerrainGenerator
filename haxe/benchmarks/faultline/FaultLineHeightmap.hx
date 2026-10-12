/**
	A synthetic, representative workload for comparing Haxe compile targets —
	NOT a port of the real Rust heightmap-engine (MapGenerator/Heightmap).
	It is shaped like that family of stages: a tight, allocation-light,
	per-cell numeric loop over a grid, run many times. Heightmap and
	WeatherAnalyses are both this shape today (Rust); this workload exists
	only to compare `cpp` against `cs` before either stage is ported
	(haxe/README.md "Target selection").

	Classic fault-formation terrain generation (Fournier/Fussell/Carpenter):
	each pass picks a random line through the grid and raises every cell on
	one side of it, lowers every cell on the other. All-integer line-side
	test (a 2D cross product) keeps the workload free of floating-point
	rounding, so the same seed produces byte-identical output on every
	target -- required for the parity check this benchmark exists to make.
**/
class FaultLineHeightmap {
	/** Deterministic PRNG shared by every call — identical sequence on every target. **/
	static function makeRng(seed:Int):() -> Int {
		var state = seed;
		return () -> {
			state = (state * 1103515245 + 12345) & 0x7fffffff;
			return state;
		};
	}

	/**
		Run `passes` fault-line iterations over a `width` x `height` grid and
		return the result normalized to 0..255, row-major.
	**/
	public static function generate(width:Int, height:Int, passes:Int, seed:Int):Array<Int> {
		var raw = [for (_ in 0...(width * height)) 0];
		var next = makeRng(seed);

		for (_ in 0...passes) {
			var x1 = next() % width;
			var y1 = next() % height;
			var x2 = next() % width;
			var y2 = next() % height;
			var dx = x2 - x1;
			var dy = y2 - y1;
			if (dx == 0 && dy == 0) {
				continue; // degenerate line, skip this pass
			}
			var i = 0;
			for (y in 0...height) {
				for (x in 0...width) {
					var cross = dx * (y - y1) - dy * (x - x1);
					if (cross > 0) {
						raw[i]++;
					} else {
						raw[i]--;
					}
					i++;
				}
			}
		}

		var min = raw[0];
		var max = raw[0];
		for (v in raw) {
			if (v < min) min = v;
			if (v > max) max = v;
		}
		var range = max - min;
		if (range == 0) {
			range = 1;
		}
		return [for (v in raw) Std.int((v - min) * 255 / range)];
	}

	/**
		FNV-1a-style checksum so two runs can be confirmed to have produced
		byte-identical output. Relies on Haxe `Int` being a guaranteed 32-bit
		wraparound value on every compiled target (cpp, cs) — not masked
		explicitly, since the literal for the top bit set does not fit a
		signed 32-bit Int.
	**/
	public static function checksum(heights:Array<Int>):Int {
		var hash = 0x7ee3623d; // low 31 bits of the FNV offset basis; sign bit irrelevant to the mix
		for (v in heights) {
			hash ^= v;
			hash *= 0x01000193;
		}
		return hash;
	}
}
