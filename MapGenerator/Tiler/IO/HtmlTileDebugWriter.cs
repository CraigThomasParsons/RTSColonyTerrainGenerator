using System;
using System.IO;
using System.Text;

namespace Tiler.IO
{
    /// <summary>
    /// Writes a human-readable HTML visualization of the tile grid.
    ///
    /// This output is for debugging ONLY:
    /// - Never consumed by automation
    /// - Never affects production output
    /// - Deterministic and inspectable
    ///
    /// Each tile is rendered as a table cell with:
    /// - Background color based on terrain
    /// - Borders based on adjacency mask
    /// - Tooltip showing tile metadata
    /// </summary>
    public static class HtmlTileDebugWriter
    {
        /// <summary>
        /// Writes an HTML file visualizing the tile grid.
        /// </summary>
        /// <param name="outputPath">Destination .html file path.</param>
        /// <param name="tileIds">Resolved tile ID grid [x,y].</param>
        public static void Write(
            string outputPath,
            ushort[,] tileIds)
        {
            uint width = (uint)tileIds.GetLength(0);
            uint height = (uint)tileIds.GetLength(1);

            var sb = new StringBuilder(1024 * 1024);

            // ---- HTML Header ----
            sb.AppendLine("<!DOCTYPE html>");
            sb.AppendLine("<html>");
            sb.AppendLine("<head>");
            sb.AppendLine("<meta charset=\"utf-8\" />");
            sb.AppendLine("<title>Tiler Debug View</title>");
            sb.AppendLine("<style>");
            sb.AppendLine("table { border-collapse: collapse; }");
            sb.AppendLine("td { width: 10px; height: 10px; padding: 0; }");
            sb.AppendLine("</style>");
            sb.AppendLine("</head>");
            sb.AppendLine("<body>");
            sb.AppendLine("<table>");

            // ---- Table Rows ----
            for (uint y = 0; y < height; y++)
            {
                sb.AppendLine("<tr>");

                for (uint x = 0; x < width; x++)
                {
                    ushort tileId = tileIds[x, y];

                    byte terrain = (byte)(tileId >> 8);
                    byte mask = (byte)(tileId & 0x0F);

                    string bgColor = TerrainColor(terrain);
                    string borderStyle = BorderStyle(mask);

                    sb.Append("<td style=\"");
                    sb.Append($"background:{bgColor};");
                    sb.Append(borderStyle);
                    sb.Append("\"");

                    sb.Append($" title=\"tileId={tileId}, terrain={terrain}, mask={mask}\"");
                    sb.Append("></td>");
                }

                sb.AppendLine("</tr>");
            }

            sb.AppendLine("</table>");
            sb.AppendLine("</body>");
            sb.AppendLine("</html>");

            File.WriteAllText(outputPath, sb.ToString());
        }

        /// <summary>
        /// Maps terrain layer to a background color.
        /// </summary>
        private static string TerrainColor(byte terrain)
        {
            return terrain switch
            {
                0 => "#4a90e2", // Water
                1 => "#8ea38fff", // Land
                2 => "#2e7d32", // PineMountain
                3 => "#8d6e63", // RockMountain
                _ => "#000000"
            };
        }

        /// <summary>
        /// Generates CSS border styles from a 4-bit adjacency mask.
        ///
        /// Missing neighbors produce thick borders.
        /// </summary>
        private static string BorderStyle(byte mask)
        {
            string top =    (mask & 1) == 0 ? "border-top:2px solid black;"    : "border-top:1px solid transparent;";
            string right =  (mask & 2) == 0 ? "border-right:2px solid black;"  : "border-right:1px solid transparent;";
            string bottom = (mask & 4) == 0 ? "border-bottom:2px solid black;" : "border-bottom:1px solid transparent;";
            string left =   (mask & 8) == 0 ? "border-left:2px solid black;"   : "border-left:1px solid transparent;";

            return top + right + bottom + left;
        }
    }
}
