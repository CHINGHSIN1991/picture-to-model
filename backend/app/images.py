import io
import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import AppError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_EDGE = 4096
MAX_PIXELS = 16_000_000


@dataclass(frozen=True)
class SanitizedImage:
    content: bytes
    mime: str
    extension: str


def sanitize_image(content: bytes, filename: str, content_type: str | None) -> SanitizedImage:
    if len(content) > MAX_UPLOAD_BYTES:
        raise AppError("image_too_large", "圖片不可超過 10 MiB。", 413)
    if not content:
        raise AppError("invalid_image", "圖片是空檔案。")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise AppError("unsupported_image", "僅接受 PNG 或 JPEG 圖片。", 415)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                image_format = source.format
                # Phone JPEGs with an MPF segment (depth/thumbnail frames) open as MPO;
                # the primary frame is still a plain JPEG.
                if image_format == "MPO":
                    image_format = "JPEG"
                if image_format not in {"PNG", "JPEG"}:
                    raise AppError("unsupported_image", "圖片內容必須是 PNG 或 JPEG。", 415)
                expected = "PNG" if suffix == ".png" else "JPEG"
                mime = "image/png" if image_format == "PNG" else "image/jpeg"
                if expected != image_format or content_type not in {
                    None,
                    "application/octet-stream",
                    mime,
                }:
                    raise AppError("image_type_mismatch", "副檔名或檔案類型與圖片內容不符。", 415)
                width, height = source.size
                if max(width, height) > MAX_EDGE or width * height > MAX_PIXELS:
                    raise AppError(
                        "image_dimensions_exceeded",
                        "圖片最長邊不可超過 4096 px，總像素不可超過 16 MP。",
                    )
                if source.format != "MPO" and getattr(source, "n_frames", 1) != 1:
                    raise AppError("unsupported_image", "請上傳靜態 PNG 或 JPEG 圖片。", 415)
                source.verify()
            with Image.open(io.BytesIO(content)) as source:
                source.load()
                oriented = ImageOps.exif_transpose(source)
                has_alpha = "A" in oriented.getbands() or "transparency" in source.info
                mode = "RGBA" if image_format == "PNG" and has_alpha else "RGB"
                # A fresh pixel-only image drops EXIF, ICC, comments, and PNG text chunks.
                clean = Image.new(mode, oriented.size)
                clean.paste(oriented.convert(mode))
                output = io.BytesIO()
                options = {"quality": 95} if image_format == "JPEG" else {}
                clean.save(output, format=image_format, **options)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise AppError("image_dimensions_exceeded", "圖片像素超過安全上限。") from error
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as error:
        raise AppError("invalid_image", "圖片已損毀或無法解碼，請重新選擇。") from error
    sanitized = output.getvalue()
    if len(sanitized) > MAX_UPLOAD_BYTES:
        raise AppError("image_too_large", "移除圖片中繼資料後超過 10 MiB，請先縮小圖片。", 413)
    return SanitizedImage(sanitized, mime, "png" if image_format == "PNG" else "jpg")
