# GIS Local Web Viewer

A local, offline-first web application for viewing and exploring GIS field data, built with FastAPI and Leaflet.js.

> ⚠️ **This project is a work in progress and not yet production-ready.**

---

## Overview

GIS Local Web Viewer converts GIS data files (GeoJSON, Shapefile, File Geodatabase) into an interactive web map, without any dependency on the internet or cloud services. It's designed to run entirely on a local machine (localhost) for humanitarian field data workflows.

## Current Features

- View GIS layers from multiple formats: GeoJSON, Shapefile, File Geodatabase (.gdb)
- Auto-loading of layers from the `data_layers/` folder
- Support for raster basemaps (XYZ tiles) from the `raster_data/` folder
- Live text search across layer properties
- Linking between table and spatial layers (interactive field mapping)
- Query panel for viewing details of selected features
- Clear error handling for failed layer loads

## Tech Stack

**Backend:** Python, FastAPI, Uvicorn, GeoPandas, pyogrio, Shapely, Pydantic

**Frontend:** HTML, CSS, JavaScript (Vanilla), Leaflet.js

## Project Structure

GIS_wep_app/
├── backend/          # FastAPI backend (adapters, routes, models)
├── frontend/         # User interface (Leaflet + JS)
├── services/         # Helper services
├── data_layers/       # GIS layers auto-loaded (each subfolder = one layer)
├── raster_data/       # Raster basemap layers (tiles)
├── uploads/           # Files uploaded manually via the UI
└── requirements.txt

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

## Version 1 Scope & Limitations

This version does **not** currently include:

- User authentication / accounts
- A database (PostgreSQL/PostGIS)
- WebSocket connections or real-time updates
- Drawing or editing tools
- Network deployment (local use only)

See `GIS_SPEC.md` for the full scope of Version 1.

## Note

This is a volunteer project supporting humanitarian field teams. This repository does not contain any real personal data.

## License

Not yet determined.
