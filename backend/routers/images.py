import base64
import uuid as uuid_mod
import os
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Form
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_async_session
from db.image import Image

router = APIRouter()

EXT_TO_CONTENT_TYPE = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "heic": "image/heic",
    "heif": "image/heif",
    "svg": "image/svg+xml",
}


@router.post("/upload")
async def upload_image(
    file: Optional[UploadFile] = File(None),
    base64_image: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Upload an image and store it in the database.
    Accepts either a file upload or base64 encoded image.
    Returns the URL path to serve the image (/images/serve/{id}).
    """
    try:
        if file:
            file_data = await file.read()
            filename = file.filename or f"image_{uuid_mod.uuid4().hex[:8]}.jpg"

            content_type = (file.content_type or "").strip().lower()
            ext = os.path.splitext(filename)[1].lower().lstrip(".")
            allowed_exts = {"jpg", "jpeg", "png", "gif", "webp", "heic", "heif"}
            if content_type and not content_type.startswith("image/"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")
            if (not content_type or content_type == "application/octet-stream") and ext and ext not in allowed_exts:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image")

            if len(file_data) < 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image file appears to be corrupted or too small",
                )
            if len(file_data) > 25 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image size must be less than 25MB",
                )

            if not content_type or content_type == "application/octet-stream":
                content_type = EXT_TO_CONTENT_TYPE.get(ext, "image/jpeg")

            image_id = uuid_mod.uuid4()
            img = Image(id=image_id, data=file_data, content_type=content_type)
            db.add(img)
            await db.commit()

            return JSONResponse(content={
                "url": f"/images/serve/{image_id}",
                "id": str(image_id),
                "name": filename,
            })

        elif base64_image:
            content_type = "image/jpeg"
            if "," in base64_image:
                prefix, b64_payload = base64_image.split(",", 1)
                base64_image = b64_payload
                if prefix.startswith("data:") and ";" in prefix:
                    content_type = prefix.split(";")[0].replace("data:", "").strip() or content_type
            file_data = base64.b64decode(base64_image)
            if len(file_data) < 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image file appears to be corrupted or too small",
                )
            if len(file_data) > 25 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image size must be less than 25MB",
                )

            filename = f"image_{uuid_mod.uuid4().hex[:8]}.jpg"
            image_id = uuid_mod.uuid4()
            img = Image(id=image_id, data=file_data, content_type=content_type)
            db.add(img)
            await db.commit()

            return JSONResponse(content={
                "url": f"/images/serve/{image_id}",
                "id": str(image_id),
                "name": filename,
            })

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'file' or 'base64_image' must be provided",
            )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}",
        )


@router.get("/serve/{image_id}", response_class=Response)
async def serve_image(
    image_id: UUID,
    db: AsyncSession = Depends(get_async_session),
):
    """Serve image binary by id. No auth required so img src works."""
    result = await db.execute(select(Image).where(Image.id == image_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return Response(content=bytes(row.data), media_type=row.content_type)
