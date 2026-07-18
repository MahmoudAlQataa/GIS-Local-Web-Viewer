"""
File Validator
===============
Validates uploaded GIS files before they are handed to any adapter.

Per the project specification, validation must never expose internal
exceptions to the user — only clear, human-readable error messages.
"""

import os

SUPPORTED_EXTENSIONS = {".geojson", ".json"}
MAX_FILE_SIZE_MB = 50  # Configurable backend setting.


def validate_file(file_path: str) -> None:
    """
    Validate an uploaded GIS file.

    Args:
        file_path: Path to the file on disk.

    Raises:
        ValueError: If the file fails any validation check, with a
                    user-friendly message describing the problem.
    """

    # 1. File must exist.
    if not os.path.isfile(file_path):
        raise ValueError("Uploaded file could not be found.")

    # 2. File must not be empty.
    if os.path.getsize(file_path) == 0:
        raise ValueError("Uploaded file is empty.")

    # 3. Extension must be supported.
    _, extension = os.path.splitext(file_path)
    if extension.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{extension}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # 4. File size limit.
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"File size ({size_mb:.1f} MB) exceeds the maximum allowed "
            f"size ({MAX_FILE_SIZE_MB} MB)."
        )