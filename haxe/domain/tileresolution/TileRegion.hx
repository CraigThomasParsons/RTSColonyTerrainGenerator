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

	`coordinates` is read-only from outside this class: the backing Array is
	private, and the public getter returns a copy. `final` alone does not
	achieve this in Haxe — it stops the *field* from being reassigned, but the
	Array object it points to stays fully mutable (push/pop/splice/element
	assignment all succeed on a `final` field), which would let a caller break
	the four-unique-coordinates invariant the constructor just enforced
	(Codex review, PR #108/#8). The C# twin gets this for free from
	`ReadOnlyCollection`.
**/
class TileRegion {
	final _coordinates:Array<TileCoordinate>;

	public var coordinates(get, never):Array<TileCoordinate>;

	public var topLeft(get, never):TileCoordinate;
	public var topRight(get, never):TileCoordinate;
	public var bottomLeft(get, never):TileCoordinate;
	public var bottomRight(get, never):TileCoordinate;

	function get_coordinates():Array<TileCoordinate>
		return _coordinates.copy();

	function get_topLeft():TileCoordinate
		return _coordinates[0];

	function get_topRight():TileCoordinate
		return _coordinates[1];

	function get_bottomLeft():TileCoordinate
		return _coordinates[2];

	function get_bottomRight():TileCoordinate
		return _coordinates[3];

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
			throw new haxe.exceptions.ArgumentException("coordinates", "A tile region must contain four unique coordinates.");
		}
		this._coordinates = ordered;
	}

	public function equals(other:TileRegion):Bool {
		if (other == null) {
			return false;
		}
		for (i in 0..._coordinates.length) {
			if (!_coordinates[i].equals(other._coordinates[i])) {
				return false;
			}
		}
		return true;
	}
}
