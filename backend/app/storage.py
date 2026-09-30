import os
import tempfile
import warnings
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener(thumbnails=False)

MAX_FILE_BYTES = 15 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000
MAX_SIDE = 1600

upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
if not upload_dir.is_absolute():
    upload_dir = Path(__file__).resolve().parents[1] / upload_dir


def image_path(kind: str, record_id: int) -> Path:
    return upload_dir / kind / f"{record_id}.jpg"


def remove_image(kind: str, record_id: int) -> None:
    image_path(kind, record_id).unlink(missing_ok=True)


def save_image(file: UploadFile, kind: str, record_id: int) -> None:
    raw = file.file.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 15 MB or smaller")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if source.format == "EPS":
                    raise HTTPException(status_code=415, detail="EPS images cannot be uploaded. Export it from Photos as JPEG and try again")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(status_code=422, detail="Image is too large (maximum 50 megapixels)")
                image = ImageOps.exif_transpose(source)
                image.thumbnail((MAX_SIDE, MAX_SIDE))
                rgba = image.convert("RGBA")
                rgb = Image.new("RGB", rgba.size, "white")
                rgb.paste(rgba, mask=rgba.getchannel("A"))
                encoded = BytesIO()
                rgb.save(encoded, format="JPEG", quality=85, optimize=True)
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(status_code=422, detail="Image is too large (maximum 50 megapixels)") from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=422, detail="Could not read this file as a photo. Export it from Photos as JPEG and try again") from None

    destination = image_path(kind, record_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".upload-", suffix=".jpg", delete=False) as temporary:
        temporary.write(encoded.getvalue())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
