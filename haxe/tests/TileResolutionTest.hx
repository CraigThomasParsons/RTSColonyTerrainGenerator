import domain.tileresolution.AdjacencyMask;
import domain.tileresolution.AdjacencyMaskCalculator;
import domain.tileresolution.CellCoordinate;
import domain.tileresolution.CellExpander;
import domain.tileresolution.CellMapDimensions;
import domain.tileresolution.TerrainGrid;
import domain.tileresolution.TileCoordinate;
import domain.tileresolution.TileMapDimensions;

/**
	Haxe twin of CellExpanderPropertyTests.cs and of the Gherkin scenarios in
	tests/bdd/features/01-cell-to-tile/cell-to-tile-expansion.feature. Every
	named check states which Dafny lemma (specs/tiling/CellToTile.dfy) or
	scenario it mirrors. This does not replace either reference — it checks
	the Haxe implementation against them, the same role CellExpanderPropertyTests
	plays for the C# implementation.

	Run from haxe/ with: haxe tests/build-test.hxml   (see haxe/README.md)
**/
class TileResolutionTest {
	static var failures = 0;

	static function check(name:String, condition:Bool):Void {
		if (condition) {
			Sys.println('  ok  $name');
		} else {
			Sys.println('  FAIL $name');
			failures++;
		}
	}

	static function expectThrows(name:String, action:() -> Void):Void {
		try {
			action();
			Sys.println('  FAIL $name (expected an exception, none was thrown)');
			failures++;
		} catch (e:Dynamic) {
			Sys.println('  ok  $name');
		}
	}

	// ---- Gherkin scenarios: tests/bdd/features/01-cell-to-tile/cell-to-tile-expansion.feature ----

	static function scenario_expand_the_origin_cell():Void {
		var dims = new CellMapDimensions(10, 10);
		var region = CellExpander.expand(new CellCoordinate(0, 0), dims);
		check("origin cell: exactly 4 coordinates", region.coordinates.length == 4);
		check("origin cell: contains (0,0)", region.topLeft.equals(new TileCoordinate(0, 0)));
		check("origin cell: contains (1,0)", region.topRight.equals(new TileCoordinate(1, 0)));
		check("origin cell: contains (0,1)", region.bottomLeft.equals(new TileCoordinate(0, 1)));
		check("origin cell: contains (1,1)", region.bottomRight.equals(new TileCoordinate(1, 1)));
	}

	static function scenario_expand_an_interior_cell():Void {
		var dims = new CellMapDimensions(10, 10);
		var region = CellExpander.expand(new CellCoordinate(3, 4), dims);
		check("interior cell: exactly 4 coordinates", region.coordinates.length == 4);
		check("interior cell: contains (6,8)", region.topLeft.equals(new TileCoordinate(6, 8)));
		check("interior cell: contains (7,8)", region.topRight.equals(new TileCoordinate(7, 8)));
		check("interior cell: contains (6,9)", region.bottomLeft.equals(new TileCoordinate(6, 9)));
		check("interior cell: contains (7,9)", region.bottomRight.equals(new TileCoordinate(7, 9)));
	}

	static function scenario_expand_the_final_valid_cell():Void {
		var dims = new CellMapDimensions(10, 10);
		var tileMap = TileMapDimensions.from(dims);
		var region = CellExpander.expand(new CellCoordinate(9, 9), dims);
		check("final valid cell: tile map is 20x20", tileMap.width == 20 && tileMap.height == 20);
		for (t in region.coordinates) {
			check('final valid cell: ${t.toString()} inside 20x20 tile map', tileMap.contains(t));
		}
	}

	static function scenario_reject_an_out_of_bounds_cell():Void {
		var dims = new CellMapDimensions(10, 10);
		expectThrows("out-of-bounds cell (10,9): operation fails", () -> CellExpander.expand(new CellCoordinate(10, 9), dims));
		expectThrows("out-of-bounds cell (9,10): operation fails", () -> CellExpander.expand(new CellCoordinate(9, 10), dims));
	}

	// ---- Dafny lemmas: specs/tiling/CellToTile.dfy ----
	// A small fixed-seed property sweep stands in for FsCheck's generators —
	// deterministic so a failure is reproducible without recording a seed.

	static function forEachValidInput(body:(CellMapDimensions, CellCoordinate) -> Void):Void {
		var seed = 20260914;
		function next():Int {
			seed = (seed * 1103515245 + 12345) & 0x7fffffff;
			return seed;
		}
		for (_ in 0...500) {
			var width = 1 + (next() % 256);
			var height = 1 + (next() % 256);
			var x = next() % width;
			var y = next() % height;
			body(new CellMapDimensions(width, height), new CellCoordinate(x, y));
		}
	}

	static function lemma_ExpandCellProducesExactlyFour():Void {
		var ok = true;
		forEachValidInput((dims, cell) -> ok = ok && CellExpander.expand(cell, dims).coordinates.length == 4);
		check("ExpandCellProducesExactlyFour", ok);
	}

	static function lemma_ExpandCellCoordinatesAreUnique():Void {
		var ok = true;
		forEachValidInput((dims, cell) -> {
			var coords = CellExpander.expand(cell, dims).coordinates;
			for (i in 0...coords.length) {
				for (j in (i + 1)...coords.length) {
					if (coords[i].equals(coords[j])) {
						ok = false;
					}
				}
			}
		});
		check("ExpandCellCoordinatesAreUnique", ok);
	}

	static function lemma_ExpandCellStaysInTileBounds():Void {
		var ok = true;
		forEachValidInput((dims, cell) -> {
			var tileMap = TileMapDimensions.from(dims);
			for (t in CellExpander.expand(cell, dims).coordinates) {
				ok = ok && tileMap.contains(t);
			}
		});
		check("ExpandCellStaysInTileBounds", ok);
	}

	static function lemma_ExpandCellEmitsTheContractualCorners():Void {
		var ok = true;
		forEachValidInput((dims, cell) -> {
			var r = CellExpander.expand(cell, dims);
			ok = ok
				&& r.topLeft.equals(new TileCoordinate(2 * cell.x, 2 * cell.y))
				&& r.topRight.equals(new TileCoordinate(2 * cell.x + 1, 2 * cell.y))
				&& r.bottomLeft.equals(new TileCoordinate(2 * cell.x, 2 * cell.y + 1))
				&& r.bottomRight.equals(new TileCoordinate(2 * cell.x + 1, 2 * cell.y + 1));
		});
		check("ExpandCellEmitsTheContractualCorners", ok);
	}

	static function lemma_ExpandCellExtrema():Void {
		var ok = true;
		forEachValidInput((dims, cell) -> {
			var coords = CellExpander.expand(cell, dims).coordinates;
			var minX = coords[0].x, maxX = coords[0].x, minY = coords[0].y, maxY = coords[0].y;
			for (t in coords) {
				if (t.x < minX) minX = t.x;
				if (t.x > maxX) maxX = t.x;
				if (t.y < minY) minY = t.y;
				if (t.y > maxY) maxY = t.y;
			}
			ok = ok && minX == cell.x * 2 && maxX == cell.x * 2 + 1 && minY == cell.y * 2 && maxY == cell.y * 2 + 1;
		});
		check("ExpandCellExtrema", ok);
	}

	static function lemma_DistinctCellsHaveDisjointRegions():Void {
		var ok = true;
		// Pair each cell with an independently generated second cell anywhere in
		// the map, as the lemma quantifies over any two distinct cells.
		var pairSeed = 20261010;
		function nextPair():Int {
			pairSeed = (pairSeed * 1103515245 + 12345) & 0x7fffffff;
			return pairSeed;
		}
		forEachValidInput((dims, cell) -> {
			var other = new CellCoordinate(nextPair() % dims.width, nextPair() % dims.height);
			if (other.equals(cell)) {
				return; // same cell: the lemma only speaks about distinct cells
			}
			var a = CellExpander.expand(cell, dims).coordinates;
			var b = CellExpander.expand(other, dims).coordinates;
			for (t in a) {
				for (u in b) {
					if (t.equals(u)) {
						ok = false;
					}
				}
			}
		});
		check("DistinctCellsHaveDisjointRegions", ok);
	}

	static function lemma_EveryTileHasAnOwningCell():Void {
		var ok = true;
		// Any in-bounds tile, not just the bottom-right one: the lemma is over
		// every tile of the tile map.
		var tileSeed = 20261011;
		function nextTile():Int {
			tileSeed = (tileSeed * 1103515245 + 12345) & 0x7fffffff;
			return tileSeed;
		}
		forEachValidInput((dims, _) -> {
			var tileMap = TileMapDimensions.from(dims);
			var tx = nextTile() % tileMap.width;
			var ty = nextTile() % tileMap.height;
			var t = new TileCoordinate(tx, ty);
			var owner = new CellCoordinate(Std.int(tx / 2), Std.int(ty / 2));
			ok = ok && dims.contains(owner);
			var region = CellExpander.expand(owner, dims).coordinates;
			var owned = false;
			for (candidate in region) {
				if (candidate.equals(t)) {
					owned = true;
				}
			}
			ok = ok && owned;
		});
		check("EveryTileHasAnOwningCell", ok);
	}

	// Structural in Dafny (ExpandCell is a pure function) — checked the same way
	// CellExpanderPropertyTests.Expansion_is_deterministic checks the C# twin.
	static function property_expansion_is_deterministic():Void {
		var ok = true;
		forEachValidInput((dims, cell) -> ok = ok && CellExpander.expand(cell, dims).equals(CellExpander.expand(cell, dims)));
		check("Expansion_is_deterministic", ok);
	}

	// ---- Regression tests: Codex review findings on PR #108/#8, fixed in issue #115 ----

	static function regression_oversized_dimensions_are_rejected_not_overflowed():Void {
		expectThrows("width beyond MaxSafeDimension is rejected",
			() -> new CellMapDimensions(CellMapDimensions.MaxSafeDimension + 1, 1));
		expectThrows("height beyond MaxSafeDimension is rejected",
			() -> new CellMapDimensions(1, CellMapDimensions.MaxSafeDimension + 1));

		// At exactly the boundary, the rightmost/bottommost cell must still
		// expand correctly instead of wrapping negative.
		var dims = new CellMapDimensions(CellMapDimensions.MaxSafeDimension, CellMapDimensions.MaxSafeDimension);
		var edgeCell = CellMapDimensions.MaxSafeDimension - 1;
		var region = CellExpander.expand(new CellCoordinate(edgeCell, edgeCell), dims);
		check("boundary cell doubles without overflow (no negative coordinate)",
			region.topLeft.x >= 0 && region.topLeft.y >= 0 && region.bottomRight.x >= 0 && region.bottomRight.y >= 0);
		check("boundary cell doubles to the exact expected corner",
			region.bottomRight.equals(new TileCoordinate(edgeCell * 2 + 1, edgeCell * 2 + 1)));
	}

	static function regression_coordinates_getter_returns_a_copy():Void {
		var region = CellExpander.expand(new CellCoordinate(3, 4), new CellMapDimensions(10, 10));
		var original = region.topLeft;

		var borrowed = region.coordinates;
		borrowed[0] = new TileCoordinate(0, 0); // overwrite an element
		borrowed.push(new TileCoordinate(99, 99)); // and append one — neither should reach the region

		check("mutating the returned array does not change topLeft", region.topLeft.equals(original));
		check("mutating the returned array does not change the region's length", region.coordinates.length == 4);
		check("a fresh call to .coordinates is unaffected by a previous caller's mutation", region.coordinates[0].equals(original));
	}

	// ==== slice-02-adjacency-mask ====================================

	// ---- Gherkin scenarios: tests/bdd/features/02-adjacency-mask/adjacency-mask.feature ----

	static function grid3x3(rows:Array<Array<Int>>):TerrainGrid {
		var flat = [];
		for (row in rows) {
			for (v in row) {
				flat.push(v);
			}
		}
		return new TerrainGrid(3, 3, flat);
	}

	static function scenario_a_cell_surrounded_by_the_same_terrain_sets_all_four_bits():Void {
		var grid = grid3x3([[1, 1, 1], [1, 1, 1], [1, 1, 1]]);
		var mask = AdjacencyMaskCalculator.computeMask(grid, 1, 1);
		check("surrounded cell: mask is 15", mask.value == 15);
	}

	static function scenario_a_corner_cell_can_only_see_east_and_south():Void {
		var grid = grid3x3([[1, 1, 1], [1, 1, 1], [1, 1, 1]]);
		var mask = AdjacencyMaskCalculator.computeMask(grid, 0, 0);
		check("corner cell: mask is 6", mask.value == 6);
		check("corner cell: has East and South but not North or West", mask.hasEast && mask.hasSouth && !mask.hasNorth && !mask.hasWest);
	}

	static function scenario_a_cell_whose_neighbours_differ_sets_no_bits():Void {
		var grid = grid3x3([[1, 2, 1], [2, 3, 2], [1, 2, 1]]);
		var mask = AdjacencyMaskCalculator.computeMask(grid, 1, 1);
		check("differing neighbours: mask is 0", mask.value == 0);
	}

	static function scenario_only_matching_neighbours_set_their_bit():Void {
		var grid = grid3x3([[0, 1, 0], [2, 1, 2], [0, 1, 0]]);
		var mask = AdjacencyMaskCalculator.computeMask(grid, 1, 1);
		check("partial match: mask is 5", mask.value == 5);
		check("partial match: has North and South but not East or West", mask.hasNorth && mask.hasSouth && !mask.hasEast && !mask.hasWest);
	}

	static function scenario_reject_an_out_of_bounds_cell_adjacency():Void {
		var grid = grid3x3([[1, 1, 1], [1, 1, 1], [1, 1, 1]]);
		expectThrows("out-of-bounds cell (3,1): operation fails", () -> AdjacencyMaskCalculator.computeMask(grid, 3, 1));
	}

	// ---- Dafny lemmas: specs/tiling/AdjacencyMask.dfy ----
	// A small fixed-seed property sweep stands in for FsCheck's GridAndCell generator.

	static function forEachGridAndCell(body:(TerrainGrid, Int, Int) -> Void):Void {
		var seed = 20261012;
		function next():Int {
			seed = (seed * 1103515245 + 12345) & 0x7fffffff;
			return seed;
		}
		for (_ in 0...500) {
			var width = 1 + (next() % 12);
			var height = 1 + (next() % 12);
			var terrain = [for (_ in 0...(width * height)) next() % 4];
			var x = next() % width;
			var y = next() % height;
			body(new TerrainGrid(width, height, terrain), x, y);
		}
	}

	static function lemma_MaskInRange():Void {
		var ok = true;
		forEachGridAndCell((grid, x, y) -> {
			var v = AdjacencyMaskCalculator.computeMask(grid, x, y).value;
			ok = ok && v >= 0 && v <= 15;
		});
		check("MaskInRange", ok);
	}

	static function lemma_EdgeCellsNeverSetOffMapBits():Void {
		var ok = true;
		forEachGridAndCell((grid, x, y) -> {
			var mask = AdjacencyMaskCalculator.computeMask(grid, x, y);
			ok = ok
				&& (y != 0 || !mask.hasNorth)
				&& (x != 0 || !mask.hasWest)
				&& (y != grid.height - 1 || !mask.hasSouth)
				&& (x != grid.width - 1 || !mask.hasEast);
		});
		check("EdgeCellsNeverSetOffMapBits", ok);
	}

	static function lemma_BitsReflectNeighbourPredicate():Void {
		var ok = true;
		forEachGridAndCell((grid, x, y) -> {
			var mask = AdjacencyMaskCalculator.computeMask(grid, x, y);
			var self = grid.terrainAt(x, y);
			var north = y > 0 && grid.terrainAt(x, y - 1) == self;
			var east = x + 1 < grid.width && grid.terrainAt(x + 1, y) == self;
			var south = y + 1 < grid.height && grid.terrainAt(x, y + 1) == self;
			var west = x > 0 && grid.terrainAt(x - 1, y) == self;
			ok = ok && mask.hasNorth == north && mask.hasEast == east && mask.hasSouth == south && mask.hasWest == west;
		});
		check("BitsReflectNeighbourPredicate", ok);
	}

	static function lemma_EastWestSymmetry():Void {
		var ok = true;
		forEachGridAndCell((grid, x, y) -> {
			if (x + 1 >= grid.width) {
				return; // no east neighbour to be symmetric with
			}
			var selfEast = AdjacencyMaskCalculator.computeMask(grid, x, y).hasEast;
			var neighbourWest = AdjacencyMaskCalculator.computeMask(grid, x + 1, y).hasWest;
			ok = ok && selfEast == neighbourWest;
		});
		check("EastWestSymmetry", ok);
	}

	static function lemma_NorthSouthSymmetry():Void {
		var ok = true;
		forEachGridAndCell((grid, x, y) -> {
			if (y + 1 >= grid.height) {
				return;
			}
			var selfSouth = AdjacencyMaskCalculator.computeMask(grid, x, y).hasSouth;
			var neighbourNorth = AdjacencyMaskCalculator.computeMask(grid, x, y + 1).hasNorth;
			ok = ok && selfSouth == neighbourNorth;
		});
		check("NorthSouthSymmetry", ok);
	}

	static function property_mask_computation_is_deterministic():Void {
		var ok = true;
		forEachGridAndCell((grid, x,
			y) -> ok = ok && AdjacencyMaskCalculator.computeMask(grid, x, y).value == AdjacencyMaskCalculator.computeMask(grid, x, y).value);
		check("Mask_computation_is_deterministic", ok);
	}

	public static function main():Void {
		Sys.println("Gherkin scenarios (tests/bdd/features/01-cell-to-tile/cell-to-tile-expansion.feature):");
		scenario_expand_the_origin_cell();
		scenario_expand_an_interior_cell();
		scenario_expand_the_final_valid_cell();
		scenario_reject_an_out_of_bounds_cell();

		Sys.println("Dafny lemmas (specs/tiling/CellToTile.dfy), 500 generated cases each:");
		lemma_ExpandCellProducesExactlyFour();
		lemma_ExpandCellCoordinatesAreUnique();
		lemma_ExpandCellStaysInTileBounds();
		lemma_ExpandCellEmitsTheContractualCorners();
		lemma_ExpandCellExtrema();
		lemma_DistinctCellsHaveDisjointRegions();
		lemma_EveryTileHasAnOwningCell();
		property_expansion_is_deterministic();

		Sys.println("Regression tests (Codex review, PR #108/#8 -> issue #115):");
		regression_oversized_dimensions_are_rejected_not_overflowed();
		regression_coordinates_getter_returns_a_copy();

		Sys.println("Gherkin scenarios (tests/bdd/features/02-adjacency-mask/adjacency-mask.feature):");
		scenario_a_cell_surrounded_by_the_same_terrain_sets_all_four_bits();
		scenario_a_corner_cell_can_only_see_east_and_south();
		scenario_a_cell_whose_neighbours_differ_sets_no_bits();
		scenario_only_matching_neighbours_set_their_bit();
		scenario_reject_an_out_of_bounds_cell_adjacency();

		Sys.println("Dafny lemmas (specs/tiling/AdjacencyMask.dfy), 500 generated cases each:");
		lemma_MaskInRange();
		lemma_EdgeCellsNeverSetOffMapBits();
		lemma_BitsReflectNeighbourPredicate();
		lemma_EastWestSymmetry();
		lemma_NorthSouthSymmetry();
		property_mask_computation_is_deterministic();

		if (failures == 0) {
			Sys.println('All checks passed.');
			Sys.exit(0);
		} else {
			Sys.println('$failures check(s) failed.');
			Sys.exit(1);
		}
	}
}
