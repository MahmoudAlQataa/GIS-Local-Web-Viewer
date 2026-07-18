"""
Base Adapter
=============
Every GIS format adapter (GeoJSON, Shapefile, KML, ...) must inherit from
this class and implement the `read` method.

This is the contract that guarantees all adapters produce the exact same
Internal Data Model, regardless of the original file format.
"""

from abc import ABC, abstractmethod

from backend.models.layer import LayerModel


class BaseAdapter(ABC):
    """
    Abstract base class for all GIS format adapters.
    """

    @abstractmethod
    def read(self, file_path: str) -> LayerModel:
        """
        Read a GIS file and convert it into the unified internal Layer model.

        Args:
            file_path: Path to the uploaded GIS file on disk.

        Returns:
            Layer: The standardized internal representation
                   (name, crs, features) that the rest of the
                   application depends on.

        Raises:
            ValueError: If the file cannot be read or converted.
        """
        raise NotImplementedError