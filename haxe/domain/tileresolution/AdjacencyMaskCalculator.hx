package domain.tileresolution;

/**
	Adjacency-mask construction — the Haxe twin of the verified model
	(specs/tiling/AdjacencyMask.dfy Mask) and of the C# production
	implementation (MapGen.Domain.TileResolution.AdjacencyMaskCalculator).
	Pure and deterministic: a direction bit is set iff that orthogonal
	neighbour exists on the grid and shares the cell's terrain. Diagonals
	ignored. Postconditions (range, per-bit predicate, edge safety, symmetry)
	are proved in Dafny and checked here by TileResolutionTest, one case per
	lemma.
**/
class AdjacencyMaskCalculator {
	/** Compute the 4-bit mask for one in-bounds cell. **/
	public static function computeMask(grid:TerrainGrid, x:Int, y:Int):AdjacencyMask {
		if (!grid.contains(x, y)) {
			throw new haxe.exceptions.ArgumentException("x", 'Cell ($x,$y) is outside the ${grid.width}x${grid.height} terrain grid.');
		}

		var self = grid.terrainAt(x, y);
		var mask = 0;

		if (y > 0 && grid.terrainAt(x, y - 1) == self) {
			mask |= AdjacencyMask.North;
		}

		if (x + 1 < grid.width && grid.terrainAt(x + 1, y) == self) {
			mask |= AdjacencyMask.East;
		}

		if (y + 1 < grid.height && grid.terrainAt(x, y + 1) == self) {
			mask |= AdjacencyMask.South;
		}

		if (x > 0 && grid.terrainAt(x - 1, y) == self) {
			mask |= AdjacencyMask.West;
		}

		return new AdjacencyMask(mask);
	}
}
