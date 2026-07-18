"""
Upload Response Model
=======================
Represents the standardized API response returned after a file upload.

This matches the "Error Response Format" and "API Models" sections of
the project specification: the API must always return a consistent
JSON structure, whether the upload succeeded or failed.
"""

from typing import Optional

from pydantic import BaseModel, Field

from backend.models.layer import LayerModel


class UploadResponseModel(BaseModel):
    """
    Standardized response returned by the upload endpoint.

    On success:
        success = True
        layer   = LayerModel (the parsed data)
        error   = None

    On failure:
        success = False
        layer   = None
        error   = "Human-readable error message."
    """

    success: bool = Field(..., description="Whether the upload/processing succeeded.")
    layer: Optional[LayerModel] = Field(
        default=None, description="Parsed layer data, present only on success."
    )
    error: Optional[str] = Field(
        default=None, description="User-friendly error message, present only on failure."
    )