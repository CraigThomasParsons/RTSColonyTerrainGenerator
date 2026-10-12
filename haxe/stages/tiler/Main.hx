import domain.tileresolution.AdjacencyMaskCalculator;
import domain.tileresolution.CellCoordinate;
import domain.tileresolution.CellExpander;
import domain.tileresolution.CellMapDimensions;
import domain.tileresolution.TerrainGrid;

/**
	Target-specific adapter for the Tiler stage. Holds no domain behaviour —
	it only proves the shared Haxe domain code (haxe/domain/) compiles and
	runs on the selected target (cs: see haxe/README.md). Domain logic lives
	entirely in domain/tileresolution/; this stays a thin entry point, per
	the architecture note's "keep target-specific code in small adapters" rule.
**/
class Main {
	public static function main():Void {
		var dims = new CellMapDimensions(10, 10);
		var region = CellExpander.expand(new CellCoordinate(3, 4), dims);
		Sys.println('cell (3,4) -> ${region.topLeft}, ${region.topRight}, ${region.bottomLeft}, ${region.bottomRight}');

		var grid = new TerrainGrid(3, 3, [1, 1, 1, 1, 1, 1, 1, 1, 1]);
		var mask = AdjacencyMaskCalculator.computeMask(grid, 1, 1);
		Sys.println('adjacency mask at (1,1) of a uniform 3x3 grid -> ${mask.value}');
	}
}
