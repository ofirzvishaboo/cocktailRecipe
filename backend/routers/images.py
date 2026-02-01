from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form
from fastapi.responses import JSONResponse
from typing import Optional
from core.imagekit_client import upload_image_to_imagekit, upload_base64_to_imagekit
import uuid
import os

router = APIRouter()


@router.post("/upload")
async def upload_image(
    file: Optional[UploadFile] = File(None),
    base64_image: Optional[str] = Form(None)
):
    """
    Upload an image to ImageKit.
    Accepts either a file upload or base64 encoded image.
    Returns the ImageKit URL.
    """
    try:
        if file:
            # Handle file upload
            file_data = await file.read()
            filename = file.filename or f"image_{uuid.uuid4().hex[:8]}.jpg"

            # Validate file type.
            # Note: some iPhone/Safari uploads may come with empty/odd content_type.
            content_type = (file.content_type or "").strip().lower()
            ext = os.path.splitext(filename)[1].lower().lstrip(".")
            allowed_exts = {"jpg", "jpeg", "png", "gif", "webp", "heic", "heif"}
            if content_type and not content_type.startswith("image/"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")
            if (not content_type or content_type == "application/octet-stream") and ext and ext not in allowed_exts:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")

            # Validate file size (min 100 bytes, max 10MB)
            if len(file_data) < 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image file appears to be corrupted or too small"
                )
            if len(file_data) > 25 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image size must be less than 25MB"
                )

            # Log file size for debugging
            print(f"Uploading file: {filename}, size: {len(file_data)} bytes, type: {file.content_type}")
            result = await upload_image_to_imagekit(file_data, filename)
            print(f"Upload result: {result}")

        elif base64_image:
            # Handle base64 image
            filename = f"image_{uuid.uuid4().hex[:8]}.jpg"
            result = await upload_base64_to_imagekit(base64_image, filename)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'file' or 'base64_image' must be provided"
            )

        return JSONResponse(content={
            "url": result["url"],
            "file_id": result["file_id"],
            "name": result["name"]
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )

