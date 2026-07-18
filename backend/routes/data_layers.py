"""
Data Layers Route
===================
Scans the `data_layers/` folder and auto-loads every subfolder as a
separate Layer, using the existing Adapter Factory.
"""

import os
from typing import List

from fastapi import APIRouter

from backend.adapters.gdb_adapter import GDBAdapter
from backend.models.layer import LayerModel
from backend.services.adapter_factory import get_adapter

router = APIRouter()

DATA_LAYERS_DIR = "data_layers"


@router.get("/data-layers", response_model=List[LayerModel])
def load_data_layers() -> List[LayerModel]:
    """Auto-load every subfolder inside data_layers/ as a Layer."""
    layers = []

    if not os.path.isdir(DATA_LAYERS_DIR):
        return layers

    for subfolder in os.listdir(DATA_LAYERS_DIR):
        folder_path = os.path.join(DATA_LAYERS_DIR, subfolder)
        if not os.path.isdir(folder_path):
            continue

        shp_file = next(
            (f for f in os.listdir(folder_path) if f.lower().endswith(".shp")),
            None,
        )
        gdb_folder = next(
            (f for f in os.listdir(folder_path) if f.lower().endswith(".gdb")
             and os.path.isdir(os.path.join(folder_path, f))),
            None,
        )

        # Case: the subfolder itself IS the .gdb (e.g. data_layers/Geodatabase.gdb/)
        if gdb_folder is None and subfolder.lower().endswith(".gdb"):
            try:
                gdb_layers = GDBAdapter().read_all(folder_path)
                for gdb_layer in gdb_layers:
                    gdb_layer.name = f"{subfolder} - {gdb_layer.name}"
                    layers.append(gdb_layer)
            except ValueError as e:
                print(f"[data-layers] Failed '{subfolder}': {e}")
                layers.append(LayerModel(name=subfolder, features=[], error=str(e)))
            continue

        if shp_file is not None:
            try:
                adapter = get_adapter(shp_file)
                layer = adapter.read(os.path.join(folder_path, shp_file))
                layer.name = subfolder  # use folder name as layer name
                layers.append(layer)
            except ValueError as e:
                print(f"[data-layers] Failed '{subfolder}': {e}")
                layers.append(LayerModel(name=subfolder, features=[], error=str(e)))
            continue

        if gdb_folder is not None:
            try:
                gdb_layers = GDBAdapter().read_all(os.path.join(folder_path, gdb_folder))
                for gdb_layer in gdb_layers:
                    gdb_layer.name = f"{subfolder} - {gdb_layer.name}"
                    layers.append(gdb_layer)
            except ValueError as e:
                print(f"[data-layers] Failed '{subfolder}': {e}")
                layers.append(LayerModel(name=subfolder, features=[], error=str(e)))
            continue

    return layers
