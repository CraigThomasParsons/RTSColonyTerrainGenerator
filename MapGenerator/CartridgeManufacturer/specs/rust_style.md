# Rust Style Guide — WCAR Project

## General Principles

• Prefer clarity over cleverness
• Avoid macros unless strictly necessary
• No global mutable state
• No hidden magic

## Formatting

• Follow rustfmt defaults
• 4-space indentation
• One item per line where reasonable

## Types

• Use fixed-width integers (u8, u16, u32, u64)
• Avoid usize in serialized structures
• Explicit endianness when reading/writing binary data

## Error Handling

• Use Result<T, E>
• Prefer custom error enums over boxed errors
• Fail fast on invalid WCAR structure

## Modules

• One module per conceptual concern
• Binary layout code must be isolated
• Parsing != validation != projection

## Comments

• Comment binary layouts
• Comment projection assumptions
• Comment any lossy transformation

Future readers should be able to understand the format without reading
the specification document.
