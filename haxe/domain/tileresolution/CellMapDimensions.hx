package domain.tileresolution;

/**
	Width and height of the source map, measured in cells. Both are strictly
	positive (precondition of the verified model, CellToTile.dfy
	ValidDimensions). Mirrors MapGen.Domain.TileResolution.CellMapDimensions (C#).

	Also bounded above, unlike the Dafny model's unbounded `nat`: the largest
	in-bounds cell coordinate is `width - 1` (or `height - 1`), and
	`CellExpander` doubles it (`cell.x * 2`). Haxe's `Int` is a signed 32-bit
	value, so an unbounded width would let that doubling overflow and wrap
	negative for a cell the model still considers valid (Codex review,
	PR #108/#8). `MaxSafeDimension` is the largest width/height for which
	`2 * (width - 1) + 1` — the rightmost tile coordinate `CellExpander`
	produces — still fits in a 32-bit `Int`.
**/
class CellMapDimensions {
	public static final MaxSafeDimension = 1073741824; // 2*(MaxSafeDimension-1)+1 == Int32 max

	public final width:Int;
	public final height:Int;

	public function new(width:Int, height:Int) {
		if (width <= 0) {
			throw new haxe.exceptions.ArgumentException("width", "Cell map width must be greater than zero.");
		}
		if (height <= 0) {
			throw new haxe.exceptions.ArgumentException("height", "Cell map height must be greater than zero.");
		}
		if (width > MaxSafeDimension) {
			throw new haxe.exceptions.ArgumentException("width",
				'Cell map width $width would overflow when doubled to tile space; the largest safe width is $MaxSafeDimension.');
		}
		if (height > MaxSafeDimension) {
			throw new haxe.exceptions.ArgumentException("height",
				'Cell map height $height would overflow when doubled to tile space; the largest safe height is $MaxSafeDimension.');
		}
		this.width = width;
		this.height = height;
	}

	public function contains(cell:CellCoordinate):Bool {
		return cell.x < width && cell.y < height;
	}
}
