"""
Feature Model
==============
Represents a single GIS feature inside the Internal Data Model.

A feature is the atomic unit of GIS data: one point, line, or polygon
with its associated attributes (properties).
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FeatureModel(BaseModel):
    """
    Standardized representation of a single GIS feature.

    Attributes:
        geometry: GeoJSON-style geometry dict, e.g.
                  {"type": "Point", "coordinates": [35.23, 32.22]}
                  None for table-only features with no spatial location
                  (e.g. a person record linked to a camp by ID).
        properties: Arbitrary key-value attributes attached to the feature
                    (e.g. name, city, type). Used for search and popups.
    """

    geometry: Optional[Dict[str, Any]] = Field(
        default=None, description="GeoJSON geometry object (type + coordinates), or None if this feature has no spatial location."
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Feature attributes used for search, popups, and display.",
    )