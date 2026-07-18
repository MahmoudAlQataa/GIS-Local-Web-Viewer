"""
Layer Model
============
Represents a full GIS layer inside the Internal Data Model.

Every adapter (GeoJSONAdapter, ShapefileAdapter, ...) must return data
in this exact shape, regardless of the original file format.
"""

from typing import List

from pydantic import BaseModel, Field

from backend.models.feature import FeatureModel


class LayerModel(BaseModel):
    """
    Standardized representation of a GIS layer.

    Attributes:
        name: Layer name (e.g. derived from the uploaded file name).
        crs: Coordinate Reference System of the layer. Must always be
             EPSG:4326 by the time it reaches the frontend — adapters
             are responsible for reprojecting before returning this model.
        features: List of features belonging to this layer.
    """

    name: str = Field(..., description="Layer name.")
    type: str = Field(
        default="spatial",
        description="'spatial' if features have geometry, 'table' if this is attribute-only data (e.g. linked by ID, no coordinates).",
    )
    crs: str = Field(
        default="EPSG:4326",
        description="Coordinate Reference System (must be EPSG:4326 for Leaflet).",
    )
    features: List[FeatureModel] = Field(
        default_factory=list,
        description="List of features contained in this layer.",
    )
    error: str = Field(
        default=None,
        description="If this layer failed to load, a short human-readable reason. None if loaded successfully.",
    )