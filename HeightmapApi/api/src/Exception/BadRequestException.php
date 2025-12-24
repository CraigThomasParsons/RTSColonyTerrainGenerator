<?php

declare(strict_types=1);

namespace MapGenerator\HeightmapApi\Exception;

use RuntimeException;

/**
 * Thrown when the client sends invalid input.
 */
final class BadRequestException extends RuntimeException
{
}
