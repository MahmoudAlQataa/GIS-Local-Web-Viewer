# GIS Local Web Viewer

An offline-first GIS web application for visualizing, exploring, and querying geospatial field data locally — no internet or cloud dependency required.

Built with **FastAPI**, **GeoPandas**, and **Leaflet.js**.

> ⚠️ This project is a work in progress. Core features are functional; some enhancements are still in development.

---

## Overview

GIS Local Web Viewer converts GIS data files — GeoJSON, Shapefile, and File Geodatabase (`.gdb`) — into an interactive web map. It's designed for humanitarian field data workflows where an internet connection can't be relied on: everything runs on `localhost`.

---

## Features

- **Multi-format support**: GeoJSON, Shapefile (with automatic handling of the `.dbf` 10-byte field name limit), and File Geodatabase (`.gdb`) via `pyogrio`/OpenFileGDB.
- **Automatic layer discovery**: drop a folder into `data_layers/` and it's auto-loaded as a layer — no manual configuration.
- **Offline raster basemaps**: any XYZ tile folder placed in `raster_data/` is auto-detected (zoom levels, tile extension) and made switchable from the map's layer control.
- **Mixed geometry handling**: tables containing both spatial and non-spatial rows (common in real-world `.gdb` exports) are automatically split into separate spatial/table layers.
- **Attribute search**:
  - General spatial search (press Enter → highlights match, pans map, opens popup)
  - Live-filtering search by name / ID / camp
  - Family-name search (matches the last word of a person's full name)
- **Interactive field mapping**: map arbitrary column names (person name, ID, camp) per table layer directly from the sidebar, with auto-detected defaults.
- **Table ↔ spatial linking**: clicking a person record opens a query panel and pans the map to their linked location.
- **Clear error handling**: layers or basemaps that fail to load (unsupported raster format, corrupt file, etc.) show a dismissable error banner instead of failing silently.

---

## Tech Stack

**Backend**: Python, FastAPI, Uvicorn, GeoPandas, pyogrio, Shapely, Pydantic

**Frontend**: HTML, CSS, JavaScript (Vanilla), Leaflet.js

---

## Project Structure
```
GIS-Local-Web-Viewer/
├── backend/              # FastAPI app: adapters, routes, models
├── frontend/             # Leaflet map UI (HTML/CSS/JS)
├── services/             # Helper services
├── data_layers/          # GIS layers, auto-loaded (each subfolder = one layer)
├── raster_data/          # Offline basemap tiles, auto-loaded (each subfolder = one basemap)
├── uploads/              # Files uploaded manually via the UI
└── requirements.txt
```

---

## Running Locally

```bash
# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn backend.main:app --reload
```

Then open your browser at: `http://127.0.0.1:8000`

---

## Screenshots

_Coming soon._

---

## Version 1 Scope & Limitations

By design, this version does not include:

- User authentication / accounts
- A database (PostgreSQL/PostGIS)
- WebSocket connections or real-time sync
- Drawing or feature-editing tools
- Network/multi-user deployment (local, single-user only)

See `GIS_SPEC.md` for the full Version 1 specification.

## Roadmap

- [ ] Fix cross-table name matching for spatial linking
- [ ] Persistent field-mapping configuration (currently session-only)
- [ ] Real-time polling for `data_layers/` updates
- [ ] Offline street basemap tiles
- [ ] Broader multi-layer search

---

## Note

This is a volunteer project supporting humanitarian field teams. This repository does not contain any real personal data.

## License

Not yet determined.
