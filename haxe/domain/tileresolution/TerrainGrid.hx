package domain.tileresolution;

/**
	A width x height grid of terrain values in row-major order — the input to
	adjacency-mask construction (mirrors `Grid` in specs/tiling/AdjacencyMask.dfy).
	Terrain values are the cell's terrain layer; equality of two cells' values
	is what "same terrain" means. Mirrors
	MapGen.Domain.TileResolution.TerrainGrid (C#).
**/
class TerrainGrid {
	final terrain:Array<Int>;

	public final width:Int;
	public final height:Int;

	/** `terrain` is row-major, length width*height: index = y*width + x. **/
	public function new(width:Int, height:Int, terrain:Array<Int>) {
		if (width <= 0) {
			throw new haxe.exceptions.ArgumentException("width", "Grid width must be greater than zero.");
		}
		if (height <= 0) {
			throw new haxe.exceptions.ArgumentException("height", "Grid height must be greater than zero.");
		}
		if (terrain.length != width * height) {
			throw new haxe.exceptions.ArgumentException("terrain",
				'Terrain length ${terrain.length} does not match ${width}x${height} = ${width * height}.');
		}
		this.width = width;
		this.height = height;
		this.terrain = terrain.copy();
	}

	public function terrainAt(x:Int, y:Int):Int {
		return terrain[(y * width) + x];
	}

	public function contains(x:Int, y:Int):Bool {
		return x >= 0 && y >= 0 && x < width && y < height;
	}
}
