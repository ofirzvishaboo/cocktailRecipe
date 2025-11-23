from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from core.config import settings
import base64
from io import BytesIO
import tempfile
import os

# Initialize ImageKit client
imagekit = ImageKit(
    public_key=settings.imagekit_public_key,
    private_key=settings.imagekit_private_key,
    url_endpoint=settings.imagekit_url_endpoint
)


async def upload_image_to_imagekit(file_data: bytes, filename: str, folder: str = "cocktails") -> dict:
    """
    Upload an image to ImageKit and return the URL.

    Args:
        file_data: Image file bytes
        filename: Name for the file
        folder: Folder path in ImageKit (default: "cocktails")

    Returns:
        dict with 'url' and 'file_id' keys
    """
    try:
        # Validate file data
        if len(file_data) < 100:
            raise ValueError(f"File data too small: {len(file_data)} bytes")

        # Create a temporary file and write the data to it
        # ImageKit SDK requires a file object opened in binary mode
        file_ext = os.path.splitext(filename)[1] or '.jpg'
        temp_file_path = None

        try:
            # Write file data to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext, mode='wb') as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name
                # Ensure data is flushed to disk
                temp_file.flush()
                os.fsync(temp_file.fileno())

            # Upload file to ImageKit using the temporary file
            upload_options = UploadFileRequestOptions(
                folder=folder,
                use_unique_file_name=True,
                is_private_file=False
            )

            # Open the file in binary read mode for ImageKit
            # The file must be opened fresh for ImageKit to read it correctly
            with open(temp_file_path, 'rb') as file_obj:
                # Verify file was written correctly
                file_obj.seek(0, os.SEEK_END)
                file_size = file_obj.tell()
                file_obj.seek(0)

                if file_size != len(file_data):
                    raise ValueError(f"Temporary file size mismatch: expected {len(file_data)} bytes, got {file_size} bytes")

                # Upload to ImageKit
                upload = imagekit.upload_file(
                    file=file_obj,
                    file_name=filename,
                    options=upload_options
                )
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    print(f"Warning: Failed to delete temporary file {temp_file_path}: {cleanup_error}")

        # Verify upload was successful
        if not upload or not upload.url:
            raise Exception("Upload returned no URL")

        # Verify the uploaded file size by checking the response
        print(f"Upload successful: URL={upload.url}, file_id={upload.file_id}, original_size={len(file_data)} bytes")

        return {
            "url": upload.url,
            "file_id": upload.file_id,
            "name": upload.name
        }
    except Exception as e:
        raise Exception(f"Failed to upload image to ImageKit: {str(e)}")


async def upload_base64_to_imagekit(base64_string: str, filename: str, folder: str = "cocktails") -> dict:
    """
    Upload a base64 encoded image to ImageKit.

    Args:
        base64_string: Base64 encoded image string (with or without data URL prefix)
        filename: Name for the file
        folder: Folder path in ImageKit (default: "cocktails")

    Returns:
        dict with 'url' and 'file_id' keys
    """
    try:
        # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
        if "," in base64_string:
            base64_string = base64_string.split(",")[1]

        # Decode base64 to bytes
        file_data = base64.b64decode(base64_string)

        return await upload_image_to_imagekit(file_data, filename, folder)
    except Exception as e:
        raise Exception(f"Failed to upload base64 image to ImageKit: {str(e)}")


async def delete_image_from_imagekit(file_id: str) -> bool:
    """
    Delete an image from ImageKit.

    Args:
        file_id: ImageKit file ID

    Returns:
        True if successful
    """
    try:
        imagekit.delete_file(file_id)
        return True
    except Exception as e:
        raise Exception(f"Failed to delete image from ImageKit: {str(e)}")

