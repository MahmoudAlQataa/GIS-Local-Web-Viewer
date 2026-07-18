"""
Adapter Factory
=================
Selects and returns the appropriate adapter instance based on the
uploaded file's extension.

New formats (Shapefile, KML, GPX, GeoPackage...) should be registered
in the `_ADAPTERS` mapping below WITHOUT modifying any other part of
the application.
"""

import os

from backend.adapters.base_adapter import BaseAdapter
from backend.adapters.geojson_adapter import GeoJSONAdapter
from backend.adapters.shapefile_adapter import ShapefileAdapter

# Map file extensions to their adapter class.
# Future formats: add an entry here only.
_ADAPTERS = {
    ".geojson": GeoJSONAdapter,
    ".json": GeoJSONAdapter,
    ".shp": ShapefileAdapter,
}


def get_adapter(file_path: str) -> BaseAdapter:
    """
    Return an adapter instance suitable for the given file.

    Args:
        file_path: Path to the uploaded file.

    Returns:
        BaseAdapter: An instance of the matching adapter.

    Raises:
        ValueError: If no adapter supports the file's extension.
    """
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()

    adapter_class = _ADAPTERS.get(extension)
    if adapter_class is None:
        raise ValueError(f"No adapter available for file format '{extension}'.")

    return adapter_class()