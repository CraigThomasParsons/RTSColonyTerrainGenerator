package domain.tileresolution;

/**
	The four tiles belonging to one cell, in the contractual order
	TL, TR, BL, BR (CellToTile.dfy ExpandCellEmitsTheContractualCorners;
	legacy TileIdResolver.cs emits the same order). Constructed only by
	`CellExpander`. Mirrors MapGen.Domain.TileResolution.TileRegion (C#).

	Value semantics over the ordered coordinates, same reason as the C# twin:
	an identity-based equality would make two identical expansions compare
	unequal (CellExpanderPropertyTests.Expansion_is_deterministic / the Haxe
	twin `deterministic` in TileResolutionTest).
**/
class TileRegion {
	public final coordinates:Array<TileCoordinate>;

	public var topLeft(get, never):TileCoordinate;
	public var topRight(get, never):TileCoordinate;
	public var bottomLeft(get, never):TileCoordinate;
	public var bottomRight(get, never):TileCoordinate;

	function get_topLeft():TileCoordinate
		return coordinates[0];

	function get_topRight():TileCoordinate
		return coordinates[1];

	function get_bottomLeft():TileCoordinate
		return coordinates[2];

	function get_bottomRight():TileCoordinate
		return coordinates[3];

	public function new(topLeft:TileCoordinate, topRight:TileCoordinate, bottomLeft:TileCoordinate, bottomRight:TileCoordinate) {
		var ordered = [topLeft, topRight, bottomLeft, bottomRight];
		var distinct = 0;
		for (i in 0...ordered.length) {
			var isDuplicate = false;
			for (j in 0...i) {
				if (ordered[i].equals(ordered[j])) {
					isDuplicate = true;
					break;
				}
			}
			if (!isDuplicate) {
				distinct++;
			}
		}
		if (distinct != 4) {
			throw "A tile region must contain four unique coordinates.";
		}
		this.coordinates = ordered;
	}

	public function equals(other:TileRegion):Bool {
		if (other == null) {
			return false;
		}
		for (i in 0...coordinates.length) {
			if (!coordinates[i].equals(other.coordinates[i])) {
				return false;
			}
		}
		return true;
	}
}
