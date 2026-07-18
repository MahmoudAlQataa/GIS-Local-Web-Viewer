"""
GDB Adapter (File Geodatabase)
================================
Reads a File Geodatabase (.gdb folder) and converts EVERY table/feature
class it contains into the unified Internal Data Model.

Unlike other adapters, a single .gdb can hold multiple tables — so this
adapter exposes `read_all()` which returns a LIST of LayerModel objects
instead of a single one. `read()` is kept only for BaseAdapter contract
compatibility and returns just the first table.

Uses the OpenFileGDB driver (via pyogrio) — free, read-only, ships with
GDAL by default. No Esri SDK/license required.

Notes:
- We do NOT read the .gdb's internal Relationship Classes. Linking
  between tables/feature classes (e.g. person -> camp) is handled by
  the project's existing generic linking system (auto-detect shared
  column + manual dropdown), same as any other table/spatial layer pair.
- If another program (e.g. ArcGIS) has an active, unsaved Edit Session
  on the .gdb, reads may fail or return stale data until "Save Edits"
  is done in that program. This adapter does not currently detect or
  report that condition.
"""

from typing import List

import geopandas as gpd
import pyogrio

from backend.adapters.base_adapter import BaseAdapter
from backend.models.feature import FeatureModel
from backend.models.layer import LayerModel


class GDBAdapter(BaseAdapter):
    def read(self, file_path: str) -> LayerModel:
        """
        BaseAdapter contract compatibility. A .gdb usually contains
        multiple tables — prefer read_all() instead. This returns only
        the first table found.
        """
        layers = self.read_all(file_path)
        if not layers:
            raise ValueError(f"No readable tables found inside '{file_path}'.")
        return layers[0]

    def read_all(self, gdb_path: str) -> List[LayerModel]:
        """
        Read every table/feature class inside a .gdb and return one
        LayerModel per table.
        """
        try:
            layer_names = [row[0] for row in pyogrio.list_layers(gdb_path)]
        except Exception as e:
            raise ValueError(f"Failed to open File Geodatabase '{gdb_path}': {e}")

        layers = []
        for layer_name in layer_names:
            try:
                layers.extend(self._read_single_layer(gdb_path, layer_name))
            except Exception as e:
                print(f"[GDBAdapter] Failed table '{layer_name}' in '{gdb_path}': {e}")
                layers.append(
                    LayerModel(
                        name=layer_name,
                        features=[],
                        error=self._friendly_error(e),
                    )
                )
                continue

        return layers

    @staticmethod
    def _friendly_error(e: Exception) -> str:
        """Translate common low-level GDAL errors into a message the user can act on."""
        text = str(e)
        if "index is out of sync" in text or "appears to be deleted" in text:
            return (
                "الجدول فيه تلف بسيط بالفهرسة (index) داخل ملف الـ .gdb، غالباً بسبب "
                "حذف صف من ArcGIS بدون تحديث الفهرس. الحل: افتح الـ Geodatabase من "
                "ArcGIS Pro/Catalog واعمل Compact عليها، ثم أعد تحميل الصفحة."
            )
        return f"تعذّرت قراءة هذا الجدول: {text}"

    def _read_single_layer(self, gdb_path: str, layer_name: str) -> List[LayerModel]:
        """
        Read one table/feature class. If the table mixes rows that have
        geometry with rows that don't (seen in real .gdb data — e.g. a
        person row with no location alongside camp rows that do), split
        it into two separate LayerModels: one "spatial" and one "table".
        If the table is uniformly one or the other, a single LayerModel
        is returned (list of length 1), same as before.
        """
        gdf = gpd.read_file(gdb_path, layer=layer_name, engine="pyogrio")

        if gdf.crs is not None and gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        spatial_features = []
        table_features = []
        for _, row in gdf.iterrows():
            geom_obj = row.geometry if "geometry" in row else None
            properties = row.drop("geometry").to_dict() if "geometry" in row else row.to_dict()
            if geom_obj is not None and not geom_obj.is_empty:
                geometry = geom_obj.__geo_interface__
                spatial_features.append(FeatureModel(geometry=geometry, properties=properties))
            else:
                table_features.append(FeatureModel(geometry=None, properties=properties))

        print(f"[DEBUG-GDB] {layer_name}: spatial={len(spatial_features)}, table={len(table_features)}")
        result = []
        if spatial_features:
            result.append(
                LayerModel(name=layer_name, type="spatial", crs="EPSG:4326", features=spatial_features)
            )
        if table_features:
            # Give the table half a distinguishable name when the source
            # table was mixed, so both halves are recognizable in the UI.
            table_name = f"{layer_name} (بدون موقع)" if spatial_features else layer_name
            result.append(
                LayerModel(name=table_name, type="table", crs="EPSG:4326", features=table_features)
            )

        if not result:
            # Empty table — keep old behavior of returning something rather than nothing.
            result.append(LayerModel(name=layer_name, type="table", crs="EPSG:4326", features=[]))

        return result
    