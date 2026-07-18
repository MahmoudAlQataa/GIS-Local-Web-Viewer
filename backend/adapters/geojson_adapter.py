"""
GeoJSON Adapter
================
Reads GeoJSON files using GeoPandas and converts them into the
unified Internal Data Model (LayerModel).

Responsible for:
    - Reading the file via GeoPandas.
    - Checking the source CRS.
    - Reprojecting to EPSG:4326 if needed (Leaflet requirement).
    - Converting each row into a FeatureModel.
"""

import os

import geopandas as gpd

from backend.adapters.base_adapter import BaseAdapter
from backend.models.feature import FeatureModel
from backend.models.layer import LayerModel

TARGET_CRS = "EPSG:4326"


class GeoJSONAdapter(BaseAdapter):
    """
    Adapter for reading GeoJSON files (.geojson, .json).
    """

    def read(self, file_path: str) -> LayerModel:
        try:
            gdf = gpd.read_file(file_path)
        except Exception:
            raise ValueError("Invalid GeoJSON file. Failed to read uploaded file.")

        if gdf.empty:
            raise ValueError("Invalid GeoJSON file. No features found.")

        # Reproject to WGS84 if the source CRS is different (or missing).
        if gdf.crs is not None and str(gdf.crs) != TARGET_CRS:
            gdf = gdf.to_crs(TARGET_CRS)

        layer_name = os.path.splitext(os.path.basename(file_path))[0]

        features = []
        for _, row in gdf.iterrows():
            geometry = row.geometry.__geo_interface__ if row.geometry is not None else None
            if geometry is None:
                continue

            properties = row.drop(labels="geometry").to_dict()

            features.append(
                FeatureModel(geometry=geometry, properties=properties)
            )

        return LayerModel(name=layer_name, crs=TARGET_CRS, features=features)