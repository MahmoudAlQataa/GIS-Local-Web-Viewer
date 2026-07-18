"""
Shapefile Adapter
==================
Reads a Shapefile (.shp + its companion files) directly from disk
and converts it into the unified Internal Data Model.

Handles a known limitation of the .dbf format: field NAMES are capped
at 10 bytes, which can truncate multi-byte (e.g. Arabic/UTF-8) field
names mid-character and make them undecodable. When that happens, we
work on a temporary copy of the shapefile with only the broken field
names replaced by safe placeholders (e.g. FIELD_1) — the actual data
VALUES (which are not length-limited) are left untouched and keep
their original language/content.
"""

import os
import shutil
import tempfile

import geopandas as gpd

from backend.adapters.base_adapter import BaseAdapter
from backend.models.feature import FeatureModel
from backend.models.layer import LayerModel


def _sanitize_field_names(dbf_path: str) -> bool:
    """
    Rewrite any undecodable (truncated multi-byte) field name in the
    given .dbf file with a safe ASCII placeholder, in place.

    Returns True if any field name was changed, False otherwise.
    """
    with open(dbf_path, "rb") as f:
        content = bytearray(f.read())

    header_size = int.from_bytes(content[8:10], "little")
    num_fields = (header_size - 33) // 32

    changed = False
    for i in range(num_fields):
        offset = 32 + i * 32
        raw_name = bytes(content[offset:offset + 11])
        name_bytes = raw_name.split(b"\x00")[0]
        try:
            name_bytes.decode("utf-8")
        except UnicodeDecodeError:
            placeholder = f"FIELD_{i + 1}".encode("ascii").ljust(11, b"\x00")
            content[offset:offset + 11] = placeholder
            changed = True

    if changed:
        with open(dbf_path, "wb") as f:
            f.write(content)

    return changed


class ShapefileAdapter(BaseAdapter):
    def read(self, file_path: str) -> LayerModel:
        try:
            gdf = gpd.read_file(file_path, encoding="utf-8")
        except Exception:
            gdf = self._read_with_sanitized_field_names(file_path)

        if gdf.crs is not None and gdf.crs.to_string() != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        features = []
        has_any_geometry = False
        for _, row in gdf.iterrows():
            geom_obj = row.geometry
            if geom_obj is not None and not geom_obj.is_empty:
                geometry = geom_obj.__geo_interface__
                has_any_geometry = True
            else:
                geometry = None
            properties = row.drop("geometry").to_dict() if "geometry" in row else row.to_dict()
            features.append(FeatureModel(geometry=geometry, properties=properties))

        name = os.path.splitext(os.path.basename(file_path))[0]
        layer_type = "spatial" if has_any_geometry else "table"

        return LayerModel(name=name, type=layer_type, crs="EPSG:4326", features=features)

    def _read_with_sanitized_field_names(self, file_path: str) -> "gpd.GeoDataFrame":
        """
        Fallback used when the initial read fails (likely due to a
        truncated multi-byte field name). Copies the whole shapefile
        set to a temp folder, patches only the broken field names,
        and retries the read from there. Data VALUES are untouched.
        """
        src_dir = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        tmp_dir = tempfile.mkdtemp()
        try:
            for fname in os.listdir(src_dir):
                if os.path.splitext(fname)[0] == base_name:
                    shutil.copy2(os.path.join(src_dir, fname), os.path.join(tmp_dir, fname))

            tmp_dbf = os.path.join(tmp_dir, base_name + ".dbf")
            if os.path.exists(tmp_dbf):
                _sanitize_field_names(tmp_dbf)

            tmp_shp = os.path.join(tmp_dir, base_name + ".shp")
            try:
                return gpd.read_file(tmp_shp, encoding="utf-8")
            except Exception as e:
                raise ValueError(f"Invalid or corrupted Shapefile: {e}")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)