package domain.tileresolution;

/**
	Zero-based (x, y) position in tile space — the grid twice the cell
	dimensions in each axis. Mirrors MapGen.Domain.TileResolution.TileCoordinate
	(C#) and CellToTile.dfy's TileCoordinate datatype.
**/
class TileCoordinate {
	public final x:Int;
	public final y:Int;

	public function new(x:Int, y:Int) {
		if (x < 0) {
			throw new haxe.exceptions.ArgumentException("x", "Tile x must not be negative.");
		}
		if (y < 0) {
			throw new haxe.exceptions.ArgumentException("y", "Tile y must not be negative.");
		}
		this.x = x;
		this.y = y;
	}

	public function equals(other:TileCoordinate):Bool {
		return other != null && x == other.x && y == other.y;
	}

	public function toString():String {
		return '($x,$y)';
	}
}
