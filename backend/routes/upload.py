"""
Upload Route
=============
Receives an uploaded GIS file, validates it, selects the appropriate
adapter, converts it into the Internal Data Model, and returns a
standardized JSON response.
"""

import os
import uuid

from fastapi import APIRouter, UploadFile, File

from backend.models.upload_response import UploadResponseModel
from backend.services.file_validator import validate_file
from backend.services.adapter_factory import get_adapter

router = APIRouter()

UPLOAD_DIR = "uploads"


@router.post("/upload", response_model=UploadResponseModel)
async def upload_file(file: UploadFile = File(...)) -> UploadResponseModel:
    """
    Upload a GIS file and return its parsed data as a standardized Layer.

    Flow:
        1. Save the uploaded file temporarily to disk.
        2. Validate it (existence, extension, size...).
        3. Pick the right adapter via the Adapter Factory.
        4. Read the file and convert it into the Internal Data Model.
        5. Return a consistent JSON response (success/error).
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save with a unique name to avoid collisions between uploads.
    temp_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, temp_filename)

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        validate_file(file_path)

        adapter = get_adapter(file_path)
        layer = adapter.read(file_path)

        # Use the original uploaded filename (without UUID prefix or extension)
        # instead of the temp file name, so the layer name is clean and meaningful.
        original_name = os.path.splitext(file.filename)[0]
        layer.name = original_name

        return UploadResponseModel(success=True, layer=layer, error=None)

    except ValueError as e:
        return UploadResponseModel(success=False, layer=None, error=str(e))

    except Exception:
        # Never expose internal exceptions to the user.
        return UploadResponseModel(
            success=False, layer=None, error="Failed to process uploaded file."
        )

    finally:
        # Clean up the temporary file regardless of outcome.
        if os.path.exists(file_path):
            os.remove(file_path)