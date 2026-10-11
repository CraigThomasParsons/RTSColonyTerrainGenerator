package domain.tileresolution;

/**
	Width and height of the source map, measured in cells. Both are strictly
	positive (precondition of the verified model, CellToTile.dfy
	ValidDimensions). Mirrors MapGen.Domain.TileResolution.CellMapDimensions (C#).
**/
class CellMapDimensions {
	public final width:Int;
	public final height:Int;

	public function new(width:Int, height:Int) {
		if (width <= 0) {
			throw new haxe.exceptions.ArgumentException("width", "Cell map width must be greater than zero.");
		}
		if (height <= 0) {
			throw new haxe.exceptions.ArgumentException("height", "Cell map height must be greater than zero.");
		}
		this.width = width;
		this.height = height;
	}

	public function contains(cell:CellCoordinate):Bool {
		return cell.x < width && cell.y < height;
	}
}
