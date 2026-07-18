"""
Raster Layers Route
====================
Auto-discovers basemap tile layers inside raster_data/.

Each subfolder under raster_data/ represents one basemap layer.
The actual tile root (the folder containing numeric zoom-level folders,
e.g. "12", "13", ...) may be nested one or two levels deep inside the
layer folder (matches the pattern used by tiles_satellite/satellite/{z}/{x}/{y}.png).

No caching: the folder is rescanned on every request (refresh = update),
same behavior as /data-layers.
"""

import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

RASTER_DATA_DIR = "raster_data"
MAX_SEARCH_DEPTH = 3  # كم مستوى فرعي ندور فيه عن مجلد الـ z levels

SUPPORTED_TILE_EXTENSIONS = ["png", "jpg", "jpeg", "webp"]
RAW_RASTER_EXTENSIONS = ["tif", "tiff", "jp2"]  # صيغ مصدر خام، مش تايلز جاهزة للعرض


class RasterLayerModel(BaseModel):
    name: str
    url_template: str | None = None
    error: str | None = None


def _looks_like_zoom_folder(path: str) -> bool:
    """True إذا كل الأسماء جوا هاد المجلد أرقام (يعني هاد مجلد الـ z levels)."""
    try:
        entries = [e for e in os.listdir(path) if not e.startswith(".")]
    except OSError:
        return False
    if not entries:
        return False
    return all(e.isdigit() for e in entries)


def _find_tile_root(layer_folder_path: str) -> str | None:
    """
    يدور recursively (لحد MAX_SEARCH_DEPTH) عن أول مجلد فرعي
    كل محتوياته أرقام (z levels)، ويرجع مساره الكامل.
    لو ما لقى شي بيرجع None.
    """

    def _search(current_path: str, depth: int) -> str | None:
        if depth > MAX_SEARCH_DEPTH:
            return None
        if _looks_like_zoom_folder(current_path):
            return current_path
        try:
            subdirs = [
                os.path.join(current_path, e)
                for e in os.listdir(current_path)
                if os.path.isdir(os.path.join(current_path, e)) and not e.startswith(".")
            ]
        except OSError:
            return None
        for sub in subdirs:
            found = _search(sub, depth + 1)
            if found:
                return found
        return None

    return _search(layer_folder_path, 0)


def _detect_tile_extension(tile_root: str) -> str | None:
    """
    يفتح أول مجلد zoom (رقم) وأول مجلد x جواه، ويشوف امتداد
    أول ملف تايل موجود فعلياً. بيرجع الامتداد (بدون نقطة) أو None.
    """
    try:
        z_folders = [e for e in os.listdir(tile_root) if e.isdigit()]
        if not z_folders:
            return None
        z_path = os.path.join(tile_root, z_folders[0])

        x_folders = [
            e for e in os.listdir(z_path)
            if os.path.isdir(os.path.join(z_path, e))
        ]
        if not x_folders:
            return None
        x_path = os.path.join(z_path, x_folders[0])

        for f in os.listdir(x_path):
            ext = f.rsplit(".", 1)[-1].lower() if "." in f else None
            if ext in SUPPORTED_TILE_EXTENSIONS:
                return ext
    except OSError:
        return None
    return None


def _find_raw_raster_file(layer_folder_path: str) -> str | None:
    """
    يدور recursively عن أي ملف .tif/.tiff/.jp2 جوا مجلد الطبقة —
    مؤشر إنو حد حط ملف رسترية خام بالغلط بدل تايلز مقسّمة.
    بيرجع اسم الملف (للرسالة) أو None.
    """
    for root, _dirs, files in os.walk(layer_folder_path):
        for f in files:
            ext = f.rsplit(".", 1)[-1].lower() if "." in f else None
            if ext in RAW_RASTER_EXTENSIONS:
                return f
    return None


@router.get("/raster-layers", response_model=list[RasterLayerModel])
def get_raster_layers():
    """
    يمسح raster_data/ ويرجع كل طبقة خريطة (basemap) مكتشفة تلقائياً،
    مع رابط الـ tile template الجاهز للاستخدام مباشرة بـ Leaflet.
    لو انلقى ملف رسترية خام (.tif/.jp2) بدل تايلز، بترجع الطبقة
    مع حقل error يوضح المشكلة بدل ما تتجاهل بصمت.
    """
    layers: list[RasterLayerModel] = []

    if not os.path.isdir(RASTER_DATA_DIR):
        return layers

    for entry in sorted(os.listdir(RASTER_DATA_DIR)):
        layer_path = os.path.join(RASTER_DATA_DIR, entry)
        if not os.path.isdir(layer_path) or entry.startswith("."):
            continue

        tile_root = _find_tile_root(layer_path)
        if tile_root is None:
            # ما انلقت بنية z/x/y جاهزة — نتحقق هل السبب ملف رسترية خام
            raw_file = _find_raw_raster_file(layer_path)
            if raw_file:
                layers.append(RasterLayerModel(
                    name=entry,
                    error=(
                        f"الملف '{raw_file}' صيغة رسترية خام (GeoTIFF/JP2)، "
                        "مش تايلز جاهزة للعرض. لازم تصدير التايلز أولاً "
                        "(مثلاً عبر QTiles) قبل ما تنحط بـ raster_data/."
                    ),
                ))
            continue  # ولو ما في ملف خام ولا بنية تايلز، تجاهله تماماً

        ext = _detect_tile_extension(tile_root)
        if ext is None:
            continue  # ما انلقى أي ملف تايل بامتداد مدعوم — تجاهله

        rel_path = os.path.relpath(tile_root, RASTER_DATA_DIR).replace(os.sep, "/")
        url_template = f"/raster_data/{rel_path}/{{z}}/{{x}}/{{y}}.{ext}"

        layers.append(RasterLayerModel(name=entry, url_template=url_template))

    return layers