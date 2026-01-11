using System.Collections.Generic;
using Dafny;

namespace Tiler.Logging
{
    /// <summary>
    /// Dafny runtime interop helpers.
    ///
    /// PURPOSE:
    /// - Convert C# strings into Dafny seq<Rune>
    /// - Convert C# dictionaries into Dafny maps
    ///
    /// This is the ONLY place Dafny string weirdness is allowed to exist.
    /// </summary>
    internal static class DafnyInterop
    {
        /// <summary>
        /// Convert a C# string into Dafny seq<Rune>.
        ///
        /// WHY THIS EXISTS:
        /// Dafny's C# runtime does NOT provide a FromString helper
        /// for Rune sequences. We must build it manually.
        /// </summary>
        public static ISequence<Rune> String(string value)
        {
            var runes = new Rune[value.Length];

            for (int i = 0; i < value.Length; i++)
            {
                // Rune constructor takes a Unicode scalar value
                runes[i] = new Rune(value[i]);
            }

            return Sequence<Rune>.FromArray(runes);
        }

        /// <summary>
        /// Convert Dictionary<string,string> into Dafny map<seq<Rune>, seq<Rune>>.
        /// </summary>
        public static IMap<ISequence<Rune>, ISequence<Rune>> StringMap(
            IDictionary<string, string> source
        )
        {
            IMap<ISequence<Rune>, ISequence<Rune>> map =
                Map<ISequence<Rune>, ISequence<Rune>>.Empty;

            foreach (var pair in source)
            {
                map = Map<ISequence<Rune>, ISequence<Rune>>.Update(
                    map,
                    String(pair.Key),
                    String(pair.Value)
                );
            }

            return map;
        }
    }
}
