package domain.tileresolution;

/**
	Width and height of the expanded map, measured in tiles. Only derivable
	from cell dimensions — exactly double in each axis (CellToTile.dfy
	TileMapWidth/Height), which is what the legacy Tiler produces
	(TileIdResolver.cs). Mirrors MapGen.Domain.TileResolution.TileMapDimensions (C#).
**/
class TileMapDimensions {
	public final width:Int;
	public final height:Int;

	function new(width:Int, height:Int) {
		this.width = width;
		this.height = height;
	}

	public static function from(cells:CellMapDimensions):TileMapDimensions {
		return new TileMapDimensions(cells.width * 2, cells.height * 2);
	}

	public function contains(tile:TileCoordinate):Bool {
		return tile.x < width && tile.y < height;
	}
}
