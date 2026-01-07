<?php

namespace Tests\TreePlanter\Engine;

use PHPUnit\Framework\TestCase;
use RTSColonyTerrainGenerator\TreePlanter\Engine\TreePlacementEngine;
use Tests\Fake\FakeTile;
use Tests\Fake\FakeTileAssembler;

/**
 * TreePlacementEngineTest
 *
 * These tests define the *contract* of the TreePlacementEngine.
 *
 * They ensure:
 * - Deterministic output
 * - Biome-aware density differences
 * - Exclusion of invalid terrain
 * - Correct tree type selection
 *
 * NOTE:
 * - These tests should continue to pass even as the engine grows
 * - New features should ADD tests, not break these
 */
final class TreePlacementEngineTest extends TestCase
{
    /**
     * The engine must be deterministic.
     *
     * Given:
     * - Same input tiles
     * - Same random seed
     *
     * Then:
     * - Tree placements must be identical
     */
    public function test_is_deterministic_with_same_seed(): void
    {
        $tiles = [
            new FakeTile(0, 0, 'forest'),
            new FakeTile(1, 0, 'forest'),
            new FakeTile(2, 0, 'plains'),
            new FakeTile(3, 0, 'plains'),
        ];

        $assembler = new FakeTileAssembler($tiles);

        $engineA = new TreePlacementEngine(seed: 123);
        $engineB = new TreePlacementEngine(seed: 123);

        $resultA = $engineA->run($assembler)->all();
        $resultB = $engineB->run($assembler)->all();

        $this->assertEquals(
            $resultA,
            $resultB,
            'Tree placement must be deterministic for a given seed'
        );
    }

    /**
     * Forest biomes should generate more trees than plains.
     *
     * This test does NOT assert exact numbers.
     * It asserts relative density only.
     */
    public function test_forest_has_more_trees_than_plains(): void
    {
        $tiles = [];

        // Create paired rows of forest and plains tiles
        for ($i = 0; $i < 50; $i++) {
            $tiles[] = new FakeTile($i, 0, 'forest');
            $tiles[] = new FakeTile($i, 1, 'plains');
        }

        $assembler = new FakeTileAssembler($tiles);
        $engine = new TreePlacementEngine(seed: 999);

        $placements = $engine->run($assembler)->all();

        $forestCount = 0;
        $plainsCount = 0;

        foreach ($placements as $tree) {
            if ($tree->y === 0) {
                $forestCount++;
            }

            if ($tree->y === 1) {
                $plainsCount++;
            }
        }

        $this->assertGreaterThan(
            $plainsCount,
            $forestCount,
            'Forest biome should produce more trees than plains'
        );
    }

    /**
     * Water and mountain tiles must never receive trees.
     *
     * This is a hard exclusion rule.
     */
    public function test_water_and_mountains_never_get_trees(): void
    {
        $tiles = [
            new FakeTile(0, 0, 'forest', water: true),
            new FakeTile(1, 0, 'forest', mountain: true),
            new FakeTile(2, 0, 'forest'),
        ];

        $assembler = new FakeTileAssembler($tiles);
        $engine = new TreePlacementEngine(seed: 555);

        $placements = $engine->run($assembler)->all();

        foreach ($placements as $tree) {
            $this->assertNotEquals(
                0,
                $tree->x,
                'Trees must not spawn on water tiles'
            );

            $this->assertNotEquals(
                1,
                $tree->x,
                'Trees must not spawn on mountain tiles'
            );
        }
    }

    /**
     * Tree type selection must match biome rules.
     *
     * This ensures biome logic stays stable even if
     * placement density or clustering changes later.
     */
    public function test_tree_type_matches_biome(): void
    {
        $tiles = [
            new FakeTile(0, 0, 'forest'),
            new FakeTile(1, 0, 'swamp'),
            new FakeTile(2, 0, 'plains'),
        ];

        $assembler = new FakeTileAssembler($tiles);
        $engine = new TreePlacementEngine(seed: 777);

        $placements = $engine->run($assembler)->all();

        foreach ($placements as $tree) {
            match ($tree->x) {
                0 => $this->assertSame('oak', $tree->treeType),
                1 => $this->assertSame('mangrove', $tree->treeType),
                2 => $this->assertSame('scrub', $tree->treeType),
                default => null,
            };
        }
    }
}
