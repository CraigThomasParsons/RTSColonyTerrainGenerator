<?php

declare(strict_types=1);

namespace MapGenerator\HeightmapApi\Controller;

use MapGenerator\HeightmapApi\Exception\BadRequestException;
use MapGenerator\HeightmapApi\Service\HeightmapJobWriter;
use Throwable;


/**
 * Handles HTTP requests for enqueueing heightmap jobs.
 * This whole class is intentionally verbose to ensure
 * input validation rules are explicit and readable.
 *
 * - Builds an API end point.
 *   - Fetches Width and Height from requestData.
 *   - Validates width and height and ensure correct types (integer)
 * - Hands off the job via writing to a file.
 */
final class EnqueueHeightmapController
{

    /**
     * Entry point for handling the enqueue request.
     *
     * This method:
     * - Validates HTTP method
     * - Parses JSON input
     * - Extracts width and height
     * - Writes a job file into the heightmap inbox
     * - Handles all failures in a single catch block
     */
    public function handleRequest(): void
    {
        header('Content-Type: application/json');

        try {
            $this->assertPostMethod();
            $requestData = $this->decodeJsonRequestBody();

            $mapWidthInCells  = $this->extractWidth($requestData);
            $mapHeightInCells = $this->extractHeight($requestData);

            $jobWriter = new HeightmapJobWriter(
                '/MapGenerator/Heightmap/inbox'
            );

            $jobMetadata = $jobWriter->writeJob(
                $mapWidthInCells,
                $mapHeightInCells
            );

            http_response_code(201);

            echo json_encode([
                'ok' => true,
                'job_id' => $jobMetadata['job_id'],
                'job_file' => $jobMetadata['job_file'],
            ]);
        } catch (BadRequestException $exception) {
            http_response_code(400);

            echo json_encode([
                'error' => $exception->getMessage(),
            ]);
        } catch (Throwable $exception) {
            http_response_code(500);

            echo json_encode([
                'error' => 'Internal server error',
            ]);
        }
    }

    /**
     * Ensure the request method is POST.
     */
    private function assertPostMethod(): void
    {
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            throw new BadRequestException(
                'Only POST requests are allowed'
            );
        }
    }

    /**
     * Decode and validate JSON request body.
     *
     * @return array
     */
    private function decodeJsonRequestBody(): array
    {
        $requestBody = file_get_contents('php://input');

        if ($requestBody === false) {
            throw new BadRequestException(
                'Unable to read request body'
            );
        }

        $decodedData = json_decode($requestBody, true);

        if (is_array($decodedData) === false) {
            throw new BadRequestException(
                'Invalid JSON body'
            );
        }

        return $decodedData;
    }

    /**
     * Extract and validate width from request data.
     */
    private function extractWidth(array $requestData): int
    {
        if (array_key_exists('width', $requestData) === false) {
            throw new BadRequestException(
                'width is required'
            );
        }

        $width = $requestData['width'];

        if (is_int($width) === false) {
            throw new BadRequestException(
                'width must be an integer'
            );
        }

        if ($width <= 0) {
            throw new BadRequestException(
                'width must be positive'
            );
        }

        return $width;
    }

    /**
     * Extract and validate height from request data.
     */
    private function extractHeight(array $requestData): int
    {
        if (array_key_exists('height', $requestData) === false) {
            throw new BadRequestException(
                'height is required'
            );
        }

        $height = $requestData['height'];

        if (is_int($height) === false) {
            throw new BadRequestException(
                'height must be an integer'
            );
        }

        if ($height <= 0) {
            throw new BadRequestException(
                'height must be positive'
            );
        }

        return $height;
    }
}