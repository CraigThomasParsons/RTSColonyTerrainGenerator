package domain.tileresolution;

/**
	A 4-bit orthogonal adjacency mask for one cell (mirrors `Mask` in
	specs/tiling/AdjacencyMask.dfy). A direction bit is set iff that neighbour
	exists and shares the cell's terrain. Value is always in [0, 15].

	North = 1, East = 2, South = 4, West = 8.

	Mirrors MapGen.Domain.TileResolution.AdjacencyMask (C#).
**/
class AdjacencyMask {
	public static final North = 1;
	public static final East = 2;
	public static final South = 4;
	public static final West = 8;

	public final value:Int;

	public function new(value:Int) {
		if (value < 0 || value > 15) {
			throw new haxe.exceptions.ArgumentException("value", "An adjacency mask must be in [0, 15].");
		}
		this.value = value;
	}

	public var hasNorth(get, never):Bool;
	public var hasEast(get, never):Bool;
	public var hasSouth(get, never):Bool;
	public var hasWest(get, never):Bool;

	function get_hasNorth():Bool
		return (value & North) != 0;

	function get_hasEast():Bool
		return (value & East) != 0;

	function get_hasSouth():Bool
		return (value & South) != 0;

	function get_hasWest():Bool
		return (value & West) != 0;
}
