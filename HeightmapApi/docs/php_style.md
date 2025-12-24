# PHP Coding Style & Commenting Conventions (PSR-Aligned)

This document defines the required PHP coding style for all MapGenerator
and Heightmap-related PHP code.

The goal is clarity, explicitness, and long-term maintainability,
while strictly adhering to PHP Standard Recommendations (PSR).

---

## Core Philosophy

- Code should explain itself without cleverness
- Readability is more important than brevity
- Descriptive names are preferred over short names
- Code must remain understandable months later without external context
- PHP code should feel boring, predictable, and explicit

---

## Standards Compliance

This project follows:

- **PSR-1**: Basic Coding Standard
- **PSR-12**: Extended Coding Style Guide

Where PSR is silent (e.g., local variables), this document defines
project-specific conventions.

---

## Naming Conventions (LOCKED)

✅ Good:
```php
private int $mapWidthInCells;
protected string $jobIdentifier;
```

### Class Properties
- **camelCase**
- No leading underscores
- No Hungarian notation

### Variables
- Use **descriptive, multi-word variable names**
- Never write single-letter variable names.

### Contants
  - Use uppercase with underscores
```
const HEIGHTMAP_INBOX_DIRECTORY = '/app/Heightmap/inbox';
```

Methods / Functions

  - camelCase
  - Verb-based, explicit names
  - No abbreviations

Good:
```
enqueueHeightmapJob()
validateRequestPayload()
generateUniqueJobIdentifier()
```
Bad:
```
enqueue_job()
doStuff()
handle()
```

Local Variables

PSR does not mandate a format for local variables.
This project explicitly standardizes on camelCase for consistency.

 - camelCase
 - Descriptive, multi-word names
 - Single-letter variables are forbidden

Good:
```
$decodedRequestPayload
$jobFilePath
$heightmapInboxDirectory
```
Bad:
```
$i
$tmp
$data
$payload_arr
```

File Structure Rules:

  - One responsibility per file

  - No mixed concerns

  - API endpoints must do exactly one thing

  - No hidden side effects

Example:

  - enqueueHeightmapJob.php

    - Accept request

    - Validate input

    - Write job file

    - Respond

Nothing more.
---
Commenting Rules (CRITICAL)
Comment Density

A comment every 3–4 logical lines

  - Comments should explain intent and reasoning

  - Avoid narrating obvious syntax

  - Explain why things needed to be done over what is being done

---

### File-Level / Block Comments

Use block comments to explain purpose and constraints:
```
/**
 * Enqueues a heightmap generation job.
 *
 * This endpoint does NOT:
 * - Generate terrain
 * - Invoke the heightmap engine
 * - Block on results
 *
 * Its sole responsibility is to write a valid job file
 * into the heightmap inbox directory.
 */
```
---

### Inline Comments (Why > What)

```
// Generate a unique identifier to avoid filename collisions
$jobIdentifier = generateUniqueJobIdentifier();
```
### Guard Clauses Must Be Commented

Every early exit must justify its existence:
```
// Reject empty request bodies to prevent writing invalid jobs
if ($rawRequestBody === false || trim($rawRequestBody) === '') {
    http_response_code(400);
    echo json_encode(['error' => 'Empty request body']);
    exit;
}
```

### Error Handling Rules

- Fail fast

- Be explicit

- Never silently ignore errors

- Prefer guard clauses over deep nesting

---

### JSON Handling

  - Always decode into associative arrays

  - Always pretty-print when writing to disk

  - Never trust incoming JSON blindly
```
json_encode($jobPayload, JSON_PRETTY_PRINT);
```
---
### Formatting Rules (PSR-12)

 - 4 spaces per indent

 - No tabs

 - One statement per line

 - Blank lines between logical sections

 - Opening braces on the next line for classes and functions

---

### Forbidden Practices

🚫 Single-letter variable names
🚫 Abbreviations
🚫 Deeply nested conditionals
🚫 Clever one-liners
🚫 Implicit behavior
🚫 Mixing I/O and logic in the same function

---
Canonical Example (PSR-Correct)
```
<?php

declare(strict_types=1);

/**
 * Enqueue a heightmap generation job.
 *
 * This endpoint accepts a JSON payload and writes a job file
 * into the heightmap inbox directory.
 */

const HEIGHTMAP_INBOX_DIRECTORY = '/app/Heightmap/inbox';

// Read the raw request body
$rawRequestBody = file_get_contents('php://input');

// Reject empty request bodies early
if ($rawRequestBody === false || trim($rawRequestBody) === '') {
    http_response_code(400);
    echo json_encode(['error' => 'Empty request body']);
    exit;
}

// Decode the JSON payload
$decodedRequestPayload = json_decode($rawRequestBody, true);

// Validate JSON decoding
if ($decodedRequestPayload === null) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON payload']);
    exit;
}

// Generate a unique job identifier
$jobIdentifier = date('Ymd_His') . '_' . bin2hex(random_bytes(4));

// Build the job payload
$jobPayload = [
    'job_id' => $jobIdentifier,
    'requested_at_utc' => gmdate('c'),
    'payload' => $decodedRequestPayload,
];

// Construct the output file path
$jobFilePath =
    HEIGHTMAP_INBOX_DIRECTORY . '/' . $jobIdentifier . '.json';

// Write the job file to disk
file_put_contents(
    $jobFilePath,
    json_encode($jobPayload, JSON_PRETTY_PRINT)
);

// Respond with success
header('Content-Type: application/json');

echo json_encode([
    'ok' => true,
    'job_id' => $jobIdentifier,
]);
```

### Final Rule

If a future reader must guess intent, the code is wrong.

PSR compliance is the baseline.
Clarity is the priority.


---
