"""
Main Application Entry Point
==============================
Creates the FastAPI application and registers all routes.

Run from the project root with:
    uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routes.upload import router as upload_router
from backend.routes.data_layers import router as data_layers_router
from backend.routes.raster_layers import router as raster_layers_router

app = FastAPI(
    title="GIS Local Web Viewer",
    description="A lightweight local web app for visualizing GIS data.",
    version="1.0.0",
)

app.include_router(upload_router)
app.include_router(data_layers_router)
app.include_router(raster_layers_router)


@app.get("/api/health")
def read_root():
    """Simple health check endpoint."""
    return {"status": "GIS Local Web Viewer backend is running."}



# Serve static files for raster data -map-
app.mount("/raster_data", StaticFiles(directory="raster_data"), name="raster_data")

# لازم يضل آخر شي مسجل بالتطبيق — بيسرف ملفات الفرونت إند
# وبيرجع index.html تلقائياً لأي مسار مش API
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")