package domain.tileresolution;

/**
	Zero-based (x, y) position in cell space. Coordinates are never negative;
	upper bounds belong to `CellMapDimensions`, not the coordinate itself.
	Mirrors MapGen.Domain.TileResolution.CellCoordinate (C#) and
	CellToTile.dfy's CellCoordinate datatype.
**/
class CellCoordinate {
	public final x:Int;
	public final y:Int;

	public function new(x:Int, y:Int) {
		if (x < 0) {
			throw new haxe.exceptions.ArgumentException("x", "Cell x must not be negative.");
		}
		if (y < 0) {
			throw new haxe.exceptions.ArgumentException("y", "Cell y must not be negative.");
		}
		this.x = x;
		this.y = y;
	}

	public function equals(other:CellCoordinate):Bool {
		return other != null && x == other.x && y == other.y;
	}

	public function toString():String {
		return '($x,$y)';
	}
}
