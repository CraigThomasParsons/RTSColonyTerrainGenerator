package mapgen.worldfeatures

data class CivicCoord(val x: Int, val y: Int)

data class CivicBridge(
    val id: String?,
    val x: Int,
    val y: Int,
    val length: Int?,
    val orientation: String?,
    val status: String?,
    val cause: String?
)

data class CivicRoad(
    val path: List<CivicCoord>,
    val status: String?
)

data class CivicBuilding(
    val x: Int,
    val y: Int,
    val type: String?,
    val status: String?
)

data class CivicOverreachData(
    val bridges: List<CivicBridge>,
    val roads: List<CivicRoad>,
    val buildings: List<CivicBuilding>
)
