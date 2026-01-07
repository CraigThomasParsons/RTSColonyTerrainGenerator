namespace Tiler.Model
{
    /// <summary>
    /// Authoritative terrain layer enum values emitted by the Heightmap Engine.
    ///
    /// These values are NOT hints.
    /// These values are NOT subject to reinterpretation by the Tiler.
    ///
    /// The Tiler must treat them as truth and only use them to select
    /// tile IDs / visual variants via bitmasking.
    /// </summary>
    public enum TerrainLayer : byte
    {
        /// <summary>
        /// Water cell.
        /// </summary>
        Water = 0,

        /// <summary>
        /// Land (grass / soil) cell.
        /// </summary>
        Land = 1,

        /// <summary>
        /// Pine mountain cell (higher elevation mountainous region, forested category).
        /// </summary>
        PineMountain = 2,

        /// <summary>
        /// Rock mountain cell (higher elevation mountainous region, rocky category).
        /// </summary>
        RockMountain = 3
    }
}
