package domain.tileresolution;

/**
	The cell-to-tile expansion rule — the Haxe twin of the verified model
	(specs/tiling/CellToTile.dfy ExpandCell) and of the C# production
	implementation (MapGen.Domain.TileResolution.CellExpander). Pure and
	deterministic: no clock, no randomness, no IO. Postconditions (exactly
	four, unique, in-bounds, exact corners) are proved in Dafny and checked
	here by TileResolutionTest, one case per lemma.
**/
class CellExpander {
	/**
		Expand `cell` into its 2x2 tile region.
		Precondition: the cell lies inside `dimensions`.
	**/
	public static function expand(cell:CellCoordinate, dimensions:CellMapDimensions):TileRegion {
		if (!dimensions.contains(cell)) {
			throw new haxe.exceptions.ArgumentException("cell",
				'Cell (${cell.x},${cell.y}) is outside the ${dimensions.width}x${dimensions.height} cell map.');
		}

		var baseX = cell.x * 2;
		var baseY = cell.y * 2;

		return new TileRegion(new TileCoordinate(baseX, baseY), new TileCoordinate(baseX + 1, baseY), new TileCoordinate(baseX, baseY + 1),
			new TileCoordinate(baseX + 1, baseY + 1));
	}
}
