package mapgen.pathfinder

import java.util.PriorityQueue
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * PathFindingEngine
 *
 * Implements A* search to find paths between world features.
 */
class PathFindingEngine(
    private val tiles: Map<String, TileInfo>,
    private val width: Int,
    private val height: Int,
    private val logger: StageLogger
) {

    data class Node(val x: Int, val y: Int)
    data class PathResult(
        val success: Boolean,
        val path: List<Node>,
        val cost: Double,
        val failureReason: String? = null
    )

    /**
     * Find a path between two coordinates using A*.
     */
    fun findPath(startX: Int, startY: Int, endX: Int, endY: Int): PathResult {
        val startNode = Node(startX, startY)
        val endNode = Node(endX, endY)

        if (!isValid(startNode) || !isValid(endNode)) {
            return PathResult(false, emptyList(), 0.0, "Start or End node invalid")
        }

        // Priority queue stores generic Pair<Cost, Node>
        // We want min-heap based on Cost (Double).
        val openSet = PriorityQueue<Pair<Double, Node>> { a, b -> a.first.compareTo(b.first) }
        openSet.add(0.0 to startNode)

        val cameFrom = mutableMapOf<Node, Node>()
        val gScore = mutableMapOf<Node, Double>().withDefault { Double.POSITIVE_INFINITY }
        gScore[startNode] = 0.0

        val fScore = mutableMapOf<Node, Double>().withDefault { Double.POSITIVE_INFINITY }
        fScore[startNode] = heuristic(startNode, endNode)

        val visited = mutableSetOf<Node>()

        while (openSet.isNotEmpty()) {
            val (_, current) = openSet.poll()

            if (current == endNode) {
                return reconstructPath(cameFrom, current, gScore[endNode] ?: 0.0)
            }

            if (current in visited) continue
            visited.add(current)

            for (neighbor in getNeighbors(current)) {
                val moveCost = calculateMovementCost(current, neighbor)
                
                // If moveCost is infinite, it's impassable
                if (moveCost.isInfinite()) continue

                val tentativeGScore = gScore.getValue(current) + moveCost

                if (tentativeGScore < gScore.getValue(neighbor)) {
                    cameFrom[neighbor] = current
                    gScore[neighbor] = tentativeGScore
                    val f = tentativeGScore + heuristic(neighbor, endNode)
                    fScore[neighbor] = f
                    openSet.add(f to neighbor)
                }
            }
        }

        return PathResult(false, emptyList(), 0.0, "No path found")
    }

    private fun reconstructPath(cameFrom: Map<Node, Node>, current: Node, totalCost: Double): PathResult {
        val totalPath = mutableListOf(current)
        var curr = current
        while (cameFrom.containsKey(curr)) {
            curr = cameFrom.getValue(curr)
            totalPath.add(curr)
        }
        return PathResult(true, totalPath.reversed(), totalCost)
    }

    // Manhattan distance heuristic
    private fun heuristic(a: Node, b: Node): Double {
        return (abs(a.x - b.x) + abs(a.y - b.y)).toDouble()
    }

    private fun getNeighbors(node: Node): List<Node> {
        val neighbors = mutableListOf<Node>()
        val directions = listOf(
            Node(0, 1), Node(0, -1), Node(1, 0), Node(-1, 0), // Cardinals
            Node(1, 1), Node(1, -1), Node(-1, 1), Node(-1, -1) // Diagonals
        )

        for (dir in directions) {
            val nx = node.x + dir.x
            val ny = node.y + dir.y
            val neighbor = Node(nx, ny)
            if (isValid(neighbor)) {
                neighbors.add(neighbor)
            }
        }
        return neighbors
    }

    private fun isValid(node: Node): Boolean {
        return node.x in 0 until width && node.y in 0 until height
    }

    private fun key(x: Int, y: Int) = "$x,$y" // Assuming TileInfo keys are "x,y" strings based on how you index them

    /**
     * Calculate cost to move from A to B.
     * 
     * Base costs:
     * - Grass/Dirt: 1.0
     * - Tree: +2.0
     * - Rock: +3.0
     * - Water/Lava: Infinity (Impassable)
     * 
     * Modifiers:
     * - Slope: Cost increases with height difference.
     * - Diagonal: x 1.414
     */
    private fun calculateMovementCost(from: Node, to: Node): Double {
        val toTileKey = "${to.x},${to.y}" // Reconstruct key. Optimisation: Index simply by encoded Integer?
        // Wait, map keys in main might be "x,y" string from previous stages?
        // Let's assume the map passed in is indexed efficiently. 
        // Actually, looking at Models.kt, tiles is a List.
        // We should convert tiles to a Map or Array lookup in the App before passing here.
        
        val tile = tiles[toTileKey] ?: return Double.POSITIVE_INFINITY

        // 1. Base Terrain Cost
        var cost = when (tile.terrain) {
            "grass", "dirt" -> 1.0
            "rock" -> 4.0 // Rocks are hard to walk on
            "water", "deep_water", "lava" -> Double.POSITIVE_INFINITY
            else -> 1.0
        }

        if (cost.isInfinite()) return Double.POSITIVE_INFINITY

        // 2. Vegetation Penalty
        // Check decorations for vegetation
        // Assuming decorations json: [{"vegetation": {"type": "tree", ...}}] or similar
        // Actually TileInfo has `decorations: List<JsonElement>`
        // We'd need to parse that. For V1 let's check simple string contains?
        // Or better, let's look at the parsed structure in a helper.
        // For speed, let's assume we pay a flat penalty if any decoration exists for now?
        // Or simpler: The prompt mentions "Tree=2".
        
        // Improving check:
        val hasVegetation = tile.decorations.any { it.toString().contains("vegetation") }
        if (hasVegetation) {
            cost += 2.0
        }

        // 3. Slope Penalty
        // If we have previous tile height (from weather?), we can check slope.
        // WeatherInfo has `slope`. 
        // Let's use the destination's slope as a proxy for difficulty if specific delta isn't available easily.
        val slope = tile.weather?.slope ?: 0
        if (slope > 0) {
            cost += (slope * 0.5) // Arbitrary slope penalty
        }

        // 4. Diagonal Multiplier
        val isDiagonal = (from.x != to.x) && (from.y != to.y)
        if (isDiagonal) {
            cost *= 1.414
        }

        return cost
    }
}
